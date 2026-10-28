"""Rainfall (observed + forecast) from Open-Meteo. Free, no key, non-commercial.

A rain "site" is one or more points; the site value is the average across them,
which is a rough stand-in for basin rainfall.
"""
from __future__ import annotations

import numpy as np
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
        if "rain" not in site["vars"]:
            continue
        s = _get(FORECAST, site, {"past_days": past_days, "forecast_days": forecast_days})
        obs.append(_rows(site, s[s.index < today]))
        fc.append(_rows(site, s[s.index >= today]))
    cat = lambda xs: pd.concat(xs, ignore_index=True) if xs else pd.DataFrame()
    return cat(obs), cat(fc)


def backfill_daily(region: Region, start: str = "1998-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or (pd.Timestamp.today() - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    out = [_rows(site, _get(ARCHIVE, site, {"start_date": start, "end_date": end}))
           for site in region.sites_by(source="openmeteo") if "rain" in site["vars"]]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


# ---------------------------------------------------------------- wind
def _wind_rows(site: dict, js: dict) -> pd.DataFrame:
    js = js[0] if isinstance(js, list) else js
    h = js["hourly"]
    df = pd.DataFrame({"spd": h["wind_speed_10m"], "dir": h["wind_direction_10m"]},
                      index=pd.to_datetime(h["time"])).dropna()
    rad = np.radians(df["dir"])
    df["u"], df["v"] = -df.spd * np.sin(rad), -df.spd * np.cos(rad)   # direction the wind blows toward
    d = df.resample("D").agg({"u": "mean", "v": "mean", "spd": "max", "dir": "count"})
    d = d[d["dir"] >= 18]                                                # need most of the day
    out = []
    for var, col in (("wind_u", "u"), ("wind_v", "v"), ("wind_max", "spd")):
        out.append(pd.DataFrame({"site": site["id"], "var": var, "date": d.index, "value": d[col].values,
                                 "source": "openmeteo"}))
    return pd.concat(out, ignore_index=True)


def _wind_get(url: str, site: dict, params: dict):
    import requests
    lat, lon = site["points"][0]
    r = requests.get(url, timeout=300, params={"latitude": lat, "longitude": lon,
                                                "hourly": "wind_speed_10m,wind_direction_10m",
                                                "wind_speed_unit": "ms", "timezone": "America/Chicago", **params})
    r.raise_for_status()
    return r.json()


def wind_recent(region: Region, past_days: int = 10) -> pd.DataFrame:
    today = pd.Timestamp.now(tz=region.timezone).tz_localize(None).normalize()
    out = []
    for site in region.sites_by(source="openmeteo"):
        if site["kind"] != "wind":
            continue
        rows = _wind_rows(site, _wind_get(FORECAST, site, {"past_days": past_days, "forecast_days": 1}))
        out.append(rows[rows.date < today])
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def wind_backfill(region: Region, start: str = "1998-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or (pd.Timestamp.today() - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    out = [_wind_rows(site, _wind_get(ARCHIVE, site, {"start_date": start, "end_date": end}))
           for site in region.sites_by(source="openmeteo") if site["kind"] == "wind"]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
