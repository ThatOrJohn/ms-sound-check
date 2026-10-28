# ms-sound-check: feasibility notes

*Researched 2026-10-28. Seed idea: [`seed.md`](seed.md).*

## The short version

There is a real gap. Nobody turns Mississippi Sound water data into plain
language for the people who fish it, eat from it, or live beside it. The
plumbing exists and is free. The audience is small and local, and that is
fine for a hobby.

Three findings change the plan compared to the seed doc:

1. **The station network is thinner than it looks.** Two of the five open-Sound
   salinity stations have been dark since 2024. The project should build around
   the three that still report, and say so on the page.
2. **The USGS API the seed assumed is being retired** in the first quarter of 2027.
   Build the live pipeline on the new API from day one.
3. **An X bot is no longer free.** Bluesky and RSS are free. Treat X as an
   optional, nearly free extra rather than the main channel.

The most valuable single feature may not be shrimp prediction. It may be a
**freshwater-stress counter** built on a published oyster threshold (see
"Angles, re-ranked").

## Does something useful already exist?

The test is not "is there a dashboard?" It is "can a shrimper, angler, or
curious Biloxi local open one page and learn what the Sound is doing and
whether that matters?" Today, nobody answers that.

| What exists | What it actually gives you | Gap |
|---|---|---|
| MDMR hydrological monitoring page | A paragraph, a link to an ArcGIS map of stations, and a link to the USGS gage finder | No current values, no interpretation |
| USGS Water Data station pages | Raw time series, one station at a time, in scientific units | No context, no comparison to normal, no "so what" |
| Dauphin Island Sea Lab ARCOS | A good real-time network with salinity, DO, and turbidity | **Alabama stations only.** Column names and units, no explanations, no forecasts |
| USGS MissS salinity predictions | Machine-learning daily salinity estimates for 18 Sound locations, with uncertainty | **A static 2024 data release**, not an ongoing feed. Useful for history, not "this week" |
| USM msbCOAWST model | A daily hindcast running since Jan 2025, plus forecast maps | **No public portal.** It appears in presentations, and access is by contacting the team |
| Spillway research (NGI / USM, 2026) | A concrete oyster tipping point, plus a call for real-time monitoring | The researchers call for this, but no public tool exists |

ARCOS confirms that "raw dashboard" is the wrong product. It has better
instruments than Mississippi and still doesn't explain anything. The
opportunity is interpretation: "salinity at Merrill Shell is 6 ppt below
normal for late October, the Pearl is running high, here's what that tends to
mean."

**Red team on "useful":** The serious users (MDMR, oyster farmers, USM) already
get this data from the source and won't need the site. The real audience is the
casual middle: recreational anglers, seafood-curious locals, and coast people
who heard "the spillway opened" and want to know what it means for the Sound. That
audience exists, but it is small and seasonal. Engagement will spike around
shrimp opening day and spillway events and be quiet otherwise. Design for
that pattern (event alerts plus a weekly digest) rather than expecting daily
visits.

## Data health check (as of 2026-10-28)

From the USGS series catalog for each MDMR/USGS station:

| Station | Conductance / salinity | Water temp | Status |
|---|---|---|---|
| Merrill Shell Bank Light (301429089145600) | since **1998** | since 1998 | ✅ reporting |
| Biloxi Bay at Point Cadet (302318088512600) | since **2000** | since 2000 | ✅ reporting |
| Round Island Light (301849088350000) | since 2009 (conductance only) | since 2009 | ✅ reporting |
| East Pearl River at CSX (301141089320300) | since 2001 | since 2002 | ✅ reporting (river mouth) |
| Gulfport Light (301912088583300) | 2009 – **Aug 2024** | to Oct 2025 | ❌ salinity dead |
| East Ship Island Light (301527088521500) | 2008 – **Dec 2024** | to Jan 2026 | ❌ salinity dead |
| St. Joseph Island Light (301104089253400) | — | — | active, no salinity |

Rivers: Pearl River near Bogalusa (02489500, since 1938) and Pascagoula River at
Merrill (02479000, since 1930) are both reporting daily discharge.

Two things follow from this:

- **Derive salinity from conductance.** USGS's own salinity series only starts
  in 2011 and is gappy. But conductance goes back to 1998–2009, and practical
  salinity can be computed from specific conductance with the standard
  formula (PSS-78, via the `gsw` package). That roughly doubles the history at
  the best stations. The probe script already does this.
- **The west/east split is covered, but the outer Sound is not.** Merrill Shell
  (west, Pearl-influenced) and Round Island (east, Pascagoula-influenced)
  bracket the Sound nicely, and Point Cadet covers Back Bay. With Gulfport
  Light and East Ship dark, there is nothing out by the islands. Be honest on
  the page about which water is being described.

Worth adding later: the Grand Bay NERR water-quality sondes (east of
Pascagoula) via NOAA's NERRS data system, and NOAA tide and buoy stations for
wind and water level. Neither is needed for v1.

**API migration (done: `backfill` now uses `waterdata.get_daily`; the experiment scripts still call the old service).** USGS will decommission `waterservices.usgs.gov` in Q1 2027,
with removal work running from November 2026 through February 2027. The
replacement is `api.waterdata.usgs.gov/ogcapi/`, which has `latest-continuous`,
`continuous`, `daily`, and `time-series-metadata` collections. It accepts free
api.data.gov keys for higher rate limits. The Python `dataretrieval` package
has a `waterdata` module that wraps it. The one-off probe script uses the old
service because it is familiar and only has to work once. The live pipeline
should use the new one.

## Angles, re-ranked

**1. Sound conditions, explained (the core product).** A weekly
plain-language read plus a simple page. For each station it shows salinity,
temperature, and a comparison to that station's normal for this week of the
year (percentile band from 15 to 25 years of history). It also shows river flow
compared to normal and one paragraph of "what this means." This is the thing
that doesn't exist, and every other angle hangs off it.

**2. Freshwater-stress counter (new, strongest single hook).** The 2026
NGI/USM spillway work reported a concrete threshold: oysters die when Sound
salinity stays **below 2 ppt for more than two weeks**. "Merrill Shell: 9
consecutive days under 2 ppt" is clear, checkable, and newsworthy precisely
when people care. It needs no model, just a running counter per station. It
also pairs naturally with Bonnet Carré status. Caveats: the threshold comes from
news coverage of the research, so get the actual report before stating it
authoritatively. It is also an oyster threshold, not a shrimp or fish one.

**3. Shrimp opening forecast (fun, fragile).** It is still the best
storytelling hook, and the probe will tell us if it is real. Fifteen seasons
(2012–2026) are compiled in `data/shrimp_openings.csv` with sources. The
spread is about 5 weeks (May 22 to June 23). The anecdotes line up with the hypothesis:
the wet spring of 2013 and the spillway year of 2019 were both late. But
anecdotes are exactly how you fool yourself with n=15.

Two structural problems to keep in mind:

- MDMR sets the date from its own trawl sampling, so the official date is a
  noisy, human-decided proxy for shrimp size. Weekday and holiday effects
  probably add a few days of noise that water data can't explain.
- The forecast is only interesting if it is made **well before** MDMR's
  announcement, which comes roughly 1–2 weeks ahead of opening day. The probe
  uses Mar–Apr data so the "prediction" would exist by May 1.

**4. Spillway / freshwater pulse alerts.** These belong as a feature of #1 and
#2, not a product of their own. USACE has no clean machine-readable status
feed that I found. The practical signal is Mississippi River flow at
Baton Rouge/Red River Landing plus news. Do this manually at first.

**5. Fishing conditions and dock prices.** Park both. Fishing is a crowded
space where trout behavior depends on much more than salinity. Dock prices
die without contributors, as the seed notes.

## Can it be free? Yes, with one asterisk

| Piece | Choice | Cost |
|---|---|---|
| Scheduled ingest | GitHub Actions cron in a public repo, Python, every 1–3 h | $0 |
| Storage | "Git scraping": commit small JSON/CSV snapshots to the repo, so history comes for free | $0 |
| Normals | One-time backfill to Parquet in the repo, a few MB | $0 |
| Site | Static site on Cloudflare Pages reading the JSON (Astro or plain HTML, Observable Plot for charts) | $0 |
| Narrative text | Rule-based templates first, LLM summary later if wanted | $0 (templates) |
| Bluesky posts | AT Protocol API from the same Action | $0 |
| RSS / Atom feed | Generated with the site | $0 |
| X posts | Pay-per-use API: about $0.015 per text post, about $0.20 if it contains a link | **~$1–2/mo** for text-only weekly posts plus alerts; keep links in the bio |

Asterisks and red-team notes on the stack:

- **GitHub disables scheduled workflows in public repos after 60 days without
  activity.** Git scraping commits keep the repo active, so this works itself out.
  Still, add a heartbeat check so a silent stall gets noticed.
- **Cron on GitHub is best-effort.** Runs can be delayed by tens of minutes
  under load. That's fine for a weekly digest and acceptable for alerts.
- **USGS data is provisional.** Values get revised and sondes foul. A few days
  of junk (e.g., a sudden 0 ppt) will happen. Add simple sanity filters, and
  never fire an alert on a single reading. Require persistence over at least 6–12 h.
- **LLM-written narrative is a trap at first.** It is cheap, but it confidently
  explains noise. Hand-written rules ("below the 10th percentile for this week")
  are boring and honest. Add an LLM layer only to rephrase rule output, never
  to decide what's notable.

## Probe results (run 2026-10-28)

**Verdict: shrimp is a footnote, not the headline.** The signal is real enough
to publish as a seasonal lean (early / normal / late), but not good enough to
publish as a date.

- **Temperature, not salinity, carries the signal.** Warmer Mar–Apr water means
  an earlier opening, about 6 days earlier per standard deviation of warmth. The
  three-station composite (n=15, Spearman -0.57, permutation p≈0.03) cuts the
  leave-one-out error from 8.5 to 6.1 days and lands within a week in 10 of 15
  seasons, versus 7 of 15 for guessing the average. The mechanism is
  plausible: MDMR has blamed a delayed season on cold water slow to reach 68°F,
  the temperature at which shrimp grow well.
- **Salinity was the original hypothesis and is weak.** It points the right way,
  but adding it to temperature makes predictions worse (6.7 days), and it is
  partly a proxy for temperature (r=0.42). Freshwater seems to matter only in
  extremes: 2019, the spillway year, opened 11 days later than temperature
  predicted. River flow shows nothing.
- **Red team.** The hypothesis moved after seeing the data, and roughly 20
  variants were tried. Mechanistic refinements (degree-days above 20°C, the
  date the water crosses 20°C) did *not* beat the plain mean, which is a mild
  warning sign. 2025 was a warm spring that opened 3.5 weeks late, and nothing
  here explains it. Recent seasons (2022–2025) have the largest errors.
- **What would make it credible.** Publish the lean on May 1 each year, before
  MDMR announces, and score it in public. Spring 2027 is the first true
  out-of-sample test.

## Suggested build order

1. ~~Run the probe~~ Done: shrimp is a footnote (see above).
2. **Backfill normals** for the four live stations and two rivers, and compute
   day-of-year percentile bands.
3. **Ingest Action** on the new USGS API, writing `data/latest.json` hourly and a
   weekly snapshot.
4. **One static page**: four station cards plus river flow, each with "vs.
   normal," a freshwater-stress counter, and a short text block.
5. **Weekly Bluesky/RSS digest.** Add X only if the audience is there.
6. **Shrimp lean** (early / normal / late from Mar–Apr water temperature),
   published May 1, 2027 and scored publicly against MDMR's actual date.

## Open questions for John

- Who is the first reader you picture: your parents' neighbors, the X/Bluesky
  crowd, or shrimpers at the harbor? That changes the tone and the cadence.
- Is it worth emailing the msbCOAWST team (contact on their 2025 State of the
  Coast slides) about a public feed of their forecast? A salinity *forecast*
  would make this much more useful, and they may welcome a public front end.

## Sources

- [MDMR hydrological monitoring](https://dmr.ms.gov/hydrological-monitoring/)
- [USGS MissS data release (data.gov)](https://catalog.data.gov/dataset/misss)
- [DISL ARCOS](https://www.disl.edu/arcos/)
- [msbCOAWST, State of the Coast 2025 slides](https://www.stateofthecoast.org/wp-content/uploads/2025/06/2025_Session-24_-Brandy-Armstrong.pdf)
- [WDAM: spillway tipping points (Apr 2026)](https://www.wdam.com/2026/04/06/researchers-discuss-tipping-points-with-bonnet-carr-spillway)
- [USGS: WaterServices decommission](https://waterdata.usgs.gov/blog/api-waterservices-decom/)
- [USGS OGC API docs](https://api.waterdata.usgs.gov/docs/ogcapi/)
- [X API in 2026 (OpenTweet)](https://opentweet.io/answers/is-the-x-api-free-in-2026)
- USGS series catalog per station, via waterservices site service (queried 2026-10-28)
- Shrimp opening dates: per-row sources in `data/shrimp_openings.csv`

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

**Decision:** don't ship a salinity forecast. The gains are on ordinary days, too small for readers to
notice, and the models are weakest during the events that matter. Do add wind as data: for the virtual
sensors, for explaining events ("south wind pushed Gulf water in"), and for the fishing outlook.

**Virtual sensors and step detection.** See `docs/architecture.md`. The neighbor-based estimate is
good enough to publish for Gulfport Light (about 2.3 ppt typical error). Watching for sudden *steps* in
a station's gap from its neighbors found exactly one event at Round Island in 17 years (+10 ppt, Oct 17,
2026). Merrill Shell stepped +14 ppt a day earlier, which points to real Gulf water rather than a sensor
fault. The rule to ship: a step at one station is suspect; matching steps at two or more stations within
a few days are an event worth reporting.

Reproduce: run the `Update conditions` workflow with task `experiment`, or `python scripts/experiment_drivers.py`.
