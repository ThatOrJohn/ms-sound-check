"""CLI.

  python -m msc backfill  --region ms     one-time history pull (USGS + rain)
  python -m msc normals   --region ms     recompute normals from history
  python -m msc train     --region ms     retrain virtual-sensor models (QC + estimates)
  python -m msc ingest    --region ms     pull recent data from every source
  python -m msc build     --region ms     write site/data/<region>/*.json
  python -m msc run       --region ms     ingest + build (what the schedule runs)
  python -m msc check     --region ms     fail if the newest water reading is stale
  python -m msc basemap                   one-time: depth shading + contours for the map (commit the output)

Every source is independent: if one is down, the rest still update, and the
page shows that source's data as stale instead of breaking.
"""
from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from . import normals as nm
from . import store
from .build import build
from .config import load_region

log = logging.getLogger("msc")


def _try(label, fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:  # keep going; report at the end
        log.warning("%s failed: %s", label, e)
        _try.failures.append(label)
        return None
_try.failures = []


def cmd_backfill(region, args):
    from .adapters import openmeteo, usgs
    for label, fn in [("usgs backfill", usgs.backfill_daily), ("rain backfill", openmeteo.backfill_daily),
                      ("wind backfill", openmeteo.wind_backfill)]:
        df = _try(label, fn, region, start=args.start)
        if df is not None:
            log.info("%s: %d rows", label, store.upsert_daily(region, df))


def cmd_normals(region, args):
    n = nm.compute(region, store.read_daily(region))
    nm.save(region, n)
    log.info("normals: %d rows for %d site/vars", len(n), n.groupby(["site", "var"]).ngroups if len(n) else 0)


def cmd_ingest(region, args):
    from .adapters import nws, openmeteo, usgs
    recent = []
    for label, fn in [("usgs recent", usgs.recent), ("nws recent", nws.recent)]:
        df = _try(label, fn, region, days=args.days)
        if df is not None and not df.empty:
            recent.append(df)
    if recent:
        new = pd.concat(recent, ignore_index=True)
        store.write_recent(region, new)
        store.upsert_daily(region, store.recent_to_daily(region, new))
    from .adapters import nwps
    res_st = _try("river stage", nwps.recent_and_forecast, region)
    if res_st is not None:
        obs, fc = res_st
        if not obs.empty:
            store.write_recent(region, obs[["site", "var", "time", "value", "source"]])
            store.upsert_daily(region, store.recent_to_daily(region, obs[["site", "var", "time", "value", "source"]]))
        region.data_dir.mkdir(parents=True, exist_ok=True)
        fc.to_parquet(region.data_dir / "stage_forecast.parquet", index=False)
    wind = _try("wind", openmeteo.wind_recent, region)
    if wind is not None and not wind.empty:
        store.upsert_daily(region, wind)
    wx = _try("weather forecast", nws.forecast, region)
    if wx:
        nws.save_forecast(region, wx)
    from .adapters import tides
    tide_rows = _try("tides", tides.fetch, region)
    if tide_rows:
        tides.save(region, tide_rows)
    from .adapters import beaches
    snap = _try("beaches", beaches.fetch, region)
    if snap:
        beaches.save(region, snap)
    res = _try("rain", openmeteo.recent_and_forecast, region)
    if res is not None:
        obs, fc = res
        store.upsert_daily(region, obs)
        region.data_dir.mkdir(parents=True, exist_ok=True)
        fc.to_parquet(region.data_dir / "rain_forecast.parquet", index=False)


def cmd_build(region, args):
    daily = store.read_daily(region)
    normals = nm.load(region)
    if args.asof:
        asof = pd.Timestamp(args.asof)
    else:
        asof = pd.Timestamp.now(tz=region.timezone).tz_localize(None).normalize()
    fc_path = region.data_dir / "rain_forecast.parquet"
    fc = pd.read_parquet(fc_path) if fc_path.exists() else None
    latest = build(region, daily, normals, asof, fc)
    log.info("built %s: %d findings, asof %s", region.id, len(latest["findings"]), latest["asof"])


def cmd_check(region, args) -> int:
    """Health check: fail if the newest water reading is too old (the schedule or a source has stalled)."""
    import json
    import os
    from .config import SITE_OUT
    latest = json.loads((SITE_OUT / region.id / "latest.json").read_text())
    dates = [v["date"] for c in latest["cards"] if c["kind"] in ("sound", "river")
             for v in c["vars"].values() if v.get("date") and not v.get("stale")]
    newest = max(dates) if dates else None
    today = pd.Timestamp.now(tz=region.timezone).tz_localize(None).normalize()
    age = (today - pd.Timestamp(newest)).days if newest else None
    healthy = age is not None and age <= args.max_age_days
    msg = f"newest water reading {newest} ({age} days old)" if newest else "no water readings at all"
    (log.info if healthy else log.error)("health: %s", msg)
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"healthy={'true' if healthy else 'false'}\nmessage={msg}\n")
    return 0 if healthy else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="msc")
    ap.add_argument("command", choices=["backfill", "normals", "train", "ingest", "build", "run", "check", "basemap"])
    ap.add_argument("--region", default="ms")
    ap.add_argument("--start", default="1998-01-01", help="backfill start date")
    ap.add_argument("--days", type=int, default=7, help="ingest lookback days")
    ap.add_argument("--asof", help="build as of this date (testing)")
    ap.add_argument("--stride", type=int, default=1, help="basemap: take every Nth grid cell (1 = full 3 arc-second)")
    ap.add_argument("--max-age-days", type=int, default=2, help="check: oldest acceptable newest reading")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    region = load_region(args.region)
    if args.command == "train":
        from .models import virtual
        meta = virtual.train(region, store.read_daily(region))
        for sid, m in meta.items():
            log.info("virtual %-22s mae=%s (neighbors avg %s) estimate=%s", sid, m["metrics"].get("mae"),
                     m["metrics"].get("mae_neighbors_avg"), "yes" if m["publish_estimate"] else "no")
        return 0
    if args.command == "basemap":
        from .basemap import build as build_basemap
        meta = build_basemap(stride=args.stride)
        log.info("basemap written: %s px, bounds %s", meta["size"], meta["bounds"])
        return 0
    if args.command == "check":
        return cmd_check(region, args)
    if args.command == "run":
        cmd_ingest(region, args)
        cmd_build(region, args)
    else:
        {"backfill": cmd_backfill, "normals": cmd_normals,
         "ingest": cmd_ingest, "build": cmd_build}[args.command](region, args)
    if _try.failures:
        log.warning("sources that failed this run: %s", ", ".join(_try.failures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
