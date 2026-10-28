"""National Weather Service station observations (api.weather.gov; free, no key)."""
from __future__ import annotations

import logging

import pandas as pd

from ..config import Region

log = logging.getLogger(__name__)
UA = {"User-Agent": "ms-sound-check (https://github.com/; hobby coastal conditions page)",
      "Accept": "application/geo+json"}


def latest_url(station: str) -> str:
    """Newest observation; api.weather.gov allows cross-origin requests, so the page refreshes from it on load."""
    return f"https://api.weather.gov/stations/{station}/observations/latest"


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


def forecast(region: Region) -> list[dict]:
    """NWS 7-day forecast periods (day/night) for each weather site with a forecast_point."""
    import requests
    out = []
    for site in region.sites_by(source="nws"):
        pt = site.get("forecast_point")
        if not pt:
            continue
        meta = requests.get(f"https://api.weather.gov/points/{pt[0]},{pt[1]}", headers=UA, timeout=60)
        meta.raise_for_status()
        url = meta.json()["properties"]["forecast"]
        r = requests.get(url, headers=UA, timeout=60)
        r.raise_for_status()
        out += parse_forecast(site, r.json())
    return out


def parse_forecast(site: dict, js: dict) -> list[dict]:
    import re
    rows = []
    for p in js.get("properties", {}).get("periods", []):
        mph = [int(x) for x in re.findall(r"\d+", p.get("windSpeed") or "")]
        rows.append({
            "site": site["id"], "name": p.get("name"), "start": p.get("startTime"), "end": p.get("endTime"),
            "is_day": bool(p.get("isDaytime")), "temp_f": p.get("temperature"),
            "wind_mph_lo": min(mph) if mph else None, "wind_mph_hi": max(mph) if mph else None,
            "wind_dir": p.get("windDirection"), "short": p.get("shortForecast"),
            "rain_pct": (p.get("probabilityOfPrecipitation") or {}).get("value"),
        })
    return rows


MAX_AGE = pd.Timedelta(days=2)


def save_forecast(region: Region, rows: list[dict]) -> None:
    import json
    region.data_dir.mkdir(parents=True, exist_ok=True)
    (region.data_dir / "weather_forecast.json").write_text(json.dumps(
        {"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), "periods": rows}))


def load_forecast(region: Region) -> list[dict]:
    """Forecast periods, or [] if missing or older than two days (a stale forecast is worse than none)."""
    import json
    p = region.data_dir / "weather_forecast.json"
    if not p.exists():
        return []
    js = json.loads(p.read_text())
    if isinstance(js, list) or pd.Timestamp.now(tz="UTC") - pd.Timestamp(js["fetched_at"]) > MAX_AGE:
        return []
    return js["periods"]
