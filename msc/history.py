"""Every year on record: shared rules for the salinity history picture, "in the record" findings and
"years like this one" (docs/decisions/0028).

- Measured readings only. The daily store never holds virtual-sensor estimates; readings `is_suspect` rejects
  (e.g. Round Island's 37 ppt) are dropped here.
- A past year with data on under MIN_COVERAGE of its days is left out of counts, ranks and matches. The current
  year always counts: it's today.
"""
from __future__ import annotations

import pandas as pd

from .indicators import is_suspect

MIN_COVERAGE = 0.8


def series(daily: pd.DataFrame, site: str, var: str, asof: pd.Timestamp) -> pd.Series:
    """Daily values up to asof, indexed by date, suspect readings removed."""
    s = daily[(daily.site == site) & (daily["var"] == var) & (daily.date <= asof)]
    s = s.drop_duplicates("date", keep="last").set_index("date")["value"].sort_index()
    return s[[not is_suspect(var, v) for v in s.values]]


def coverage(s: pd.Series) -> pd.Series:
    """Share of each calendar year's days that have a value."""
    counts = s.groupby(s.index.year).count()
    days = [366 if pd.Timestamp(y, 12, 31).dayofyear == 366 else 365 for y in counts.index]
    return counts / days


def good_years(s: pd.Series, asof: pd.Timestamp) -> list[int]:
    """Years that count: past years with enough coverage, plus the current one if it has any data."""
    cov = coverage(s)
    return [int(y) for y, c in cov.items() if c >= MIN_COVERAGE and y < asof.year] + \
           ([asof.year] if asof.year in cov.index else [])


def same_day(asof: pd.Timestamp, year: int) -> pd.Timestamp:
    """asof's calendar day in another year (Feb 29 becomes Feb 28)."""
    try:
        return asof.replace(year=year)
    except ValueError:
        return pd.Timestamp(year, 2, 28)


def window_means(s: pd.Series, asof: pd.Timestamp, days: int, min_days: int) -> dict[int, float]:
    """Mean of the `days` calendar days ending on asof's date, for each year that counts and has `min_days` of them."""
    out = {}
    for y in good_years(s, asof):
        end = same_day(asof, y)
        w = s[(s.index > end - pd.Timedelta(days=days)) & (s.index <= end)]
        if len(w) >= min_days:
            out[y] = float(w.mean())
    return out
