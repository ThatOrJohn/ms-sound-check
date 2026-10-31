# 0045: Grand Bay NERR as a reference reading from NDBC, not a station

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
The roadmap asked for the Grand Bay NERR sondes as extra stations in the eastern Sound. The NERRS CDMO web service has
the full record back to 2004, but only answers registered IP addresses, which GitHub Actions doesn't have; its bulk
download is a manual form. NOAA's National Data Buoy Center republishes two of the reserve's sondes with salinity,
temperature and dissolved oxygen every 15 minutes: Bangs Lake (GDQM6) and Bayou Heron (GBHM6). NDBC keeps 45 days
(`/data/realtime2/<ID>.ocean`) and no history for them.

## Decision
- Ingest Bangs Lake's daily mean salinity (12 hours of readings or more) as a reference site, `NDBC-GDQM6`
  (`msc/adapters/ndbc.py`), and show it like Dauphin Island ([0019](0019-disl-reference-data-no-auto-flag.md)):
  a chip at the map's east edge, "Reference, 15 km east of East Sound". Not a card, not a model input, not in the sketch.
- Leave Bayou Heron out: it's a bayou upstream in the marsh, further from the Sound.

## Why
- A station card needs years of history for "vs. normal" and the year dots; without CDMO there's none, and the
  virtual sensors and step detector would take a new neighbor with no record.
- Bangs Lake is a marsh lagoon, not open Sound, so even with history it would be a reference, not one of our stations.
- It's still the closest independent reading to Round Island. On 2026-10-30 it read 29.5 ppt while Round Island read
  about 37: more evidence that Round Island's readings over 36 ppt are the sensor, though a lagoon isn't proof.

## Consequences
- The record builds forward from 2026-10-30. After a year or two, revisit a Round Island gap check like the one tried
  with Dauphin Island in 0019, or ask CDMO for an export and backfill.
- Dissolved oxygen is in the same file: the low-oxygen watch (Moonshot 3) can start from it.
- Reference chips now sort west to east, so Grand Bay comes before Dauphin Island.
