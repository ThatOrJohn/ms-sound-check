# 0012: Oyster closure watch uses MDMR's published criteria at PERL1

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
MDMR closes conditionally approved oyster areas by river stage and 24-hour rainfall. Closure notices
say only "river stage exceeding management plan criteria."

## Decision
Use the thresholds in MDMR's *Molluscan Shellfish Growing Waters Management Plan* (Dec 2025 edits):
Pearl River near Pearl River, LA (NWS PERL1, USGS 02492600) at 10 ft (Areas I-B, II-A, II-B) and 11 ft
(II-E, II-F, II-G), plus the plan's rainfall triggers. Show observed and NWS-forecast stage. Never state
that an area *is* closed; only MDMR says that.

## Why
Published, specific, checkable criteria. The NWS issues stage forecasts year-round, which turns this from
a report into a heads-up.

## Consequences
The plan's rainfall gauges (Hancock County Utility Authority, Keesler AFB) aren't all available as public
feeds; rainfall is approximate until confirmed. If MDMR revises the plan, update the region config.
