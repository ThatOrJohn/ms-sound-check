"""Satellite map layers for the site (decision 0023).

Each layer is written as a small PNG that holds data, not colors: gray = the value scaled to the layer's range
(log for clarity), alpha 0 = no clear view. The map colors it from the theme's tokens and clips it to water. A plain
sentence per layer says where the water is clearest/murkiest or warmest/coolest, by part of the Sound.
"""
from __future__ import annotations

import struct
import zlib

import numpy as np
import pandas as pd

from ..units import convert, unit_label

# Kd490 (1/m) to words. Secchi depth is roughly 1.4/Kd in coastal water, so: under 0.3 is about 15 ft or more of
# visibility, 0.6 about 8 ft, 1.5 about 3 ft. Words only on the page; the numbers are too rough to print.
CLARITY_WORDS = [(0.3, "clear"), (0.6, "fairly clear"), (1.5, "murky"), (np.inf, "muddy")]
# Parts of the Sound, by latitude/longitude. North of the barrier islands is the Sound; south of them, the Gulf side.
ZONES = [   # names carry their preposition so sentences read right
    ("in the western Sound", lambda la, lo: (la > 30.24) & (lo < -89.2)),
    ("in the central Sound", lambda la, lo: (la > 30.24) & (lo >= -89.2) & (lo < -88.75)),
    ("in the eastern Sound", lambda la, lo: (la > 30.24) & (lo >= -88.75)),
    ("on the Gulf side of the islands", lambda la, lo: la < 30.19),
]
MIN_ZONE_PX = 30
SPREAD = 1.25          # name the murkiest and clearest parts when they differ by at least this ratio


def png(gray: np.ndarray, alpha: np.ndarray) -> bytes:
    """8-bit gray+alpha PNG, no dependencies."""
    h, w = gray.shape
    raw = np.dstack([gray, alpha]).astype(np.uint8)
    rows = b"".join(b"\x00" + raw[y].tobytes() for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 4, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def _zones(c: dict) -> list[tuple[str, float]]:
    la, lo = np.meshgrid(c["lats"], c["lons"], indexing="ij")
    out = []
    for name, f in ZONES:
        v = c["values"][f(la, lo) & np.isfinite(c["values"])]
        if v.size >= MIN_ZONE_PX:
            out.append((name, float(np.median(v))))
    return out


def clarity_summary(zones: list[tuple[str, float]]) -> str | None:
    """'Murky across the area. Murkiest in the western Sound, clearest on the Gulf side of the islands.'"""
    if not zones:
        return None
    word = lambda kd: next(w for lim, w in CLARITY_WORDS if kd < lim)
    words = [w for _, w in CLARITY_WORDS if w in {word(kd) for _, kd in zones}]
    lead = (f"{words[0].capitalize()} across the area." if len(words) == 1
            else f"{words[0].capitalize()} to {words[-1]} across the area.")
    murk, clear = max(zones, key=lambda z: z[1]), min(zones, key=lambda z: z[1])
    if murk[1] / clear[1] >= SPREAD:
        lead += f" Murkiest {murk[0]}, clearest {clear[0]}."
    return lead


def temp_summary(zones: list[tuple[str, float]], units: dict) -> str | None:
    if len(zones) < 2:
        return None
    lo, hi = min(zones, key=lambda z: z[1]), max(zones, key=lambda z: z[1])
    u = unit_label("water_temp", units)
    f = lambda v: f"{convert('water_temp', v, units):.0f}{u}"
    if convert("water_temp", hi[1], units) - convert("water_temp", lo[1], units) < 1.5:
        return f"About {f(np.median([z[1] for z in zones]))} across the area, with little difference from place to place."
    return f"Warmest {hi[0]} (about {f(hi[1])}), coolest {lo[0]} (about {f(lo[1])})."


def build(region, out_dir) -> dict:
    """Write sat-<id>.png for each fresh layer; return the map metadata. Stale or missing layers are left out."""
    from ..adapters import coastwatch
    cfg = region.extras.get("satellite")
    if not cfg:
        return {}
    now = pd.Timestamp.now(tz="UTC")
    layers = {}
    for layer in cfg["layers"]:
        c = coastwatch.load(region, layer["id"])
        if not c or not c["used"]:
            continue
        newest = pd.Timestamp(c["used"][-1])
        newest = newest.tz_localize("UTC") if newest.tzinfo is None else newest
        if now - newest > pd.Timedelta(days=layer.get("max_age_days", 4)):
            continue
        v = c["values"]
        ok = np.isfinite(v)
        if layer["range"] == "scene":
            lo, hi = np.nanpercentile(v, [2, 98])
            lo, hi = float(np.floor(lo)), float(np.ceil(hi))
            hi = max(hi, lo + 1)
        else:
            lo, hi = map(float, layer["range"])
        f = (lambda x: np.log(x)) if layer.get("log") else (lambda x: x)
        k = (f(np.clip(np.where(ok, v, lo), lo, hi)) - f(lo)) / (f(hi) - f(lo))
        gray = np.where(ok, 1 + np.round(k * 254), 0)
        (out_dir / f"sat-{layer['id']}.png").write_bytes(png(gray, np.where(ok, 255, 0)))
        dlat, dlon = abs(float(np.diff(c["lats"]).mean())), float(np.diff(c["lons"]).mean())
        zones = _zones(c)
        is_temp = layer["var"] == "sea_surface_temperature"
        layers[layer["id"]] = {
            "label": layer["label"], "png": f"sat-{layer['id']}.png", "source": layer.get("source"),
            "bounds": [float(c["lons"][0]) - dlon / 2, float(c["lats"][-1]) - dlat / 2,
                       float(c["lons"][-1]) + dlon / 2, float(c["lats"][0]) + dlat / 2],
            "from": pd.Timestamp(c["used"][0]).strftime("%Y-%m-%d"), "to": newest.strftime("%Y-%m-%d"),
            "log": bool(layer.get("log")),
            "range": ([round(convert("water_temp", lo, region.units)), round(convert("water_temp", hi, region.units))]
                      if is_temp else [lo, hi]),
            "unit": unit_label("water_temp", region.units) if is_temp else None,
            "coverage": round(float(ok.mean()), 3),
            "summary": temp_summary(zones, region.units) if is_temp else clarity_summary(zones),
            "zones": [[n, round(x, 2)] for n, x in zones],
        }
    return layers
