# Roadmap

Updated 2026-10-28. Process notes are in [docs/README.md](README.md).

## Now
Nothing scheduled. Sprint 3 is done apart from the wind comparison (first item under Next).

## Done
- **[Sprint 3: Persona utility](sprints/2026-10-28-s03-persona-utility.md)**: oyster closure watch with typical-year context, fishing weekend outlook, wind data, shrimp in-season notices, live air temp, UI refresh.
- **[Sprint 2: Map and first ML](sprints/2026-10-28-s02-map-and-ml.md)**: MapLibre map with NOAA depth, virtual sensors, forecast experiments, beach status.
- **[Sprint 1: Foundation](sprints/2026-10-28-s01-foundation.md)**: pipeline, live sources, Astro site, personas, CI and deploy.

## Next
- **Get wind history loading in CI**: the ERA5 backfill fails on the GitHub runner (429, then timeouts). Then compare `train` scores with and without the wind features.
- **Step detection in the build**: a step at one station is suspect; matching steps at two or more stations within a few days become an event finding ("Gulf water pushed into the Sound").
- **Event explanations from wind**: attach the likely wind cause to step events.
- **Revisit Round Island's caveat**: Merrill Shell's matching step suggests the 37 ppt may be real.
- **Share previews**: generated Open Graph images per page (for Bluesky and X).
- **Weekly digest**: Bluesky post + RSS from the same build.

- **Move `backfill` to the new USGS API** before the old one retires in early 2027 (daily runs already use the new one).

## Later
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
- Round Island's "possibly a sensor problem" caveat may be wrong (see Next).
- East Ship Island can't be estimated (held-out error ~7 ppt), so it shows as offline.
- Open-Meteo's free API is non-commercial; revisit if sponsorship happens.
