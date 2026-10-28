"""Oyster closure watch: MDMR's published criteria for conditionally approved areas (decision 0012).

Compares the Pearl River stage at PERL1 (observed and NWS forecast) and recent rainfall with the plan's
thresholds per area group. Wording only ever says what the criteria indicate; MDMR decides closures.
"""
from __future__ import annotations

import pandas as pd

from .. import store
from ..config import Region

NEAR_FT = 2.0
MM_PER_IN = 25.4


def _cfg(region: Region) -> dict | None:
    return next((c for c in region.indicators if c.get("fn") == "msc.models.oyster:closure_watch"), None)


def _areas(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def section(region: Region, daily: pd.DataFrame, asof: pd.Timestamp) -> dict | None:
    cfg = _cfg(region)
    if not cfg:
        return None
    gid = cfg["gauge"]
    gauge = region.site(gid)
    now = pd.Timestamp.now(tz="UTC")

    rec = store.read_recent(region)
    rec = rec[(rec.site == gid) & (rec["var"] == "stage")].sort_values("time")
    stage = time = change = None
    if len(rec):
        stage, time = float(rec.value.iloc[-1]), rec.time.iloc[-1]
        prior = rec[rec.time <= time - pd.Timedelta(hours=24)]
        if len(prior):
            change = round(stage - float(prior.value.iloc[-1]), 2)
    else:   # fall back to the daily maximum
        d = daily[(daily.site == gid) & (daily["var"] == "stage") & (daily.date <= asof)].sort_values("date")
        if len(d):
            stage, time = float(d.value.iloc[-1]), pd.Timestamp(d.date.iloc[-1]).tz_localize(region.timezone)
    if stage is None:
        return {"available": False, "plan_name": cfg["plan_name"], "plan_url": cfg["plan_url"],
                "status_url": cfg.get("status_url"), "hotline": cfg.get("hotline")}
    stale = time is not None and (now - pd.Timestamp(time).tz_convert("UTC")) > pd.Timedelta(hours=36)

    fc_path = region.data_dir / "stage_forecast.parquet"
    fc = pd.read_parquet(fc_path) if fc_path.exists() else pd.DataFrame()
    if len(fc):
        fc = fc[(fc.site == gid)].copy()
        fc["time"] = pd.to_datetime(fc["time"], utc=True)
        fc = fc[fc.time > now].sort_values("time")
    fmax = fmax_time = None
    if len(fc):
        i = fc.value.idxmax()
        fmax, fmax_time = float(fc.value[i]), fc.time[i]

    rain_site = cfg.get("rain_site")
    rain_in = None
    if rain_site:
        r = daily[(daily.site == rain_site) & (daily["var"] == "rain") & (daily.date < asof)].sort_values("date")
        if len(r) and (asof - r.date.iloc[-1]).days <= 2:
            rain_in = round(float(r.value.iloc[-1]) / MM_PER_IN, 2)

    groups = []
    for g in cfg["groups"]:
        thr = float(g["stage_ft"])
        crossing = None
        if len(fc):
            over = fc[fc.value >= thr]
            if len(over):
                crossing = over.time.iloc[0]
        status = ("above" if stage >= thr else "forecast" if crossing is not None
                  else "near" if stage >= thr - NEAR_FT else "clear")
        rain_hits = [a for a, t in (g.get("rain_in") or {}).items() if rain_in is not None and rain_in >= t]
        groups.append({"areas": g["areas"], "names": g.get("names"), "stage_ft": thr, "status": status,
                       "crossing_time": crossing.isoformat() if crossing is not None else None,
                       "rain_in": g.get("rain_in"), "rain_triggered": rain_hits})
    return {
        "available": True, "stale": bool(stale),
        "gauge": {"id": gid, "name": gauge["name"], "lid": gauge.get("nws_lid"), "stage": round(stage, 2),
                  "time": pd.Timestamp(time).isoformat(), "change_24h": change},
        "forecast": {"points": [[t.isoformat(), round(float(v), 2)] for t, v in zip(fc.time, fc.value)] if len(fc) else [],
                     "max": round(fmax, 2) if fmax is not None else None,
                     "max_time": fmax_time.isoformat() if fmax_time is not None else None},
        "rain": {"site": rain_site, "yesterday_in": rain_in, "approximate": True},
        "groups": groups,
        "plan_name": cfg["plan_name"], "plan_url": cfg["plan_url"],
        "status_url": cfg.get("status_url"), "hotline": cfg.get("hotline"),
    }


def closure_watch(region, cfg, daily, normals, asof):
    sec = section(region, daily, asof)
    if not sec or not sec.get("available") or sec.get("stale"):
        return []
    g0, out = sec["gauge"], []
    for g in sec["groups"]:
        where = f"Areas {_areas(g['areas'])}"
        if g["status"] == "above":
            out.append({"severity": "warning", "text":
                f"The Pearl River near Pearl River, LA is at {g0['stage']:.1f} ft, above the {g['stage_ft']:.0f}-ft level "
                f"where MDMR's management plan closes {where} to oyster harvest. Check MDMR for current status."})
        elif g["status"] == "forecast":
            when = pd.Timestamp(g["crossing_time"]).tz_convert(region.timezone).strftime("%A, %B %-d")
            out.append({"severity": "watch", "text":
                f"The Pearl River near Pearl River, LA is forecast to pass {g['stage_ft']:.0f} ft by {when}, "
                f"the level where MDMR's management plan closes {where} to oyster harvest."})
        if g["rain_triggered"]:
            r = sec["rain"]["yesterday_in"]
            out.append({"severity": "watch", "text":
                f"About {r:.1f} in of rain fell in Hancock County yesterday, at or above MDMR's rainfall criterion for "
                f"Areas {_areas(g['rain_triggered'])}. (Our rain figure is an estimate; MDMR uses its own gauge.)"})
    for f in out:
        f.update({"indicator": cfg["id"], "site": cfg["gauge"], "topics": cfg.get("topics", []), "var": "stage"})
    return out
