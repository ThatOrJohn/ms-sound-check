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
- [x] **Fishing weekend outlook** (Fishing page): per-day wind with a plain verdict, sky, rain chance, tides at
      Gulfport Harbor (all three stations in a table), water temperature trend, saltiest/freshest station,
      muddy-water risk; best day becomes the Fishing headline. Shows this weekend, or the next three days
      on Sun/Mon.
  - [ ] Verify the first live NWS forecast and CO-OPS tide fetches in CI
- [x] **Wind in the data**: daily wind over mid-Sound (Open-Meteo: ERA5 history at backfill, recent each run);
      six wind features added to the virtual sensors
  - [ ] After the next backfill, compare the `train` log's scores with the numbers in architecture.md and
        record the result here
- [x] **Shrimp in-season** ([0014](../decisions/0014-mdmr-notices-from-wordpress-api.md)): MDMR's shrimp notices from its
      public WordPress API (last year, newest five, linked), 3-day day/night wind outlook from the NWS forecast; a
      notice from the past week leads the Shrimp headline
  - [ ] Verify the first live MDMR fetch in CI

- [x] **Air temp shows the latest reading**: the readout tile led with today's daily mean (61°F at noon on a cool
      morning that warmed to 77°F). The build now adds the newest NWS observation with its time and today's low/high
      (`"now": True` in `VARIABLES`), hidden after 4 hours; the station page labels the daily value as an average.
  - [x] Refresh it in the browser on load from api.weather.gov ([0015](../decisions/0015-live-air-temp-in-browser.md));
        checked live: built 75°F at 11:05 AM became 79°F at 1:20 PM
- [x] **UI refresh** ([0013](../decisions/0013-instrument-panel-design.md)): Geist, new palette, readout strip, signals rail,
      percentile meters, segmented controls. Axe passes on every page in both themes. Sample data for review:
      `python scripts/dev_fixtures.py apply` (and `clear` afterward).

## Notes
- 2026-10-28: MDMR's WordPress API (`dmr.ms.gov/wp-json/wp/v2/posts`) is open, with no bot challenge. Category 6 plus the title
  filter `shrimp season|shrimping` returned 19 clean notices for 2021-2026. The notices could also check
  `data/shrimp_openings.csv` ("shrimp season opens <date>" titles); not done yet.
- 2026-10-28: Wind verdict bands (NWS forecast's upper sustained mph): light ≤10, moderate ≤15, breezy ≤20,
  windy above. Muddy-water risk is a stated heuristic: 3-day coast rain (≥0.5 / ≥1 in), rivers above normal,
  forecast rain ≥1 in.
- 2026-10-28: Oyster watch built and checked with simulated readings (rising river forecast to cross 10 ft).
  Rainfall uses an Open-Meteo point in Hancock County as a stand-in for the HCUA gauge; labeled as an estimate.
- 2026-10-28: The plan names "Pearl River, Louisiana" as the gauge, not Bogalusa as first assumed.
  PERL1's flood categories start at 12 ft, so the oyster thresholds sit below anything a flood map shows.
- Rainfall triggers use a Hancock County Utility Authority gauge (Areas I-B, II-A/B/E/F/G) and Keesler AFB
  (Area V-A). Keesler is NWS station KBIX; the HCUA gauge needs a public source or an honest approximation.
