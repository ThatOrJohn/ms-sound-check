"""Reading and writing source snapshots so a bad file can't break a build (decision 0046).

Every snapshot source (beaches, MDMR, tides, forecasts...) saves one file per run and the build reads it back. A file
can go bad in ways the source's own code never planned for: a run killed mid-write, a source that answered 200 with
an HTML error page, a field that turned into null. `read_json` treats all of those like a missing file: it logs and
returns None, and the section hides as if the source were down. `write_json` writes to a temporary file and renames,
so a half-written file never replaces a good one.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
_warned: set[str] = set()   # each bad file is logged once per run, not once per section that reads it


def _warn(path: Path, kind: str, e: Exception) -> None:
    if str(path) not in _warned:
        _warned.add(str(path))
        log.warning("%s %s unreadable, ignored: %s", kind, path.name, e)


def write_json(path: Path, data, **dump) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, **dump))
    os.replace(tmp, path)


def read_json(path: Path, max_age: pd.Timedelta | None = None, need: tuple[str, ...] = ()) -> dict | None:
    """The snapshot, or None if it's missing, unreadable, not an object, lacks any `need` key (or has it as null), or
    its `fetched_at` is older than `max_age`."""
    if not path.exists():
        return None
    try:
        js = json.loads(path.read_text())
        if not isinstance(js, dict):
            raise ValueError(f"expected an object, got {type(js).__name__}")
        missing = [k for k in need if js.get(k) is None]
        if missing:
            raise ValueError(f"missing {', '.join(missing)}")
        if max_age is not None and pd.Timestamp.now(tz="UTC") - pd.Timestamp(js["fetched_at"]) > max_age:
            return None
    except Exception as e:  # noqa: BLE001  any bad file reads as no file
        _warn(path, "snapshot", e)
        return None
    return js


def read_parquet(path: Path, columns: list[str] | None = None) -> pd.DataFrame | None:
    """The table, or None if it's missing, unreadable, or lacks any of `columns`."""
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        missing = [c for c in columns or [] if c not in df.columns]
        if missing:
            raise ValueError(f"missing columns {', '.join(missing)}")
    except Exception as e:  # noqa: BLE001
        _warn(path, "table", e)
        return None
    return df
