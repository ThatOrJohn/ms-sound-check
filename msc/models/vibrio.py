"""Vibrio-favorable water: warm and moderately salty, where Vibrio bacteria grow fastest (decision 0024).

A seasonal note, not a finding: these conditions hold on most days from April to October at every Sound
station (1998-2026), so as a Signal it would be on half the year. We compare readings to a range; we
don't measure bacteria. Nothing is said when no station is in range, because cooler water isn't "safe".
"""
from __future__ import annotations

import pandas as pd

from ..config import Region
from ..indicators import is_suspect
from ..units import fmt


def _names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def section(region: Region, daily: pd.DataFrame, asof: pd.Timestamp, suspect: set | None = None) -> dict | None:
    """None unless at least one live station averaged in range over the last `days` days.

    suspect: {(site, var)} that failed QC (virtual sensors); like the ceiling check, they're left out.
    """
    cfg = region.extras.get("vibrio")
    if not cfg:
        return None
    lo, hi = cfg["salinity"]
    days = cfg.get("days", 3)
    recent = daily[(daily.date > asof - pd.Timedelta(days=days)) & (daily.date <= asof)]
    found = []
    for site in region.sites:
        if site.get("retired") or site["kind"] not in cfg["kinds"] or (site["id"], "salinity") in (suspect or set()):
            continue
        s = recent[recent.site == site["id"]].pivot_table(index="date", columns="var", values="value")
        if not {"salinity", "water_temp"} <= set(s.columns):
            continue
        s = s[["salinity", "water_temp"]].dropna()
        if len(s) < min(2, days) or any(is_suspect("salinity", v) for v in s.salinity):
            continue
        sal, temp = s.salinity.mean(), s.water_temp.mean()
        if temp >= cfg["temp_min_c"] and lo <= sal <= hi:
            found.append({"id": site["id"], "short": site["short"], "in_text": site.get("in_text", site["short"]),
                          "salinity": fmt("salinity", sal, region.units), "water_temp": fmt("water_temp", temp, region.units)})
    if not found:
        return None
    return {
        "stations": found,
        "places": _names([f["in_text"] for f in found]),
        "temp_min": fmt("water_temp", cfg["temp_min_c"], region.units),
        "salinity_range": f"{lo}–{hi} ppt",
        "days": days,
        "season": cfg.get("season"),
        "links": cfg.get("links", []),
    }
