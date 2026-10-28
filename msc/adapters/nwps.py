"""NWS National Water Prediction Service: observed stage and the official stage forecast.

api.water.noaa.gov/nwps/v1/gauges/<LID>/stageflow returns {"observed": {...}, "forecast": {...}}, each with
primaryName/primaryUnits and data: [{validTime, primary, secondary}]. Free, no key.
"""
from __future__ import annotations

import logging

import pandas as pd

from ..config import Region

log = logging.getLogger(__name__)
API = "https://api.water.noaa.gov/nwps/v1/gauges"


def _series(block: dict | None) -> pd.DataFrame:
    if not block or not block.get("data"):
        return pd.DataFrame(columns=["time", "value"])
    df = pd.DataFrame(block["data"])
    df = df.rename(columns={"validTime": "time", "primary": "value"})[["time", "value"]]
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[df["value"] > -900].dropna()   # NWPS uses -999 for missing


def parse(site: dict, js: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    obs, fc = _series(js.get("observed")), _series(js.get("forecast"))
    for df in (obs, fc):
        df["site"], df["var"], df["source"] = site["id"], "stage", "nwps"
    issued = (js.get("forecast") or {}).get("issuedTime")
    fc["issued"] = pd.to_datetime(issued, utc=True) if issued else pd.NaT
    return obs, fc


def recent_and_forecast(region: Region) -> tuple[pd.DataFrame, pd.DataFrame]:
    import requests
    obs_all, fc_all = [], []
    for site in region.sites_by(source="nwps"):
        r = requests.get(f"{API}/{site['nws_lid']}/stageflow", timeout=60)
        r.raise_for_status()
        obs, fc = parse(site, r.json())
        if obs.empty:
            log.warning("nwps: no observed stage for %s", site["nws_lid"])
        obs_all.append(obs)
        fc_all.append(fc)
    cat = lambda xs: pd.concat(xs, ignore_index=True) if xs else pd.DataFrame()
    return cat(obs_all), cat(fc_all)
