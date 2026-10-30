# 0042: The map loads after the page, when it's near the screen

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Lighthouse (mobile, 4× CPU slowdown) scored the home page 43: first paint 2.7 s, headline painted at 5.6 s, 7.3 s of
total blocking time. Almost all of it was the map. MapLibre was already a dynamic import, but it started as soon as the
island mounted, and its 71 KB stylesheet sat in `<head>` as a render-blocking link (Astro hoists CSS even from dynamic
imports). A CPU profile showed MapLibre's own JavaScript is only a few hundred ms; the rest is WebGL and image work,
which headless Chrome runs on a software GPU, so Lighthouse overstates it compared with a real phone. It still delays
the headline. On phones the map sits below the headline and readouts (0035), off the first screen.

The station pages had a 0.147 layout shift, and the home page had one hidden behind the blocking stylesheet: the
freshness line's script ran after first paint and could add "This page hasn't refreshed recently…" above the readouts.

## Decision
- `SoundMap` waits until the page has loaded and gone idle (`requestIdleCallback`, at most 2 s) and the map box is
  within 200 px of the screen, then imports MapLibre and links its stylesheet itself (`?url`, not an import).
- A replay day in the address (`#YYYY-MM-DD`) starts the map at once, since the link scrolls to it.
- Pages with the map preconnect to the OpenFreeMap tile host.
- The freshness script is inline, right after its line, so its text is final before first paint.

## Why
Before and after, local build, Lighthouse 12:

| | Score | Headline painted | Blocking time | Layout shift |
|---|---|---|---|---|
| Home, mobile | 43 → 98 | 5.6 → 2.3 s | 7,290 → 50 ms | 0.001 → 0.005 |
| Home, desktop | 91 → 96 | 0.5 → 0.5 s | 20 → 10 ms | 0.19 → 0.12 |
| Station, mobile | 87 → 97 | 2.3 → 1.7 s | 260 → 180 ms | 0.147 → 0 |

The mobile home number partly reflects that the map never starts in the test: it's below the first screen. That's
the point: someone reading the headline and readings doesn't pay for a map they haven't scrolled to.

## Consequences
- On a phone the map starts loading as it scrolls near the screen, so it can be blank (water color) for a moment.
- The remaining desktop shift is `SoundMap` and `TideStrip` being `client:only`: they take no space until they mount
  and push the station list down. Fixed-height fallbacks would remove it.
- Other ideas from the same audit, not done yet: simplify `contours.geojson` (762 KB, 177 KB gzipped) and load it after
  the map is idle, WebP for the depth images, preloading the two Latin Geist fonts, and building the salinity sketch
  only when that layer or the replay is used.
