# Roadmap

Updated 2026-10-28. Process notes are in [docs/README.md](README.md).

## Now
**[Sprint 4: Step events](sprints/2026-10-28-s04-step-events.md)** (to 2026-11-04): matching salinity steps across stations (detector built), then wind causes. Also shipped: the Vibrio note ([0024](decisions/0024-vibrio-as-seasonal-note.md)), a tide strip under the map ([0025](decisions/0025-tide-strip-predictions-in-the-browser.md)), beach popups on the map, MDMR oyster notices, a shrimp-openings check in `msc check`, river flow on phones, Dauphin Island salinity at the map's east edge, share images for every page ([0026](decisions/0026-share-images-at-build-time.md)), the headline beside the map ([0027](decisions/0027-headline-beside-the-map.md)) "28 years of the Sound": the salinity history picture, "in the record" signals and years like this one ([0028](decisions/0028-every-year-on-record.md)), Gulf water level in event text ([0030](decisions/0030-gulf-water-level-in-event-text.md)) and the weekly digest feed ([0031](decisions/0031-weekly-digest-rss-and-bluesky.md)), and Showing the Sound: year dots, the long replay with the salinity sketch, wind and river motion, and the home layout (0032-0035), then a shorter home page (0036) and the Sound west to east as one bar ([0037](decisions/0037-the-sound-west-to-east.md)).

## Done
- **[Sprint 3: Persona utility](sprints/2026-10-28-s03-persona-utility.md)**: oyster closure watch with typical-year context, fishing weekend outlook, wind data, shrimp in-season notices, live air temp, UI refresh.
- **[Sprint 2: Map and first ML](sprints/2026-10-28-s02-map-and-ml.md)**: MapLibre map with NOAA depth, virtual sensors, forecast experiments, beach status.
- **[Sprint 1: Foundation](sprints/2026-10-28-s01-foundation.md)**: pipeline, live sources, Astro site, personas, CI and deploy.

## Next
In this order. Usage numbers come first so they can steer the rest, including the moonshots.
1. **Custom domain and Cloudflare Web Analytics** (about $12/yr; the owner picks and pays for the domain). No usage
   data exists yet for any of the 37 decisions' worth of features.
2. **MDMR shellfish areas on the oyster map**: the molluscan shellfish and oyster growing waters classification areas
   as a map layer (I-B, II-A and so on), so the closure table's area names point at places. Look for a public MDMR
   feature service first, like the beach layer, and don't work around bot checks. If there isn't one, park it.
3. **Grand Bay NERR water-quality sondes** as extra stations, from the public NERRS CDMO service: more coverage in the
   eastern Sound and a closer reference than Dauphin Island ([0019](decisions/0019-disl-reference-data-no-auto-flag.md)).
4. Then moonshots 1 and 2 below, which reuse data already in the store.

### Showing the Sound
Built 2026-10-28 ([0032](decisions/0032-year-dots-from-the-record-indicator.md)-[0035](decisions/0035-home-map-first-and-one-instrument-table.md)):
cleaner stripes, year dots, the salinity sketch for any day back to 1998, wind and river motion, and the home layout.
Home height follow-up done: one history picture on home and a folded spillway section (home 6,035 → 4,972 px,
[0036](decisions/0036-one-history-picture-and-a-folded-spillway.md)). Replay speed on a real phone is parked (below).

## Later
- **Per-beach RSS**: one feed per beach, alongside the weekly digest. Worth it if analytics show the digest is used.
- **Chlorophyll map layer**: CoastWatch chlorophyll as a satellite layer, the same newest-clear-view approach as
  [0023](decisions/0023-satellite-layers-newest-clear-view.md). This is the realistic form of "harmful algal bloom
  notices beyond beaches", since Mississippi has little bloom reporting of its own. Describe it as greener water, not
  as a bloom.
- **Spillway status feed**: if the Corps publishes structure flow or bays open, use it instead of the hand-kept list
  ([0022](decisions/0022-spillway-watch-from-the-river.md)). Blocked until they do.

## Moonshots
Bigger bets, ranked by value against risk. Each one needs a decision record before it's built, and every rule in
CLAUDE.md still applies: oyster wording, the disclaimer, plain language, `_try` and stale-data hiding.
1. **Oyster stress days per reef**: count the days this season when the water was both fresh and hot (roughly under
   5 ppt and above 25 °C, a pairing known to kill oysters), from station readings and the virtual sensors, against
   every year since 1998. Describe conditions on the reefs, never closures. Check the thresholds against published
   oyster mortality studies first.
2. **Spillway "what happened last time"**: when the Mississippi nears 17 ft, show what West Sound and the oyster
   stations did during the 2008, 2011, 2016, 2019 and 2020 openings, week by week. These are past openings side by
   side, not a forecast ([0008](decisions/0008-no-salinity-forecast.md) still holds), so say so in the text.
3. **Low-oxygen watch**: dissolved oxygen from the USGS and NERR stations that measure it, plus the summer Gulf
   dead-zone extent when it's published. It covers fish kills and "jubilee"-type nights for the Fishing and Shrimp
   views.
4. **Storm mode**: when a National Hurricane Center forecast cone touches the coast, home leads with observed water
   level against predicted tide (CO-OPS, already ingested), river rises and official links (NHC, NWS, county
   emergency management). Observations only: no surge predictions of our own. The disclaimer matters most here.
5. **A citable dataset**: the cleaned 1998-onward salinity, river flow and step-event record on Zenodo with a DOI,
   refreshed yearly, with a short data paper or README. Cheap, and it puts the work in front of researchers, MDMR and
   the Gulf Coast Research Lab.
6. **The whole northern Gulf**: a second region and then more (Mobile Bay via ARCOS, Lake Pontchartrain and
   Barataria, Texas bays), as new YAML and maybe one adapter each
   ([0010](decisions/0010-personas-as-config.md)). The real cost is each region's official sources for closures and
   beaches.
7. **Community pier sensors**: low-cost conductivity and temperature loggers at piers, run with schools or USM, fed
   into the pipeline with their own quality checks. Needs hardware, partners and upkeep. It would fill gaps like
   East Ship Island, which can't be estimated.

Considered and left off: an LLM "ask the Sound" chat. It needs a backend, which breaks the static-site model
([0001](decisions/0001-static-site-scheduled-pipeline.md)), and its answers can't be held to the oyster wording rule
or the plain, non-alarmist language.

## Parked
- **Virtual-sensor models on Hugging Face**: little benefit for a plain-language site. Revisit if a researcher asks,
  or alongside the citable dataset (Moonshot 5).
- **Smaller rivers in the virtual sensors**: no station improved in both test periods, and fresh days got worse in 5 of
  8 cases ([0021](decisions/0021-smaller-rivers-shown-not-weighed.md), update 2026-10-29). Rerun if a station nearer a
  river mouth is added.
- **Replay speed on a real phone**: no mid-range phone to test on. Headless software WebGL at 6x CPU slowdown gives
  about 67 ms frames while playing a year; that's the map repaint, and self-pacing the steps didn't clearly help (tried
  2026-10-29, reverted). Recheck if someone reports stutter, or via a real-device service; then lengthen the play
  interval first (0033).
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
