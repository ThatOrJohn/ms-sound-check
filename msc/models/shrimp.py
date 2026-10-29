"""Shrimp: in-season notices and wind (section), and the season lean (early / normal / late) from spring
water temperature.

Season lean evidence and caveats: docs/feasibility.md ("Probe results"). In short:
warmer Mar-Apr water -> earlier MDMR opening, about 6 days per standard
deviation; typical leave-one-out miss ~6 days vs 8.5 for guessing the mean;
some years (2025) miss by weeks. Published as a lean, never a date.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from ..config import REFERENCE

WINDOW_START = "03-01"
WINDOW_END = "04-30"


def _window_z(daily, sites, asof):
    """Per-year mean water temp from Mar 1 to min(asof, Apr 30), z-scored per site, averaged."""
    end_md = min(asof.strftime("%m-%d"), WINDOW_END)
    per_site = {}
    for site in sites:
        s = daily[(daily.site == site) & (daily["var"] == "water_temp")].set_index("date")["value"]
        means = {}
        for y in sorted(s.index.year.unique()):
            w = s[f"{y}-{WINDOW_START}":f"{y}-{end_md}"]
            if len(w) >= 0.7 * max(1, (pd.Timestamp(f"{y}-{end_md}") - pd.Timestamp(f"{y}-{WINDOW_START}")).days):
                means[y] = w.mean()
        per_site[site] = pd.Series(means)
    df = pd.DataFrame(per_site)
    z = (df - df.mean()) / df.std()
    return z.mean(axis=1, skipna=True), end_md


NOTICE_DAYS = 365      # notices older than this drop off the list
NOTICE_COUNT = 5
HEADLINE_DAYS = 7      # a notice this recent leads the Shrimp headline
WIND_DAYS = 3


def _wind_days(region, asof):
    """Today and the next two days, day and night wind from the NWS forecast. Shrimpers work both, so the
    verdict goes by the windier of the two."""
    from ..adapters import nws
    from .fishing import _verdict, wind_text
    periods = nws.load_forecast(region)
    out = []
    for i in range(WIND_DAYS):
        d = asof + pd.Timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        ps = [p for p in periods if p["start"][:10] == key]
        day = next((p for p in ps if p["is_day"]), None)
        night = next((p for p in ps if not p["is_day"]), None)
        if not ps:
            continue
        mph = max([p["wind_mph_hi"] for p in ps if p.get("wind_mph_hi") is not None], default=None)
        vkey, _ = _verdict(mph)
        out.append({"date": key, "label": "Today" if i == 0 else d.strftime("%A"),
                    "day_wind": wind_text(day), "night_wind": wind_text(night), "wind_mph_hi": mph,
                    "sky": day["short"] if day else night["short"] if night else None,
                    "rain_pct": max([p["rain_pct"] or 0 for p in ps]), "verdict": vkey})
    return out


def section(region, asof):
    """MDMR's recent shrimp notices plus a 3-day wind outlook. None if neither source has anything current."""
    from ..adapters import mdmr
    m = mdmr.recent(region, "shrimp", asof, NOTICE_DAYS, NOTICE_COUNT)
    days = _wind_days(region, asof)
    if not m["available"] and not days:
        return None
    return {"notices": m["notices"], "notices_available": m["available"], "link": m["link"], "source": m["source"],
            "days": days}


def headline(sec, asof) -> str | None:
    """A notice from the past week leads: it's the one thing a shrimper can't see from the water."""
    from ..adapters import mdmr
    return mdmr.headline(sec["notices"], asof, HEADLINE_DAYS) if sec else None


_OPENS = re.compile(r"shrimp season (?:opens|to open|will open)\b", re.I)
_DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b")


def openings_check(region) -> list[str]:
    """Compare MDMR's spring "shrimp season opens" notices with data/shrimp_openings.csv, which the season lean
    trains on. Returns one line per notice with no matching row (or a different date). Empty when they agree or
    the notices snapshot is missing or stale."""
    from ..adapters import mdmr
    notices = mdmr.load(region, "shrimp")
    if not notices:
        return []
    openings = pd.read_csv(REFERENCE / "shrimp_openings.csv", parse_dates=["open_date"])
    have = dict(zip(openings.season, openings.open_date))
    problems = []
    for n in notices:
        posted = pd.Timestamp(n["date"])
        if not _OPENS.search(n["title"]) or not 3 <= posted.month <= 8:   # the fall reopenings aren't the season
            continue
        m = _DATE.search(n["title"].split("open", 1)[-1])
        said = pd.Timestamp(f"{m.group(1)} {m.group(2)} {posted.year}") if m else None
        if posted.year not in have:
            problems.append(f"{posted.year} shrimp opening missing from shrimp_openings.csv "
                            f"(MDMR {n['date']}: {n['title']}, {n['link']})")
        elif said is not None and said != have[posted.year]:
            problems.append(f"{posted.year} shrimp opening in shrimp_openings.csv is {have[posted.year]:%Y-%m-%d}, "
                            f"MDMR said {said:%Y-%m-%d} ({n['title']}, {n['link']})")
    return problems


def season_lean(region, cfg, daily, normals, asof):
    if asof.strftime("%m-%d") < "03-15":
        return []
    openings = pd.read_csv(REFERENCE / "shrimp_openings.csv", parse_dates=["open_date"])
    openings["days"] = (openings.open_date - pd.to_datetime(openings.season.astype(str) + "-05-01")).dt.days
    target = openings.set_index("season")["days"]

    z, end_md = _window_z(daily, cfg["sites"], asof)
    if asof.year not in z.index:
        return []
    hist = pd.concat([z.drop(asof.year, errors="ignore"), target.drop(asof.year, errors="ignore")],
                     axis=1, keys=["z", "days"]).dropna()
    if len(hist) < 8:
        return []
    slope, icpt = np.polyfit(hist.z, hist.days, 1)
    zc = float(z[asof.year])
    pred = slope * zc + icpt
    lo, hi = np.percentile(hist.days, [33.3, 66.7])
    lean = "early" if pred <= lo else "late" if pred >= hi else "normal"
    warmth = "warm" if zc > 0.5 else "cool" if zc < -0.5 else "about average"
    when = (pd.Timestamp(f"{asof.year}-05-01") + pd.Timedelta(days=round(pred)))
    partial = end_md < WINDOW_END
    period = (f"so far this spring (through {pd.Timestamp(f'{asof.year}-{end_md}').strftime('%b %-d')})"
              if partial else "this spring (March-April)")
    text = (f"Water in the Sound ran {warmth} {period}. "
            f"Seasons like this have tended to open {lean if lean != 'normal' else 'near the usual time'}"
            f", around {when.strftime('%B %-d')} give or take a week. A lean, not a forecast: "
            f"MDMR sets the date from its own trawl sampling.")
    actual = openings[openings.season == asof.year]
    if not actual.empty:
        text += f" MDMR set this year's opening for {actual.open_date.iloc[0].strftime('%B %-d')}."
    return [{"indicator": cfg["id"], "site": None, "severity": "notice", "topics": cfg.get("topics", []),
             "text": text,
             "short": (f"Shrimp season leans {lean if lean != 'normal' else 'toward the usual date'}, "
                       f"around {when.strftime('%B %-d')}: spring water has been {warmth}."),
             "lean": lean, "z": round(zc, 2), "provisional": partial,
             "n_seasons": int(len(hist))}]
