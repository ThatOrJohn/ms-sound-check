"""Region config loading. A region is one YAML file in regions/."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ROOT / "regions"
REFERENCE = ROOT / "data"                       # hand-curated reference data (in git)
DATA = Path(os.environ.get("MSC_DATA_DIR", ROOT / "data"))  # pipeline store (data branch in CI)
SITE_OUT = ROOT / "web" / "public" / "data"  # read by the Astro build and served as-is

# Canonical variables: stored unit, how daily values aggregate, label. "now": also publish the newest
# observation, for variables whose daily value hides what it's like outside right now.
VARIABLES = {
    "salinity":   {"unit": "ppt",  "agg": "mean", "label": "Salinity", "suspect_above": 36.0},
    "water_temp": {"unit": "degC", "agg": "mean", "label": "Water temp"},
    "air_temp":   {"unit": "degC", "agg": "mean", "label": "Air temp", "now": True},
    "flow":       {"unit": "cfs",  "agg": "mean", "label": "River flow"},
    "rain":       {"unit": "mm",   "agg": "sum",  "label": "Rain"},
    "stage":      {"unit": "ft",   "agg": "max",  "label": "River stage"},
    "wind_u":     {"unit": "m/s",  "agg": "mean", "label": "Wind toward east"},
    "wind_v":     {"unit": "m/s",  "agg": "mean", "label": "Wind toward north"},
    "wind_max":   {"unit": "m/s",  "agg": "max",  "label": "Peak wind"},
}


@dataclass
class Region:
    id: str
    name: str
    timezone: str
    units: dict
    sites: list[dict]
    personas: list[dict]
    indicators: list[dict]
    map: dict = field(default_factory=dict)
    extras: dict = field(default_factory=dict)   # optional region-level sources, e.g. beaches

    def site(self, site_id: str) -> dict:
        return next(s for s in self.sites if s["id"] == site_id)

    def sites_by(self, *, source: str | None = None, kind: str | None = None) -> list[dict]:
        return [s for s in self.sites
                if (source is None or s["source"] == source)
                and (kind is None or s["kind"] == kind)]

    @property
    def data_dir(self) -> Path:
        return DATA / self.id


def load_region(region_id: str) -> Region:
    raw = yaml.safe_load((REGIONS / f"{region_id}.yaml").read_text())
    return Region(
        id=raw["id"], name=raw["name"], timezone=raw.get("timezone", "UTC"),
        units=raw.get("units", {}), sites=raw["sites"], personas=raw.get("personas", []),
        indicators=raw.get("indicators", []), map=raw.get("map", {}),
        extras={k: raw[k] for k in ("beaches", "tides", "mdmr_notices", "reference", "ungauged_rivers",
                                     "spillway", "satellite", "vibrio") if k in raw},
    )
