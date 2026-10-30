# 0015: Air temp refreshes in the browser on page load

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

The site is static and rebuilt every 4 hours ([0001](0001-static-site-scheduled-pipeline.md)). That suits the water
data, which changes slowly and arrives hourly at best. Air temperature doesn't fit that pattern. At noon on
2026-10-28 the readout showed 61°F, the day's average so far, while Biloxi was 77°F. Switching the build to the newest
observation fixed most of that, but a reading can still be up to about 4 hours old by the time someone views it, and
on a warming morning that can be 10°F or more.

## Decision

Readings marked `"now"` (only air temp so far) carry their source URL in `latest.json`. On load, `web/src/lib/live.ts`
fetches the newest observation from api.weather.gov and replaces the built reading if the new one is newer and under
4 hours old. Today's low and high widen to include the new reading if it's from the same local day; otherwise the range
is dropped. The built value is the fallback and always shows its own time.

## Why

api.weather.gov is free, needs no key, and allows cross-origin requests (`Access-Control-Allow-Origin: *`), so this
needs no server or proxy. One request per page view to a government API is a small load and leaks nothing beyond the
viewer's IP, which the About page now discloses. Fixing it in the page itself, instead of building more often, keeps the
3-hour schedule and its Actions minutes unchanged.

## Consequences

- This is the first data the browser fetches at view time. Water readings stay build-time only. Adding another
  live reading means a `"now"` flag in `msc/config.py` and a source URL from its adapter, but only for sources that
  allow cross-origin requests and need no key. Never put a key in the page.
- The wording lives in `nowTileSub`/`nowRowText` (`web/src/lib/format.ts`), so the built page and the refresh say the
  same thing.
- Tests mock api.weather.gov. If NWS drops CORS or changes the response shape, the page quietly keeps the built value;
  revisit if that happens.
