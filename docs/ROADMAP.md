# Roadmap

Updated 2026-10-28. Process notes are in [docs/README.md](README.md).

## Now
**[Sprint 4: Step events](sprints/2026-10-28-s04-step-events.md)** (to 2026-11-04): matching salinity steps across stations (detector built), then wind causes. Also shipped: the Vibrio note ([0024](decisions/0024-vibrio-as-seasonal-note.md)), a tide strip under the map ([0025](decisions/0025-tide-strip-predictions-in-the-browser.md)) and beach popups on the map.

## Done
- **[Sprint 3: Persona utility](sprints/2026-10-28-s03-persona-utility.md)**: oyster closure watch with typical-year context, fishing weekend outlook, wind data, shrimp in-season notices, live air temp, UI refresh.
- **[Sprint 2: Map and first ML](sprints/2026-10-28-s02-map-and-ml.md)**: MapLibre map with NOAA depth, virtual sensors, forecast experiments, beach status.
- **[Sprint 1: Foundation](sprints/2026-10-28-s01-foundation.md)**: pipeline, live sources, Astro site, personas, CI and deploy.

## Next
- **Beach advisory heads-up**: `beach_history.parquet` plus rainfall could show how often MDEQ advisories follow heavy
  rain and how soon, for a "likely after rain like this" note between the weekly samples. Never says a beach is closed.
- **Better event explanations**: wind and rivers explain under half of the events ([0017](decisions/0017-step-events-describe-wind-and-rivers.md)). The Mississippi River added nothing beyond chance ([0020](decisions/0020-mississippi-flow-not-added-to-event-text.md)). Left to test: Gulf water level at Dauphin Island (NOAA CO-OPS 8735180; pull slowly, the API refused a fast bulk request).
- **Use the Dauphin Island reference data**: DISL salinity is ingested ([0019](decisions/0019-disl-reference-data-no-auto-flag.md)) but not used for flags. Next: show it on the map's east end, or pair it with a closer station such as Grand Bay NERR.
- **Smaller rivers in the virtual sensors**: run an experiment with the Wolf and Biloxi gauges as inputs for West Sound and Biloxi Back Bay. They're shown but not used today ([0021](decisions/0021-smaller-rivers-shown-not-weighed.md)).
- **Share previews**: generated Open Graph images per page (for Bluesky and X).
- **Weekly digest**: Bluesky post + RSS from the same build.

## Later
- **West-to-east salinity strip**: one gradient bar from the Pearl River mouth to East Sound, each station placed by
  where it sits, with a faint band for typical. The whole Sound at a glance, and a good share image.
- **Reference years on station charts**: a faint line for 2019 (the spillway year) or a year the reader picks.
- **River panel on phones**: the map's river flow panel is hidden under 900 px; show it as a compact row instead.
- **Per-beach RSS**: one feed per beach, alongside the weekly digest.
- **Spillway status feed**: if the Corps publishes structure flow or bays open, use it instead of the hand-kept list
  ([0022](decisions/0022-spillway-watch-from-the-river.md)).
- **MDMR shellfish areas on the oyster map**: the molluscan shellfish and oyster growing waters classification areas as a map layer (I-B, II-A and so on), so the closure table's area names point at places. Look for a public MDMR feature service first, like the beach layer, and don't work around bot checks.
- Custom domain (about $12/yr) and Cloudflare Web Analytics.
- Grand Bay NERR water-quality sondes as extra stations.
- A second region (Alabama via ARCOS, or a Texas bay): new YAML, maybe one adapter.
- Publish virtual-sensor models to Hugging Face with a model card once they're stable.
- Harmful algal bloom notices beyond beaches.
- Oyster reef opening notices from MDMR (same adapter, an `oyster` topic in the region file).
- Check `shrimp_openings.csv` against MDMR's "season opens" notices so the spring update can't be missed.

## Parked
- **Salinity forecast**: no edge over persistence during the events that matter ([0008](decisions/0008-no-salinity-forecast.md)).
- **Databricks**: free-tier limits and nothing to gain at this data size ([0003](decisions/0003-no-databricks.md)).
- **Dock price tracker**: needs committed contributors ([seed.md](seed.md)).

## Known issues
- Oyster rainfall is an estimate (Open-Meteo point), not MDMR's Hancock County Utility Authority gauge.
- Round Island's 36-40 ppt readings since 2026-10-15 are probably a sensor problem: nothing nearby corroborates them (Sprint 4 notes). The "possibly a sensor problem" caveat stays.
- East Ship Island can't be estimated (held-out error ~7 ppt), so it shows as offline.
- Open-Meteo's free API is non-commercial; revisit if sponsorship happens.
