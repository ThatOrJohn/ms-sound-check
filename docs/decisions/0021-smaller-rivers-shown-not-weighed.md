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

## Update 2026-10-29: the experiment says keep them out
`scripts/experiment_minor_rivers.py` in CI (`experiment` task, run 40816456411). MAE in ppt with the minor rivers
added minus without; negative means they helped. "Fresh" is days under 8 ppt.

| Station | Test | Overall | Fresh days (n) |
|---|---|---|---|
| West Sound | last two years | -0.12 | -0.41 (45) |
| West Sound | 2019-2020 | +0.29 | +0.61 (125) |
| Biloxi Back Bay | last two years | +0.31 | +0.18 (56) |
| Biloxi Back Bay | 2019-2020 | -0.23 | +0.19 (123) |
| East Sound | last two years | -0.16 | -0.21 (6) |
| East Sound | 2019-2020 | +0.15 | +0.18 (63) |
| Pearl River mouth | last two years | +0.03 | +0.05 (424) |
| Pearl River mouth | 2019-2020 | +0.06 | +0.11 (606) |

No station gains in both periods, and on fresh days, where a small river should matter most, they made things worse in
5 of 8 cases. The one helpful line (West Sound, recent fresh days) reverses in the spillway years. The rivers stay
out of the virtual sensors. Rerun only if a station closer to a river mouth (Grand Bay, a Bay St. Louis gauge) is added.
