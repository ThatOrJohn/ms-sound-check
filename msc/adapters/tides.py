"""Tide predictions (highs and lows) from NOAA CO-OPS. Free, no key."""
from __future__ import annotations

import pandas as pd

from ..config import Region
from ..snapshots import read_json, write_json

API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def parse(station: dict, js: dict) -> list[dict]:
    if "error" in js:
        raise RuntimeError(js["error"])
    return [{"station": station["id"], "name": station["name"], "time": p["t"],
             "type": "high" if p["type"] == "H" else "low", "ft": round(float(p["v"]), 2)}
            for p in js.get("predictions", [])]


def fetch(region: Region, days: int = 5) -> list[dict]:
    """From yesterday on, so the map's tide strip can show the last half day as well as what's coming."""
    import requests
    start = (pd.Timestamp.now(tz=region.timezone) - pd.Timedelta(days=1)).strftime("%Y%m%d")
    out = []
    for st in region.extras.get("tides", []):
        r = requests.get(API, timeout=60, params={
            "product": "predictions", "station": st["id"], "begin_date": start, "range": (days + 1) * 24,
            "datum": "MLLW", "interval": "hilo", "units": "english", "time_zone": "lst_ldt",
            "format": "json", "application": "ms-sound-check"})
        r.raise_for_status()
        out += parse(st, r.json())
    return out


MAX_AGE = pd.Timedelta(days=2)


def save(region: Region, rows: list[dict]) -> None:
    write_json(region.data_dir / "tides.json", {"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), "predictions": rows})


def load(region: Region) -> list[dict]:
    """Tide predictions, or [] if missing, unreadable or fetched more than two days ago."""
    js = read_json(region.data_dir / "tides.json", MAX_AGE, need=("fetched_at", "predictions"))
    return js["predictions"] if js and isinstance(js["predictions"], list) else []
