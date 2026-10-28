# 0008: Don't publish a salinity forecast (for now)

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Tested 1-14 day salinity forecasts against persistence (details in feasibility.md, "ML experiments").

## Decision
No salinity forecast on the site.

## Why
River data, including the Mississippi, added nothing over persistence. Wind added 9-16% at 3-7 days,
but only on ordinary days; every model was worse than persistence during freshwater events, the moments
that matter.

## Consequences
Wind gets ingested anyway (fishing outlook, virtual sensors, event explanations). Revisit if wind-driven
virtual sensors or a hybrid "persistence during events" approach shows a clear win.
