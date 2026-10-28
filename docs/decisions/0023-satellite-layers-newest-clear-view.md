# 0023: Satellite layers show the newest clear view, colored in the browser

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Our stations measure water at a handful of points. Anglers in particular want to know where the water is muddy or
clear, which a point can't show. NOAA CoastWatch's ERDDAP serves free daily satellite products with no key. Checked on
2026-10-28 over the map's area (90.0°W-88.1°W, 29.9°N-30.72°N):

- Water clarity: VIIRS (S-NPP) Kd490, 750 m, near real time, sector VY (`noaacwNPPVIIRSkd490SectorVYDaily`). About
  12,000 water pixels on a clear day; 2 of the 7 days checked were fully clouded.
- Surface temperature: ACSPO multi-satellite L3S, 0.02° (about 2 km), daily (`noaacwLEOACSPOSSTL3SnrtCDaily`), quality
  level 5 only. About 1,700 water pixels on clear days. Coarse next to a Sound 15-20 km wide, but enough to show the
  Sound against the Gulf side of the islands.
- Gap-filled products (DINEOF) exist only at 9 km, too coarse for the Sound.

## Decision
- For each layer, take the last few days (5 for clarity, 3 for temperature) and keep the newest clear value per pixel.
  The page names the date span ("Satellite, Oct 23-27"). Hide the layer when its newest pass is older than
  `max_age_days`, like every other stale source.
- Write each layer as a gray+alpha PNG that holds the value (clarity on a fixed log scale, 0.1-3.0 per m, so days
  compare; temperature stretched to the scene so fronts show), not colors. The map colors it from theme tokens and
  clips it to the water mask, so both themes work and the coast stays sharp at 750 m.
- Clarity is in words only: clear, fairly clear, murky, muddy, at Kd490 0.3, 0.6 and 1.5 per m. With Secchi depth about
  1.4/Kd in coastal water those are roughly 15, 8 and 3 ft, too rough to print as numbers. The summary names the
  murkiest and clearest parts of the Sound when they differ by a quarter or more.
- Salinity sketch, clarity and temperature fill the same water, so turning one on turns the others off.
- The PNG is written with `zlib` so the scheduled job needs no image library.

## Why
A single day's pass is often clouded; the newest clear view per pixel shows the most water while staying a few days
fresh at most, and naming the span keeps it honest. Coloring in the browser follows the design rule that colors come
only from tokens, and keeps one data file per layer instead of two per theme.

## Consequences
- The near-real-time VIIRS product can be retired or renamed (the S-NPP satellite is aging). If the layer disappears,
  look for the NOAA-20 or NOAA-21 version of the same sector.
- Shallow, clear water can read murky where the bottom reflects. Fine at Sound scale; don't use the layer for anything
  finer.
- The Fishing outlook repeats the clarity summary next to its rain-and-river muddy-water rule, but doesn't change that
  rule's score. Revisit once there's a season of both to compare.
