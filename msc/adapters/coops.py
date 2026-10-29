"""Measured water level from NOAA CO-OPS (decision 0030). Free, no key.

Daily means relative to mean sea level: averaging a day cancels most of the Sound's once-a-day tide and leaves what
wind and the Gulf did to the water. Used as context for salinity step events (msc/models/steps.py), not as a card.

CO-OPS refused a fast bulk pull before (decision 0020), so the backfill asks for one year at a time with a pause.
"""
from __future__ import annotations

import time

import pandas as pd

from ..config import Region

API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
MIN_HOURLY, MIN_SIX_MIN = 20, 120    # readings a day needs before its mean counts
PAUSE_S = 4


def _get(station: str, product: str, begin: str, end: str) -> list[dict]:
    import requests
    r = requests.get(API, timeout=120, params={
        "product": product, "station": station, "begin_date": begin, "end_date": end, "datum": "MSL",
        "units": "metric", "time_zone": "lst", "format": "json", "application": "ms-sound-check"})
    r.raise_for_status()
    js = r.json()
    if "error" in js:
        if "No data was found" in js["error"].get("message", ""):
            return []
        raise RuntimeError(js["error"])
    return js.get("data", [])


def parse(site: dict, rows: list[dict], min_count: int) -> pd.DataFrame:
    """CO-OPS readings -> canonical daily rows (meters above MSL)."""
    df = pd.DataFrame(rows, columns=["t", "v"])
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df = df.dropna(subset=["v"])
    if df.empty:
        return pd.DataFrame(columns=["site", "var", "date", "value", "source"])
    g = df.groupby(pd.to_datetime(df["t"]).dt.normalize())["v"].agg(["mean", "count"])
    g = g[g["count"] >= min_count]
    return pd.DataFrame({"site": site["id"], "var": "water_level", "date": g.index,
                         "value": g["mean"].round(3).values, "source": "coops"})


def recent(region: Region, days: int = 10) -> pd.DataFrame:
    """Preliminary 6-minute water levels for the last `days` days (CO-OPS allows at most 31 per request)."""
    end = pd.Timestamp.now(tz=region.timezone)
    begin = (end - pd.Timedelta(days=days)).strftime("%Y%m%d")
    out = [parse(s, _get(s["station"], "water_level", begin, end.strftime("%Y%m%d")), MIN_SIX_MIN)
           for s in region.sites_by(source="coops")]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def backfill(region: Region, start: str = "1998-01-01") -> pd.DataFrame:
    """Verified hourly heights, one calendar year per request."""
    out = []
    today = pd.Timestamp.now(tz=region.timezone).tz_localize(None)
    for s in region.sites_by(source="coops"):
        for year in range(pd.Timestamp(start).year, today.year + 1):
            end = min(pd.Timestamp(year, 12, 31), today)
            out.append(parse(s, _get(s["station"], "hourly_height", f"{year}0101", end.strftime("%Y%m%d")), MIN_HOURLY))
            time.sleep(PAUSE_S)
    out = [df for df in out if not df.empty]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
