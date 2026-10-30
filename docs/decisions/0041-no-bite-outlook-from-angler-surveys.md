# 0041: No "fish are biting" outlook from angler surveys

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
We wanted to know whether conditions we already measure (salinity, water temperature, rivers, wind, rain, water level,
moon) say anything about whether anglers catch fish, which could feed the fishing outlook.

Mississippi's own catch reporting doesn't help. Tails n' Scales (red snapper trip reports) publishes no data, and
tailsnscales.org now says it's no longer in operation. Its successors, the Recreational Offshore Landing Permit and the
MS CREEL weekly survey, publish nothing either. The only public figures are yearly snapper totals against the state
quota on NOAA's exempted fishing permit page.

NOAA's Marine Recreational Information Program (MRIP) does publish its dockside angler interviews as free CSV files
([public-use survey data](https://www.st.nmfs.noaa.gov/st1/recreational/MRIP_Survey_Data/CSV/)). Each row has a date,
a county (where the angler landed, not where they fished), mode, area, the species they were fishing for, and fish kept
and released. Mississippi has 51,958 interviews from 2000 to 2025, all in Hancock, Harrison and Jackson counties.
Estimates for a two-month wave come out about 45 days after it ends, so this can only ever explain, not forecast.

`scripts/probe_mrip_bite.py` takes the anglers who said they were fishing for a species and asks whether they caught
at least one. It matches each interview day to our daily store, using the county's nearest USGS station. It then
scores each condition by how much it improves a season-only model (month, county, mode, area, year trend), leaving out
one year at a time.

## Decision
Don't build a bite outlook or "good fishing conditions" score. Park it on the roadmap with these numbers.

## Why
- **Season itself is weak.** Month, county and mode improve on a flat average by only about 2% for speckled trout
  (13,106 trips, 51% caught one) and 4% for redfish (7,755 trips, 30%).
- **No condition clears the noise.** For six species (speckled trout, redfish, flounder, white trout, sheepshead, red
  snapper) and 14 conditions, the best improvement was under 1%. The best for trout was mean wind (0.18%, better in 20
  of 26 held-out years). Flounder, sheepshead and snapper stayed under 1% even with their much smaller samples.
- **The steadiest patterns are too small to tell anyone.** Within the same month and county, trout trips on the
  saltiest third of days caught one 4.5 points less often than on the freshest third (95% CI 1.4 to 7.6). Windy days
  were about 3 points worse for trout and 7 for flounder. With 84 species-condition pairs, a few such intervals will
  exclude zero by chance.
- **County is a confounder.** Ranked within month only, salinity looked like a sharp threshold. Part of that was
  Jackson County: its station reads saltier, and its trout anglers catch less overall (48% against 53-56%).

## Consequences
- The fishing outlook stays as conditions only: wind, sky, tides, waves, sun and moon (0040). It makes no claims about
  bites.
- Rerun if a finer catch source appears: MS CREEL estimates if MDMR publishes them, or catch rates with a known fishing
  location. A different outcome (fish per hour, or kept fish only) is worth one more try with the same script before
  giving up on MRIP entirely.
