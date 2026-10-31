# 0044: MDMR's shrimp status board and oyster season page, quoted with the page's date

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
[0014](0014-mdmr-notices-from-wordpress-api.md) chose not to derive open or closed from press releases. But MDMR
publishes its own status: the Shrimp & Crab page has a "Shrimp season status" box (three areas, each OPEN or CLOSED),
and each oyster season has a page with the season's text, its opening and closing orders, and the days with no harvest.
Both are WordPress pages, readable from the same public REST API (`/wp-json/wp/v2/pages`) with their `modified` date.

## Decision
- Fetch the `shrimp-crab` page and the newest page whose slug matches `NNNN-NNNN-public-oyster-season`; parse the
  status box, and the season text, orders and no-harvest days (`msc/adapters/mdmr.py`, `mdmr_pages` in
  `regions/ms.yaml`).
- Shrimp page: "MDMR's status board", each area with MDMR's word, then "As shown on MDMR's Shrimp & Crab page, last
  changed <date>. A new order can come before the page catches up."
- Oysters page: "The 2026–2027 season, from MDMR": the season text as a quote, the no-harvest days, the orders newest
  first, and "Quoted from MDMR's season page, last changed <date>."

## Why
- It's MDMR's own status in MDMR's words, so we still decide nothing; the oyster wording rule holds because every
  open or closed in this block is a quote, attributed and dated.
- The date matters: on 2026-10-30 the shrimp page was last changed October 16, the day after the Biloxi Bay opening, so
  it was current; a page can also lag an order, and the date lets readers judge.

## Consequences
- Parsing depends on the page layout (Elementor headings and buttons). If MDMR redesigns a page, the parser raises,
  that page is left out of the snapshot, and the run logs `mdmr page <key>` as a failed source; the rest still shows.
- The snapshot hides after 2 days without a good fetch, like the notices.
- Out of season the newest oyster page is last season's; the heading names the season, so it reads as history.
