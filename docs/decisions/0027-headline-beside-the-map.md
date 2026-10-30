# 0027: The headline sits beside the map

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

The home page opened with a large headline across the full width, with an empty right half, so on a 900 px tall
laptop screen the map started about 570 px down. The map's header said "The Sound, live" (the data updates every
4 hours, so it isn't live) next to an unlabeled "Fresh / Gulf" color bar that didn't say it was the station colors.

## Decision

The headline, with its region and persona line and blurb, is a panel at the top of the right column, above the Signals
rail. Both scroll together as one sticky column, and Signals scrolls inside it when there isn't room. Below 1080 px the
column stacks above the map as before. The map header is a key: "Dot color: salinity (ppt)", River 0 to 25+ Gulf,
which matches the color scale in `SoundMap.tsx` (fresh at 0, brackish at 12, Gulf at 25 and up).

## Why

The map starts about 270 px higher, and the readouts, map, headline and signals are all visible on a laptop
without scrolling. The headline and the signals both say what matters now, so they belong together.

## Consequences

- The headline is the page's `h1` but now follows the readouts strip. Inside the console the side column comes
  first in the DOM, so screen readers and phones get headline and signals before the map.
- The Signals rail can scroll inside the column, so it has `tabindex="0"` for keyboard access (axe
  `scrollable-region-focusable`).
- A very long headline leaves less room for Signals on short screens. If headlines grow, shorten them rather than
  bringing back the full-width hero.
