# 0043: Oyster growing areas on the map as MDMR's classes, never open or closed

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
The closure watch names areas (I-B, II-A, II-E) that readers can't place. MDMR publishes `Oyster_Harvest_Zones` on its
public ArcGIS Online account (`services5.arcgis.com/CYWvDQNfmlrPP5Rh`): 83 polygons, each with `ZONE_ID`
('Area II "E"') and `CONDITIONS` (approved, conditionally approved, restricted, prohibited, unclassified). It's a
plain feature service with no bot check, like MDEQ's beach layer ([0011](0011-beach-status-from-feature-service.md)).

The same layer has a `Status` field. On 2026-10-30 it was last edited 2026-07-06 and still said "Closed" for I-B, II-B,
II-E and V-A, which MDMR reopened on October 15-19.

## Decision
- Read only `ZONE_ID` and `CONDITIONS` (`msc/adapters/shellfish.py`), simplified to about 30 m. Never read `Status`.
- Draw an "Oyster growing areas" map layer: ink outlines told apart by line pattern (solid approved, dashed
  conditionally approved, dotted and faint for the rest), the area name on the biggest piece of each approved or
  conditional area, and a popup with MDMR's name, the class and what it means. No fill, no red or green.
- On by default for Oysters, alongside the salinity sketch. Hidden while replaying a past day.
- The key and popup say the class isn't whether an area is open today, and give the date MDMR last edited its map.

## Why
- The class is stable and checkable against MDMR's management plan; the `Status` field is neither. Showing it would
  have told readers four reopened areas were closed, and it would break the oyster wording rule.
- Red and green fills read as open and closed at a glance whatever the key says. Outlines in ink don't, and they sit
  over the salinity sketch, so readers see where fresh water is next to which areas MDMR opens by river stage.

## Consequences
- The snapshot hides after 7 days without a good fetch, and the GeoJSON is removed with it.
- About 140 KB of GeoJSON, fetched only when the map loads.
- The same account has the season's tonging boxes, cultch-plant marker buoys and closed harvest areas (edited
  2026-09-15). They're left out for now: they change each season and need their own wording. Add them if readers ask.
- If MDMR renames the fields or classes, unknown classes are dropped and the layer may go empty: the fetch then fails
  through `_try` and the layer disappears after a week.
