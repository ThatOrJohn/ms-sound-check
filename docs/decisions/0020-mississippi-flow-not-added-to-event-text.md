# 0020: Mississippi River flow is not added to step-event text

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
[0017](0017-step-events-describe-wind-and-rivers.md) left the Mississippi River and Bonnet Carré openings as possible
explanations for the events that wind and the Pearl and Pascagoula rivers miss. We tested the Mississippi (USGS 07374000,
Baton Rouge, daily flow) against the same events: 139 matching events from 1998-2026, 132 with enough flow data.
Mississippi change = the 4 days up to onset against the 7 days before that.

## Decision
Leave the Mississippi out of `msc/models/steps.py:context`. The event text stays as in 0017.

## Why
- High Mississippi flow (top quarter of days) came before 21% of drops and 25% of rises, against 25% of all days. No signal.
- A Mississippi rise of 10% or more came before 23 of 67 drops, against about 14 expected by chance. Real, but weak, and
  mostly where the Pearl or Pascagoula already rose.
- The point of adding it is the events that currently say "our data doesn't point to a cause": 34 of 132. Among the 15
  drops in that group, 5 followed a Mississippi rise of 10% or more (about 3 expected by chance). Among the 19 rises,
  6 followed a Mississippi fall of 10% or more (about 4 expected). Both are within chance.
- Bonnet Carré has opened only about eight times since 1998, too few to test; high Mississippi flow is the nearest proxy and showed nothing.

## Consequences
- No new data source, and no new sentence that would be right about as often as a guess.
- Not tested: Gulf water level at Dauphin Island (NOAA CO-OPS 8735180) as a "Gulf water pushed in" signal. Our bulk
  pull was refused by CO-OPS (HTTP 403 "Forbidden") after about 350 rapid requests, so redo it slowly and cached.
- Revisit if the water-level test or a closer station shows a signal. The 15 + 19 unexplained events are a small sample.
