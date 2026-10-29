# 0029: No "likely after rain" beach heads-up

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The roadmap proposed a note between MDEQ's weekly samples: how often advisories follow heavy rain, and how soon. Our own
`beach_history.parquet` starts in October 2026, so we tested on MDEQ's past enterococcus samples from the Water Quality
Portal (organizations 21MSWQ_WQX and 21MSBCH, Hancock, Harrison and Jackson counties, 2015-2025, about 14,000 results
at the coast's beach sites). A sample over 104 per 100 mL counts as over the swimming limit, the level MDEQ is reported to
use ([Swim Guide](https://www.theswimguide.org/beach/4708)). Resamples after a high result were dropped (only samples with
no earlier sample at that beach in 5 days), leaving 9,278 routine samples. Rain: our Open-Meteo points at Biloxi and
Hancock County.

## Decision
Don't build the heads-up. Park it on the roadmap with these numbers.

## Why
- 2015-2021: after 1 inch or more over the 2 days before sampling, 38% of routine samples were over the limit, against
  18% in dry weather. That would have supported a note.
- 2022-2025: 17% after an inch or more, against 12% dry (Biloxi rain; Hancock rain gives 19% vs. 13%). Rain of 2 inches
  or more did no worse than 1 inch (15-18%). The effect has mostly faded, and there's no dose-response.
- A note built on all years would overstate today's risk by about double. "Likely" was never supported: even in the
  early years, most samples after heavy rain came back fine.
- Per-beach rates rest on 40-55 wet samples each, too few to name the beaches that react most.

## Consequences
- The Beaches section keeps showing only MDEQ's own status. No new source.
- Revisit after another year or two of samples, or with a closer rain gauge. If the post-2021 change has a known cause
  (sewer work, a change in sampling), that's worth noting here.
