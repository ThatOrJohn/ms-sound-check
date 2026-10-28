# 0017: Step events describe the wind and rivers; they don't name a cause

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The roadmap planned to attach "the likely wind cause" to step events ([0016](0016-step-events-need-matching-stations.md)).
The expectation was that southerly wind pushes Gulf water into the Sound and raises salinity.

## Decision
Each event's text adds what the wind and the rivers were doing in the three days up to onset: wind averaging
about 7 mph or more (strength and compass direction), and the Pearl and Pascagoula rivers up 50% or down 25% or more
against the week before. When neither stands out it says so: the data doesn't point to a cause.
`msc/models/steps.py:context`. No cause is stated.

## Why
Checked against the 139 matching events from 1998-2026 (ERA5 wind at mid-Sound, USGS river flow):
- Wind did not behave as expected. Salinity drops had a strong southerly wind 58% of the time (33% of all days).
  Salinity rises had one 7% of the time. A "southerly wind pushes salt in" explanation would be backwards.
- Rivers are the clearer signal but not a majority one. 44% of drops followed a river rise of 50% or more (16% of
  all days, 2.8 times as often). 44% of rises followed a fall of 25% or more (24% of days, 1.8 times as often).
- So more than half of the drops had no river rise, and rises show no wind signature. Any sentence that said
  "caused by" would be wrong more often than right, and the 2026-10-15 event (calm wind, steady low rivers,
  +18 ppt at Merrill Shell Bank) has no explanation in the data we hold.

## Consequences
- The text is a set of facts a reader can weigh, and it stays honest when there is nothing to say.
- Missing from the picture: the Mississippi River, Bonnet Carré Spillway openings, tides and wind direction at
  Gulf passes, all of which may explain the unexplained events. Worth revisiting if one of them becomes available.
- The wind point is one location over mid-Sound, averaged over three days, so a short, sharp wind shift can be missed.
- The thresholds (7 mph, +50% / -25%) are judgments from the numbers above, not tuned to maximize matches.
