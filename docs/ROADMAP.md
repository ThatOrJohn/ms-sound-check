# Roadmap

Updated 2026-10-28. Process notes are in [docs/README.md](README.md).

## Now
**[Sprint 4: Step events](sprints/2026-10-28-s04-step-events.md)** (to 2026-11-04): matching salinity steps across stations (detector built), then wind causes. Also shipped: the Vibrio note ([0024](decisions/0024-vibrio-as-seasonal-note.md)), a tide strip under the map ([0025](decisions/0025-tide-strip-predictions-in-the-browser.md)), beach popups on the map, MDMR oyster notices, a shrimp-openings check in `msc check`, river flow on phones, Dauphin Island salinity at the map's east edge, share images for every page ([0026](decisions/0026-share-images-at-build-time.md)), the headline beside the map ([0027](decisions/0027-headline-beside-the-map.md)) "28 years of the Sound": the salinity history picture, "in the record" signals and years like this one ([0028](decisions/0028-every-year-on-record.md)), Gulf water level in event text ([0030](decisions/0030-gulf-water-level-in-event-text.md)) and the weekly digest feed ([0031](decisions/0031-weekly-digest-rss-and-bluesky.md)).

## Done
- **[Sprint 3: Persona utility](sprints/2026-10-28-s03-persona-utility.md)**: oyster closure watch with typical-year context, fishing weekend outlook, wind data, shrimp in-season notices, live air temp, UI refresh.
- **[Sprint 2: Map and first ML](sprints/2026-10-28-s02-map-and-ml.md)**: MapLibre map with NOAA depth, virtual sensors, forecast experiments, beach status.
- **[Sprint 1: Foundation](sprints/2026-10-28-s01-foundation.md)**: pipeline, live sources, Astro site, personas, CI and deploy.

## Next
- **Smaller rivers in the virtual sensors**: `scripts/experiment_minor_rivers.py` compares the models with and without the
  Wolf and Biloxi gauges (last two years and 2019-2020, overall and on fresh days). Run the `experiment` workflow task
  (LightGBM won't load on the dev Mac) and add them only on a clear, consistent gain ([0021](decisions/0021-smaller-rivers-shown-not-weighed.md)).

### Showing the Sound
Five items that put more of the data in view. A suggested order: the stripes cleanup and the year dots first (small,
and they reuse `history/*.json`), then the water color and the long replay, then motion, with the layout work alongside.
Every item follows [0013](decisions/0013-instrument-panel-design.md): colors as tokens (map ones in hex), axe passing
in both themes, plain language, and a text alternative for each picture.

- **The water shows salinity, back to 1998**
  - *Goal:* the water itself takes the salinity colors, and the replay can go to any day since 1998, not just the last 30.
    Someone picks May 2019 and watches fresh water from the spillway spread east.
  - *Steps:*
    1. Turn the salinity sketch on by default for Coast (`map_layers` in `regions/ms.yaml`; Oysters already has it).
       Keep the "a sketch, not a measurement" label and the fade away from stations.
    2. Make `salinityImage` in `SoundMap.tsx` draw any day's values, not just today's live stations. It's hidden
       during replay now. Stations don't move, so compute each pixel's weights once and redraw each frame as a
       weighted sum, or move it to WebGL if a phone can't keep up.
    3. In replays of past days, use each station's own measured values when it had them, including Gulfport Light
       (to Aug 2024) and East Ship Island (to Dec 2024). Leave virtual-sensor estimates out of the sketch. Draw no
       fill on days with fewer than two stations, and say so.
    4. Have `build.py` write `replay/<year>.json` with the same daily values the history files use, plus each river's
       daily flow percentile against its normals. Fetch it only when someone picks that year; aim for under
       about 20 KB gzipped per year.
    5. Add a year picker with month jumps next to the replay slider, and a `#YYYY-MM-DD` link to open a day directly.
       Add shortcuts to notable days from `data/notable_years.csv` and `data/spillway_openings.csv`.
    6. Add a one-line text readout for screen readers for the day shown ("May 10, 2019: West Sound 0.6 ppt, ...").
    7. Test the picker and the hash in Playwright, check frame time on a mid-range phone, and add a decision record:
       the sketch on by default, the long replay, and why estimates stay out of the sketch.

- **Wind and river flow as motion**
  - *Goal:* see which way the wind is pushing and how hard the rivers are running without reading a number.
  - *Steps:*
    1. Use the `wind-sound` daily wind (`wind_u`, `wind_v`, `wind_max`) for today, and add it per day to the replay
       files (ERA5 history goes back to 1998), so the replay moves the wind too.
    2. Draw a few hundred faint particles on a canvas over the map, kept on the water by the mask the sketch
       already uses. Their speed comes from the wind speed. Add a new hex token for their color.
    3. Animate the river lines' dashes, with speed set by each river's flow percentile. Very low rivers barely move.
    4. Label it honestly: "Wind over the middle of the Sound, shown across the map. Not a water current." Give the
       direction and speed in words too.
    5. Add a "Wind" layer toggle, on by default for Fishing. With `prefers-reduced-motion`, draw still arrows
       instead, and stop animating when the map is off screen or the tab is hidden.
    6. Check performance, Playwright and axe as for the water color.

- **Today against every year**
  - *Goal:* show "third-saltiest late October since 1999" as a picture. One dot per year for today's date, today's
    value ringed, the highest and lowest years labeled.
  - *Steps:*
    1. In `build.py`, add each year's value for today's date to a reading's output. Do it for salinity, river flow
       and Pearl stage, using the same window and year rules as `msc/history.py`, so the dots always agree with the
       "in the record" text. Mirror it in `lib/types.ts`.
    2. Build a small SVG component, `YearDots.tsx`, not ECharts. Values go across, the typical range is shaded,
       and hovering or tapping a dot shows the year and value. Its text alternative is a sentence like "27.3 ppt,
       3rd highest of 27 years".
    3. Put it under each big reading on station pages and inside Signals that come from the `record` indicator.
       Try it in the home readout tiles in place of the meter, and keep it only if it still reads at phone width.
    4. Add unit tests that check its rank against the record indicator, plus Playwright and axe.

- **Cleaner salinity stripes**
  - *Goal:* the 28-year picture reads as data rather than texture, and the years that matter are easy to find.
  - *Steps:*
    1. Check that the home "28 years" panels draw. They came out blank in a headless full-page screenshot, probably
       because `client:visible` never fired, but confirm it in a browser and add an e2e test that scrolls to them.
    2. Move rows under 80% coverage into a separate "partial years" group below, or behind a toggle, instead of
       mixing faded rows in with the counted ones. Use one light, even color for missing days.
    3. Label notable years in the right margin with a word or two ("spillway", "Ida", "drought") from
       `data/notable_years.csv` and the spillway openings.
    4. Draw a full-height "today" line and faint month lines. Show a row's summary on hover (days under 5 and over
       25 ppt).
    5. On the home page, make it the full section width with taller rows, keeping the compact version on phones.
       A row links to the station page's `#year-YYYY` (already supported), and to that year on the map once the long
       replay exists.
    6. Recheck the "Show as table" alternative, both themes and axe.

- **Home layout**
  - *Goal:* a shorter home page, the map sooner on phones, and sections that only look different when they say
    different things.
  - *Steps:*
    1. Phones: put the map right after the headline, ahead of Signals. Change the order in the DOM, not with CSS
       `order`, so screen readers follow the same order. Update [0027](decisions/0027-headline-beside-the-map.md)
       with a new record if the order changes.
    2. Replace the repeated card grids (Out in the Sound, Rivers, Rain, On the coast, River mouths) with one
       instrument table. Each row has the place, its reading, the meter or year dots, a 30-day sparkline and a link,
       grouped by kind. Keep each persona's `card_order`.
    3. Leave the sections that say something particular as they are: beaches, oysters, fishing, shrimp, spillway,
       Vibrio and history.
    4. Optionally, add the west-to-east salinity strip (below, in Later) as a band under the map.
    5. Measure the result: about half the current desktop height (about 6,000 px now), screenshots in light, dark
       and phone widths, no layout shift, and Playwright and axe passing.

## Later
- **West-to-east salinity strip**: one gradient bar from the Pearl River mouth to East Sound, each station placed by
  where it sits, with a faint band for typical. The whole Sound at a glance, and a good share image.
- **Per-beach RSS**: one feed per beach, alongside the weekly digest.
- **Spillway status feed**: if the Corps publishes structure flow or bays open, use it instead of the hand-kept list
  ([0022](decisions/0022-spillway-watch-from-the-river.md)).
- **MDMR shellfish areas on the oyster map**: the molluscan shellfish and oyster growing waters classification areas as a map layer (I-B, II-A and so on), so the closure table's area names point at places. Look for a public MDMR feature service first, like the beach layer, and don't work around bot checks.
- Custom domain (about $12/yr) and Cloudflare Web Analytics.
- Grand Bay NERR water-quality sondes as extra stations (and a closer reference than Dauphin Island, [0019](decisions/0019-disl-reference-data-no-auto-flag.md)).
- A second region (Alabama via ARCOS, or a Texas bay): new YAML, maybe one adapter.
- Publish virtual-sensor models to Hugging Face with a model card once they're stable.
- Harmful algal bloom notices beyond beaches.

## Parked
- **Beach advisory heads-up after rain**: the effect in MDEQ's 2015-2025 samples faded after 2021 and shows no
  dose-response ([0029](decisions/0029-no-beach-rain-heads-up.md)). Retest in a year or two.
- **Salinity forecast**: no edge over persistence during the events that matter ([0008](decisions/0008-no-salinity-forecast.md)).
- **Databricks**: free-tier limits and nothing to gain at this data size ([0003](decisions/0003-no-databricks.md)).
- **Dock price tracker**: needs committed contributors ([seed.md](seed.md)).
- **Bluesky posting**: not planned. The digest stays as RSS; `python -m msc post` is built but won't be switched on
  ([0031](decisions/0031-weekly-digest-rss-and-bluesky.md)).

## Known issues
- Oyster rainfall is an estimate (Open-Meteo point), not MDMR's Hancock County Utility Authority gauge.
- Round Island's 36-40 ppt readings since 2026-10-15 are probably a sensor problem: nothing nearby corroborates them (Sprint 4 notes). The "possibly a sensor problem" caveat stays.
- East Ship Island can't be estimated (held-out error ~7 ppt), so it shows as offline.
- Open-Meteo's free API is non-commercial; revisit if sponsorship happens.
