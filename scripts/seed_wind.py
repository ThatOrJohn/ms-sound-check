#!/usr/bin/env python3
"""
One-time wind history for the data store, fetched from your machine when the GitHub runner can't reach
Open-Meteo's ERA5 archive (429s and stalls).

    git fetch origin data && git worktree add ../msc-data origin/data    # a checkout of the data branch
    python scripts/seed_wind.py ../msc-data                              # fetch ERA5 wind, upsert into it
    # then commit in ../msc-data and push it: git push -f origin HEAD:data

Safe to re-run: rows are keyed by site, var and date, and newer values replace older ones.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("store", type=Path, help="checkout of the data branch (the folder that contains <region>/daily/)")
ap.add_argument("--region", default="ms")
ap.add_argument("--start", default="1998-01-01")
args = ap.parse_args()

os.environ["MSC_DATA_DIR"] = str(args.store.resolve())      # msc.config reads this at import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msc import store                          # noqa: E402
from msc.adapters import openmeteo             # noqa: E402
from msc.config import load_region            # noqa: E402

region = load_region(args.region)
if not (region.data_dir / "daily").exists():
    sys.exit(f"{region.data_dir / 'daily'} not found: pass the data branch checkout, not the repo root")

rows = openmeteo.wind_backfill(region, start=args.start)
n = store.upsert_daily(region, rows)
print(f"wrote {n} wind rows ({rows.date.min():%Y-%m-%d} to {rows.date.max():%Y-%m-%d}) into {region.data_dir}")
