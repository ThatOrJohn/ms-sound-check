# 0021: Smaller rivers are shown, not weighed

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The site only knew the Pearl and Pascagoula, so the headline said "Both rivers" and the map left out the rivers that
empty into the Bay of St. Louis and Biloxi's Back Bay. Live USGS flow gauges in the coastal counties (checked 2026-10-28):

| River | Gauge | Daily flow record | Live |
|---|---|---|---|
| Wolf | 02481510 near Landon | 1971- | yes |
| Biloxi | 02481000 at Wortham | 1952- | yes |
| Jourdan | 02481660 near Bay St. Louis | tidal, to 2004 | no |
| Escatawpa | 02479560 near Agricola / 0248018020 at I-10 | to 2020 / tidal | no |
| Tchoutacabouffa | none | | |

Median daily flow since 1998: Pearl 4,720 cfs, Pascagoula 4,830, Wolf 239, Biloxi 56.

## Decision
Add the Wolf and Biloxi as river sites with `minor: true`. Minor rivers get a card, a map line, a place in the
station list, and count toward the fishing outlook's muddy-water risk. They stay out of:
- the headline's direction (the big rivers decide it; a minor river is named only when it runs the same way),
- the home page's readout tiles,
- the virtual-sensor inputs (`msc/models/virtual.py`).

The ungauged rivers are listed under `ungauged_rivers` in the region file. They're drawn dashed and named on the map,
with one sentence under the river cards.

## Why
- At 1-5% of the big rivers' flow, letting the Wolf or Biloxi tip "the rivers are running high" would mislead about the Sound.
- Adding them to the virtual sensors changes the models' features. The live models were trained without them, so
  adding them would need a retrain and an experiment run first. They might help Back Bay (Biloxi River) and West
  Sound (Wolf); that's a test to run, not an assumption.
- Fishing cares about muddy water near river mouths, and that's local, so the small rivers belong there.

## Consequences
- River lines and label points now come from `web/public/basemap/rivers.geojson` (`python -m msc rivers`, OpenStreetMap
  via Overpass), not the vector tiles: at the Sound-wide zoom (z8) OpenMapTiles keeps only the Pearl, and MapLibre
  won't fetch vector tiles one zoom deeper. This also fixed the missing Pascagoula line.
- The Wolf can raise its own "running low/high" signal through `river_vs_normal`.
- New gauged rivers need the `backfill` workflow task for their history and normals; until then the cards show flow
  without a "typical" comparison.
- Revisit if an experiment shows the Wolf or Biloxi improving the Back Bay or West Sound virtual sensors.
