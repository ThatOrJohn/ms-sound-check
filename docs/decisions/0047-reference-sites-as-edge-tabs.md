# 0047: Reference sites as edge tabs that point at the site

- **Status:** Accepted
- **Date:** 2026-10-31

## Context
Dauphin Island ([0019](0019-disl-reference-data-no-auto-flag.md)) and Grand Bay ([0045](0045-grand-bay-as-reference-from-ndbc.md))
were three-line chips stacked under the Layers panel at the map's lower right. With two of them, they covered a good
part of the eastern Sound, East Sound and Pascagoula included, and they stayed put however the map moved, even when
Grand Bay (just past the default view's east edge, inside the pan limits) was on screen.

## Decision
Each reference is a one-line tab ("REF Grand Bay 29.5 ppt") placed like an off-screen pointer in a game: on the map
edge nearest the site, level with it, with a caret pointing toward it. It follows the site as the map pans and zooms,
and when the site comes into view the tab sits just above it with the caret pointing down. Hover, keyboard focus or
a tap opens the note ("Reference, 15 km east of East Sound"); folded, the note stays readable to screen readers.
Each tab takes the nearest free spot to its site's line, clear of the Layers panel, zoom buttons, river panel, station
dots and labels, and the other tab. Phones keep the text strip under the map.

## Why
- These sites really are east of the map, so a tab on that edge pointing that way says where they are. The old chip
  only said it in words.
- One line covers about a third of what the old chip did, and avoiding station labels keeps it off the readings.
- Placing the tabs from `map.project` on each move, in a single animation frame, costs nothing noticeable and needs
  no MapLibre layer. A layer would draw them like stations, which 0019 rules out.

## Consequences
- Positions come from code, not CSS, so the tabs are hidden until placed. If the map fails to load, desktop shows no
  reference readings. The About page still describes both sites.
- A third reference site would just be another tab. With many it would need grouping.
- The station-label boxes are estimated (label to the right of the dot, about 135 by 40 px). If labels change
  size or side, update the estimate in `SoundMap.tsx`.
