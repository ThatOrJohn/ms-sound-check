"""Fresh-and-hot days near the reefs (decision 0039).

A day counts when a station's daily mean salinity is under `salinity_below` and its daily mean water temperature is
above `temp_above_c`, both measured there: the pairing tied to Gulf oyster die-offs (La Peyre 2013, Rybovich 2016).
Each station is compared only with its own past years, since one by a river mouth is fresh and hot most summers.
This describes the water near the reefs; it never says anything about harvest status, which is MDMR's call.
"""
from __future__ import annotations

import pandas as pd

from ..config import Region

STALE_DAYS = 3          # the same age past which a station card hides its reading


def _run(x: pd.Series) -> tuple[int, int]:
    """Longest run of True days in a daily-indexed bool series, and the run still going on its last day."""
    groups = (~x).cumsum()
    runs = x.groupby(groups).sum()
    return int(runs.max()) if len(runs) else 0, int(runs.iloc[-1]) if len(runs) and x.iloc[-1] else 0


def station_years(daily: pd.DataFrame, site: str, asof: pd.Timestamp, cfg: dict) -> list[dict]:
    """One row per year with any readings: fresh-and-hot days, the longest run, days to `asof`'s day of year (so a
    year so far compares with the same stretch of past years), and whether the hot season was covered well enough."""
    d = daily[(daily.site == site) & daily["var"].isin(["salinity", "water_temp"]) & (daily.date <= asof)]
    if d.empty:
        return []
    p = d.pivot_table(index="date", columns="var", values="value")
    if not {"salinity", "water_temp"} <= set(p.columns):
        return []
    p.index = pd.to_datetime(p.index)
    p = p.reindex(pd.date_range(f"{p.index.min().year}-01-01", asof))
    both = p.salinity.notna() & p.water_temp.notna()
    hit = both & (p.salinity < cfg["salinity_below"]) & (p.water_temp > cfg["temp_above_c"])
    m0, m1 = cfg["season_months"]
    season = (p.index.month >= m0) & (p.index.month <= m1)
    out = []
    for y, x in hit.groupby(hit.index.year):
        b = both[x.index]
        s = season[(p.index.year == y)]
        if not b.any():
            continue
        # A season still under way needs the same share of the days it has had so far.
        need = s.sum() * cfg["min_coverage"]
        longest, now = _run(x)
        out.append({"year": int(y), "days": int(x.sum()), "run": longest, "run_now": now,
                    "to_date": int(x[x.index.dayofyear <= asof.dayofyear].sum()),
                    "complete": bool(b[s].sum() >= need)})
    return out


def _summary(years: list[dict], asof: pd.Timestamp) -> dict | None:
    """This year against the same station's past complete years, counted to the same day of the year."""
    cur = next((y for y in years if y["year"] == asof.year), None)
    past = [y for y in years if y["year"] < asof.year and y["complete"]]
    if cur is None or not past:
        return None
    vals = sorted(y["to_date"] for y in past)
    more = sum(v > cur["to_date"] for v in vals)
    last_as_many = max((y["year"] for y in past if y["to_date"] >= cur["to_date"]), default=None)
    return {"days": cur["days"], "run": cur["run"], "run_now": cur["run_now"], "complete": cur["complete"],
            "of": len(past), "more": more, "median": float(pd.Series(vals).median()),
            "last_as_many": last_as_many if cur["to_date"] > 0 else None}


def section(region: Region, daily: pd.DataFrame, asof: pd.Timestamp, suspect: set | None = None) -> dict | None:
    cfg = region.extras.get("oyster_stress")
    if not cfg:
        return None
    suspect = suspect or set()
    stations = []
    for site in region.sites:
        if site.get("retired") or not {"salinity", "water_temp"} <= set(site.get("vars", [])):
            continue
        years = station_years(daily, site["id"], asof, cfg)
        if not years:
            continue
        last = daily[(daily.site == site["id"]) & daily["var"].isin(["salinity", "water_temp"])
                     & (daily.date <= asof)].groupby("var").date.max()
        stale = len(last) < 2 or (asof - last.min()).days > STALE_DAYS
        stations.append({
            "id": site["id"], "short": site["short"], "name": site["name"],
            "since": years[0]["year"], "years": years,
            "now": None if stale else _summary(years, asof), "stale": bool(stale),
            "suspect": (site["id"], "salinity") in suspect or (site["id"], "water_temp") in suspect,
        })
    if not stations:
        return None
    return {"salinity_below": cfg["salinity_below"], "temp_above_c": cfg["temp_above_c"],
            "season_months": cfg["season_months"], "min_coverage": cfg["min_coverage"], "stations": stations}
