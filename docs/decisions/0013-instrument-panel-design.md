# 0013: An instrument-panel look, one typeface

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The first site used a serif headline face, a sans body face and bordered cards. It read clearly but looked like any
generated site. The goal is "Apple meets Palantir": calm and precise, with numbers up front and structure you can scan.

## Decision
One family, Geist (Variable for text, Mono for small uppercase labels), with tabular figures everywhere. Quiet surfaces
separated by hairlines and soft shadows; translucent "glass" panels only where they float over the map. The home page
reads top to bottom as a briefing: headline, a strip of key readouts, the map with a sticky signals rail, then numbered
sections. Readings carry a percentile meter showing where today sits among every year's readings for the date.
Personas and theme use segmented controls.

## Why
One typeface with a mono companion looks deliberate and keeps numbers aligned. The readout strip and meters let someone
take in the Sound in a few seconds, and the signals rail keeps what matters in view while they look at the map.
The salinity colors (tannin, brackish, gulf) and channel-marker red and green stay, because they carry meaning.

## Consequences
- Colors live as tokens in `web/src/styles/global.css`. The map and charts read them at runtime, so palette changes
  restyle everything. Keep the map tokens (`--land`, `--water`, `--fresh`, `--brackish`, `--gulf`) as hex.
- Every color pair must pass the axe contrast checks in both themes; the tests gate deploys.
- `--block` sets the width of section bodies; `--measure` sets the width of prose.
