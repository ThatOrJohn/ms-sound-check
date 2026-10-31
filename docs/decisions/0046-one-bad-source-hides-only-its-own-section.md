# 0046: One bad source hides only its own section, and the page says so

- **Status:** Accepted
- **Date:** 2026-10-31

## Context
`_try` already kept a failed fetch from stopping a run, but nothing protected the build from what a fetch had saved.
On 2026-10-31 we broke each snapshot in turn (an HTML error page in place of JSON, `{}`, a list, a missing key, a key
set to null, a corrupt Parquet or satellite file). 51 of 63 cases crashed `msc build`. In CI that fails the update
step, so nothing deploys and the data store isn't saved, which loses that run's good USGS readings too. The WordPress
pages are the likeliest to change shape: they're parsed from Elementor markup ([0044](0044-mdmr-season-pages-quoted.md)).
A section that dropped out also left nothing in its place. With no Beaches section, the page reads as if there were
no advisories.

## Decision
- Snapshots are read through `msc/snapshots.py`. A file that's unreadable, the wrong shape or past its max age reads
  as missing (logged once). Writes go to a temporary file and are renamed into place.
- `build()` wraps each section in `_section`. A section that raises is logged, left out, and named in the run's
  "sources that failed" line. A failed headline falls back to the plain conditions sentence.
- Fetches don't save a response that's empty or broken: no beach stations raises. A failed beach-segments query keeps
  the stations and the old map lines. A MDMR page that fails keeps its last good copy, with that copy's own
  `fetched_at`, until the copy is past its max age.
- `latest.json` lists `unavailable` sections: configured, sourced (beaches, oyster watch, shrimp season, fishing
  outlook, spillway) and empty this build. In their place the page shows the section heading, says we couldn't check,
  and links the agency.
- `msc check` fails when a sourced section, an MDMR notice topic or an MDMR page is hidden, so the health job emails
  the owner.

## Why
- Hiding stale data was already the rule (CLAUDE.md). Now a bad file hides only its own section, not the whole page.
- A missing beach or shrimp section can mislead, so "We couldn't check, see MDEQ" is the honest version of hiding it.
- A parser broken by a redesign won't fix itself. Before this change, the health check only looked at water readings,
  so a hidden MDMR page could go unnoticed for weeks.

## Consequences
- Every sourced section can disappear without breaking the layout. A unit test builds against each kind of bad
  snapshot and table. E2E tests that need a sourced section skip when it's absent, so a source outage can't block a
  deploy. One e2e test checks the "couldn't check" note, its link and axe in both themes whenever a section is
  unavailable.
- The health job now goes red on a two-day MDMR or MDEQ outage, not just a water outage. If that's too noisy, drop the
  `hidden` block in `cmd_check` to warnings.
- Vibrio, oyster stress, history and similar years can be absent by design (out of season, not enough data), so
  they're never listed as unavailable.
