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
- [x] Official-source notices up front on the home page and in each section; About provenance ([0018](../decisions/0018-official-source-notices-up-front.md))

## Notes
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
