# 0007: Virtual sensors with calibrated ranges and a publishing bar

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Two salinity sensors died in 2024, and live sensors sometimes report implausible values.

## Decision
LightGBM quantile models predict each station from its neighbors, rivers, rain and season. Ranges are
calibrated on the latest two held-out years (conformalized quantile regression). Estimates are published
only where held-out error is at most 3.5 ppt; suspect flags need a 98% range miss on 2 of 3 days.

## Why
Uncalibrated ranges covered only 54-75% of readings and would have flagged healthy sensors constantly.
With calibration, the flag fired on zero readings in 400 days that passed the hard ceiling.

## Consequences
Good for gap-filling (Gulfport Light, ~2.3 ppt) and charts; weak as a fault detector for slow drift.
Step detection (backlog) is the planned complement.
