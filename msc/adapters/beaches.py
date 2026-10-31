"""Beach water-quality status from a public ArcGIS feature service (MDEQ's Beach Monitoring Program in MS).

Two layers: 0 = monitoring stations (points), 1 = the beach segments they cover (lines).
Each feature carries isadvisory / isclosure flags, the advisory or closure text, the event type
(Enterococci bacteria, debris, harmful algal bloom), when it started, and the last sample date.

The run keeps a snapshot (beaches.json + beaches.geojson for the map) and appends one row per
station per day to beach_history.parquet, so the page can say how long an advisory has lasted.
"""
from __future__ import annotations

import logging

import pandas as pd

from ..config import Region
from ..snapshots import read_json, read_parquet, write_json

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
    """Stations are the section; without them the run fails and the last snapshot stands until it ages out. The
    segments only draw the map's lines, so if that query fails the stations still save and the old lines stay."""
    cfg = (region.extras or {}).get("beaches")
    if not cfg:
        return None
    stations = _query(cfg["url"], cfg.get("stations_layer", 0), geojson=False)
    try:
        segments = _query(cfg["url"], cfg.get("segments_layer", 1), geojson=True)
    except Exception as e:  # noqa: BLE001
        log.warning("beach segments failed, keeping the last ones: %s", e)
        segments = None
    data = normalize(stations, segments)
    if not data["stations"]:
        raise RuntimeError("no active beach stations in the response")
    data["fetched_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    data["source"] = cfg.get("name", "Beach monitoring program")
    return data


def save(region: Region, data: dict) -> None:
    d = region.data_dir
    write_json(d / "beaches.json", {k: v for k, v in data.items() if k != "segments"}, indent=1)
    if data.get("segments"):
        write_json(d / "beaches.geojson", data["segments"], separators=(",", ":"))
    today = pd.Timestamp.now(tz=region.timezone).tz_localize(None).normalize()
    rows = pd.DataFrame([{"date": today, "id": s["id"], "status": s["status"], "event": s["event"]}
                         for s in data["stations"]])
    p = d / "beach_history.parquet"
    old = read_parquet(p, ["date", "id", "status"])   # unreadable history starts over rather than block the snapshot
    if old is not None:
        rows = pd.concat([old, rows]).drop_duplicates(["date", "id"], keep="last")
    rows.to_parquet(p, index=False)


def load(region: Region) -> tuple[dict | None, dict | None]:
    """The snapshot and the map's segments, each None if missing or unreadable. The build checks the age."""
    d = region.data_dir
    snap = read_json(d / "beaches.json", need=("fetched_at", "stations"))
    if snap and not isinstance(snap["stations"], list):
        snap = None
    seg = read_json(d / "beaches.geojson", need=("features",))
    return snap, seg if seg and isinstance(seg["features"], list) else None
