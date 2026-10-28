# 0014: Shrimp season notices from MDMR's WordPress API, shown as MDMR wrote them

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Shrimpers need MDMR's in-season changes (the opening, area openings like Biloxi Bay, the Jan 1 closure north
of the ICW, the May 1 closure west of the Gulfport Ship Channel). dmr.ms.gov is WordPress, and its public REST
API (`/wp-json/wp/v2/posts`) answers plain JSON with no bot check. The same orders appear twice: as press
releases (News & Updates, category 6) and as legal notices (Public Notices, category 7).

## Decision
Each run, search category 6 for "shrimp" and keep posts whose title matches `shrimp season|shrimping`. Show the
last year's notices (newest five) with title, date, opening lines and a link. Don't derive an open/closed status.

## Why
- Press releases are the plain-language version; legal notices repeat them in statute text.
- The title filter, checked against 2021-2026, keeps every opening, area change and closure and drops license
  sales and disaster-relief posts that mention shrimp in passing.
- Openings and closures are by area, with boundaries drawn from channel beacons. Turning that into "open" or
  "closed" would mean parsing legal boundaries and risk being wrong. Same principle as the oyster watch
  ([0012](0012-oyster-watch-criteria.md)): MDMR decides, and we point to what it said.

## Consequences
- A notice from the past 7 days leads the Shrimp headline.
- The snapshot hides after 2 days without a good fetch, so the list can't silently miss a closure.
- If MDMR renames its titles, notices drop out of the list without any error. The legal-notice category is the fallback if that happens.
- Oyster reef openings could use the same adapter: add an `oyster` topic in `regions/ms.yaml`.
