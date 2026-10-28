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
BEFORE_DAYS = 30                    # "before" = median salinity in the month before an opening
AFTER_DAYS = 14                     # the low is looked for until two weeks after it closed
MIN_DAYS = 10                       # need this many daily values on each side to say anything
EFFECTS = 3                         # most recent openings to describe


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


def effects(daily: pd.DataFrame, site: str, opens: list[dict], asof: pd.Timestamp) -> list[dict]:
    """Salinity at `site` before each opening and its low during (and just after) it, newest first."""
    s = daily[(daily.site == site) & (daily["var"] == "salinity")].drop_duplicates("date").set_index("date").value.sort_index()
    out = []
    for o in reversed(opens):
        start = pd.Timestamp(o["opened"])
        end = min(start + pd.Timedelta(days=(o["days"] or (asof - start).days) + AFTER_DAYS), asof)
        before = s[start - pd.Timedelta(days=BEFORE_DAYS):start - pd.Timedelta(days=1)]
        during = s[start:end]
        if len(before) < MIN_DAYS or len(during) < MIN_DAYS:
            continue
        out.append({"opened": o["opened"], "year": o["year"], "days": o["days"], "before": round(float(before.median()), 1),
                    "low": round(float(during.min()), 1), "low_date": during.idxmin().strftime("%Y-%m-%d")})
        if len(out) == EFFECTS:
            break
    return out


def section(region: Region, daily: pd.DataFrame, asof: pd.Timestamp) -> dict | None:
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
        "effects": effects(daily, cfg["sound_site"], opens, asof),
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
