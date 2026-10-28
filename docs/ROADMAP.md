# Roadmap

Updated 2026-10-28. Process notes are in [docs/README.md](README.md).

## Now
**[Sprint 4: Step events](sprints/2026-10-28-s04-step-events.md)** (to 2026-11-04): matching salinity steps across stations (detector built), then wind causes.

## Done
- **[Sprint 3: Persona utility](sprints/2026-10-28-s03-persona-utility.md)**: oyster closure watch with typical-year context, fishing weekend outlook, wind data, shrimp in-season notices, live air temp, UI refresh.
- **[Sprint 2: Map and first ML](sprints/2026-10-28-s02-map-and-ml.md)**: MapLibre map with NOAA depth, virtual sensors, forecast experiments, beach status.
- **[Sprint 1: Foundation](sprints/2026-10-28-s01-foundation.md)**: pipeline, live sources, Astro site, personas, CI and deploy.

## Next
- **Better event explanations**: wind and rivers explain under half of the events ([0017](decisions/0017-step-events-describe-wind-and-rivers.md)). Candidates: Mississippi River flow and Bonnet Carré openings, tides at the Gulf passes.
- **Use Dauphin Island Sea Lab as an independent check**: GCOOS ERDDAP serves its salinity hourly (DISL_DISL since 2008, DISL_KATA since 2011), no key. It could back a QC check for Round Island (see the Sprint 4 notes) and extend the east end of the map.
- **Share previews**: generated Open Graph images per page (for Bluesky and X).
- **Weekly digest**: Bluesky post + RSS from the same build.

- **Move `backfill` to the new USGS API** before the old one retires in early 2027 (daily runs already use the new one).

## Later
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
- First live beach, NWPS stage and MDMR notice fetches not yet verified in CI.
- Oyster rainfall is an estimate (Open-Meteo point), not MDMR's Hancock County Utility Authority gauge.
- Round Island's 36-40 ppt readings since 2026-10-15 are probably a sensor problem: nothing nearby corroborates them (Sprint 4 notes). The "possibly a sensor problem" caveat stays.
- East Ship Island can't be estimated (held-out error ~7 ppt), so it shows as offline.
- Open-Meteo's free API is non-commercial; revisit if sponsorship happens.
