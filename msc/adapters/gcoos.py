"""Reference salinity from GCOOS ERDDAP (Dauphin Island Sea Lab stations). Free, no key.

Used only as an independent check on our own stations (see msc/models/reference.py); these sites are not
shown as cards. Hourly values with QC flag 1 ("pass") are averaged to a day when at least 12 hours are present.
"""
from __future__ import annotations

import io

import pandas as pd

from ..config import Region

ERDDAP = "https://erddap.gcoos.org/erddap/tabledap"
VAR, QC = "sea_water_practical_salinity_1", "sal_qc_1_agg"
MIN_HOURS = 12


def parse(ref: dict, text: str) -> pd.DataFrame:
    """ERDDAP CSV (row 2 is units) -> canonical daily rows for this reference site."""
    df = pd.read_csv(io.StringIO(text), skiprows=[1])
    if df.empty:
        return pd.DataFrame(columns=["site", "var", "date", "value", "source"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df[VAR] = pd.to_numeric(df[VAR], errors="coerce")
    df = df[(df[QC] == 1) & df[VAR].between(0, 45)]
    g = df.groupby(df["time"].dt.tz_localize(None).dt.normalize())[VAR]
    daily = g.agg(["mean", "count"])
    daily = daily[daily["count"] >= MIN_HOURS]
    return pd.DataFrame({"site": ref["id"], "var": "salinity", "date": daily.index,
                         "value": daily["mean"].round(2).values, "source": "gcoos"})


def daily(region: Region, start: str | None = None, days: int = 10) -> pd.DataFrame:
    import requests
    start = start or (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    out = []
    for ref in region.extras.get("reference", []):
        # ERDDAP rejects a raw ">" in the query, so the time constraint is hand-encoded
        r = requests.get(f"{ERDDAP}/{ref['dataset']}.csv?time,{VAR},{QC}&time%3E={start}T00:00:00Z",
                         timeout=120, headers={"User-Agent": "ms-sound-check"})
        r.raise_for_status()
        out.append(parse(ref, r.text))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
