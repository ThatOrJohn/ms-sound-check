# 0002: Plain Parquet store on a single-commit data branch

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Committing data to `main` every 4 hours would grow git history by hundreds of MB a year.

## Decision

The data store (daily history, recent values, normals, models, beach snapshots) lives on a `data` branch
that is force-pushed as one commit each run. Formats are plain Parquet/JSON.

## Why

The Parquet files carry their own history, so git history adds nothing. Plain formats keep every tool
(DuckDB, pandas, notebooks, Databricks) able to read the data, so no platform lock-in.

## Consequences

No git-level history of snapshots. If a bad run corrupts the store, recovery is a re-backfill.
