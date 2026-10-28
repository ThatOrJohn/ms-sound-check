# 0003: Don't use the Databricks free tier

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Considered as a compute/notebook platform.

## Decision
Not used for the pipeline or hosting.

## Why
Free Edition limits outbound internet to trusted domains (our sources may be blocked), shuts compute off
for the day when quotas are hit, stops apps after 24 hours, forbids commercial use, and may delete inactive
accounts. The data is tens of MB, so Spark adds nothing.

## Consequences
Fine to use as an optional notebook workbench against the same Parquet files (see 0002).
