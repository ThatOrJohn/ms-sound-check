# 0038: Past spillway openings side by side

- **Status:** Accepted (Moonshot 2; replaces the "effects" list from [0022](0022-spillway-watch-from-the-river.md))
- **Date:** 2026-10-28

## Context
When the Mississippi nears 17 ft at New Orleans, people on the coast ask what happened to the Sound last time. The
spillway section answered with three lines of text (salinity the month before, the low during). The daily store
already holds West Sound (Merrill Shell Bank, `spillway.sound_site`) salinity around most openings since 2000, and the
station's day-of-year normals.

## Decision
The Bonnet Carré section shows one small chart per year with openings since 2000, all on the same axes: days from 4
weeks before the year's first opening to 28 weeks after, salinity 0 to the highest value in any year. Each chart shades
the open spells, draws a dashed typical line (the station's median for that day of year), marks 2 ppt, and has one
sentence: the median of the 4 weeks before, the low and how long after the opening it came, and the longest run of
days under 2 ppt. The sentence is also the chart's text version. `spillway.past` in latest.json replaces `effects`.

## Why
- Small multiples on one scale let the eye compare years without reading numbers. On today's data: 2011 dropped to
  1.1 ppt 4 weeks after opening and stayed under 2 ppt for 8 days; 2016 reached 0.5 ppt; 2019's two openings (122
  days) held West Sound near 0.3 ppt for 19 days in a row; 2020 never went under 5.5 ppt.
- A fixed 28-week span shows recovery as well as the drop, and fits 2019's second opening (closed on day 151).
- 2 ppt is the `oyster_fresh_stress` threshold already on the site (reefs start dying past two weeks under it), so the
  charts and Signals agree. Runs end at a missing day, so a gap never counts as fresh.
- Years with too few readings are left out and named (today 2008 and 2018) rather than drawn from scraps: at least 10
  daily values before the opening and 60 after.

## Consequences
- These are past openings, not a forecast, and the text says so; [0008](0008-no-salinity-forecast.md) still holds. The
  note that coastal rivers were often high in the same springs stays.
- While the river is low the charts sit inside the folded section from [0036](0036-one-history-picture-and-a-folded-spillway.md),
  so home height is unchanged. When the river reaches the watch level they show with no setting to change.
- latest.json grows about 3.5 KB per year shown (14 KB today). A new opening shows up as a chart on its own once it has 60 days of
  readings after it.
- Revisit if a station closer to Lake Borgne gets a long record, or to add the oyster stations as a second row.
