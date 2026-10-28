"""Shrimp season lean (early / normal / late) from spring water temperature.

Evidence and caveats: docs/feasibility.md ("Probe results"). In short:
warmer Mar-Apr water -> earlier MDMR opening, about 6 days per standard
deviation; typical leave-one-out miss ~6 days vs 8.5 for guessing the mean;
some years (2025) miss by weeks. Published as a lean, never a date.
"""
from __future__ import annotations

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
