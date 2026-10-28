#!/usr/bin/env python3
"""
Sample data for local design work: fills the sections that only exist with live feeds
(beaches, oyster watch, fishing outlook, shrimp notices) so every part of the page can be seen and styled.

    python scripts/dev_fixtures.py apply    # write samples into data/<region>/, then: python -m msc build
    python scripts/dev_fixtures.py clear    # remove them again, then: python -m msc build

Everything written here is tagged source="fixture" (rows) or "fixture": true (snapshots), and `clear`
removes only those. The data store is local and gitignored, so nothing here can reach the live site.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msc import store                          # noqa: E402
from msc.adapters import beaches, mdmr, nws, tides   # noqa: E402
from msc.config import load_region             # noqa: E402

SNAPSHOTS = ["beaches.json", "beaches.geojson", "weather_forecast.json", "tides.json", "stage_forecast.parquet",
             "mdmr_notices.json"]


def apply(region):
    d = region.data_dir
    now = pd.Timestamp.now(tz="UTC").floor("h")
    local = pd.Timestamp.now(tz=region.timezone).normalize()

    # Beaches: 6 of the real stations, two under a bacteria advisory.
    rows = [("1", "Lakeshore Beach", "Bay St. Louis", "Hancock", -89.424, 30.2465, 0),
            ("2", "Buccaneer State Park Beach", "Waveland", "Hancock", -89.4038, 30.2606, 1),
            ("6", "Pass Christian West Beach", "Pass Christian", "Harrison", -89.27, 30.31, 1),
            ("9", "Gulfport Harbor Beach", "Gulfport", "Harrison", -89.09, 30.36, 0),
            ("13", "Biloxi Lighthouse Beach", "Biloxi", "Harrison", -88.90, 30.394, 0),
            ("20", "Pascagoula Beach East", "Pascagoula", "Jackson", -88.53, 30.345, 0)]
    st = {"features": [{"attributes": {
        "stationnumber": i, "name": n, "location": f"near {loc}", "county": c, "westend": "west end", "eastend": "east end",
        "active": 1, "sortorder": int(i), "longitude": lon, "latitude": lat, "isadvisory": adv, "isclosure": 0,
        "lastsampledate": (local - pd.Timedelta(days=2)).strftime("%m/%d/%Y 09:30:00"), "eventtype": "Enterococci",
        "advisorydesc": "Enterococci above the EPA standard" if adv else None, "closuredesc": None,
        "startdate": (local - pd.Timedelta(days=3)).strftime("%m/%d/%Y 12:00:00") if adv else None}} for i, n, loc, c, lon, lat, adv in rows]}
    seg = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "stationnumber": i, "name": n, "active": 1, "isadvisory": adv, "isclosure": 0},
        "geometry": {"type": "LineString", "coordinates": [[lon - 0.02, lat - 0.003], [lon + 0.02, lat + 0.003]]}}
        for i, n, loc, c, lon, lat, adv in rows]}
    data = beaches.normalize(st, seg)
    data.update({"fetched_at": now.isoformat(), "source": "MDEQ Beach Monitoring Program (sample data)", "fixture": True})
    beaches.save(region, data)

    # River stage at PERL1: rising, forecast to crest just over 10 ft.
    t = pd.date_range(now - pd.Timedelta(days=5), now, freq="15min")
    obs = pd.DataFrame({"site": "NWS-PERL1", "var": "stage", "time": t,
                        "value": 6.0 + 3.4 * (np.arange(len(t)) / len(t)) ** 1.5, "source": "fixture"})
    store.write_recent(region, obs)
    store.upsert_daily(region, store.recent_to_daily(region, obs))
    ft = pd.date_range(now + pd.Timedelta(hours=6), periods=24, freq="6h")
    peak = np.r_[np.linspace(9.5, 10.4, 12), np.linspace(10.35, 9.6, 12)]
    pd.DataFrame({"site": "NWS-PERL1", "var": "stage", "time": ft, "value": peak, "source": "fixture",
                  "issued": now}).to_parquet(d / "stage_forecast.parquet", index=False)

    # NWS forecast and tides for the next 5 days.
    periods, preds = [], []
    winds = [(5, 10, "SE", "Sunny", 5), (10, 15, "S", "Mostly Sunny", 10), (15, 20, "N", "Chance Showers", 40),
             (5, 10, "NE", "Sunny", 0), (10, 15, "E", "Partly Sunny", 20)]
    for k, (lo, hi, dr, sky, pop) in enumerate(winds):
        day = local + pd.Timedelta(days=k)
        periods.append({"name": day.strftime("%A"), "startTime": (day + pd.Timedelta(hours=6)).isoformat(),
                        "endTime": (day + pd.Timedelta(hours=18)).isoformat(), "isDaytime": True, "temperature": 74 - k,
                        "windSpeed": f"{lo} to {hi} mph", "windDirection": dr, "shortForecast": sky,
                        "probabilityOfPrecipitation": {"value": pop}})
        periods.append({"name": day.strftime("%A") + " Night", "startTime": (day + pd.Timedelta(hours=18)).isoformat(),
                        "endTime": (day + pd.Timedelta(hours=30)).isoformat(), "isDaytime": False, "temperature": 62 - k,
                        "windSpeed": f"{max(0, lo - 5)} to {hi - 5} mph", "windDirection": dr, "shortForecast": "Clear",
                        "probabilityOfPrecipitation": {"value": pop // 2}})
        for sid in ("8747437", "8745557", "8741533"):
            preds.append({"station": sid, "name": {"8747437": "Bay Waveland Yacht Club", "8745557": "Gulfport Harbor",
                                                   "8741533": "Pascagoula NOAA Lab"}[sid],
                          "time": (day + pd.Timedelta(hours=4, minutes=10 + 40 * k)).strftime("%Y-%m-%d %H:%M"), "type": "high", "ft": 1.6})
            preds.append({"station": sid, "name": preds[-1]["name"],
                          "time": (day + pd.Timedelta(hours=17, minutes=30 + 40 * k)).strftime("%Y-%m-%d %H:%M"), "type": "low", "ft": 0.2})
    nws.save_forecast(region, nws.parse_forecast(region.site("NWS-KGPT"), {"properties": {"periods": periods}}))
    tides.save(region, preds)
    # MDMR shrimp notices: one from today (leads the Shrimp headline) and an older one.
    mdmr.save(region, {"fetched_at": now.isoformat(), "source": "MDMR (sample data)", "topics": {"shrimp": [
        {"id": 1, "date": local.strftime("%Y-%m-%d"), "title": "Shrimp season to close north of ICW on January 1",
         "summary": "Sample notice: all waters north of the Intracoastal Waterway will close at 12:01 a.m. Jan. 1, as provided by law.",
         "link": "https://dmr.ms.gov/shrimp/"},
        {"id": 2, "date": (local - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
         "title": "Certain waters for commercial and recreational shrimping to open, re-establish shrimping line",
         "summary": "Sample notice: in addition to waters previously opened, waters south and west of a line in Biloxi Bay open.",
         "link": "https://dmr.ms.gov/shrimp/"}]}})
    for name in ("beaches.json", "weather_forecast.json", "tides.json", "mdmr_notices.json"):
        p = d / name
        js = json.loads(p.read_text())
        js["fixture"] = True
        p.write_text(json.dumps(js))
    print("Sample data written. Now: python -m msc build")


def clear(region):
    d = region.data_dir
    removed = []
    for name in SNAPSHOTS:
        p = d / name
        if not p.exists():
            continue
        is_fixture = (name.endswith(".parquet") and (pd.read_parquet(p).get("source") == "fixture").all()) or \
                     (name.endswith(".json") and json.loads(p.read_text()).get("fixture")) or \
                     (name == "beaches.geojson" and (d / "beaches.json").exists() is False)
        if name == "beaches.geojson":
            is_fixture = not (d / "beaches.json").exists()
        if is_fixture:
            p.unlink()
            removed.append(name)
    rec = store.read_recent(region)
    if len(rec):
        rec[rec.source != "fixture"].to_parquet(d / "recent.parquet", index=False)
    for f in sorted((d / "daily").glob("*.parquet")):
        df = pd.read_parquet(f)
        df[df.source != "fixture"].to_parquet(f, index=False)
    hist = d / "beach_history.parquet"
    print("Removed:", ", ".join(removed) or "nothing", "(plus fixture rows in recent/daily). Now: python -m msc build")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    region = load_region(sys.argv[2] if len(sys.argv) > 2 else "ms")
    {"apply": apply, "clear": clear}.get(cmd, lambda r: print(__doc__))(region)
