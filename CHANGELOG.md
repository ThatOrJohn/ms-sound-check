# Changelog

User-visible changes, newest first. Internal work is tracked in [docs/ROADMAP.md](docs/ROADMAP.md).

## 2026-10-28
### Added
- Salinity history picture: every day since 1998 at a station, one row per year, colored like the map. Station pages show the full picture, and a "28 years of the Sound" section on the Coast and Oysters pages shows West Sound and Biloxi Back Bay side by side, with a line on the freshest and saltiest years. Pick a year (or tap its row) to draw it on the station's salinity chart. A "Show as table" button lists each year's average and days under 5 and over 25 ppt. The home page's share image is now this picture ([0028](docs/decisions/0028-every-year-on-record.md)).
- "In the record" signals: when the last two weeks rank among the three highest or lowest for those dates since records began, Signals say so, for example "The Pearl River near Bogalusa is at its third-lowest late-October flow since 1998. Only 2000 and 2010 were lower." This takes the place of the plain "running low" note for that station.
- "Years like this one": the river section names the three past years whose Pearl and Pascagoula flows over the last 60 days looked most like this year's, with a short note on each, and links each to that year on the West Sound history picture. It's background, not a forecast.

### Changed
- The map's Layers panel keeps one width as you turn layers on and off. It no longer slides under the Dauphin Island reading or, on phones, the zoom buttons: when the map is too short to fit everything, the panel scrolls.
- The map comes up sooner on the home page: the headline now sits in a panel beside the map, above Signals, instead of across the top. On phones and tablets it comes right after the key readings. The map's header now says what the dot colors mean ("Dot color: salinity (ppt)", river 0 to 25+ Gulf) in place of "The Sound, live" ([0027](docs/decisions/0027-headline-beside-the-map.md)).
- Stations whose sensors have stopped are left off the map unless we publish an estimate for them, so the map no longer shows a station that only says "offline" (today that's East Ship Island). They're still in the station list.
- Beach segments on the map no longer rely on color alone: clear beaches are solid, advisories dashed and closures dotted, flagged beaches are labeled "Advisory" or "Closed", and the Layers panel shows a key when the beach layer is on. The map's Layers panel, the "All beaches" list and the extra fishing details now show a chevron so it's clear they open and close.
- Footer and About page now link to the project's GitHub issues for reporting wrong numbers or confusing wording, and say the code is open source (MIT).
- A small "Not the official record" chip under the headline expands to show, for beach advisories, oyster closures, shrimp seasons and marine weather it says who decides, links to them (MDEQ, MDMR, the National Weather Service and the MDMR oyster line), how our copy is made and when it was last pulled. The same note, collapsed to one line, heads the Beaches, Oyster, Shrimp and Fishing sections, and About the data has the full provenance ([0018](docs/decisions/0018-official-source-notices-up-front.md)).
- Air temp on the home page is now the latest airport reading with its time and today's low and high, not the day's average so far. The page fetches the newest reading from the weather service when it loads, so it isn't hours behind. The station page labels the daily value as an average.
- New look ([0013](docs/decisions/0013-instrument-panel-design.md)): a single Geist typeface with tabular numbers, a deep marine dark theme and a cool light theme, a sticky translucent header, and segmented controls for persona and theme.
- Home page reads as a briefing: headline, a strip of key readouts (Sound salinity, water temp, river flows, rain, air temp), the map beside a sticky Signals rail, then numbered sections.
- Each reading shows a meter for where today sits among past years for the same date.
- Station charts, beaches, oyster watch and fishing outlook restyled to match.

### Added
- Share previews: links to any page posted on Bluesky, X or in a message now show a picture with that page's headline, the key readings (Sound salinity, water temp, river flows) or a station's readings, when it was updated, and that it's not for navigation or harvest decisions. The images are redrawn with every update ([0026](docs/decisions/0026-share-images-at-build-time.md)).
- River stage readings now show their unit ("5.0 ft", not "5.0").
- Oyster season notices: the Oysters section lists MDMR's latest oyster notices (season openings, closings, growing-area changes) with their opening lines and links, and a notice from the past week leads the Oysters headline in MDMR's own words.
- River flow on phones: the river readings that float over the map on wider screens now show as a compact strip under the map on phones.
- Dauphin Island salinity at the map's east edge: the Dauphin Island Sea Lab's daily reading, labeled as a reference about 50 km east of our easternmost station. It's for comparison only and never used to flag our stations.
- Tide strip under the map: NOAA's predicted tide at Gulfport Harbor for the last 12 hours and the next 36, with a "now" marker, each high and low labeled, and a sentence on which way it's heading and when it next turns. It notes that wind can push the water above or below the prediction ([0025](docs/decisions/0025-tide-strip-predictions-in-the-browser.md)).
- Beach popups on the map: hover over a beach segment (or tap it on a phone) to see its name, status, the reason for any advisory and how long it has lasted, or when a clear beach was last sampled. The popup links to that beach in the Beaches section.
- Warm-water bacteria (Vibrio) note on the Coast, Oysters and Fishing pages: when the water at a station is warm (68°F and up) and moderately salty (5–25 ppt), the conditions where Vibrio grows fastest, a short section names the stations, explains who is most at risk and how to avoid infection (cover cuts, cook shellfish), and links to the Mississippi State Department of Health and the CDC. It's normal most of April–October, so it's a plain note, not an alert, and it disappears when the water cools ([0024](docs/decisions/0024-vibrio-as-seasonal-note.md)).
- Bonnet Carré Spillway section (Coast, Oysters, Shrimp and Fishing views): the Mississippi at New Orleans now and in the NWS two-week forecast against the 17-ft level where the Corps has opened the spillway, a chart of the past 30 days, a timeline of all 15 openings since 1937, and what West Sound did during the most recent ones. Signals note it when the river is forecast to near that level ([0022](docs/decisions/0022-spillway-watch-from-the-river.md)).
- Satellite map layers: water clarity (clear to murky) and surface temperature from NOAA CoastWatch, each the newest clear view over the last few days, with a key, the dates, and a sentence on where the water is murkiest or warmest. The Fishing view starts with clarity on, and its outlook repeats what the satellite saw ([0023](docs/decisions/0023-satellite-layers-newest-clear-view.md)).
- Map replay: a slider and Play button under the map step through the last 30 days of station salinity and river flow.
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
