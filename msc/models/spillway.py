"""Bonnet Carré Spillway watch (decision 0022).

The Corps opens the spillway when the Mississippi at New Orleans nears 1.25 million cfs, about 17 ft at Carrollton.
No public feed says live whether it's open, so this compares the river's stage and NWS forecast with that level, and
reads past openings from a hand-kept CSV. It also shows what our own Sound station did during past openings: rivers
were often high at the same time, so that's what the Sound did, not what the spillway alone caused.
"""
from __future__ import annotations

import pandas as pd

from ..config import REFERENCE, Region

STALE = pd.Timedelta(days=2)       # river readings older than this are hidden, not shown
LEAD_DAYS = 28                      # each past-opening chart starts 4 weeks before the first opening of its year
SPAN_DAYS = 196                     # ...and runs 28 weeks after it, the same for every year so they compare (0038)
MIN_BEFORE, MIN_AFTER = 10, 60      # daily values needed before / after the opening to draw a year
FRESH_PPT = 2.0                     # the oyster_fresh_stress threshold; longest run under it is in the sentence
SINCE_YEAR = 2000


def openings(region: Region) -> list[dict]:
    cfg = region.extras.get("spillway") or {}
    p = REFERENCE / cfg.get("openings", "spillway_openings.csv")
    if not p.exists():
        return []
    df = pd.read_csv(p, comment="#", parse_dates=["opened"])
    out = []
    for r in df.itertuples():
        days = None if pd.isna(r.days) else int(r.days)
        out.append({"opened": r.opened.strftime("%Y-%m-%d"), "year": int(r.opened.year), "days": days,
                    "closed": (r.opened + pd.Timedelta(days=days)).strftime("%Y-%m-%d") if days else None,
                    "max_bays": None if pd.isna(r.max_bays) else int(r.max_bays),
                    "peak_cfs": None if pd.isna(r.peak_cfs) else int(r.peak_cfs)})
    return out


def _longest_run(s: pd.Series, below: float) -> tuple[int, pd.Timestamp | None]:
    """Longest run of consecutive calendar days under `below`, and the day it started. A missing day ends a run."""
    best, start, run, first, prev = 0, None, 0, None, None
    for d, v in s.items():
        if v < below and prev is not None and run and d - prev == pd.Timedelta(days=1):
            run += 1
        elif v < below:
            run, first = 1, d
        else:
            run = 0
        if run > best:
            best, start = run, first
        prev = d
    return best, start


def past(daily: pd.DataFrame, normals: pd.DataFrame | None, site: str, opens: list[dict], asof: pd.Timestamp) -> list[dict]:
    """What `site` did around each year's openings since 2000, on the same day axis (days since the year's first
    opening), with that time of year's typical salinity beside it. Past openings side by side, not a forecast (0008)."""
    s = daily[(daily.site == site) & (daily["var"] == "salinity")].drop_duplicates("date").set_index("date").value.sort_index()
    s.index = pd.to_datetime(s.index)
    typ = None
    if normals is not None and not normals.empty:
        n = normals[(normals.site == site) & (normals["var"] == "salinity")]
        typ = dict(zip(n.doy, n.p50)) if len(n) else None
    years: dict[int, list[dict]] = {}
    for o in opens:
        if o["year"] >= SINCE_YEAR:
            years.setdefault(o["year"], []).append(o)
    out = []
    for year, os in sorted(years.items()):
        t0 = pd.Timestamp(os[0]["opened"])
        win = s[t0 - pd.Timedelta(days=LEAD_DAYS):min(t0 + pd.Timedelta(days=SPAN_DAYS), asof)]
        before, after = win[:t0 - pd.Timedelta(days=1)], win[t0:]
        if len(before) < MIN_BEFORE or len(after) < MIN_AFTER:
            continue
        off = lambda d: int((d - t0).days)
        run, run_start = _longest_run(after, FRESH_PPT)
        days = range(-LEAD_DAYS, SPAN_DAYS + 1, 3)
        out.append({
            "year": year,
            "opened": [o["opened"] for o in os],
            "bands": [[off(pd.Timestamp(o["opened"])), off(pd.Timestamp(o["opened"])) + (o["days"] or off(asof))] for o in os],
            "days_open": sum(o["days"] or 0 for o in os),
            "series": [[off(d), round(float(v), 1)] for d, v in win.items()],
            "typical": [[d, round(float(typ[k]), 1)] for d in days
                        if typ and (k := min((t0 + pd.Timedelta(days=d)).dayofyear, 365)) in typ],
            "before": round(float(before.median()), 1),
            "low": round(float(after.min()), 1), "low_day": off(after.idxmin()),
            "fresh_run": run, "fresh_run_day": off(run_start) if run_start is not None else None,
        })
    return out


def section(region: Region, daily: pd.DataFrame, asof: pd.Timestamp, normals: pd.DataFrame | None = None) -> dict | None:
    cfg = region.extras.get("spillway")
    if not cfg:
        return None
    from ..adapters import spillway as src
    opens = openings(region)
    open_now = next((o for o in reversed(opens) if o["days"] is None), None)
    sec = {
        "gauge_name": cfg["gauge_name"], "open_ft": cfg["open_ft"], "watch_ft": cfg["watch_ft"], "link": cfg.get("link"),
        "openings": opens, "open_now": open_now,
        "count": len(opens), "since": opens[0]["year"] if opens else None,
        "since_2000": sum(o["year"] >= 2000 for o in opens),
        "past": past(daily, normals, cfg["sound_site"], opens, asof), "fresh_ppt": FRESH_PPT,
        "sound_site": next((s["short"] for s in region.sites if s["id"] == cfg["sound_site"]), cfg["sound_site"]),
        "river": None,
    }
    snap = src.load(region)
    now = pd.Timestamp.now(tz="UTC")
    if not snap or not snap.get("observed") or now - pd.Timestamp(snap["fetched_at"]) > STALE:
        return sec
    obs = [(pd.Timestamp(t), v) for t, v in snap["observed"]]
    t_last, stage = obs[-1]
    if now - t_last > STALE:
        return sec
    prior = [v for t, v in obs if t <= t_last - pd.Timedelta(hours=24)]
    fc = [(pd.Timestamp(t), v) for t, v in snap.get("forecast", []) if pd.Timestamp(t) > now]
    crest = max(fc, key=lambda x: x[1]) if fc else None
    first = lambda lvl: next((t for t, v in fc if v >= lvl), None)
    reach_open, reach_watch = first(cfg["open_ft"]), first(cfg["watch_ft"])
    status = ("open_level" if stage >= cfg["open_ft"] else "forecast_open" if reach_open is not None
              else "watch" if stage >= cfg["watch_ft"] or reach_watch is not None else "low")
    iso = lambda t: t.isoformat() if t is not None else None
    sec["river"] = {
        "stage": round(stage, 2), "time": iso(t_last), "change_24h": round(stage - prior[-1], 2) if prior else None,
        "status": status,
        "forecast": [[iso(t), v] for t, v in fc],
        "crest": round(crest[1], 2) if crest else None, "crest_time": iso(crest[0]) if crest else None,
        "reach_open_time": iso(reach_open), "reach_watch_time": iso(reach_watch),
        # last 30 days observed, thinned to one value per 6 hours for the chart
        "observed": [[iso(t), v] for t, v in obs if t.hour % 6 == 0 and t.minute == 0],
    }
    return sec


def findings(region, cfg, daily, normals, asof):
    sec = section(region, daily, asof)
    if not sec:
        return []
    out, river = [], sec["river"]
    when = lambda iso: pd.Timestamp(iso).tz_convert(region.timezone).strftime("%A, %B %-d")
    where = "the level where the Corps has opened the Bonnet Carré Spillway"
    if sec["open_now"]:
        out.append({"severity": "warning", "text":
            f"The Corps opened the Bonnet Carré Spillway on {pd.Timestamp(sec['open_now']['opened']).strftime('%B %-d')}. "
            "Its water reaches the western Sound through Lake Borgne, and the Sound turned much fresher during past openings."})
    elif river and river["status"] == "open_level":
        out.append({"severity": "warning", "text":
            f"The Mississippi at New Orleans is at {river['stage']:.1f} ft, at or above {sec['open_ft']} ft, {where}. "
            "Check the Corps for whether it's open."})
    elif river and river["status"] == "forecast_open":
        out.append({"severity": "watch", "text":
            f"The Mississippi at New Orleans is forecast to reach {sec['open_ft']} ft by {when(river['reach_open_time'])}, "
            f"{where}. When it's open, the western Sound turns fresher in the weeks after."})
    elif river and river["status"] == "watch":
        top = max(river["stage"], river["crest"] or 0)
        verb = "is at" if top == river["stage"] else "is forecast to crest near"
        out.append({"severity": "notice", "text":
            f"The Mississippi at New Orleans {verb} {top:.1f} ft, within "
            f"{sec['open_ft'] - sec['watch_ft']} ft of {sec['open_ft']} ft, {where}."})
    for f in out:
        f.update({"indicator": cfg["id"], "site": None, "topics": cfg.get("topics", []), "var": "spillway"})
    return out
