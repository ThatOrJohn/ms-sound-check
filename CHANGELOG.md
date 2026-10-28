# Changelog

User-visible changes, newest first. Internal work is tracked in [docs/ROADMAP.md](docs/ROADMAP.md).

## 2026-10-28
### Changed
- Air temp on the home page is now the latest airport reading with its time and today's low and high, not the day's average so far. The page fetches the newest reading from the weather service when it loads, so it isn't hours behind. The station page labels the daily value as an average.
- New look ([0013](docs/decisions/0013-instrument-panel-design.md)): a single Geist typeface with tabular numbers, a deep marine dark theme and a cool light theme, a sticky translucent header, and segmented controls for persona and theme.
- Home page reads as a briefing: headline, a strip of key readouts (Sound salinity, water temp, river flows, rain, air temp), the map beside a sticky Signals rail, then numbered sections.
- Each reading shows a meter for where today sits among past years for the same date.
- Station charts, beaches, oyster watch and fishing outlook restyled to match.

### Added
- Oyster closure watch now says how often the Pearl River reaches each closure level in a typical year (about 145 days at 10 ft since 1998), which months are busiest, and how this month compares. It describes the river, not how often areas close.
- Shrimp season section on the Shrimp page: MDMR's latest shrimp notices (openings, area changes, closures) with links, and a three-day wind outlook with day and overnight wind. A notice from the past week leads the Shrimp headline.
- Fishing outlook on the Fishing page: wind, sky and rain chances from the NWS forecast with a plain verdict per day, NOAA tides for three stations, water temperature trend, where the saltiest and freshest water is, and muddy-water risk. The best day leads the Fishing headline.
- Oyster closure watch on the Oysters page: Pearl River stage at the gauge MDMR's management plan uses, the official NWS stage forecast, closure levels by reef area (10 and 11 ft), rainfall criteria, and links to MDMR.
- Gauge page for the Pearl River near Pearl River, LA with MDMR's closure levels and the NWS forecast on the chart.
- Beach status from MDEQ: advisories lead the headline, a Beaches section lists every beach by county, and a map layer colors beach segments.
- Map defaults per persona, remembered per persona.
- Virtual sensors: Gulfport Light is back as a labeled estimate; every salinity chart shows what nearby stations suggest.
- Map: OpenStreetMap coastline, NOAA depth shading and contours, river widths by flow, an optional salinity sketch, and layer toggles.
- Station pages with linked rain, river, salinity and temperature charts on one time axis.
- Persona pages for oysters, shrimp and fishing; the choice is remembered.
- The site: plain-language headline, findings, readings compared to normal, freshness warnings, light and dark themes.

### Fixed
- Switching between light and dark no longer leaves the map without its stations, rivers and beaches.
- Map is announced to screen readers instead of being hidden while focusable.
- Missing spaces before links in wrapped text.
