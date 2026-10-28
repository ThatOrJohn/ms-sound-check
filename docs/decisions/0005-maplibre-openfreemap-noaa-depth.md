# 0005: MapLibre with OpenFreeMap tiles and NOAA depth data

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The map needs accurate land and water boundaries, depth, and our own styling, for free.

## Decision
MapLibre GL with OpenFreeMap vector tiles (OpenStreetMap coastline, no key), styled in the site palette.
Depth shading and contours come from NOAA's Coastal Relief Model, prepared once (`python -m msc basemap`)
and committed as static files.

## Why
No API keys or usage billing, accurate coastline, full control of style. Depth changes on geologic time,
so a one-time prep is enough.

## Consequences
The map depends on OpenFreeMap's availability; the station list below the map carries the same
information if tiles fail. Max zoom is 12.5 because depth data is 90 m.
