# 0028: Every year on record: history picture, record lines, years like this one

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The store has daily readings back to 1998, but the site used them only for normal bands and percentile meters. Three
features now use the full record, and each needs the same answers to three questions: which readings count, which
years count, and how far a comparison may go.

## Decision
- **Shared rules** (`msc/history.py`): measured readings only (the daily store holds no virtual-sensor estimates);
  readings `is_suspect` rejects are dropped, and so are a station's last 3 days when virtual-sensor QC flags it
  (QC looks at 3 days). A past year with readings on under 80% of its days is left out of every count, rank and
  match. The current year always counts, because it is today.
- **History picture**: one row per year, 366 columns (Feb 29 empty in common years so March lines up), in
  `history/<slug>.json`, apart from `latest.json`. Years under 80% are still drawn, faded, and the table marks them
  "not counted": hiding measured data would be less honest than showing it as partial. The home takeaway compares
  days under 5 ppt and over 25 ppt at the configured station, naming a spillway year from `spillway_openings.csv`
  when one is the natural comparison.
- **Record lines** (`type: record`): each year's mean of the same 14 calendar days ending today, with at least 10
  days of data, and at least 10 such years. Only a top-3 or bottom-3 rank becomes a `notice`. It replaces the
  `vs_normal` finding for the same station and variable, and gives way to anything stronger (e.g. the oyster
  freshwater-stress alert). "Since" is the first year that made it into the ranking. Water temperature is left out
  until its trend question is settled.
- **Years like this one**: root-mean-square difference of daily log10 flow over the last 60 days, Pearl and
  Pascagoula together, against the same 60 days in every past year that counts for both; at least 50 days each,
  at least 10 years compared, and nothing named past an RMS of 0.5. It's shown as background only and never says
  what followed in those years (0008).

## Why
- A 14-day window is long enough that a single day can't set a record, and short enough to describe "now". A
  top/bottom 3 out of ~25 years is rarer than the p10/p90 that `vs_normal` already says, so it only speaks when it
  adds something. Checked: on 2026-10-28 the Pearl is 3rd-lowest (after 2000 and 2010); on 2019-06-02 Pearl flow
  and stage are the highest.
- Log flow treats a doubling the same at 500 cfs and 50,000 cfs, which is how the Sound responds. On known dates the
  matches look right: 2026-10-28 gives 2016, 2023, 2010; spring 2019 gives 2008, 2003, 2018 (two spillway years);
  fall 2021 gives 2012, 2005, 2001 (Isaac, Katrina, Allison); the 2000 drought has too few earlier years and shows
  nothing.
- The 80% rule keeps a year with a summer-long gap from looking unusually fresh or salty in the counts.

## Consequences
- Station pages get a long-term picture, and a #year-YYYY link picks that year on the salinity chart.
- `data/notable_years.csv` is hand-kept, like the spillway list. Its notes say what happened, never what it means now.
- Update 2026-10-28: years under 80% now sit in their own "partial years" group below the counted ones instead of
  being faded in place, notable years carry a short tag in the right margin (from `notable_years.csv`'s `tag`
  column, plus every spillway year), and a full-height line marks today's date ([0033](0033-salinity-sketch-and-the-long-replay.md)).
- Revisit "years like this one" as a forecast only if a backtest shows what followed in matching years beats
  persistence. Revisit water temperature records once the trend question has an answer.
