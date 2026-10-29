# 0036: One history picture on home, and the spillway folded when the river is low

- **Status:** Accepted (follows [0035](0035-home-map-first-and-one-instrument-table.md); updates [0028](0028-every-year-on-record.md))
- **Date:** 2026-10-28

## Context
After 0035 the home page was still about 6,000 px tall at 1360 px wide. The "28 years of the Sound" section drew two
full stripe pictures (West Sound and Biloxi Back Bay), and the Bonnet Carré section showed the explanation, stage bar,
30-day chart, every opening since 1937 and the past-opening effects all the time, even when the river was 13 ft below
the opening level.

## Decision
- `history.home` in `regions/ms.yaml` is one station, Biloxi Back Bay, which is the `takeaway_site`, so the picture
  matches the sentence above it. Under the picture, a line links every other station's own history picture.
  `since` in latest.json is now the earliest year of any salinity station (1998), not just the home ones, so the
  heading still counts the whole record.
- When the river is in the `low` status and the spillway isn't open, the section shows one line (stage, trend, and how
  far below the opening level it is through the forecast). Everything else goes in a `<details>` labeled "What the
  spillway is, the river chart, and every opening". Official-source notices and the source line stay outside it.
  Any `watch`, `forecast_open` or `open_level` status, or an opening, shows the whole section as before.

## Why
- Measured in headless Chromium at 1360 px with the same data: home 6,035 → 4,972 px, Oysters 6,939 → 5,876,
  Shrimp 5,691 → 4,891, Fishing 5,859 → 5,059.
- Biloxi Back Bay over West Sound: the takeaway sentence is about Biloxi Back Bay, and a picture that disagrees with
  the line above it is confusing. West Sound stays one tap away, and "years like this one" still links to it.
- The spillway matters a few weeks in most years. When it's far from opening, one line answers the question people
  come with ("is it close?"). When it's close, the full section appears again with no setting to change.

## Consequences
- The page is still not "about half of 6,000". Most of what's left is the readings table, beaches, the oyster watch
  and the fishing outlook, which are what people come for.
- Adding a second home station is a one-line config change; the section draws each in `history.home`.
- e2e: the spillway test opens the details when it's there. The axe loops now also request reduced motion, so a button's
  0.15 s color transition can't be sampled mid-change, which used to make the dark-theme check fail now and then.
