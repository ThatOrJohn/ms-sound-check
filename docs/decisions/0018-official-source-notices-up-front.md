# 0018: Say we are not the official record up front, and show where each answer comes from

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
The "not official" wording lived in one footer line and one About paragraph, linking only to MDMR. Beach advisories come
from MDEQ, oyster closures and shrimp seasons from MDMR, and marine weather from the NWS. A visitor could read "Closed"
on a beach or "Forecast to reach the closure level" and take it for the agency's word, or miss that our copy can be hours old.

## Decision
- One shared component, `OfficialSources.astro`, states it. On the home page it is a one-line chip under the headline
  ("Not the official record") that expands in place (a `<details>`, no JS) to: for each topic, who decides, a link to them, and how our version is made and how it can be wrong.
- The same component renders a collapsed one-line "Official source" note (also a `<details>`) at the top of the Beaches, Oyster closure watch, Shrimp
  season and Fishing sections, so the caveat sits next to the numbers it qualifies.
- The About page has an "Official sources" section (`#official`) with the full provenance, and the footer links to it
  and to both agencies.
- Links and the oyster hotline come from the data (`beaches.link`, `oyster_watch.status_url`, `hotline`,
  `shrimp_season.link`), with the agency home pages as fallback.

## Why
- The caveat has to be seen before the numbers are, and it should say what to do (go to the agency), not only what we are not.
- One component keeps the wording the same everywhere; sections can't drift from the panel.
- It restates the rules in CLAUDE.md: we never say an area "is closed" for oysters, and only compare readings to MDMR's plan.

## Consequences
- A full-width panel was tried first and rejected as too much prime space; the chip keeps the notice visible without it.
  Collapsed, it adds one line above the readouts.
- The NWS Mobile link (`weather.gov/mob/`) is hard-coded; move it to `regions/ms.yaml` when a second region exists.
- New sources that make a claim about a closure, advisory or season must add a row here.
