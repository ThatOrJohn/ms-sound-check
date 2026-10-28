# 0022: The spillway watch reads the river, not the gates

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Bonnet Carré Spillway openings are the biggest single freshwater event the western Sound sees: in 2019 two openings
(43 and 79 days) kept it fresh for months and killed most of the oysters on its reefs. People on the coast want to know
whether one is coming. Sources checked on 2026-10-28:

- No public feed reports whether the spillway is open or how many bays are. The Corps' water-data API (CWMS, office MVN)
  has stage series for the river beside the structure and at New Orleans, but none for the structure's flow or bays, and
  all its MVN series stopped updating on 2026-09-14. USGS has no gauge in the spillway channel.
- The Corps' New Orleans District site refuses automated requests (HTTP 403). We don't work around that.
- The NWS gauge NORL1 (Mississippi River at New Orleans, Carrollton) has observed stage and a two-week official
  forecast through the same NWPS API as the Pearl River gauge. The Corps opens the spillway to hold the river near
  1.25 million cfs at New Orleans, which is about 17 ft at Carrollton, the gauge's flood stage.
- The opening history (15 openings, 1937-2020, plus a one-bay test in April 2025) is published by the Corps and
  repeated on Wikipedia.

## Decision
Watch the river, not the gates:
- Observed stage and the NWS forecast at NORL1, compared with 17 ft (`open_ft`) and 15 ft (`watch_ft`) in the region
  file. The findings say the river is at or forecast to reach "the level where the Corps has opened the spillway"; they
  never say it is open. Forecast to reach 17 ft is a watch, at or above it a warning, within 2 ft a notice.
- Past openings in `data/spillway_openings.csv`, kept by hand like the shrimp season dates. A row with a blank `days`
  means it's open now, and only then does the site say so.
- What our West Sound station did during each past opening: the median salinity in the month before, and the lowest
  value during the opening or the two weeks after.

## Why
The river forecast is the only live, public, machine-readable signal, and it leads: openings follow forecasts of
minor flood stage at New Orleans. Saying "open" from the river alone would be wrong, since the Corps decides on
forecasts, flows and other factors.

The before/low comparison is our own data, which nobody else puts next to the spillway. It shows real drops (West
Sound from about 16 ppt to 0.6 in spring 2019) but can't separate the spillway from the local rivers, which were often
high in the same springs. The page says so.

## Consequences
- Someone has to add a row when the Corps opens the spillway and fill in `days` when it closes (QUICKSTART calendar).
  Until then, the river finding still fires at 17 ft.
- If the Corps publishes a live structure-flow or bay-count series, use it and supersede this record.
- `open_ft` is a rule of thumb. If a future opening happens at a clearly different stage, revisit it.
