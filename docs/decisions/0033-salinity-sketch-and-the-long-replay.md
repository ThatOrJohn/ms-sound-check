# 0033: The salinity sketch is on for Coast, and the replay reaches back to 1998

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The map's salinity sketch (inverse-distance weighting between stations) was off by default except for Oysters, and
hidden whenever the replay showed a past day. The replay covered only the last 30 days. The store has daily
salinity back to 1998.

## Decision
- The sketch is on by default for Coast as well (`map_layers` in `regions/ms.yaml`). It keeps its "A sketch, not a
  measurement" note and the fade 30 km from the nearest station.
- `lib/sketch.ts` works out each sketch cell's distance to every station once (a 4x coarser grid than the water
  mask), then each redraw is a weighted sum scaled up and clipped by the full mask. The map shows it through a
  MapLibre canvas source, so any day can be drawn.
- On past days the sketch uses each station's own measured daily value, including stations retired since (Gulfport
  Light to Aug 2024, East Ship Island to Dec 2024). Virtual-sensor estimates never go into it, today or in the past.
  With fewer than two stations reporting there's no fill, and the Layers panel says so.
- `build.py` writes `replay/<year>.json` for every year with salinity (measured salinity per station, each river's
  daily flow percentile against its normals, and the day's mean wind), about 4 to 6 KB gzipped each. The browser
  fetches a year only when someone picks it. `latest.json` carries `replay_index`: the years, every station's
  position, and shortcut days from `data/notable_years.csv` (new `tag` and `day` columns) and every spillway opening.
- Under the slider: a Year picker ("Last 30 days" or any year), a Month jump, a "Jump to a notable day" list, and
  `#YYYY-MM-DD` links that open that day. The address follows the day shown (not while playing), so it can be shared.
  A visually hidden live line reads the day for screen readers ("May 10, 2019: West Sound 6.3 ppt, ..."), quiet while
  playing.

## Why
- Watching fresh water spread east in May 2019 is the clearest way to show what the spillway does, and the data was
  already there.
- Estimates stay out because a sketch built partly from a model's guesses would look like measurement twice over.
  Measured values from stations that have since closed are real data for their days.
- Per-year files keep `latest.json` small and nobody downloads 28 years to see today.
- Speed: in headless Chromium with software WebGL, idle frames (wind particles moving) hold 60 fps even at 4x CPU
  throttling. Playing a year redraws about every 50 ms. Drawing the sketch at half resolution made no difference,
  so the map repaint dominates, not the sketch. **Not yet measured on a real mid-range phone**; if one stutters,
  try a longer play interval before moving the sketch to WebGL.

## Consequences
- Satellite fills and beach status are still today-only and stay hidden while replaying.
- A new station needs no web change: it appears in the replay files and `replay_index.sites`.
- The station history picture links a tapped day to the map with its `#YYYY-MM-DD`.
