"""Satellite water clarity and surface temperature from NOAA CoastWatch ERDDAP (griddap). Free, no key.

For each layer in the region's `satellite` block: the last few days over the map's area, combined into the newest
clear-sky value per pixel (clouds leave gaps on any single day). Saved as data/<region>/satellite/<id>.npz.
"""
from __future__ import annotations

import io
import json
import logging

import numpy as np
import pandas as pd

from ..config import Region

log = logging.getLogger(__name__)
ERDDAP = "https://coastwatch.noaa.gov/erddap/griddap"


def _url(layer: dict, bbox: list[float], start: pd.Timestamp) -> str:
    w, s, e, n = bbox
    t = f"[({start.strftime('%Y-%m-%dT00:00:00Z')}):1:(last)]"
    alt = "[(0.0)]" if layer.get("altitude") else ""
    dims = f"{t}{alt}[({n}):1:({s})][({w}):1:({e})]"
    vars_ = [layer["var"]] + ([layer["quality"]["var"]] if layer.get("quality") else [])
    # ERDDAP wants brackets percent-encoded
    q = ",".join(f"{v}{dims}" for v in vars_).replace("[", "%5B").replace("]", "%5D")
    return f"{ERDDAP}/{layer['dataset']}.csv?{q}"


def composite(layer: dict, text: str) -> dict | None:
    """ERDDAP CSV (row 2 is units) -> newest valid value per pixel, plus which pass it came from."""
    df = pd.read_csv(io.StringIO(text), skiprows=[1])
    if df.empty:
        return None
    v = pd.to_numeric(df[layer["var"]], errors="coerce")
    if layer.get("quality"):
        v = v.where(pd.to_numeric(df[layer["quality"]["var"]], errors="coerce") >= layer["quality"]["min"])
    lats = np.sort(df.latitude.unique())[::-1]          # north first, like an image
    lons = np.sort(df.longitude.unique())
    yi = len(lats) - 1 - np.searchsorted(lats[::-1], df.latitude.values)
    xi = np.searchsorted(lons, df.longitude.values)
    times = sorted(df.time.unique())
    ti = np.searchsorted(times, df.time.values)
    vals = np.full((len(lats), len(lons)), np.nan, dtype=np.float32)
    when = np.full(vals.shape, -1, dtype=np.int16)
    for k in range(len(times)):                         # oldest first, so newer passes overwrite
        m = (ti == k) & v.notna().values
        vals[yi[m], xi[m]] = v.values[m]
        when[yi[m], xi[m]] = k
    if not np.isfinite(vals).any():
        return None
    used = sorted({int(k) for k in np.unique(when) if k >= 0})
    return {"values": vals, "lats": lats, "lons": lons, "when": when, "times": [str(t) for t in times],
            "used": [str(times[k]) for k in used]}


def fetch(region: Region) -> dict[str, dict]:
    import requests
    cfg = region.extras.get("satellite")
    if not cfg:
        return {}
    now = pd.Timestamp.now(tz="UTC")
    out = {}
    for layer in cfg["layers"]:
        start = (now - pd.Timedelta(days=layer.get("days", 5))).normalize()
        r = requests.get(_url(layer, cfg["bbox"], start), timeout=300, headers={"User-Agent": "ms-sound-check"})
        if r.status_code == 404:        # ERDDAP's answer when no pass falls in the window
            continue
        r.raise_for_status()
        c = composite(layer, r.text)
        if c:
            c["fetched_at"] = now.isoformat()
            out[layer["id"]] = c
    return out


def save(region: Region, layers: dict[str, dict]) -> None:
    d = region.data_dir / "satellite"
    d.mkdir(parents=True, exist_ok=True)
    for lid, c in layers.items():
        meta = {k: c[k] for k in ("times", "used", "fetched_at")}
        np.savez_compressed(d / f"{lid}.npz", values=c["values"], lats=c["lats"], lons=c["lons"], when=c["when"],
                            meta=np.array(json.dumps(meta)))


def load(region: Region, lid: str) -> dict | None:
    """One layer's composite, or None if missing or unreadable (that layer drops off the map; the others stay)."""
    p = region.data_dir / "satellite" / f"{lid}.npz"
    if not p.exists():
        return None
    try:
        z = np.load(p)
        return {"values": z["values"], "lats": z["lats"], "lons": z["lons"], "when": z["when"], **json.loads(str(z["meta"]))}
    except Exception as e:  # noqa: BLE001
        log.warning("satellite layer %s unreadable, ignored: %s", lid, e)
        return None
