# 0016: Salinity step events need matching stations

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Salinity at a station can jump by 10+ ppt in a day or two. A single sensor doing that is as likely to be a
fouled or recalibrated probe as a real change; we already treat readings past 36 ppt as suspect. Daily salinity
is noisy (the 95th percentile of day-to-day change is about 3-5 ppt), so a plain "big change" rule fires constantly.

## Decision
`msc/models/steps.py` flags a station as stepping when its last three days all sit well beyond the median of the
seven days before them (at least half the shift, and a shift of 3 ppt or more). A finding appears only when two
or more stations step the same way with onsets within three days, and at least one step is 6 ppt or more.
QC-suspect readings are masked first. The finding lasts a week from onset, is recomputed every build, and is a
`notice`; the wording says what matching steps usually mean, not that they prove it. An event across three or more
stations also leads the Oysters and Fishing headlines (in a short form); it never leads the General or Shrimp ones.

## Why
Run over 1998-2026 on the four active stations, 3 / 6 ppt gives about 5 events a year, so a notice shows roughly
a tenth of the time. It catches Ida (2021-08-31, down at all four), the 2019 spillway closing (2019-07-07, up at
all four), Francine and Zeta. A single threshold did not work: 4 ppt for every station gave about 8 events a year
and missed the October 2026 event, where Merrill Shell Bank rose 18 ppt and Point Cadet (Back Bay) rose 4.
Round Island's readings were past the QC ceiling, so masking removed it as a witness.

## Consequences
- Detection lags onset by about two days (it needs three days of "after" data), and longer when a station has gaps.
- Nothing is stored: events are not kept, and a step older than a week disappears.
- No cause is attached yet. Wind (and river flow) explanations are the next roadmap item.
- Thresholds are specific to salinity, and the 6 ppt lead is a judgment from this history. Revisit them if the
  event rate drifts, or if Gulfport Light and East Ship Island return as stations.
- A pair of stations is the minimum, and a pair can be a coincidence, so only three or more reach a headline.
- Headline promotion is the `lead` field on a finding; a finding with `lead` is never picked up as a persona's own model.
  Before this, any finding without a station and with a matching topic reached those headlines.
