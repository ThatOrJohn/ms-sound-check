# 0019: Keep Dauphin Island Sea Lab salinity as reference data, with no automatic flag

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Round Island read 36-40 ppt from Oct 15, 2026, and nothing nearby corroborated it. GCOOS ERDDAP serves Dauphin Island
Sea Lab (`DISL_DISL`) hourly salinity back to 2008, with a QC flag, no key. We tried it as an automatic check: flag
Round Island when it runs far saltier than its usual gap to DISL.

## Decision
- Ingest DISL daily means into the store as a reference site (`GCOOS-DISL_DISL`, `reference:` in `regions/ms.yaml`,
  `msc/adapters/gcoos.py`). It is not a card and not a model input.
- Do not flag stations from the gap to DISL. The "possibly a sensor problem" caveat keeps resting on the QC ceiling.

## Why
Gap (Round Island minus DISL), daily, 2008 to Oct 14 2026 (4,872 days): median +1.7 ppt, 95th percentile +10.5,
99th +14.7, maximum +21. Since Oct 15 it has been +8 to +17, mostly +11 to +13, inside what the two have shown before.
Three days in a row above the 99th percentile happened in 2009, 2017, 2022 and 2024, mostly real events. DISL is on the
Mobile Bay side, so the pair diverges for real reasons. A threshold tight enough to catch this week would fire on genuine
events; a safe one wouldn't catch it. DISL neither confirms nor refutes the sensor.

What does hold: KATA's highest daily value in 15 years is 34.9 ppt, so 36-40 ppt is above what the region carries.

## Consequences
- Free reference data for the Mobile Bay side, and for a later check against a closer station.
- One more source call per run, through `_try`; a failure only skips the reference rows.
- Revisit if a closer independent station (for example Grand Bay NERR) gives a tighter gap.

## Update 2026-10-28: shown at the map's east edge
DISL (30.2513, -88.0778) is about 2 km past the basemap's east edge (-88.1) and well past the default view, so it
appears as a text chip pinned to the map's lower right ("Dauphin Island, AL → 24.1 ppt, Reference, 50 km east of
East Sound"), and on phones as a line in the strip under the map. It has no dot and stays out of the salinity sketch,
so it can't pass for one of our stations or bend the interpolation across a different part of the Sound. Its daily
mean hides once it is more than 3 days old (`REFERENCE_MAX_DAYS` in `msc/build.py`) and during replay.

