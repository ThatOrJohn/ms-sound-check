# 0030: Gulf water level joins the step-event text

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
[0017](0017-step-events-describe-wind-and-rivers.md) describes wind and rivers before each salinity step event, and
[0020](0020-mississippi-flow-not-added-to-event-text.md) left one candidate untested: the Gulf water level at Dauphin
Island (NOAA CO-OPS 8735180). We pulled its verified hourly heights one year per request, 4 seconds apart (2001-2026;
nothing referenced to mean sea level before September 2001), and took daily means, which cancel most of the Sound's
once-a-day tide. Change = mean of the 3 days up to onset minus the 7 days before, the same windows as the rivers.
Events: the same 139 matching events from 1998-2026, 137 with level data.

## Decision
Add the level change to `msc/models/steps.py:context` when it moved 8 cm (3 inches) or more: "the water at Dauphin
Island, AL, rose about 4 inches". A fact, like the wind and river lines, never a cause. New daily source `coops`
(`msc/adapters/coops.py`): preliminary 6-minute data in every run, verified hourly heights in `backfill`.

## Why
- 59% of salinity drops (41 of 70) followed a rise of 8 cm or more, against 18% of all days (p < 1e-13). 34% of rises
  (23 of 67) followed a fall of 8 cm or more, against 18% (p < 0.001). Far stronger than the Mississippi (0020).
- The direction is the opposite of "Gulf water pushed in": the Sound freshens when water piles up on the coast and
  turns saltier when it drains away. That matches 0017's finding that drops come with southerly wind. We don't explain
  the mechanism in the text; we say what the gauge did.
- For events our data couldn't explain before, 7 of 16 drops followed a rise of 8 cm or more (about 3 by chance,
  p = 0.01); rises were within chance (4 of 19). So some unexplained events now get a fact, including
  2026-10-15 (the water fell about 7 inches before Merrill Shell Bank and Round Island jumped).
- 8 cm keeps it to about a fifth of days, so it isn't said every time. At 15 cm the line almost never fires on
  otherwise-unexplained events.

## Consequences
- One more source to watch in `msc check` logs; if CO-OPS is down, the sentence simply drops out.
- Verified data lags about a month; the run fetches the last 10 days of preliminary data, so a gap longer than that
  (a long outage) stays empty until `backfill`.
- Not shown as a card or station page (`water_level` is an input kind, like wind).
