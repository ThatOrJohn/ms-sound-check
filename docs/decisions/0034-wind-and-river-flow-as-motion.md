# 0034: Wind and river flow as motion

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Wind direction and river strength were numbers in text. The `wind-sound` site has daily mean `wind_u`, `wind_v` and
`wind_max` (ERA5 back to 1998, model analysis for recent days), and each river has a daily flow percentile.

## Decision
- A "Wind" map layer (on by default for Fishing) draws about 320 faint particles moving with the day's mean wind,
  kept on the water by the sketch's mask, in a new `--wind` token. It's one wind for the whole map, and the panel
  says so: "Wind over the middle of the Sound, shown across the map. Not a water current." It also gives the
  direction and speed in words ("Oct 27: from the east at about 8 mph, daily average").
- The wind feed runs about a day behind, so "today" uses the newest wind from the last two days and names its date.
- With the River flow layer on, each gauged river gets a light dash that marches toward the Sound at a speed set by
  its flow percentile, about 1 step a second for a very low river and up to 15 for a very high one.
- The replay moves both: wind is in the 30-day replay and in every `replay/<year>.json`.
- With `prefers-reduced-motion`, wind is a grid of still arrows and the dashes stand still. Nothing animates while
  the map is off screen (IntersectionObserver) or the tab is hidden. All of it lives in `lib/motion.ts`.

## Why
- A daily mean is honest about what we have: one point over the middle of the Sound, averaged by day. Drawing it as
  a field would invent spatial detail, so the label says what it is and the words carry the same fact.
- Particles on their own canvas don't make MapLibre repaint, so they stay smooth (60 fps idle at 4x CPU throttling).

## Consequences
- The daily mean vector is weaker than the day's typical wind speed when the wind turns during the day. If people
  read it as "calm" on gusty days, show `wind_max` next to it.
- Revisit if an hourly or gridded wind source becomes available.
