"""One-time basemap prep: depth shading, contours and a water mask for the Sound map.

Source: NOAA NCEI U.S. Coastal Relief Model (3 arc-second, ~90 m). Tried in order until one answers:
  1. NCEI image service, CRM mosaic       (gis.ngdc.noaa.gov DEM_mosaics/CRM_mosaic)
  2. NCEI image service, best-available   (DEM_mosaics/DEM_all)
  3. ERDDAP, CRM Vol. 4 Central Gulf      (coastwatch.pfeg.noaa.gov, then the upwell mirror)
Run once and commit the outputs:

    python -m msc basemap            # writes web/public/basemap/*

Outputs (all static, a few hundred KB):
  depth-light.png / depth-dark.png  shaded bathymetry, transparent over land
  watermask.png                     low-res water mask the salinity layer clips to
  contours.geojson                  depth contours in feet
  meta.json                         bounds and attribution
  rivers.geojson                    the region's named rivers, from OpenStreetMap (`python -m msc rivers`)
"""
from __future__ import annotations

import io
import json
import logging

import numpy as np
import pandas as pd

from .config import ROOT

log = logging.getLogger(__name__)
OUT = ROOT / "web" / "public" / "basemap"
IMAGE_SERVICES = [
    "https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/CRM_mosaic/ImageServer",
    "https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/ImageServer",
]
ERDDAPS = ["https://coastwatch.pfeg.noaa.gov/erddap", "https://upwell.pfeg.noaa.gov/erddap"]
DATASET = "usgsCeCrm4"
ARCSEC3 = 1 / 1200
BOUNDS = (-90.00, 29.90, -88.10, 30.72)      # w, s, e, n: wider than any view the map allows
CONTOURS_FT = [6, 10, 15, 20, 30, 40]
M_TO_FT = 3.28084
THEMES = {  # shallow -> deep, matching the site's water tokens
    "light": ((0xd6, 0xe6, 0xe4), (0x6f, 0x9f, 0xab)),
    "dark": ((0x24, 0x44, 0x47), (0x0c, 0x22, 0x26)),
}


# ------------------------------------------------------------------ fetch
def _from_image_service(base: str, stride: int) -> pd.DataFrame:
    """Float32 GeoTIFF export from an ArcGIS ImageServer, resampled to the requested grid."""
    import requests
    from PIL import Image
    w, s, e, n = BOUNDS
    step = ARCSEC3 * stride
    width, height = round((e - w) / step), round((n - s) / step)
    params = {
        "bbox": f"{w},{s},{e},{n}", "bboxSR": 4326, "imageSR": 4326, "size": f"{width},{height}",
        "format": "tiff", "pixelType": "F32", "noData": -99999, "compression": "None",
        "interpolation": "RSP_BilinearInterpolation", "f": "image",
    }
    log.info("fetching %s/exportImage (%dx%d)", base, width, height)
    r = requests.get(f"{base}/exportImage", params=params, timeout=(20, 300))
    r.raise_for_status()
    if "image" not in r.headers.get("content-type", "") and not r.content[:4] in (b"II*\x00", b"MM\x00*"):
        raise RuntimeError(f"not an image: {r.text[:200]}")
    z = np.array(Image.open(io.BytesIO(r.content)), dtype=float)
    z[z <= -9999] = np.nan
    lats = n - (np.arange(z.shape[0]) + 0.5) * (n - s) / z.shape[0]
    lons = w + (np.arange(z.shape[1]) + 0.5) * (e - w) / z.shape[1]
    return pd.DataFrame(z, index=lats, columns=lons)


def _from_erddap(base: str, stride: int) -> pd.DataFrame:
    import requests
    w, s, e, n = BOUNDS
    js = requests.get(f"{base}/info/{DATASET}/index.json", timeout=(20, 60)).json()
    cols = js["table"]["columnNames"]
    rows = [dict(zip(cols, r)) for r in js["table"]["rows"]]
    names = [r["Variable Name"] for r in rows if r["Row Type"] == "variable"]
    var = "topo" if "topo" in names else names[0]
    r = None
    for lat in (f"({s}):{stride}:({n})", f"({n}):{stride}:({s})"):   # ascending, else descending latitude
        url = f"{base}/griddap/{DATASET}.csv?{var}[{lat}][({w}):{stride}:({e})]"
        log.info("fetching %s", url)
        r = requests.get(url, timeout=(20, 600))
        if r.ok:
            break
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), skiprows=[1])
    df.columns = ["lat", "lon", "z"]
    return df.pivot_table(index="lat", columns="lon", values="z").sort_index(ascending=False)


def fetch_grid(stride: int = 1) -> pd.DataFrame:
    """Elevation grid (m, negative = below sea level) as a lat x lon DataFrame, north row first."""
    errors = []
    sources = [(_from_image_service, b) for b in IMAGE_SERVICES] + [(_from_erddap, b) for b in ERDDAPS]
    for fn, base in sources:
        try:
            g = fn(base, stride)
            water = (g.values < 0).mean()
            if not 0.05 < water < 0.95:   # sanity: the box is roughly half water
                raise RuntimeError(f"implausible grid ({water:.0%} water)")
            log.info("got %dx%d grid from %s (%.0f%% water)", g.shape[1], g.shape[0], base, 100 * water)
            return g
        except Exception as e:      # try the next source
            log.warning("%s failed: %s", base, e)
            errors.append(f"{base}: {e}")
    raise RuntimeError("no depth source answered:\n  " + "\n  ".join(errors))


# ------------------------------------------------------------------ render
def _box_blur(a: np.ndarray, r: int) -> np.ndarray:
    if r <= 0:
        return a
    k = 2 * r + 1
    p = np.pad(a, r, mode="edge")
    c = p.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def render(grid: pd.DataFrame) -> dict:
    from PIL import Image
    OUT.mkdir(parents=True, exist_ok=True)
    z = grid.values.astype(float)
    lats, lons = grid.index.values, grid.columns.values
    water = np.isfinite(z) & (z < 0)
    depth_ft = np.where(water, -z * M_TO_FT, 0.0)

    # Hillshade of the seabed. The Sound is shallow, so exaggerate relief to make channels and shoals read.
    zz = _box_blur(np.where(water, z, 0.0), 1) * 25.0
    dy, dx = np.gradient(zz)
    az, alt = np.radians(315), np.radians(45)
    slope = np.arctan(np.hypot(dx, dy) / 90.0)
    aspect = np.arctan2(-dx, dy)
    hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    shade = np.clip(0.78 + 0.32 * hs, 0.7, 1.08)

    t = np.clip(np.log1p(depth_ft) / np.log1p(45), 0, 1)[..., None]
    for theme, (shallow, deep) in THEMES.items():
        rgb = (np.array(shallow) * (1 - t) + np.array(deep) * t) * shade[..., None]
        rgba = np.dstack([np.clip(rgb, 0, 255), np.where(water, 255, 0)]).astype(np.uint8)
        Image.fromarray(rgba, "RGBA").save(OUT / f"depth-{theme}.png", optimize=True)

    # Water mask for clipping the salinity sketch, at full resolution so small islands
    # (Deer Island, the barrier islands' marsh fringes) stay crisp. 1-bit PNG keeps it small.
    Image.fromarray(water).convert("1").save(OUT / "watermask.png", optimize=True)
    mw, mh = int(z.shape[1]), int(z.shape[0])

    # Contours in feet, from a lightly smoothed grid so lines aren't jagged.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    smooth = np.where(water, _box_blur(depth_ft, 2), np.nan)
    fig, ax = plt.subplots()
    cs = ax.contour(lons, lats, smooth, levels=CONTOURS_FT)
    feats = []
    for level, segs in zip(cs.levels, cs.allsegs):
        for seg in segs:
            if len(seg) < 6:
                continue
            seg = seg[:: max(1, len(seg) // 400)]        # cap vertices per line
            feats.append({"type": "Feature", "properties": {"depth_ft": int(level)},
                          "geometry": {"type": "LineString",
                                       "coordinates": [[round(x, 5), round(y, 5)] for x, y in seg]}})
    plt.close(fig)
    (OUT / "contours.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                    separators=(",", ":")))

    # Image corners: pixel edges, not centers.
    dlon = float(abs(lons[1] - lons[0])) if len(lons) > 1 else 0
    dlat = float(abs(lats[0] - lats[1])) if len(lats) > 1 else 0
    meta = {
        "bounds": [float(lons.min()) - dlon / 2, float(lats.min()) - dlat / 2,
                   float(lons.max()) + dlon / 2, float(lats.max()) + dlat / 2],
        "size": [int(z.shape[1]), int(z.shape[0])],
        "mask_size": [mw, mh],
        "contours_ft": CONTOURS_FT,
        "attribution": "Depth: NOAA NCEI U.S. Coastal Relief Model",
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def build(stride: int = 1) -> dict:
    import importlib.util
    missing = [m for m in ("PIL", "matplotlib") if importlib.util.find_spec(m) is None]
    if missing:
        raise SystemExit("basemap needs Pillow and Matplotlib: pip install -r requirements-dev.txt")
    return render(fetch_grid(stride))


# ------------------------------------------------------------------ river lines
OVERPASS = "https://overpass-api.de/api/interpreter"
MIN_STEP_DEG = 0.0005                          # ~50 m: plenty for zoom 8-12.5
LABEL_ALONG = 0.35                             # name sits this far up the downstream line, from its mouth end


def _label_point(lines: list[list]) -> list:
    """A point LABEL_ALONG of the way up the river's most downstream line, measured from its southern end."""
    line = min(lines, key=lambda l: min(p[1] for p in l))
    if line[0][1] > line[-1][1]:
        line = line[::-1]
    steps = [np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(line, line[1:])]
    target, run = LABEL_ALONG * sum(steps), 0.0
    for p, d in zip(line[1:], steps):
        run += d
        if run >= target:
            return p
    return line[-1]


def _thin(pts: list[list], step: float) -> list[list]:
    """Drop vertices closer than `step` degrees to the last one kept; always keep both ends (so ways still join)."""
    if len(pts) < 2:
        return pts
    out = [pts[0]]
    for p in pts[1:-1]:
        if max(abs(p[0] - out[-1][0]), abs(p[1] - out[-1][1])) >= step:
            out.append(p)
    return out + [pts[-1]]


def _join(ways: list[list]) -> list[list]:
    """Chain lines that share an endpoint (either direction) into as few lines as possible."""
    ways = [list(w) for w in ways]
    merged = True
    while merged:
        merged = False
        for i, a in enumerate(ways):
            for j in range(i + 1, len(ways)):
                b = ways[j]
                if a[-1] == b[0]:
                    a += b[1:]
                elif a[-1] == b[-1]:
                    a += b[-2::-1]
                elif a[0] == b[-1]:
                    a[:0] = b[:-1]
                elif a[0] == b[0]:
                    a[:0] = b[:0:-1]
                else:
                    continue
                del ways[j]
                merged = True
                break
            if merged:
                break
    return ways


def rivers(names: list[str]) -> int:
    """Named river lines from OpenStreetMap (Overpass API) -> rivers.geojson. Returns the feature count.

    The vector tiles keep only the Pearl at the Sound-wide zoom (z8), so the map draws rivers from this file.
    Run again (and commit) when the river list in the region config changes:

        python -m msc rivers
    """
    import re

    import requests
    w, s, e, n = BOUNDS
    pattern = "|".join(re.escape(x) for x in sorted(set(names)))
    q = f'[out:json][timeout:90];way["waterway"="river"]["name"~"^({pattern})$"]({s},{w},{n},{e});out geom;'
    r = requests.post(OVERPASS, data={"data": q}, timeout=120, headers={"User-Agent": "ms-sound-check basemap prep"})
    r.raise_for_status()
    lines: dict[str, list[list]] = {}
    for way in r.json()["elements"]:
        pts = _thin([[round(p["lon"], 5), round(p["lat"], 5)] for p in way.get("geometry", [])], MIN_STEP_DEG)
        if len(pts) >= 2:
            lines.setdefault(way["tags"]["name"], []).append(pts)
    feats = []
    for name, ways in lines.items():
        joined = _join(ways)    # OSM splits rivers into many short ways
        feats += [{"type": "Feature", "properties": {"name": name}, "geometry": {"type": "LineString", "coordinates": l}}
                  for l in joined]
        # Meanders and bends are too tight for text to follow at the Sound-wide zoom, so each river gets one point
        # to hang its name on, near the coast where people look.
        feats.append({"type": "Feature", "properties": {"name": name, "label": True},
                      "geometry": {"type": "Point", "coordinates": _label_point(joined)}})
    (OUT / "rivers.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "attribution": "Rivers: © OpenStreetMap contributors", "features": feats},
        separators=(",", ":")))
    return len(feats)
