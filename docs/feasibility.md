# ms-sound-check: feasibility notes

*Researched 2026-10-28, updated 2026-10-30 with what has been built. Seed idea: [`seed.md`](seed.md).
What's next lives in [ROADMAP.md](ROADMAP.md).*

## The short version

There was a real gap, and the site now fills it. Nobody turned Mississippi Sound water data into plain language
for the people who fish it, eat from it, or live beside it. The plumbing exists and is free. The audience is small
and local, and that is fine for a hobby.

Three findings shaped the plan compared to the seed doc. All three are now handled:

1. **The station network is thinner than it looks.** Two of the five open-Sound salinity stations have been dark
   since 2024. The site is built around the three that still report and says so on the page. Gulfport Light is back
   as a labeled estimate from its neighbors ([0007](decisions/0007-virtual-sensors.md)); East Ship Island can't be
   estimated and shows as offline.
2. **The USGS API the seed assumed is being retired** in the first quarter of 2027. The live pipeline and the
   backfill were built on the new API from day one, and nothing in the repo calls the old service.
3. **Social posting isn't free or needed.** The weekly digest is an RSS feed built with the site
   ([0031](decisions/0031-weekly-digest-rss-and-bluesky.md)); no social account is planned.

The most valuable single feature turned out not to be shrimp prediction. It was the **freshwater-stress counter**
built on a published oyster threshold, now an Oysters signal alongside the fresh-and-hot days count
([0039](decisions/0039-fresh-and-hot-days-near-the-reefs.md)).

## Does something useful already exist?

The test is not "is there a dashboard?" It is "can a shrimper, angler, or curious Biloxi local open one page and
learn what the Sound is doing and whether that matters?" Before this site, nobody answered that.

| What exists | What it actually gives you | Gap |
|---|---|---|
| MDMR hydrological monitoring page | A paragraph, a link to an ArcGIS map of stations, and a link to the USGS gage finder | No current values, no interpretation |
| USGS Water Data station pages | Raw time series, one station at a time, in scientific units | No context, no comparison to normal, no "so what" |
| Dauphin Island Sea Lab ARCOS | A good real-time network with salinity, DO, and turbidity | **Alabama stations only.** Column names and units, no explanations, no forecasts |
| USGS MissS salinity predictions | Machine-learning daily salinity estimates for 18 Sound locations, with uncertainty | **A static 2024 data release**, not an ongoing feed. Useful for history, not "this week" |
| USM msbCOAWST model | A daily hindcast running since Jan 2025, plus forecast maps | **No public portal.** It appears in presentations, and access is by contacting the team |
| Spillway research (NGI / USM, 2026) | A concrete oyster tipping point, plus a call for real-time monitoring | The researchers call for this, but no public tool exists |

ARCOS confirms that "raw dashboard" is the wrong product. It has better instruments than Mississippi and still
doesn't explain anything. The opportunity was interpretation: "salinity at Merrill Shell is 6 ppt below normal for
late October, the Pearl is running high, here's what that tends to mean." That is what the headline, Signals and
persona pages now do. Dauphin Island's daily salinity is used only as a reference at the map's east edge
([0019](decisions/0019-disl-reference-data-no-auto-flag.md)).

**Red team on "useful":** The serious users (MDMR, oyster farmers, USM) already get this data from the source and
won't need the site. The real audience is the casual middle: recreational anglers, seafood-curious locals, and coast
people who heard "the spillway opened" and want to know what it means for the Sound. That audience exists, but it is
small and seasonal. Engagement will spike around shrimp opening day and spillway events and be quiet otherwise. The
site is designed for that pattern (step-event signals, the spillway watch and a weekly digest) rather than expecting
daily visits. No usage data exists yet; analytics are first on the roadmap.

## Data health check (as of 2026-10-28)

From the USGS series catalog for each MDMR/USGS station:

| Station | Conductance / salinity | Water temp | Status |
|---|---|---|---|
| Merrill Shell Bank Light (301429089145600) | since **1998** | since 1998 | ✅ reporting |
| Biloxi Bay at Point Cadet (302318088512600) | since **2000** | since 2000 | ✅ reporting |
| Round Island Light (301849088350000) | since 2009 (conductance only) | since 2009 | ✅ reporting |
| East Pearl River at CSX (301141089320300) | since 2001 | since 2002 | ✅ reporting (river mouth) |
| Gulfport Light (301912088583300) | 2009 – **Aug 2024** | to Oct 2025 | ❌ salinity dead; shown as an estimate |
| East Ship Island Light (301527088521500) | 2008 – **Dec 2024** | to Jan 2026 | ❌ salinity dead; can't be estimated |
| St. Joseph Island Light (301104089253400) | — | — | active, no salinity |

Rivers: Pearl River near Bogalusa (02489500, since 1938) and Pascagoula River at Merrill (02479000, since 1930) are
both reporting daily discharge. The Wolf and Biloxi rivers were added later as shown-but-not-weighed rivers
([0021](decisions/0021-smaller-rivers-shown-not-weighed.md)).

Two things followed from this:

- **Salinity is derived from conductance** ([0006](decisions/0006-salinity-from-conductance.md)). USGS's own
  salinity series only starts in 2011 and is gappy. Conductance goes back to 1998–2009, and practical salinity is
  computed from specific conductance with the standard formula (PSS-78, via the `gsw` package). That roughly doubles
  the history at the best stations and is what makes "28 years of the Sound" possible.
- **The west/east split is covered, but the outer Sound is not.** Merrill Shell (west, Pearl-influenced) and Round
  Island (east, Pascagoula-influenced) bracket the Sound, and Point Cadet covers Back Bay. With Gulfport Light and
  East Ship dark, there is nothing measured out by the islands. The page says which water is being described.

Added since: NOAA tide predictions and measured water level (CO-OPS), NWS observations and forecasts, wind, the
Pearl River stage forecast (NWPS), the Mississippi at New Orleans, CoastWatch satellite clarity and temperature, MDEQ
beach status, and MDMR season notices. Still to add: the Grand Bay NERR water-quality sondes east of Pascagoula
(roadmap, Next).

**API migration (done).** USGS will decommission `waterservices.usgs.gov` in Q1 2027, with removal work running
from November 2026 through February 2027. The replacement is `api.waterdata.usgs.gov/ogcapi/`, which has
`latest-continuous`, `continuous`, `daily`, and `time-series-metadata` collections and accepts free api.data.gov keys
for higher rate limits. The backfill uses `waterdata.get_daily` and the live pull uses `waterdata.get_continuous`,
both from the `dataretrieval` package.

## Angles and where they landed

**1. Sound conditions, explained (the core product). Built.** The home page leads with a plain-language headline,
Signals and one readings table. Each station shows salinity and temperature against its normal for this week of the
year (percentile bands from 15 to 28 years of history), "in the record" lines when a reading ranks among the
highest or lowest, and a salinity history picture back to 1998. River flow is compared to normal the same way.

**2. Freshwater-stress counter. Built.** The 2026 NGI/USM spillway work reported a concrete threshold: oysters die
when Sound salinity stays **below 2 ppt for more than two weeks**. Once a station has been under
that line for five straight days, Signals count the days (stronger at 10 and 14). The Oysters page pairs it with the Bonnet Carré spillway watch
([0022](decisions/0022-spillway-watch-from-the-river.md)) and days that are both fresh and hot
([0039](decisions/0039-fresh-and-hot-days-near-the-reefs.md)). Caveat that still stands: the threshold comes from
coverage of the research, and it is an oyster threshold, not a shrimp or fish one. The wording never says an area is
closed; the closure watch compares the Pearl River to MDMR's own plan
([0012](decisions/0012-oyster-watch-criteria.md)).

**3. Shrimp opening lean. Built, scored from spring 2027.** Published as early / normal / late from March–April
water temperature, never as a date ([0009](decisions/0009-shrimp-lean-not-date.md)). See "Probe results" below.
The Shrimp page also carries MDMR's season notices and a three-day wind outlook.

**4. Spillway / freshwater pulse alerts. Built as part of 1 and 2.** USACE still has no machine-readable structure
status. The watch uses the Mississippi at New Orleans and the NWS forecast against the level where the Corps has
opened the spillway, a hand-kept list of past openings, and side-by-side charts of what West Sound did each time
([0038](decisions/0038-past-spillway-openings-side-by-side.md)).

**5. Fishing conditions. Built as an outlook, not a bite forecast.** The Fishing page gives wind, waves, sky, rain,
tides, sun and moon, water temperature trend, clarity from satellite and where the saltiest and freshest water is
([0040](decisions/0040-waves-sun-and-moon-in-the-fishing-outlook.md)). A test against 52,000 angler interviews found
no condition worth turning into a "good bite" call (see "Angler catch vs conditions" below).
**Dock prices** stay parked: they die without contributors, as the seed notes.

## Can it be free? Yes

| Piece | Choice | Cost |
|---|---|---|
| Scheduled ingest | GitHub Actions cron in a public repo, Python, every 4 h | $0 |
| Storage | Parquet and JSON on a `data` branch, force-pushed as one commit each run ([0002](decisions/0002-parquet-store-on-data-branch.md)) | $0 |
| Normals | One-time backfill to Parquet, recomputed monthly | $0 |
| Site | Astro + React + ECharts, MapLibre with OpenFreeMap tiles, on GitHub Pages ([0004](decisions/0004-astro-react-echarts.md), [0005](decisions/0005-maplibre-openfreemap-noaa-depth.md)) | $0 |
| Narrative text | Rule-based templates from `regions/ms.yaml`; no LLM | $0 |
| Weekly digest | RSS feed generated with the site | $0 |
| Custom domain and analytics | Planned: a domain plus Cloudflare Web Analytics | ~$12/yr |

Red-team notes on the stack, and how each was handled:

- **GitHub disables scheduled workflows in public repos after 60 days without activity.** The store lives on the
  `data` branch, so `main` can go quiet; the health job (`python -m msc check`) is there so a silent stall gets
  noticed.
- **Cron on GitHub is best-effort.** Runs can be delayed by tens of minutes under load. That's fine for a 4-hour
  cadence and a weekly digest.
- **USGS data is provisional.** Values get revised and sondes foul. Sanity filters drop junk, data past its max age
  hides instead of showing old numbers, and a salinity step at one station alone is never reported: it takes
  matching steps at two or more stations ([0016](decisions/0016-step-events-need-matching-stations.md)).
- **LLM-written narrative is a trap.** It is cheap, but it confidently explains noise. Every sentence comes from a
  hand-written rule ("below the 10th percentile for this week"), which is boring and honest.

## Probe results (run 2026-10-28)

**Verdict: shrimp is a footnote, not the headline.** The signal is real enough to publish as a seasonal lean
(early / normal / late), but not good enough to publish as a date.

- **Temperature, not salinity, carries the signal.** Warmer Mar–Apr water means an earlier opening, about 6 days
  earlier per standard deviation of warmth. The three-station composite (n=15, Spearman -0.57, permutation p≈0.03)
  cuts the leave-one-out error from 8.5 to 6.1 days and lands within a week in 10 of 15 seasons, versus 7 of 15 for
  guessing the average. The mechanism is plausible: MDMR has blamed a delayed season on cold water slow to reach
  68°F, the temperature at which shrimp grow well.
- **Salinity was the original hypothesis and is weak.** It points the right way, but adding it to temperature makes
  predictions worse (6.7 days), and it is partly a proxy for temperature (r=0.42). Freshwater seems to matter only in
  extremes: 2019, the spillway year, opened 11 days later than temperature predicted. River flow shows nothing.
- **Red team.** The hypothesis moved after seeing the data, and roughly 20 variants were tried. Mechanistic
  refinements (degree-days above 20°C, the date the water crosses 20°C) did *not* beat the plain mean, which is a
  mild warning sign. 2025 was a warm spring that opened 3.5 weeks late, and nothing here explains it. Recent seasons
  (2022–2025) have the largest errors.
- **What would make it credible.** Publish the lean on May 1 each year, before MDMR announces, and score it in
  public. Spring 2027 is the first true out-of-sample test.

Reproduce: `python scripts/probe_shrimp_signal.py`. Season dates and per-row sources: `data/shrimp_openings.csv`.

## Build order, as it went

1. ~~Run the shrimp probe~~ Done: shrimp is a footnote (above).
2. ~~Backfill normals~~ Done for the four live stations and the rivers, with day-of-year percentile bands.
3. ~~Ingest on the new USGS API~~ Done, every 4 hours in GitHub Actions.
4. ~~One static page~~ Grew into the home page, station pages and four persona pages (Coast, Oysters, Shrimp,
   Fishing) set in config ([0010](decisions/0010-personas-as-config.md)).
5. ~~Weekly digest~~ Done as RSS ([0031](decisions/0031-weekly-digest-rss-and-bluesky.md)).
6. **Shrimp lean** scored publicly against MDMR's actual date: first true test May 1, 2027.

## ML experiments (2026-10-28)

All tests: gradient-boosted models (LightGBM), trained through 2018 and tested on 2019-2026, compared
against persistence ("salinity stays where it is today"). Scores are mean absolute error in ppt.

**Salinity forecasting, 1-14 days, our two rivers only: no edge.** The models never beat persistence.
Predicting the change from today instead of the level only brought them to even. Even with the *true*
future flow of the Pearl and Pascagoula (an oracle), the best case was 5-14% better at 1-2 weeks.

**Adding the Mississippi River (Baton Rouge flow): no edge.** No change, sometimes slightly worse, even
with the 2019 and 2020 Bonnet Carre openings inside the test period.

**Adding wind (ERA5 reanalysis over mid-Sound): the first real signal.** Using past wind only:

| Station | 3 days | 7 days |
|---|---|---|
| Round Island | 2.69 → 2.26 (−16%) | 3.32 → 2.81 (−15%) |
| Merrill Shell | 2.07 → 1.88 (−9%) | 2.84 → 2.59 (−9%) |
| Back Bay | 1.74 → 1.64 (−6%) | 2.41 → 2.32 (−4%) |

A perfect wind forecast adds a few percent more at most. On freshwater-event days (salinity < 8 ppt),
every model is still worse than persistence without the oracle wind.

**Decision:** don't ship a salinity forecast ([0008](decisions/0008-no-salinity-forecast.md)). The gains are on
ordinary days, too small for readers to notice, and the models are weakest during the events that matter. Wind was
added as data instead: for the virtual sensors, for explaining events ("south wind pushed Gulf water in",
[0017](decisions/0017-step-events-describe-wind-and-rivers.md)), and for the fishing outlook and map.

**Virtual sensors and step detection.** See `docs/architecture.md`. The neighbor-based estimate is
good enough to publish for Gulfport Light (about 2.3 ppt typical error). Watching for sudden *steps* in
a station's gap from its neighbors found exactly one event at Round Island in 17 years (+10 ppt, Oct 17,
2026). Merrill Shell stepped +14 ppt a day earlier, which points to real Gulf water rather than a sensor
fault. The rule shipped: a step at one station is suspect; matching steps at two or more stations within
a few days are an event worth reporting.

Reproduce: run the `Update conditions` workflow with task `experiment`, or `python scripts/experiment_drivers.py`.

## Angler catch vs conditions (2026-10-30)

**Verdict: no usable signal.** Details and decision in
[0041](decisions/0041-no-bite-outlook-from-angler-surveys.md).

Mississippi's own catch reporting (Tails n' Scales, now the offshore landing permit and MS CREEL) publishes no data.
NOAA's MRIP dockside interviews do: 51,958 Mississippi interviews, 2000-2025, with date, landing county, mode, the
species the angler was fishing for, and catch. For anglers fishing for a species, "caught at least one" was compared
against a season-only model (month, county, mode, area, year trend), leaving out one year at a time:

| Species | Trips | Caught one | Best condition | Improvement |
|---|---|---|---|---|
| Speckled trout | 13,106 | 51% | mean wind | 0.18% |
| Redfish | 7,755 | 30% | peak wind | 0.09% |
| Flounder | 2,142 | 41% | mean wind | 0.48% |
| White trout | 2,721 | 50% | none positive | - |
| Sheepshead | 882 | 53% | south wind | 0.72% (better in 11 of 25 years) |
| Red snapper | 2,546 | 71% | water level | 0.80% (better in 12 of 25 years) |

The season model itself only improves on a flat average by about 2% (trout) and 4% (redfish). The steadiest
within-month, within-county pattern: trout catch one 4.5 points less often on the saltiest third of days. Real, maybe,
but too small to tell anyone.

Reproduce: `python scripts/probe_mrip_bite.py` (downloads about 200 MB to `data/raw/mrip/`; outputs in `data/probe/mrip_*`).

## Sources

- [MDMR hydrological monitoring](https://dmr.ms.gov/hydrological-monitoring/)
- [USGS MissS data release (data.gov)](https://catalog.data.gov/dataset/misss)
- [DISL ARCOS](https://www.disl.edu/arcos/)
- [msbCOAWST, State of the Coast 2025 slides](https://www.stateofthecoast.org/wp-content/uploads/2025/06/2025_Session-24_-Brandy-Armstrong.pdf)
- [WDAM: spillway tipping points (Apr 2026)](https://www.wdam.com/2026/04/06/researchers-discuss-tipping-points-with-bonnet-carr-spillway)
- [USGS: WaterServices decommission](https://waterdata.usgs.gov/blog/api-waterservices-decom/)
- [USGS OGC API docs](https://api.waterdata.usgs.gov/docs/ogcapi/)
- USGS series catalog per station, via waterservices site service (queried 2026-10-28)
- Shrimp opening dates: per-row sources in `data/shrimp_openings.csv`
