# Sprint 3: Persona utility

- **Dates:** 2026-10-28 to 2026-11-04
- **Status:** In progress
- **Goal:** Each persona's page answers the question that reader shows up with.

## Checklist
- [ ] Verify the first live beach fetch in CI (carried from Sprint 2)
- [ ] **Oyster closure watch** ([0012](../decisions/0012-oyster-watch-criteria.md))
  - [x] Find MDMR's criteria and the gauge (PERL1 / USGS 02492600, 10 and 11 ft, plus rainfall triggers)
  - [x] Ingest PERL1 observed + NWS forecast stage (`msc/adapters/nwps.py`)
  - [x] Backfill PERL1 daily stage history from USGS 02492600 (runs with `backfill`)
  - [x] Indicator: stage vs. each area group's threshold, with forecast crossing time, plus rainfall triggers
  - [x] Oyster page section: stage bar with closure levels, table by area group, rain, links to MDMR
  - [x] Gauge station page: stage history with MDMR closure lines and the NWS forecast as a dashed line
  - [x] Wording only ever says what MDMR's criteria indicate; never "is closed"
  - [ ] Verify the first live NWPS fetch and the PERL1 backfill in CI
  - [ ] Confirm the oyster information line (228-374-5167 comes from MDMR notices; check it's current)
  - [ ] With history in hand: how often each threshold is crossed per year (context line for the section)
- [ ] **Fishing weekend outlook**: wind (NWS forecast), tides (CO-OPS 8747437, 8745557, 8741533), muddy-water risk, water temperature trend
- [ ] **Wind in the data**: ingest, add to virtual sensors, re-score
- [ ] **Shrimp in-season**: MDMR notices (check whether their WordPress API is readable), 3-day wind outlook

## Notes
- 2026-10-28: Oyster watch built and checked with simulated readings (rising river forecast to cross 10 ft).
  Rainfall uses an Open-Meteo point in Hancock County as a stand-in for the HCUA gauge; labeled as an estimate.
- 2026-10-28: The plan names "Pearl River, Louisiana" as the gauge, not Bogalusa as first assumed.
  PERL1's flood categories start at 12 ft, so the oyster thresholds sit below anything a flood map shows.
- Rainfall triggers use a Hancock County Utility Authority gauge (Areas I-B, II-A/B/E/F/G) and Keesler AFB
  (Area V-A). Keesler is NWS station KBIX; the HCUA gauge needs a public source or an honest approximation.
