# 0006: Compute salinity from specific conductance

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
USGS's own salinity series starts in 2011 and has gaps; conductance goes back to 1998 at the best stations.

## Decision
Salinity is computed from specific conductance with PSS-78 (`gsw`).

## Why
Roughly doubles usable history, which normals and models depend on.

## Consequences
Readings are faithful to the sensor, including its faults; QC (0007) has to catch those.
