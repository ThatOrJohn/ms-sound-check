"""USGS water data.

backfill_daily: new API waterdata.get_daily (daily mean/min/max per parameter). One-time history pull.
recent: new OGC API (api.waterdata.usgs.gov) via the dataretrieval package.
  Set API_USGS_PAT (free key from api.waterdata.usgs.gov) for higher rate limits.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..config import Region
from ..derive import salinity_from_specific_conductance

log = logging.getLogger(__name__)

PCODES = {"00095": "conductance", "00480": "salinity_raw", "00010": "water_temp", "00060": "flow", "00065": "stage"}
NODATA = -999999.0


def _usgs_number(site_id: str) -> str:
    return site_id.split("-", 1)[1]


def _to_canonical(site: dict, frame: pd.DataFrame, time_col: str) -> pd.DataFrame:
    """frame: columns [time_col, param, value] -> canonical rows for this site's vars."""
    rows = []
    want = set(site["vars"])
    if "water_temp" in want:
        t = frame[frame.param == "water_temp"]
        rows.append(t.assign(var="water_temp"))
    if "flow" in want:
        rows.append(frame[frame.param == "flow"].assign(var="flow"))
    if "stage" in want:
        rows.append(frame[frame.param == "stage"].assign(var="stage"))
    if "salinity" in want:
        if site.get("salinity_from", "conductance") == "conductance":
            c = frame[frame.param == "conductance"].copy()
            c["value"] = salinity_from_specific_conductance(c["value"].values)
            rows.append(c.assign(var="salinity"))
        else:
            rows.append(frame[frame.param == "salinity_raw"].assign(var="salinity"))
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out = out[np.isfinite(out["value"])]
    # Sanity filters: physically impossible values are sensor junk.
    bounds = {"salinity": (0, 45), "water_temp": (-2, 40), "flow": (0, 2e6), "stage": (-20, 80)}
    lo_hi = out["var"].map(bounds)
    ok = [(lo <= v <= hi) for v, (lo, hi) in zip(out["value"], lo_hi)]
    out = out[ok]
    out = out.rename(columns={time_col: "time" if time_col != "date" else "date"})
    out["site"] = site["id"]
    out["source"] = "usgs"
    return out


# ------------------------------------------------------------------ backfill
def _merge_stats(parts: dict) -> pd.DataFrame:
    """parts: {(param, stat_code): [Series by date, one per sonde]} -> [date, param, value].

    Top/bottom sondes are averaged; the daily mean is used when there is one, else the max/min midpoint.
    """
    merged = {k: pd.concat(v, axis=1).mean(axis=1) for k, v in parts.items()}
    rows = []
    for param in set(p for p, _ in merged):
        if (param, "00003") in merged:
            s = merged[(param, "00003")]
        elif (param, "00001") in merged and (param, "00002") in merged:
            s = (merged[(param, "00001")] + merged[(param, "00002")]) / 2
        else:
            continue
        s = s.dropna()
        rows.append(pd.DataFrame({"date": s.index, "param": param, "value": s.values}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "param", "value"])


def _daily_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Rows from waterdata.get_daily -> [date, param, value]."""
    parts: dict = {}
    for (pcode, stat, _), g in df.groupby(["parameter_code", "statistic_id", "time_series_id"]):
        if pcode not in PCODES:
            continue
        v = pd.to_numeric(g["value"], errors="coerce").where(lambda x: x != NODATA)
        parts.setdefault((PCODES[pcode], stat), []).append(pd.Series(v.values, index=pd.to_datetime(g["time"]).dt.normalize()))
    return _merge_stats(parts)


def backfill_daily(region: Region, start: str = "1998-01-01", end: str | None = None) -> pd.DataFrame:
    """Daily history from the new USGS API (waterdata.get_daily). API_USGS_PAT, if set, raises the rate limit."""
    from dataretrieval import waterdata
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    out = []
    for site in region.sites:
        number = _usgs_number(site["id"]) if site["source"] == "usgs" else site.get("history_usgs")
        if not number:
            continue
        log.info("usgs backfill %s (USGS %s)", site["id"], number)
        df, _ = waterdata.get_daily(monitoring_location_id=f"USGS-{number}", parameter_code=list(PCODES),
                                    time=f"{start}/{end}")
        if df is None or len(df) == 0:
            log.warning("usgs backfill: no data for %s", site["id"])
            continue
        out.append(_to_canonical(site, _daily_frame(pd.DataFrame(df)), "date"))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


# ------------------------------------------------------------------ recent
def recent(region: Region, days: int = 7) -> pd.DataFrame:
    """Last N days of continuous (15-min) values from the new USGS API."""
    from dataretrieval import waterdata

    sites = [s for s in region.sites_by(source="usgs") if not s.get("retired")]
    df, _ = waterdata.get_continuous(
        monitoring_location_id=[s["id"] for s in sites],
        parameter_code=list(PCODES),
        time=f"P{days}D",
    )
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(df)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["param"] = df["parameter_code"].map(PCODES)
    out = []
    for site in sites:
        g = df[df["monitoring_location_id"] == site["id"]]
        if g.empty:
            log.warning("usgs recent: no data for %s", site["id"])
            continue
        # Several sondes (top/bottom) share a parameter: average per timestamp.
        g = g.groupby(["time", "param"], as_index=False)["value"].mean()
        out.append(_to_canonical(site, g, "time"))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
