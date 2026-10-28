"""Display units and formatting."""
from __future__ import annotations


def convert(var: str, value: float | None, units: dict) -> float | None:
    if value is None:
        return None
    base = var.split("_")[0]
    if var in ("water_temp", "air_temp") and units.get("temp", "C") == "F":
        return value * 9 / 5 + 32
    if base == "rain" and units.get("rain", "mm") == "in":
        return value / 25.4
    return value


def unit_label(var: str, units: dict) -> str:
    if var in ("water_temp", "air_temp"):
        return "°F" if units.get("temp") == "F" else "°C"
    if var.startswith("rain"):
        return "in" if units.get("rain") == "in" else "mm"
    return {"salinity": "ppt", "flow": "cfs"}.get(var, "")


def fmt(var: str, value: float | None, units: dict) -> str:
    v = convert(var, value, units)
    if v is None:
        return "—"
    u = unit_label(var, units)
    if var == "flow":
        return f"{v:,.0f} {u}"
    if var.startswith("rain"):
        return f"{v:.2f} {u}" if u == "in" else f"{v:.0f} {u}"
    if var in ("water_temp", "air_temp"):
        return f"{v:.0f}{u}"
    return f"{v:.1f} {u}"


def season_phrase(ts) -> str:
    part = "early" if ts.day <= 10 else ("mid-" if ts.day <= 20 else "late")
    month = ts.strftime("%B")
    return f"mid-{month}" if part == "mid-" else f"{part} {month}"
