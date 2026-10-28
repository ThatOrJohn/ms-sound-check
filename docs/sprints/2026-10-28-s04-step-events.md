# Sprint 4: Step events

- **Dates:** 2026-10-28 to 2026-11-04
- **Status:** In progress
- **Goal:** Say when the Sound's water changed all at once, and keep a single bad sensor from looking like news.

## Checklist
- [x] Step detector and event matching ([0016](../decisions/0016-step-events-need-matching-stations.md)), `msc/models/steps.py`
- [x] `salinity_steps` indicator in `regions/ms.yaml`; the stations involved show it on their pages
- [x] Tuned on 1998-2026: about 5 events a year; catches Ida, the 2019 spillway closing, Francine, Zeta and October 2026
- [ ] Wind explanation for each event (next roadmap item)
- [x] Events across three or more stations lead the Oysters and Fishing headlines (short form); two-station events stay in Signals
- [ ] Settle the Round Island caveat (see notes)

## Notes
- 2026-10-28: Round Island went from 17.6 ppt to 36.2 ppt on Oct 14-15 and then read 37-40 ppt. Merrill Shell Bank
  stepped from 7 to 24 ppt on the same days while rivers were low and the wind was calm, so the jump looks real at
  two stations. 40 ppt is above what the Gulf should carry, so the Round Island numbers are still doubtful.
- 2026-10-28: MDMR's shellfish area maps are wanted on the oyster map (roadmap, Later).
