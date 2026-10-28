"""Rainfall (observed + forecast) from Open-Meteo. Free, no key, non-commercial.

A rain "site" is one or more points; the site value is the average across them,
which is a rough stand-in for basin rainfall.
"""
from __future__ import annotations

import pandas as pd

from ..config import Region

FORECAST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def _get(url: str, site: dict, params: dict) -> pd.Series:
    import requests
    lats = ",".join(str(p[0]) for p in site["points"])
    lons = ",".join(str(p[1]) for p in site["points"])
    r = requests.get(url, timeout=60, params={
        "latitude": lats, "longitude": lons, "daily": "precipitation_sum",
        "timezone": "America/Chicago", **params})
    r.raise_for_status()
    js = r.json()
    js = js if isinstance(js, list) else [js]
    series = [pd.Series(j["daily"]["precipitation_sum"], index=pd.to_datetime(j["daily"]["time"]),
                        dtype=float) for j in js]
    return pd.concat(series, axis=1).mean(axis=1)


def _rows(site: dict, s: pd.Series) -> pd.DataFrame:
    s = s.dropna()
    return pd.DataFrame({"site": site["id"], "var": "rain", "date": s.index,
                         "value": s.values, "source": "openmeteo"})


def recent_and_forecast(region: Region, past_days: int = 10, forecast_days: int = 7):
    """Returns (observed daily rows, forecast daily rows)."""
    obs, fc = [], []
    today = pd.Timestamp.now(tz=region.timezone).tz_localize(None).normalize()
    for site in region.sites_by(source="openmeteo"):
        s = _get(FORECAST, site, {"past_days": past_days, "forecast_days": forecast_days})
        obs.append(_rows(site, s[s.index < today]))
        fc.append(_rows(site, s[s.index >= today]))
    cat = lambda xs: pd.concat(xs, ignore_index=True) if xs else pd.DataFrame()
    return cat(obs), cat(fc)


def backfill_daily(region: Region, start: str = "1998-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or (pd.Timestamp.today() - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    out = [_rows(site, _get(ARCHIVE, site, {"start_date": start, "end_date": end}))
           for site in region.sites_by(source="openmeteo")]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
