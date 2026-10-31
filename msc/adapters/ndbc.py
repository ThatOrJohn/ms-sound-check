"""Reference salinity from NDBC's realtime water-quality files (Grand Bay NERR sondes; decision 0045). Free, no key.

NDBC republishes the reserve's 15-minute sonde readings for the last 45 days at /data/realtime2/<ID>.ocean. There is no
history here (the full record is at NERRS CDMO, which only serves registered IP addresses), so these sites build their
record forward from the first run. Readings are averaged to a day when at least 12 hours are present.
"""
from __future__ import annotations

import io

import pandas as pd

from ..config import Region

URL = "https://www.ndbc.noaa.gov/data/realtime2/{id}.ocean"
MIN_READINGS = 48      # 12 hours of 15-minute readings


def parse(ref: dict, text: str) -> pd.DataFrame:
    """NDBC .ocean text (two header lines, 'MM' for missing) -> canonical daily salinity rows for this site."""
    lines = text.splitlines()
    if len(lines) < 3 or not lines[0].startswith("#"):
        return pd.DataFrame(columns=["site", "var", "date", "value", "source"])
    cols = lines[0].lstrip("#").split()
    df = pd.read_csv(io.StringIO("\n".join(lines[2:])), sep=r"\s+", names=cols, na_values="MM", dtype=str)
    t = pd.to_datetime(df.YY + "-" + df.MM + "-" + df.DD + " " + df.hh + ":" + df.mm, utc=True, errors="coerce")
    sal = pd.to_numeric(df.SAL, errors="coerce")
    ok = t.notna() & sal.between(0, 45)
    s = pd.Series(sal[ok].values, index=t[ok].dt.tz_convert(ref.get("tz", "America/Chicago")).dt.tz_localize(None).dt.normalize())
    daily = s.groupby(level=0).agg(["mean", "count"])
    daily = daily[daily["count"] >= MIN_READINGS]
    return pd.DataFrame({"site": ref["id"], "var": "salinity", "date": daily.index,
                         "value": daily["mean"].round(2).values, "source": "ndbc"})


def daily(region: Region) -> pd.DataFrame:
    import requests
    out = []
    for ref in region.extras.get("reference", []):
        if ref.get("source") != "ndbc":
            continue
        r = requests.get(URL.format(id=ref["station"].upper()), timeout=60, headers={"User-Agent": "ms-sound-check"})
        r.raise_for_status()
        out.append(parse({**ref, "tz": region.timezone}, r.text))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
