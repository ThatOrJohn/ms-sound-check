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
