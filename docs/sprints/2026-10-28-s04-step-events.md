# Sprint 4: Step events

- **Dates:** 2026-10-28 to 2026-11-04
- **Status:** In progress
- **Goal:** Say when the Sound's water changed all at once, and keep a single bad sensor from looking like news.

## Checklist
- [x] Step detector and event matching ([0016](../decisions/0016-step-events-need-matching-stations.md)), `msc/models/steps.py`
- [x] `salinity_steps` indicator in `regions/ms.yaml`; the stations involved show it on their pages
- [x] Tuned on 1998-2026: about 5 events a year; catches Ida, the 2019 spillway closing, Francine, Zeta and October 2026
- [x] Wind and river context for each event ([0017](../decisions/0017-step-events-describe-wind-and-rivers.md)): not a cause, because the 1998-2026 history doesn't support one
- [x] Events across three or more stations lead the Oysters and Fishing headlines (short form); two-station events stay in Signals
- [x] Settle the Round Island caveat: keep it. Merrill Shell's step is real but lands at about 25 ppt, not 37 (see notes)
- [x] DISL salinity ingested as reference data; no automatic flag ([0019](../decisions/0019-disl-reference-data-no-auto-flag.md))
- [x] Official-source notices up front on the home page and in each section; About provenance ([0018](../decisions/0018-official-source-notices-up-front.md))
- [x] Smaller rivers: Wolf and Biloxi gauges as `minor` rivers, Jourdan/Tchoutacabouffa/Escatawpa named on the map, headline names rivers ([0021](../decisions/0021-smaller-rivers-shown-not-weighed.md)). Needs the `backfill` task once in CI for their normals.
- [x] Bonnet Carré Spillway watch: Mississippi stage and forecast at New Orleans against 17 ft, every past opening, and what West Sound did during recent ones ([0022](../decisions/0022-spillway-watch-from-the-river.md))
- [x] Satellite water clarity and surface temperature as map layers, with a plain summary by part of the Sound ([0023](../decisions/0023-satellite-layers-newest-clear-view.md)); clarity on by default for Fishing and repeated in its outlook
- [x] Map replay: a 30-day slider and Play button that redraw station salinity and river flow day by day
- [x] Colorblind fixes: beach segments use line patterns, labels and a key; collapsible panels show a chevron
- [x] Dev fixtures keep real data: `apply` sets aside the real snapshots, beach history and the stage readings it displaces; `clear` puts them back
- [x] Vibrio-favorable water: a calm seasonal note on Coast, Oysters and Fishing, not a Signal, since it holds on most April-October days ([0024](../decisions/0024-vibrio-as-seasonal-note.md))

- [x] Tide strip under the map: predicted tide at Gulfport, 12 hours back and 36 ahead, "now" placed in the browser ([0025](../decisions/0025-tide-strip-predictions-in-the-browser.md)); tide fetch starts a day early
- [x] Beach popups on the map: hover or tap a segment for status, reason and duration, linking to its row in Beaches
- [x] MDMR oyster season notices in the Oysters section (an `oyster` topic in `regions/ms.yaml`, with an `exclude` filter for meetings, aquaculture and leases); a notice from the past week leads the Oysters headline
- [x] `python -m msc check` fails when an MDMR spring "shrimp season opens" notice has no row in `data/shrimp_openings.csv`, or a different date
- [x] River panel on phones: the same rows as a strip under the map below 640 px
- [x] Share images: a 1200x630 PNG per page drawn at build time with satori + sharp, `og:image` with a build-time `?v=` ([0026](../decisions/0026-share-images-at-build-time.md)); river stage displays gained their "ft"
- [x] Dauphin Island salinity as a labeled reference chip at the map's east edge (0019, update); not a station dot, never in the salinity fill
- [x] Home layout: headline moved into a panel beside the map, above Signals; map header is now a labeled salinity key ([0027](../decisions/0027-headline-beside-the-map.md))
- [x] Gulf water level at Dauphin Island in step-event text ([0030](../decisions/0030-gulf-water-level-in-event-text.md)): new `coops` source; drops followed a level rise 59% of the time vs. 18% of days; 2026-10-15 now has a fact
- [x] Weekly digest ([0031](../decisions/0031-weekly-digest-rss-and-bluesky.md)): `digest.json` in the store, `digest.xml` RSS, `python -m msc post` to Bluesky once the secrets are set
- [x] Beach rain heads-up tested and parked ([0029](../decisions/0029-no-beach-rain-heads-up.md)): the rain effect in MDEQ's samples faded after 2021 (17% vs. 12%)
- [x] Smaller rivers in the virtual sensors: experiment run in CI; no consistent gain, so they stay out (0021, update 2026-10-29)
- [x] 28 years of the Sound ([0028](../decisions/0028-every-year-on-record.md)): shared rules in `msc/history.py`; salinity history picture (`history/<slug>.json`, `HistoryStripes.tsx`) on station pages and in a home section, with a table alternative, a picked year drawn on the station chart, and the home share image; `record` indicator for river flow, Pearl stage and Sound salinity (unit tests in `tests/`, now run in CI); "years like this one" in the river section with `data/notable_years.csv`
- [x] Showing the Sound: cleaner salinity stripes (partial years apart, notable-year tags, today line, month lines, row summaries, a tapped day links to its station year and map day; the home panels were drawing once scrolled to, now covered by an e2e test)
- [x] Showing the Sound: today against every year, year dots built from the record indicator's own means ([0032](../decisions/0032-year-dots-from-the-record-indicator.md)), unit test and e2e
- [x] Showing the Sound: salinity sketch on for Coast, drawn for any day; `replay/<year>.json` back to 1998; year, month, notable-day pickers and `#YYYY-MM-DD` ([0033](../decisions/0033-salinity-sketch-and-the-long-replay.md))
- [x] Showing the Sound: wind particles and marching river dashes, still arrows under reduced motion ([0034](../decisions/0034-wind-and-river-flow-as-motion.md))
- [x] Showing the Sound: home DOM order headline, map, Signals; one instrument table in place of five card grids ([0035](../decisions/0035-home-map-first-and-one-instrument-table.md))
- [ ] Showing the Sound: check replay frame time on a real mid-range phone. Parked: no device; self-paced steps tried at 6x CPU slowdown, no clear gain, reverted (ROADMAP Parked)
- [x] Showing the Sound: home height: one history picture on home (the rest linked) and the spillway folded to one line while the river is low; home 6,035 → 4,972 px ([0036](../decisions/0036-one-history-picture-and-a-folded-spillway.md))
- [x] The Sound west to east: one bar of today's salinity by station position over a fainter usual bar, a summary in the table's band words, labels that never cross, and the Oysters share image (`share: strip`) ([0037](../decisions/0037-the-sound-west-to-east.md))
- [x] Moonshot 2, past spillway openings side by side: one West Sound chart per year since 2000 on shared axes, typical line, 2 ppt runs, `spillway.past` replaces `effects`; unit tests and e2e ([0038](../decisions/0038-past-spillway-openings-side-by-side.md))

## Notes
- 2026-10-28: The spillway's open/closed status isn't published anywhere we can read: the Corps' CWMS series for MVN
  stopped on 2026-09-14 and have nothing for the structure, USGS has no gauge in the channel, and the Corps' site
  answers bots with 403. So the watch reads the river (NWS NORL1) and a hand-kept list of openings (0022).
- 2026-10-28: West Sound during openings (median the month before, then the low): 2019-02-27 15.5 to 0.6 ppt, 2019-05-10
  5.7 to 0.2, 2020-04-03 7.8 to 5.5. In 2011 it fell from 15.9 to 1.1, and in 2016 from 15.4 to 1.3.
- 2026-10-28: Round Island went from 17.6 ppt to 36.2 ppt on Oct 14-15 and then read 37-40 ppt. Merrill Shell Bank
  stepped from 7 to 24 ppt on the same days while rivers were low and the wind was calm, so the jump looks real at
  two stations. 40 ppt is above what the Gulf should carry, so the Round Island numbers are still doubtful.
- 2026-10-28: MDMR's shellfish area maps are wanted on the oyster map (roadmap, Later).
- 2026-10-28: Round Island checked against NOAA/GCOOS data from Dauphin Island Sea Lab, about 45 km east (GCOOS ERDDAP,
  `DISL_DISL` and `DISL_KATA`, hourly, public, no key).
  - Dauphin Island and KATA read 23-29 ppt all October with no step on the 15th. KATA's highest daily value in
    15 years is 34.9 ppt.
  - Round Island has read over 36 ppt on 24 days in its life: 3 in 2009, 3 in 2024, 18 in 2026 (since Oct 15).
  - Its gap to Dauphin Island has a median of +1.7 ppt and a 95th percentile of +10.6 (maximum +21). Since Oct 15
    it has been +11 to +17 for two weeks, with its daily swing at 0.3-1.6 ppt (Merrill Shell 2-3, Back Bay 3-6).
  - Merrill Shell's step (7 to 24-27 ppt) and Back Bay's (19 to 23) both landed at the regional level Dauphin Island
    shows (about 24), so the freshwater to Sound-water change at those two looks real. It says nothing in favor of 37.
  - Conclusion: the readings above 36 ppt are most likely a sensor problem, and the QC ceiling is doing its job.
    Caveat: Dauphin Island is a different part of the Sound (Mobile Bay side), so this is strong circumstantial
    evidence, not proof. The 15-minute record for Round Island starts only on Oct 21, so I couldn't compare its
    intraday swing before and after the jump.
- 2026-10-28: Tried DISL as an automatic Round Island check. Its gap to DISL is +11 to +13 ppt now, inside the historical
  range (95th pct +10.5, 99th +14.7, max +21), so a rule can't separate this from real events. Kept as reference data
  only ([0019](../decisions/0019-disl-reference-data-no-auto-flag.md)). The first live beach, NWPS stage and MDMR
  fetches are confirmed in CI (run 40762443105).
