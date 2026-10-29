# 0037: The Sound west to east, as one bar

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The roadmap asked for "one gradient bar from the Pearl River mouth to East Sound, each station placed by where it sits,
with a faint band for typical": the whole Sound at a glance, and a share image. The map already colors each station,
but you have to read the dots one by one, and it doesn't show what's usual.

## Decision
- `SoundStrip.astro`, a `strip` section in each persona's `card_order` (right after the persona's own section).
  The model is `web/src/lib/strip.ts`, shared with the share image.
- Stations are the map's: salinity stations, with retired ones only while we publish an estimate. Each sits at its
  longitude, scaled so the westmost and eastmost fill the bar.
- **Today** blends live readings and published estimates. Suspect readings are labeled with a "?" and a hollow dot but
  don't color the bar. Outside the first and last station with a usable value the bar is blank, not stretched, so a
  missing East Sound doesn't look like it matches Back Bay. **Usual** is a thinner, fainter bar of each station's
  median (`normal.p50`) for this time of year.
- The summary line uses the readings table's own band words ("Much saltier than usual at …; a bit saltier than usual
  at …; about normal at …"), so it can't sound stronger than the rest of the page.
- Labels: west-half stations above the bar, running right; east-half below, running left. In each half the station
  nearer the middle takes the row nearest the bar. That way no leader line crosses a label at any width, with no
  script to measure text.
- Text version: the bars are one `role="img"` whose label lists every station west to east, today and usual. Names
  and values are real text and link to station pages.
- Share image: a persona with `share: strip` in `regions/ms.yaml` gets the strip instead of the readout tiles.
  Oysters uses it. Coast keeps the history picture (0028).

## Why
- One bar answers "where is the river water?" faster than five dots, and the usual bar answers "is that odd?".
- Blending between stations is honest only if the page says so: the key under the bar says the colors in between are
  blended, not measured.
- Static HTML and CSS, colors from the same `salinityFill` as the history picture, so both themes follow the tokens.

## Consequences
- The page is about 390 px taller at 1360 px (home 4,972 → 5,362 after 0036).
- Dauphin Island (the out-of-state reference, 0019) is left off: at its longitude it would squeeze the Mississippi
  stations into the western two-thirds of the bar.
- If stations are added near each other (Grand Bay), labels stay apart by row, so the section grows a row per station.
  Past about eight stations, switch to a list under the bar.
