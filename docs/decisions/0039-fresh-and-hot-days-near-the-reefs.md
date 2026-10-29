# 0039: Fresh-and-hot days near the reefs

- **Status:** Accepted (Moonshot 1)
- **Date:** 2026-10-28 (built 2026-10-29)

## Context
Fresh water hurts oysters most in summer. The site already has `oyster_fresh_stress`: a run of days under 2 ppt, any
time of year. What it can't show is the slower summer squeeze: water that is only somewhat fresh but hot, for weeks.
The roadmap asked for a count of those days this year against every year since 1998, with the thresholds checked
against published studies first.

The daily store has salinity and water temperature at four stations: East Pearl River (2001 on), Merrill Shell Bank
(1998), Point Cadet in Back Bay (2000) and Round Island (2009). Gulfport Light and East Ship Island have salinity only.

## Decision
A **fresh-and-hot day** is a day when a station's daily mean salinity is under 5 ppt *and* its daily mean water
temperature is above 25 °C, both measured at that station. For each of the four stations the oyster view shows the
count so far this year, the longest run of such days in a row, and how that compares with the same station's past
complete years. The wording describes the water near the reef, never the reef's harvest status.

## Why
**The thresholds come from Gulf studies.**
- La Peyre et al. 2013 (Breton Sound, LA): the 2010 die-off followed salinity under 5 that lasted into July, when
  water topped 25 °C. A shorter low-salinity spell in 2011 ended before July and had little effect on mortality. This
  is the source of the 5 ppt / 25 °C pairing and of the point that timing matters.
  [doi:10.1016/j.ecss.2013.10.001](https://doi.org/10.1016/j.ecss.2013.10.001)
- Rybovich et al. 2016 (lab, same group): at salinity 5, all size classes lost more than half at 32 °C and under 40% at
  25 °C. At salinity 1, seed and market oysters all died within 7 days at either temperature. So 25 °C marks where the
  risk starts, not a cliff.
  [J. Shellfish Res. 35(1):101-113](https://pubs.usgs.gov/publication/70178868)
- Marshall et al. 2021 (northern Gulf stocks): oysters held at salinity 4 died at lower temperatures than those at
  moderate or high salinity.
  [doi:10.1016/j.jtherbio.2021.103072](https://www.usgs.gov/publications/tolerance-northern-gulf-mexico-eastern-oysters-chronic-warming-extreme-salinities)
- Gledhill et al. 2020 (western Mississippi Sound, 2019): oysters set out on the western reefs during the spillway
  openings were all dead after 13 days, except at Henderson Point and Kittiwake, the two easternmost sites. This is a
  local check that the effect is real here. It doesn't set a threshold of its own.
  [J. Shellfish Res. 39(2)](https://bioone.org/journals/Journal-of-Shellfish-Research/volume-39/issue-2/035.039.0205/Mass-Mortality-of-the-Eastern-Oyster-Crassostrea-virginica-in-the/10.2983/035.039.0205.full)
- Southworth et al. 2017 (Chesapeake) put the line at under 2 for more than a week above 28 °C. That's a harsher pairing
  that `oyster_fresh_stress` already covers, so the two measures don't overlap much.

**Why the longest run is shown, not just the total.** Every study above found that duration and timing matter, but
none gives a Gulf day count that turns stress into death. So the site shows the run and makes no claim about how many
days kill. The run has the same behavior as 0038: a missing day ends it.

**Why measured readings only.** The virtual sensors' held-out errors are 2.3-5 ppt on average (`virtual.json`, 2024-26
test periods), about as large as the 5 ppt line itself, so they can't say which side of it a day fell on. They also
estimate salinity only. Gulfport Light would need a borrowed temperature on top of an estimated salinity. It stays out,
as does East Ship Island, which is offline already.

**Why each station is compared only with itself.** East Pearl River sits by the river mouth. In its 22 complete years
the median is 66 fresh-and-hot days, and 2021 had 127 (81 in a row). Merrill Shell Bank's median is 0, and 2019 had 45
(28 in a row). Putting the stations side by side would make East Pearl look alarming every summer, so each station gets
compared with its own past years.

**Missing readings.** A year needs both readings on at least 148 of the 184 days from May through October (80%) to be
"complete". Otherwise its count is shown as "at least N" and left out of the comparison. Sensors tend to fail in the
same floods we're counting, so a gappy year undercounts. Today that leaves 22 of 24 years at East Pearl, 15 of 26 at
Merrill Shell Bank, 20 of 27 at Point Cadet and 9 of 18 at Round Island.

## Consequences
- On today's data: Point Cadet's top years are 2021 (66), 2017 (38) and 2019 (35). Round Island has had at most 1 day in
  any complete year. 2026 so far is 44 at East Pearl, 7 at Merrill Shell Bank, 5 at Point Cadet and 0 at Round Island.
- Built as `msc/models/oyster_stress.py` with its settings under `oyster_stress` in `regions/ms.yaml`, written to
  `oyster_stress` in latest.json. It reads only the local store, so like the spillway and vibrio sections it isn't a
  source call and doesn't go through `_try`. A station whose newest reading is more than 3 days old (the card rule)
  keeps its bars but drops this year's sentence.
- This year is compared with each past complete year's count up to the same day of the year, so a June reading isn't
  set against whole summers. The bars show whole years, with this year's bar last.
- On the Oysters page right after the closure watch (`card_order`), as one small bar chart per station on a shared
  scale, with the sentence as the chart's text version. A shared scale makes East Pearl tower over the rest; that's
  true, and each sentence compares a station only with itself.
- Round Island's suspect high readings since 2026-10-15 can't make a fresh day. If QC flags a station's salinity or
  temperature, its sentence adds that the readings may be a sensor problem.
- Daily means smooth over short fresh pulses on a falling tide, so counts run a little low. The text says "daily
  average".
- Revisit if a Gulf study puts a day count on mortality at these levels, if Grand Bay NERR stations arrive (they
  measure both readings), or if a temperature station is added at Gulfport Light.
