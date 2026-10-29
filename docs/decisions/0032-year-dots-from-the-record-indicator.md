# 0032: Year dots come from the record indicator

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
"Third-lowest late-October flow since 1998" is a sentence (0028). The roadmap asked for the same fact as a picture:
one dot per year for today's date, today ringed, with the highest and lowest years named. If the picture and the
sentence ever disagreed about the rank, both would lose trust.

## Decision
- `indicators.record_means` computes each year's mean over the `record` indicator's window (14 days ending on
  today's date, at least 10 of them, years under 80% coverage left out, at least 10 years). Both the record line
  and `build._year_dots` call it, so the dots are the same numbers the sentence ranks.
- Every reading a `record` indicator covers (river flow, Pearl stage, Sound salinity) carries `years`: the
  points, `rank_high`, `rank_low` and `of`. Stale or suspect readings get none.
- `YearDots.tsx` is plain SVG drawn at build time: values across (log scale for flow), the middle half of the years
  shaded, a small beeswarm so dots don't overlap. `lib/yeardots.ts` adds the hover and tap readout with one
  delegated listener, since the dots have no island of their own.
- The sentence under the dots is the text alternative. The long form says it's a window average ("14-day average
  26.2 ppt: 3rd highest of 14 years for late October") because it sits next to today's reading, which is a
  different number. The short form in tiles and Signals leaves the value out.
- They show under each ranked reading on station pages, under record lines in Signals, in the instrument table
  (0035), and in place of the meter in the river flow tiles.

## Why
- One function means the agreement is structural, and `tests/test_record.py` checks it on made-up series. The e2e
  test checks it on the built page.
- The first version printed "1,524 cfs, 3rd lowest" beside a 1,491 cfs reading, which read as a mistake. Labelling
  the window fixes that without inventing a second ranking for single days.
- The tiles still read at phone width (checked at 412 px in both themes), so they kept the dots.

## Consequences
- Adding a `record` indicator for another variable gives it dots with no web changes.
- Water temperature still has no record indicator (0028), so it keeps the percentile meter.
