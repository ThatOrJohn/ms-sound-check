# Roadmap

Updated 2026-10-28. Process notes are in [docs/README.md](README.md).

## Now
**[Sprint 4: Step events](sprints/2026-10-28-s04-step-events.md)** (to 2026-11-04): matching salinity steps across stations (detector built), then wind causes. Also shipped: the Vibrio note ([0024](decisions/0024-vibrio-as-seasonal-note.md)), a tide strip under the map ([0025](decisions/0025-tide-strip-predictions-in-the-browser.md)), beach popups on the map, MDMR oyster notices, a shrimp-openings check in `msc check`, river flow on phones, Dauphin Island salinity at the map's east edge, share images for every page ([0026](decisions/0026-share-images-at-build-time.md)) and the headline beside the map ([0027](decisions/0027-headline-beside-the-map.md)).

## Done
- **[Sprint 3: Persona utility](sprints/2026-10-28-s03-persona-utility.md)**: oyster closure watch with typical-year context, fishing weekend outlook, wind data, shrimp in-season notices, live air temp, UI refresh.
- **[Sprint 2: Map and first ML](sprints/2026-10-28-s02-map-and-ml.md)**: MapLibre map with NOAA depth, virtual sensors, forecast experiments, beach status.
- **[Sprint 1: Foundation](sprints/2026-10-28-s01-foundation.md)**: pipeline, live sources, Astro site, personas, CI and deploy.

## Next
**28 years of the Sound.** The store has daily readings back to 1998, but the site only uses them for normal bands and
percentile meters. These three items say what those years were. A first look at the data (2026-10-28):
- 2021 was fresher than 2019: Biloxi Back Bay spent 89 days under 5 ppt in 2021 vs. 43 in 2019. At West Sound it was
  63 vs. 68.
- 2023 was the saltiest year: Back Bay had 117 days over 25 ppt, while most years have fewer than 15.
- Over the two weeks to Oct 28, 2026, the Pearl had its 3rd-lowest late-October flow in 29 years (only 2000 and 2010
  were lower), and the Pascagoula its 4th-lowest.
- Water temperature isn't ready to publish. West Sound had 49-63 days a year at 86°F or above in 2022-2025, vs. about
  25 before, but with only 18 complete years the trend is weak (p ≈ 0.08).

Shared rules for all three:
- Leave out readings `is_suspect` rejects, and any station QC flags as "possibly a sensor problem". Round Island's
  37 ppt would otherwise be the saltiest reading ever.
- Leave out years with under 80% coverage.
- Use measured readings only, never virtual-sensor estimates.

1. **Salinity history picture** (every day since 1998, one row per year)
   - `build.py` writes `web/public/data/ms/history/<slug>.json` for each salinity station: years × 366 days, one
     decimal, `null` for gaps. That's about 10 KB per station gzipped. It goes in a separate file so `latest.json`
     stays small. Retired stations keep their measured years, up to 2024.
   - New `HistoryStripes.tsx` draws it on a `<canvas>`, using the same fresh → brackish → gulf colors as the map dots
     (0 / 12 / 25+ ppt), read from the `global.css` tokens at runtime. Today's cell gets a ring, gaps are drawn as
     empty cells, and month ticks run along the bottom.
   - Station pages get the full picture. The home page gets a "28 years" section with West Sound and Back Bay side by
     side, and a one-line takeaway written at build time (for example, "2021 was fresher than the spillway year
     2019"). The takeaway comes from per-year counts of days under 5 and over 25 ppt.
   - Tapping a year adds it as a faint line on that station's chart. That covers the "Reference years on station
     charts" item in Later, so the two get built together.
   - The home picture becomes the `og/` share image. That gives the site the whole-Sound share image the
     "West-to-east salinity strip" in Later was meant to be, though the strip, which shows space rather than time,
     stays listed.
   - Accessibility: the canvas gets a text alternative (each year's mean plus its days under 5 and over 25 ppt), as a
     table hidden behind a "Show as table" button. Both themes need to pass axe.
2. **"In the record" lines** (how today ranks against every year on the same dates)
   - New indicator type `record` in `indicators.py`, configured in `regions/ms.yaml` like `vs_normal`: which
     site/variable pairs to check, a window (14 days, ending today) and how many to call out (`top: 3`).
   - Each year contributes the mean of the same 14 calendar days, with at least 10 days of data. Today's mean is
     ranked among those years. Only a top-3 or bottom-3 rank becomes a finding, worded like "The Pearl River is at its
     third-lowest late-October flow since 1998. Only 2000 and 2010 were lower." The "since" year is the station's
     first year that passes the coverage rule.
   - It replaces the plain `vs_normal` finding for the same site and variable when both fire, so the headline doesn't
     say "running low" twice. Severity stays `notice`, and the wording stays calm and factual.
   - Start with river flow, Pearl stage and Sound salinity. Leave water temperature out until its trend question is
     settled.
   - Test with `build --asof`. On 2019-06-02 it should rank Pearl flow near the top, and on 2026-10-28 it should give
     the Pearl's 3rd-lowest. Add a unit test with a made-up series.
   - Add a decision record for the window, the coverage rule and why only the top or bottom 3 count.
3. **"Years like this one"** (shown as background, never a forecast; see [0008](decisions/0008-no-salinity-forecast.md))
   - In `build.py`, compare the last 60 days of daily log flow for the Pearl and the Pascagoula against the same 60
     days in every past year (root-mean-square difference) and keep the three closest. A first try on 2026-10-28 gave
     2016, 2023 and 2010.
   - A hand-kept `data/notable_years.csv` (year, one-line note, such as "2019: Bonnet Carré open 122 days across two openings")
     gives each match a short note. This follows the pattern of `spillway_openings.csv`.
   - It shows as a small line in the river section, like "Rivers over the last 60 days look most like 2016, 2023 and
     2010", with each year linking to that year on the history picture (item 1).
   - The text never says what came next. If a backtest later shows that what followed in the matching years beats
     plain persistence, revisit that as its own decision.
   - Before shipping, check that the matches look sensible on known dates with `--asof`: the 2019 spring, the
     2000 drought and the 2021 fall.

Other items:
- **Beach advisory heads-up**: `beach_history.parquet` plus rainfall could show how often MDEQ advisories follow heavy
  rain and how soon, for a "likely after rain like this" note between the weekly samples. Never says a beach is closed.
- **Better event explanations**: wind and rivers explain under half of the events ([0017](decisions/0017-step-events-describe-wind-and-rivers.md)). The Mississippi River added nothing beyond chance ([0020](decisions/0020-mississippi-flow-not-added-to-event-text.md)). Left to test: Gulf water level at Dauphin Island (NOAA CO-OPS 8735180; pull slowly, the API refused a fast bulk request).
- **Smaller rivers in the virtual sensors**: run an experiment with the Wolf and Biloxi gauges as inputs for West Sound and Biloxi Back Bay. They're shown but not used today ([0021](decisions/0021-smaller-rivers-shown-not-weighed.md)).
- **Weekly digest**: Bluesky post + RSS from the same build. The home page's share image (`og/index.png`) can be the post's picture.

## Later
- **West-to-east salinity strip**: one gradient bar from the Pearl River mouth to East Sound, each station placed by
  where it sits, with a faint band for typical. The whole Sound at a glance, and a good share image.
- **Reference years on station charts**: a faint line for 2019 (the spillway year) or a year the reader picks. To be
  built with the salinity history picture in Next (tap a year to add its line).
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
- **Salinity forecast**: no edge over persistence during the events that matter ([0008](decisions/0008-no-salinity-forecast.md)).
- **Databricks**: free-tier limits and nothing to gain at this data size ([0003](decisions/0003-no-databricks.md)).
- **Dock price tracker**: needs committed contributors ([seed.md](seed.md)).

## Known issues
- Oyster rainfall is an estimate (Open-Meteo point), not MDMR's Hancock County Utility Authority gauge.
- Round Island's 36-40 ppt readings since 2026-10-15 are probably a sensor problem: nothing nearby corroborates them (Sprint 4 notes). The "possibly a sensor problem" caveat stays.
- East Ship Island can't be estimated (held-out error ~7 ppt), so it shows as offline.
- Open-Meteo's free API is non-commercial; revisit if sponsorship happens.
