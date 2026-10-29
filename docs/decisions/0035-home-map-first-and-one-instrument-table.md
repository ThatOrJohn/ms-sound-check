# 0035: Map right after the headline, and one instrument table

- **Status:** Accepted (updates [0027](0027-headline-beside-the-map.md))
- **Date:** 2026-10-28

## Context
On phones the home page went readouts, headline, the whole Signals list, then the map. Below the map, five card
grids (Out in the Sound, River mouths, Rivers, Rain, On the coast) repeated the same card shape about 20 times.

## Decision
- The console's DOM order is headline, map, Signals. Wide screens still show the headline and Signals in the right
  column, using grid areas (not CSS `order`), so the reading order is the same everywhere. Signals is sticky on its
  own; the headline scrolls away.
- The five card grids become one table (`InstrumentTable.astro`): a row per reading with the place, the value, where
  it sits against normal (year dots where a record indicator ranks it, the meter otherwise, and the words), a 30-day
  sparkline, and the place linking to its station page. It is grouped by kind in the persona's `card_order` and placed
  where the first of those kinds comes. Retired sensors with no estimate are left out of the table; the list under
  the map still links them.
- Beaches, oysters, fishing, shrimp, spillway, Vibrio and history stay as they are.

## Why
- Phones reach the map one screen sooner, and screen readers get the same order as sighted readers.
- A table reads as one instrument panel, and lines up the numbers for comparison.
- Height, measured in headless Chromium at 1360 px: the table is 1,615 px against 2,162 for the first version.
  The page is 6,327 px, not the roadmap's "about half of 6,000", because the full-width history section (Showing the
  Sound, stripes item) added about 600 px, and the sections we were told to leave alone come to about 2,700 px. Getting
  to half would mean shortening those sections, which is a separate decision.

## Consequences
- 0027's sticky side column (headline and Signals scrolling together) is gone; only Signals sticks.
- `card_order` still decides where the readings sit and in what group order.
