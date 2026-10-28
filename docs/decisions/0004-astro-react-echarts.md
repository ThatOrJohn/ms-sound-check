# 0004: Astro + TypeScript site, React islands only where needed, ECharts for charts

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The published UI must be professional grade: shareable URLs, fast, accessible, interactive charts.

## Decision
Astro pre-renders every page. Content pages ship no framework JavaScript; React loads only for the map
and the charts. ECharts draws the linked, stacked history charts.

## Why
Pre-rendering gives real URLs per station and persona, fast loads and search indexing. Linked crosshairs,
log axes and zoom are built into ECharts. React was chosen over Svelte because it's what we use most.

## Consequences
A Node toolchain sits beside Python in CI. Browser and accessibility tests (Playwright + axe) gate deploys.
