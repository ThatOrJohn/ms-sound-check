# Changelog

User-visible changes, newest first. Internal work is tracked in [docs/ROADMAP.md](docs/ROADMAP.md).

## 2026-10-28
### Changed
- Footer and About page now link to the project's GitHub issues for reporting wrong numbers or confusing wording, and say the code is open source (MIT).
- A small "Not the official record" chip under the headline expands to show, for beach advisories, oyster closures, shrimp seasons and marine weather it says who decides, links to them (MDEQ, MDMR, the National Weather Service and the MDMR oyster line), how our copy is made and when it was last pulled. The same note, collapsed to one line, heads the Beaches, Oyster, Shrimp and Fishing sections, and About the data has the full provenance ([0018](docs/decisions/0018-official-source-notices-up-front.md)).
- Air temp on the home page is now the latest airport reading with its time and today's low and high, not the day's average so far. The page fetches the newest reading from the weather service when it loads, so it isn't hours behind. The station page labels the daily value as an average.
- New look ([0013](docs/decisions/0013-instrument-panel-design.md)): a single Geist typeface with tabular numbers, a deep marine dark theme and a cool light theme, a sticky translucent header, and segmented controls for persona and theme.
- Home page reads as a briefing: headline, a strip of key readouts (Sound salinity, water temp, river flows, rain, air temp), the map beside a sticky Signals rail, then numbered sections.
- Each reading shows a meter for where today sits among past years for the same date.
- Station charts, beaches, oyster watch and fishing outlook restyled to match.

### Added
- Smaller coastal rivers: the Wolf River (into the Bay of St. Louis) and the Biloxi River (into Biloxi's Back Bay) have river cards and lines on the map, from their USGS gauges. The Jourdan, Tchoutacabouffa and Escatawpa, which have no live gauge, are drawn dashed and named on the map and listed with the river cards. Every river on the map is now labeled. The headline names the rivers ("The Pearl and Pascagoula rivers are running low") instead of "Both rivers", and adds a smaller river only when it runs the same way. Biloxi Back Bay's station page now charts the Biloxi River upstream, and West Sound's adds the Wolf ([0021](docs/decisions/0021-smaller-rivers-shown-not-weighed.md)).
- Salinity step events: when two or more stations jump or drop together, the Signals list says so for a week (for example, Salinity jumped at Merrill Shell Bank and Point Cadet around October 15, by as much as 18 ppt). A single station jumping alone is not reported, since that is often the sensor. When three or more stations move together, the Oysters and Fishing headlines lead with it. Each event also says what the wind and the rivers were doing in the days before, or that nothing stood out.
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
- The Pascagoula River line was missing from the map at the default zoom (the map tiles keep only the Pearl that far out). River lines now come from a prepared OpenStreetMap file.
- Switching between light and dark no longer leaves the map without its stations, rivers and beaches.
- Map is announced to screen readers instead of being hidden while focusable.
- Missing spaces before links in wrapped text.
