"""National Weather Service station observations (api.weather.gov; free, no key)."""
from __future__ import annotations

import logging

import pandas as pd

from ..config import Region

log = logging.getLogger(__name__)
UA = {"User-Agent": "ms-sound-check (https://github.com/; hobby coastal conditions page)",
      "Accept": "application/geo+json"}


def recent(region: Region, days: int = 7) -> pd.DataFrame:
    import requests
    out = []
    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for site in region.sites_by(source="nws"):
        url = f"https://api.weather.gov/stations/{site['station']}/observations"
        r = requests.get(url, params={"start": start}, headers=UA, timeout=60)
        r.raise_for_status()
        rows = []
        for f in r.json().get("features", []):
            p = f.get("properties", {})
            t = (p.get("temperature") or {}).get("value")
            if "air_temp" in site["vars"] and t is not None:
                rows.append({"time": p["timestamp"], "var": "air_temp", "value": float(t)})
        df = pd.DataFrame(rows)
        if df.empty:
            log.warning("nws: no observations for %s", site["station"])
            continue
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df["site"], df["source"] = site["id"], "nws"
        out.append(df)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
