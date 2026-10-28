"""Normals: what's typical for each site/variable on each day of the year.

For day-of-year d we pool every year's values within +/- WINDOW days of d and
take percentiles. Rain is compared as rolling 7- and 30-day totals, since a
single day's rain is almost always zero.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Region

WINDOW = 7
PCTS = [10, 25, 50, 75, 90]
MIN_YEARS = 5


def with_rolling(daily: pd.DataFrame) -> pd.DataFrame:
    """Add rain_7d / rain_30d rolling totals (need complete coverage)."""
    rain = daily[daily["var"] == "rain"]
    extra = []
    for site, g in rain.groupby("site"):
        s = g.set_index("date")["value"].asfreq("D")
        for n in (7, 30):
            r = s.rolling(n, min_periods=n).sum().dropna()
            extra.append(pd.DataFrame({"site": site, "var": f"rain_{n}d", "date": r.index,
                                       "value": r.values, "source": "derived"}))
    return pd.concat([daily, *extra], ignore_index=True) if extra else daily


def compute(region: Region, daily: pd.DataFrame) -> pd.DataFrame:
    d = with_rolling(daily)
    d = d[d["var"] != "rain"]
    out = []
    for (site, var), g in d.groupby(["site", "var"]):
        g = g[["date", "value"]].dropna()
        if g["date"].dt.year.nunique() < MIN_YEARS:
            continue
        doy = g["date"].dt.dayofyear.clip(upper=365).values
        vals = g["value"].values
        years = g["date"].dt.year.values
        for day in range(1, 366):
            dist = np.abs(doy - day)
            dist = np.minimum(dist, 365 - dist)  # wrap around New Year
            m = dist <= WINDOW
            if m.sum() < 30:
                continue
            p = np.percentile(vals[m], PCTS)
            out.append([site, var, day, *p, len(np.unique(years[m]))])
    cols = ["site", "var", "doy"] + [f"p{p}" for p in PCTS] + ["n_years"]
    return pd.DataFrame(out, columns=cols)


def save(region: Region, normals: pd.DataFrame) -> None:
    region.data_dir.mkdir(parents=True, exist_ok=True)
    normals.to_parquet(region.data_dir / "normals.parquet", index=False)


def load(region: Region) -> pd.DataFrame:
    p = region.data_dir / "normals.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def percentile_of(value: float, row: pd.Series) -> float:
    """Rough percentile of value against a normals row (linear between bands)."""
    xs = [row[f"p{p}"] for p in PCTS]
    if value <= xs[0]:
        return 5.0 if value < xs[0] else 10.0
    if value >= xs[-1]:
        return 95.0 if value > xs[-1] else 90.0
    return float(np.interp(value, xs, PCTS))
