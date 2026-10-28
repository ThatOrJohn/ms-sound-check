"""USGS water data.

backfill_daily: legacy waterservices "dv" service. One-time history pull; USGS
  retires this service in Q1 2027, after which backfills should move to
  waterdata.get_daily (same data, new API).
recent: new OGC API (api.waterdata.usgs.gov) via the dataretrieval package.
  Set API_USGS_PAT (free key from api.waterdata.usgs.gov) for higher rate limits.
"""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from ..config import REFERENCE, Region
from ..derive import salinity_from_specific_conductance

log = logging.getLogger(__name__)

PCODES = {"00095": "conductance", "00480": "salinity_raw", "00010": "water_temp", "00060": "flow"}
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
    bounds = {"salinity": (0, 45), "water_temp": (-2, 40), "flow": (0, 2e6)}
    lo_hi = out["var"].map(bounds)
    ok = [(lo <= v <= hi) for v, (lo, hi) in zip(out["value"], lo_hi)]
    out = out[ok]
    out = out.rename(columns={time_col: "time" if time_col != "date" else "date"})
    out["site"] = site["id"]
    out["source"] = "usgs"
    return out


# ------------------------------------------------------------------ backfill
def _fetch_legacy_dv(site_number: str, start: str, end: str) -> dict:
    cache_dir = REFERENCE / "raw"  # download cache, never committed
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"dv_{site_number}_{start}_{end}.json"  # keyed by range so a newer pull refetches
    if cache.exists():
        return json.loads(cache.read_text())
    import requests
    r = requests.get("https://waterservices.usgs.gov/nwis/dv/", timeout=180, params={
        "format": "json", "sites": site_number, "parameterCd": ",".join(PCODES),
        "startDT": start, "endDT": end, "siteStatus": "all"})
    r.raise_for_status()
    cache.write_text(r.text)
    return r.json()


def _legacy_dv_frame(payload: dict) -> pd.DataFrame:
    """Daily means (or max/min midpoint) per param, top/bottom sondes averaged."""
    parts = {}
    for ts in payload.get("value", {}).get("timeSeries", []):
        pcode = ts["variable"]["variableCode"][0]["value"]
        if pcode not in PCODES:
            continue
        stat = next((o.get("optionCode") for o in ts["variable"].get("options", {}).get("option", [])
                     if o.get("name") == "Statistic"), None)
        for block in ts.get("values", []):
            vals = block.get("value", [])
            if not vals:
                continue
            s = pd.Series([float(v["value"]) for v in vals],
                          index=pd.to_datetime([v["dateTime"][:10] for v in vals]))
            s = s.where(s != NODATA)
            parts.setdefault((PCODES[pcode], stat), []).append(s)
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


def backfill_daily(region: Region, start: str = "1998-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    out = []
    for site in region.sites_by(source="usgs"):
        log.info("usgs backfill %s", site["id"])
        frame = _legacy_dv_frame(_fetch_legacy_dv(_usgs_number(site["id"]), start, end))
        out.append(_to_canonical(site, frame, "date"))
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
