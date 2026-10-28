# Sprint 1: Foundation

- **Dates:** 2026-10-28 (compressed into one day)
- **Status:** Closed
- **Goal:** Prove there's a gap worth filling, then ship a working, free, auto-updating page.

## Done
- [x] Feasibility research: existing tools, data health, free stack ([feasibility.md](../feasibility.md))
- [x] Shrimp-opening probe: temperature, not salinity, carries a weak signal ([0009](../decisions/0009-shrimp-lean-not-date.md))
- [x] Region-agnostic pipeline: adapters, Parquet store, normals, indicators, build ([architecture.md](../architecture.md))
- [x] Live sources: new USGS API, NWS air temperature, Open-Meteo rain + forecast
- [x] Plausibility ceiling for salinity readings (Round Island's 37 ppt)
- [x] Site rebuilt on Astro + TypeScript + React + ECharts ([0004](../decisions/0004-astro-react-echarts.md))
- [x] Personas with their own pages and remembered choice ([0010](../decisions/0010-personas-as-config.md))
- [x] Station pages with linked, stacked history charts
- [x] CI: 3-hour schedule, data branch, GitHub Pages deploy, Playwright + axe tests, health check
- [x] Fixes found in CI: Node version pin, test storage bug, Astro 7 whitespace

## Outcome
Live site updating every 3 hours from four public sources, with per-persona pages and tests gating deploys.
