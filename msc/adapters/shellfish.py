"""MDMR's shellfish growing-water classes as map shapes, from MDMR's public ArcGIS Online feature service (decision 0043).

Each polygon carries ZONE_ID ('Area II "E"') and CONDITIONS (approved, conditionally approved, restricted, prohibited,
unclassified). We keep only those two. The layer also has a hand-kept `Status` field that lags MDMR's orders by months,
so it is never read: open or closed is MDMR's call, in its notices and on its hotline.

The run keeps a snapshot (shellfish_areas.json) with the layer's own last-edit date. A snapshot older than MAX_AGE is
ignored, so the map drops the layer rather than show classes that may have changed.
"""
from __future__ import annotations

import json
import re

import pandas as pd

from ..config import Region

MAX_AGE = pd.Timedelta(days=7)
CLASSES = {"approved": "approved", "conditionally approved": "conditional", "restricted": "restricted",
           "prohibited": "prohibited", "unclassified": "unclassified"}
LABELED = ("approved", "conditional")      # the classes harvest can happen in; the others get an outline only
_ZONE = re.compile(r'^\s*Area\s+([IVX]+)\s*(?:["“”]\s*([A-Z])\s*["“”])?\s*$')


def short(zone_id: str | None) -> str | None:
    """'Area II "E"' -> 'II-E'; 'Area V' -> 'V' (the closure watch's names)."""
    m = _ZONE.match(zone_id or "")
    if not m:
        return (zone_id or "").strip() or None
    return f"{m.group(1)}-{m.group(2)}" if m.group(2) else m.group(1)


def _ring_area(ring: list) -> float:
    """Shoelace area in degrees², only to pick the largest piece of each area for its label."""
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0, *_), (x1, y1, *_) in zip(ring, ring[1:]))) / 2


def _area(geom: dict) -> float:
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return sum(_ring_area(p[0]) for p in polys if p)


def normalize(geojson: dict) -> dict:
    """Feature service GeoJSON -> features with zone, name and class only; one `label` per area and class."""
    feats = []
    for f in geojson.get("features", []):
        p = f.get("properties") or {}
        cls = CLASSES.get((p.get("CONDITIONS") or "").strip().lower())
        if not cls or not f.get("geometry") or f["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            continue
        name = re.sub(r"\s+", " ", (p.get("ZONE_ID") or "").replace("“", '"').replace("”", '"')).strip()
        feats.append({"type": "Feature", "geometry": f["geometry"],
                      "properties": {"zone": short(name), "name": name or None, "class": cls}})
    biggest: dict[tuple, dict] = {}
    for f in feats:
        k = (f["properties"]["zone"], f["properties"]["class"])
        if k[1] in LABELED and k[0] and (k not in biggest or _area(f["geometry"]) > _area(biggest[k]["geometry"])):
            biggest[k] = f
    for f in biggest.values():
        f["properties"]["label"] = True
    return {"type": "FeatureCollection", "features": feats}


def fetch(region: Region) -> dict | None:
    import requests
    cfg = (region.extras or {}).get("shellfish_areas")
    if not cfg:
        return None
    url = f"{cfg['url']}/{cfg.get('layer', 0)}"
    params = {"where": "1=1", "outFields": "ZONE_ID,CONDITIONS", "outSR": 4326, "f": "geojson",
              # about 30 m: plenty for areas a few km across, and a seventh of the full-detail file
              "maxAllowableOffset": cfg.get("simplify_deg", 0.0003), "geometryPrecision": 5, "resultRecordCount": 2000}
    r = requests.get(f"{url}/query", params=params, timeout=60)
    r.raise_for_status()
    js = r.json()
    if "error" in js:
        raise RuntimeError(js["error"])
    geo = normalize(js)
    if not geo["features"]:
        raise RuntimeError("no classified areas in the response")
    meta = requests.get(url, params={"f": "json"}, timeout=60).json()
    edited = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    return {"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), "source": cfg.get("name"), "link": cfg.get("link"),
            "edited": pd.Timestamp(edited, unit="ms", tz="UTC").isoformat() if edited else None, "geojson": geo}


def save(region: Region, data: dict) -> None:
    region.data_dir.mkdir(parents=True, exist_ok=True)
    (region.data_dir / "shellfish_areas.json").write_text(json.dumps(data, separators=(",", ":")))


def load(region: Region) -> dict | None:
    """The snapshot, or None if never fetched or older than MAX_AGE."""
    p = region.data_dir / "shellfish_areas.json"
    if not p.exists():
        return None
    js = json.loads(p.read_text())
    if pd.Timestamp.now(tz="UTC") - pd.Timestamp(js["fetched_at"]) > MAX_AGE:
        return None
    return js
