"""Mississippi River at New Orleans (Carrollton) stage and NWS forecast, for the Bonnet Carré Spillway watch.

Same NWPS stageflow API as the Pearl River gauge (adapters/nwps.py). Kept out of the station list on purpose: it's
context for one section, not a reading of the Sound. Saved as data/<region>/spillway.json with fetched_at.
"""
from __future__ import annotations

import pandas as pd

from ..config import Region
from ..snapshots import read_json, write_json
from .nwps import API, _series

KEEP_DAYS = 30


def parse(js: dict, now: pd.Timestamp) -> dict:
    obs, fc = _series(js.get("observed")), _series(js.get("forecast"))
    obs = obs[obs.time >= now - pd.Timedelta(days=KEEP_DAYS)]
    pts = lambda df: [[t.isoformat(), round(float(v), 2)] for t, v in zip(df.time, df.value)]
    return {"fetched_at": now.isoformat(), "observed": pts(obs), "forecast": pts(fc),
            "issued": (js.get("forecast") or {}).get("issuedTime")}


def fetch(region: Region) -> dict | None:
    import requests
    cfg = region.extras.get("spillway")
    if not cfg:
        return None
    r = requests.get(f"{API}/{cfg['gauge_lid']}/stageflow", timeout=60)
    r.raise_for_status()
    return parse(r.json(), pd.Timestamp.now(tz="UTC"))


def save(region: Region, snap: dict) -> None:
    write_json(region.data_dir / "spillway.json", snap)


def load(region: Region) -> dict | None:
    """The snapshot as saved, or None if missing or unreadable. The section checks its age."""
    return read_json(region.data_dir / "spillway.json", need=("fetched_at",))
