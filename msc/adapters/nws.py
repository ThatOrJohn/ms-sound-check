"""National Weather Service station observations (api.weather.gov; free, no key)."""
from __future__ import annotations

import logging

import pandas as pd

from ..config import Region
from ..snapshots import read_json, write_json

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
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def marine_forecast(region: Region) -> dict | None:
    """The NWS coastal waters forecast for the region's marine zone (Mississippi Sound is GMZ532)."""
    import requests
    zone = region.extras.get("marine_zone")
    if not zone:
        return None
    r = requests.get(f"https://api.weather.gov/zones/forecast/{zone['id']}/forecast", headers=UA, timeout=60)
    r.raise_for_status()
    return parse_marine(r.json(), region.timezone)


def parse_marine(js: dict, tz: str) -> dict:
    """Zone periods carry only names ("Today", "Friday Night"), so date them from the issue time: "Today",
    "Tonight" and the like are the issue date, a weekday name is the next date with that name (the issue date itself
    after midnight). Keeps the NWS's own wave wording ("Waves 2 to 3 feet, then 1 foot or less.") rather than
    parsing it into numbers."""
    import re
    props = js.get("properties", {})
    issued = pd.Timestamp(props["updated"]).tz_convert(tz)
    rows, day_dates = [], set()
    for p in props.get("periods", []):
        name = p.get("name") or ""
        first = name.split()[0] if name else ""
        is_day = not re.search(r"Night|Tonight|Overnight", name)
        date = issued
        if first in WEEKDAYS:   # Today, This Afternoon, Rest of Today, Tonight, Overnight stay on the issue date
            date = issued + pd.Timedelta(days=(WEEKDAYS.index(first) - issued.weekday()) % 7)
            if is_day and date.strftime("%Y-%m-%d") in day_dates:   # "Thursday" after "Today" on a Thursday
                date += pd.Timedelta(days=7)
        key = date.strftime("%Y-%m-%d")
        if is_day:
            day_dates.add(key)
        text = p.get("detailedForecast") or ""
        waves = " ".join(m.group(0) for m in re.finditer(r"\b(?:Waves|Seas|Bay waters)\b[^.]*\.", text))
        rows.append({"name": name, "date": key, "is_day": is_day, "waves": waves or None})
    return {"issued": issued.isoformat(), "periods": rows}


def save_marine(region: Region, fc: dict) -> None:
    write_json(region.data_dir / "marine_forecast.json", {"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), **fc})


def load_marine(region: Region) -> list[dict]:
    """Marine forecast periods, or [] if missing, unreadable or older than two days, like the land forecast."""
    js = read_json(region.data_dir / "marine_forecast.json", MAX_AGE, need=("fetched_at", "periods"))
    return js["periods"] if js and isinstance(js["periods"], list) else []


def save_forecast(region: Region, rows: list[dict]) -> None:
    write_json(region.data_dir / "weather_forecast.json",
               {"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), "periods": rows})


def load_forecast(region: Region) -> list[dict]:
    """Forecast periods, or [] if missing, unreadable or older than two days (a stale forecast is worse than none)."""
    js = read_json(region.data_dir / "weather_forecast.json", MAX_AGE, need=("fetched_at", "periods"))
    return js["periods"] if js and isinstance(js["periods"], list) else []
