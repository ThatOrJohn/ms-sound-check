"""Storage: one long table per region, in plain Parquet so any tool can read it.

  data/<region>/daily/<year>.parquet   site, var, date, value, source   (full history)
  data/<region>/recent.parquet         site, var, time, value, source   (last ~45 days, hourly)

Daily is the backbone (normals, indicators, charts). Recent keeps the
"right now" view honest between daily rollups.
"""
from __future__ import annotations

import pandas as pd

from .config import VARIABLES, Region

DAILY_COLS = ["site", "var", "date", "value", "source"]
RECENT_COLS = ["site", "var", "time", "value", "source"]
RECENT_DAYS = 45


def read_daily(region: Region) -> pd.DataFrame:
    d = region.data_dir / "daily"
    files = sorted(d.glob("*.parquet")) if d.exists() else []
    if not files:
        return pd.DataFrame(columns=DAILY_COLS)
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def upsert_daily(region: Region, new: pd.DataFrame) -> int:
    """Insert or replace daily rows (newer values win: USGS revises provisional data)."""
    if new.empty:
        return 0
    new = new[DAILY_COLS].copy()
    new["date"] = pd.to_datetime(new["date"]).dt.normalize()
    new = new.dropna(subset=["value"])
    d = region.data_dir / "daily"
    d.mkdir(parents=True, exist_ok=True)
    for year, chunk in new.groupby(new["date"].dt.year):
        path = d / f"{year}.parquet"
        if path.exists():
            old = pd.read_parquet(path)
            old["date"] = pd.to_datetime(old["date"])
            chunk = pd.concat([old, chunk], ignore_index=True)
        chunk = (chunk.drop_duplicates(["site", "var", "date"], keep="last")
                      .sort_values(["site", "var", "date"]))
        chunk.to_parquet(path, index=False)
    return len(new)


def read_recent(region: Region) -> pd.DataFrame:
    p = region.data_dir / "recent.parquet"
    if not p.exists():
        return pd.DataFrame(columns=RECENT_COLS)
    df = pd.read_parquet(p)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def write_recent(region: Region, new: pd.DataFrame) -> None:
    old = read_recent(region)
    df = pd.concat([old, new[RECENT_COLS]], ignore_index=True) if not new.empty else old
    if df.empty:
        return
    df["time"] = pd.to_datetime(df["time"], utc=True)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=RECENT_DAYS)
    df = (df[df["time"] >= cutoff]
          .drop_duplicates(["site", "var", "time"], keep="last")
          .sort_values(["site", "var", "time"]))
    region.data_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(region.data_dir / "recent.parquet", index=False)


def recent_to_daily(region: Region, recent: pd.DataFrame) -> pd.DataFrame:
    """Roll hourly/15-min values up to local calendar days."""
    if recent.empty:
        return pd.DataFrame(columns=DAILY_COLS)
    r = recent.copy()
    r["date"] = r["time"].dt.tz_convert(region.timezone).dt.tz_localize(None).dt.normalize()
    out = []
    for (site, var, src), g in r.groupby(["site", "var", "source"]):
        agg = VARIABLES[var]["agg"]
        by_day = g.groupby("date")["value"]
        # Need reasonable coverage before trusting a daily mean.
        counts = by_day.count()
        vals = by_day.sum() if agg == "sum" else by_day.mean()
        if agg == "mean":
            vals = vals[counts >= 4]
        out.append(pd.DataFrame({"site": site, "var": var, "date": vals.index,
                                 "value": vals.values, "source": src}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=DAILY_COLS)
