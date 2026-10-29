# Roadmap

Updated 2026-10-28. Process notes are in [docs/README.md](README.md).

## Now
**[Sprint 4: Step events](sprints/2026-10-28-s04-step-events.md)** (to 2026-11-04): matching salinity steps across stations (detector built), then wind causes. Also shipped: the Vibrio note ([0024](decisions/0024-vibrio-as-seasonal-note.md)), a tide strip under the map ([0025](decisions/0025-tide-strip-predictions-in-the-browser.md)), beach popups on the map, MDMR oyster notices, a shrimp-openings check in `msc check`, river flow on phones, Dauphin Island salinity at the map's east edge, share images for every page ([0026](decisions/0026-share-images-at-build-time.md)), the headline beside the map ([0027](decisions/0027-headline-beside-the-map.md)) "28 years of the Sound": the salinity history picture, "in the record" signals and years like this one ([0028](decisions/0028-every-year-on-record.md)), Gulf water level in event text ([0030](decisions/0030-gulf-water-level-in-event-text.md)) and the weekly digest feed ([0031](decisions/0031-weekly-digest-rss-and-bluesky.md)), and Showing the Sound: year dots, the long replay with the salinity sketch, wind and river motion, and the home layout (0032-0035).

## Done
- **[Sprint 3: Persona utility](sprints/2026-10-28-s03-persona-utility.md)**: oyster closure watch with typical-year context, fishing weekend outlook, wind data, shrimp in-season notices, live air temp, UI refresh.
- **[Sprint 2: Map and first ML](sprints/2026-10-28-s02-map-and-ml.md)**: MapLibre map with NOAA depth, virtual sensors, forecast experiments, beach status.
- **[Sprint 1: Foundation](sprints/2026-10-28-s01-foundation.md)**: pipeline, live sources, Astro site, personas, CI and deploy.

## Next
- **Smaller rivers in the virtual sensors**: `scripts/experiment_minor_rivers.py` compares the models with and without the
  Wolf and Biloxi gauges (last two years and 2019-2020, overall and on fresh days). Run the `experiment` workflow task
  (LightGBM won't load on the dev Mac) and add them only on a clear, consistent gain ([0021](decisions/0021-smaller-rivers-shown-not-weighed.md)).

### Showing the Sound
Built 2026-10-28 ([0032](decisions/0032-year-dots-from-the-record-indicator.md)-[0035](decisions/0035-home-map-first-and-one-instrument-table.md)):
cleaner stripes, year dots, the salinity sketch for any day back to 1998, wind and river motion, and the home layout.
Two follow-ups:
- **Replay speed on a real phone**: headless software WebGL gives about 50 ms a frame while playing a year (map repaint,
  not the sketch). Check a mid-range phone; if it stutters, lengthen the play interval before trying WebGL (0033).
- **Home height**: 6,327 px at 1360 px wide, not half of 6,000. The readings table is shorter, but the full-width
  history section added about 600 px and the sections we kept as they are come to about 2,700. Decide whether to
  shorten history (one station on the home page?) or spillway (0035).

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
