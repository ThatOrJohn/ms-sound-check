"""Oyster closure watch: MDMR's published criteria for conditionally approved areas (decision 0012).

Compares the Pearl River stage at PERL1 (observed and NWS forecast) and recent rainfall with the plan's
thresholds per area group. Wording only ever says what the criteria indicate; MDMR decides closures.
"""
from __future__ import annotations

import pandas as pd

from .. import store
from ..config import Region
from ..snapshots import read_parquet

NEAR_FT = 2.0
MM_PER_IN = 25.4
NOTICE_DAYS = 365      # MDMR oyster notices older than this drop off the list
HEADLINE_DAYS = 7      # a notice this recent leads the Oysters headline
MIN_HISTORY_DAYS = 365 * 5     # don't describe "a typical year" from less than five years of readings
PEAK_SHARE = 0.75              # a month is "peak" if it's within 75% of the busiest month's share of days


def _cfg(region: Region) -> dict | None:
    return next((c for c in region.indicators if c.get("fn") == "msc.models.oyster:closure_watch"), None)


def _areas(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def history(daily: pd.DataFrame, gid: str, thresholds: list[float], asof: pd.Timestamp) -> dict[float, dict]:
    """How often the gauge's daily stage has reached each threshold, from complete years before this one.

    Daily values are USGS daily means, so these counts run a little under what peak readings would show.
    """
    s = daily[(daily.site == gid) & (daily["var"] == "stage") & (daily.date.dt.year < asof.year)]
    s = s.drop_duplicates("date").set_index("date").value.sort_index()
    if s.index.nunique() < MIN_HISTORY_DAYS:
        return {}
    s = s.reindex(pd.date_range(s.index.min(), s.index.max()))
    seen, years = s.notna(), s.notna().sum() / 365
    out = {}
    for thr in thresholds:
        over = (s >= thr) & seen
        month = (over.groupby(s.index.month).sum() / seen.groupby(s.index.month).sum()).fillna(0)
        peak = [m for m in range(1, 13) if month[m] >= PEAK_SHARE * month.max()]
        out[thr] = {
            "since": int(s.index.min().year), "days_per_year": int(round(over.sum() / years / 5) * 5),
            "rises_per_year": round(float((over & ~over.shift(fill_value=False)).sum() / years), 1),
            "peak_months": [peak[0], peak[-1]] if peak == list(range(peak[0], peak[-1] + 1)) else peak,
            "month": int(asof.month), "this_month_pct": int(round(month[asof.month] * 100)),
        }
    return out


def _notices(region: Region, asof: pd.Timestamp) -> dict:
    """MDMR's own oyster season notices and season page, repeated as published (openings, closures, area changes)."""
    from ..adapters import mdmr
    m = mdmr.recent(region, "oyster", asof, NOTICE_DAYS)
    # MDMR's season page: its season text, orders and no-harvest days, quoted (decision 0044)
    return {"notices": m["notices"], "notices_available": m["available"], "notices_link": m["link"],
            "season": mdmr.page(region, "oyster_season")}


def headline(sec, asof) -> str | None:
    """A notice from the past week leads: MDMR's word beats anything we infer from the river."""
    from ..adapters import mdmr
    return mdmr.headline(sec.get("notices"), asof, HEADLINE_DAYS) if sec else None


def section(region: Region, daily: pd.DataFrame, asof: pd.Timestamp) -> dict | None:
    cfg = _cfg(region)
    if not cfg:
        return None
    notices = _notices(region, asof)
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
                "status_url": cfg.get("status_url"), "hotline": cfg.get("hotline"), **notices}
    stale = time is not None and (now - pd.Timestamp(time).tz_convert("UTC")) > pd.Timedelta(hours=36)

    fc_path = region.data_dir / "stage_forecast.parquet"
    fc = read_parquet(fc_path, ["site", "time", "value"])
    fc = fc if fc is not None else pd.DataFrame()
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

    hist = history(daily, gid, sorted({float(g["stage_ft"]) for g in cfg["groups"]}), asof)
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
                       "rain_in": g.get("rain_in"), "rain_triggered": rain_hits, "history": hist.get(thr)})
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
        "status_url": cfg.get("status_url"), "hotline": cfg.get("hotline"), **notices,
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
