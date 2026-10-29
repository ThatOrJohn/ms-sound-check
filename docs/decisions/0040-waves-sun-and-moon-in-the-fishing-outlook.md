# 0040: Waves, sun and moon in the fishing outlook

- **Status:** Accepted
- **Date:** 2026-10-29

## Context
The fishing outlook gave wind, sky and tides for each day, but no wave height and nothing on the sun or moon. Anglers
plan around both. The land forecast we already read has no waves; the NWS coastal waters forecast for the Mississippi
Sound (zone GMZ532) does, on the same free api.weather.gov service. Its periods carry names ("Saturday Night") but no
times.

For the sun and moon, we tried `astral` 3.2 first. Its moon times were wrong on some days: it said the moon "never
sets" on 2026-11-11 (it set at 6:35 pm) and "never rises" on 2026-11-26 (it rose at 7:05 pm). PyEphem matched the US
Naval Observatory's tables to the minute on every day we checked, including the principal phase dates.

## Decision
- Waves: fetch the GMZ532 forecast each run (`nws.marine_forecast`, through `_try`), date each period from the issue
  time, and show the NWS's own wave sentence for the daytime period. It hides when the file is over two days old,
  like the land forecast.
- Sun and moon: compute them in the pipeline with PyEphem (`msc/models/sky.py`) for the map center, using the USNO
  convention (upper limb, standard refraction). Show sunrise and sunset, the phase, the percent lit, and the moon's
  rise and set in time order. Name a principal phase (new, first quarter, full, last quarter) on the local day it
  falls.

## Why
- Quoting the NWS wording keeps "then 1 foot or less after midnight" and "bay waters a light chop" intact. Turning
  them into numbers would lose detail for no gain.
- Computing the sun and moon locally means no network call, nothing to go stale, and no third-party outage. The USNO
  API exists, but it has gone offline for months before.
- **No "bigger tides at new and full moon" line.** That's true where there are two tides a day, but the Mississippi
  Sound mostly has one tide a day. Here the range follows the moon's declination (the tropic/equatorial cycle of
  about two weeks), not its phase, so a full moon can bring small tides. The NOAA heights already shown are the real
  guide.
- No solunar "best times". The evidence for them is thin, and the outlook states facts with stated thresholds.

## Consequences
- One more pure-Python dependency (`ephem`) and one more NWS call per run.
- The moon's transit ("overhead") time is available from PyEphem if we ever want it, labeled as a fact, not a
  prediction.
- If the NWS renames or splits the zone, `marine_zone` in `regions/ms.yaml` is the one place to change.
