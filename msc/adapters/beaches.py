"""Beach water-quality status from a public ArcGIS feature service (MDEQ's Beach Monitoring Program in MS).

Two layers: 0 = monitoring stations (points), 1 = the beach segments they cover (lines).
Each feature carries isadvisory / isclosure flags, the advisory or closure text, the event type
(Enterococci bacteria, debris, harmful algal bloom), when it started, and the last sample date.

The run keeps a snapshot (beaches.json + beaches.geojson for the map) and appends one row per
station per day to beach_history.parquet, so the page can say how long an advisory has lasted.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from ..config import Region

log = logging.getLogger(__name__)
FIELDS = ["stationnumber", "name", "location", "county", "westend", "eastend", "active", "sortorder",
          "isadvisory", "isclosure", "lastsampledate", "eventtype", "advisorydesc", "closuredesc", "startdate"]


def _query(url: str, layer: int, geojson: bool) -> dict:
    import requests
    params = {"where": "1=1", "outFields": "*", "f": "geojson" if geojson else "json",
              "returnGeometry": "true" if geojson else "false", "outSR": 4326, "resultRecordCount": 2000}
    r = requests.get(f"{url}/{layer}/query", params=params, timeout=60)
    r.raise_for_status()
    js = r.json()
    if "error" in js:
        raise RuntimeError(js["error"])
    return js


def _ts(s: str | None) -> str | None:
    """'10/26/2026 09:10:00' -> ISO; tolerate blanks and odd formats."""
    if not s:
        return None
    t = pd.to_datetime(s, errors="coerce")
    return None if pd.isna(t) else t.isoformat()


def status(attrs: dict) -> str:
    if attrs.get("isclosure"):
        return "closure"
    if attrs.get("isadvisory"):
        return "advisory"
    return "clear"


def normalize(stations_json: dict, segments_geojson: dict | None) -> dict:
    stations = []
    for f in stations_json.get("features", []):
        a = {k.lower(): v for k, v in f.get("attributes", {}).items()}
        if not a.get("active", 1):
            continue
        stations.append({
            "id": str(a.get("stationnumber")), "name": a.get("name"), "location": a.get("location"),
            "county": a.get("county"), "from": a.get("westend"), "to": a.get("eastend"),
            "lat": a.get("latitude"), "lon": a.get("longitude"), "order": a.get("sortorder"),
            "status": status(a), "event": a.get("eventtype"),
            "text": a.get("closuredesc") or a.get("advisorydesc"),
            "since": _ts(a.get("startdate")), "last_sample": _ts(a.get("lastsampledate")),
        })
    stations.sort(key=lambda s: (s["order"] is None, s["order"] or 0))
    segments = None
    if segments_geojson:
        feats = []
        for f in segments_geojson.get("features", []):
            p = {k.lower(): v for k, v in (f.get("properties") or {}).items()}
            if not p.get("active", 1) or not f.get("geometry"):
                continue
            feats.append({"type": "Feature", "geometry": f["geometry"],
                          "properties": {"id": str(p.get("stationnumber")), "name": p.get("name"), "status": status(p)}})
        segments = {"type": "FeatureCollection", "features": feats}
    return {"stations": stations, "segments": segments}


def fetch(region: Region) -> dict | None:
    cfg = (region.extras or {}).get("beaches")
    if not cfg:
        return None
    data = normalize(_query(cfg["url"], cfg.get("stations_layer", 0), geojson=False),
                     _query(cfg["url"], cfg.get("segments_layer", 1), geojson=True))
    data["fetched_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    data["source"] = cfg.get("name", "Beach monitoring program")
    return data


def save(region: Region, data: dict) -> None:
    d = region.data_dir
    d.mkdir(parents=True, exist_ok=True)
    (d / "beaches.json").write_text(json.dumps({k: v for k, v in data.items() if k != "segments"}, indent=1))
    if data.get("segments"):
        (d / "beaches.geojson").write_text(json.dumps(data["segments"], separators=(",", ":")))
    today = pd.Timestamp.now(tz=region.timezone).tz_localize(None).normalize()
    rows = pd.DataFrame([{"date": today, "id": s["id"], "status": s["status"], "event": s["event"]}
                         for s in data["stations"]])
    p = d / "beach_history.parquet"
    if p.exists():
        old = pd.read_parquet(p)
        rows = pd.concat([old, rows]).drop_duplicates(["date", "id"], keep="last")
    rows.to_parquet(p, index=False)


def load(region: Region) -> tuple[dict | None, dict | None]:
    d = region.data_dir
    snap = json.loads((d / "beaches.json").read_text()) if (d / "beaches.json").exists() else None
    seg = json.loads((d / "beaches.geojson").read_text()) if (d / "beaches.geojson").exists() else None
    return snap, seg
