# Quickstart: coming back to ms-sound-check

Read this top to bottom once (10 minutes), then use the sections as a reference.

## What this is

A public web page with a plain-language read on the Mississippi Sound, rebuilt automatically every
3 hours from free public data: how salty and warm the water is, how the rivers are running, rain, wind,
tides, beach advisories and oyster closure criteria, each compared to normal for the time of year.
Separate views for the general public, oyster folks, shrimpers and anglers.

## The whole system in one picture

```
 Public data sources                 GitHub Actions (every 3 h)                  The site
 ───────────────────                 ──────────────────────────                  ────────
 USGS water stations ─┐
 NWS stage + forecast ┤              python -m msc run                          GitHub Pages
 NWS weather          ┤   ───────►     1. ingest  (adapters pull new data)  ──►  Astro builds
 Open-Meteo rain/wind ┤                2. build   (indicators, headlines,        static pages
 NOAA tides           ┤                            JSON for the site)            from the JSON
 MDEQ beaches         ┤
 MDMR notices         ┘                3. save store to the `data` branch
                                       4. build + test + deploy the site
```

- **Nothing runs on a server.** If GitHub Actions runs, the site updates. If it stops, the page keeps
  the last version and shows a staleness warning.
- **The data lives on the `data` branch** (Parquet files, one squashed commit). `main` holds only code.
- **Mississippi is one "region"**, defined entirely in `regions/ms.yaml`. Stations, thresholds, personas
  and section order are all edited there, not in code.

## Is it working?

1. **Open the site.** The URL is under the repo's Settings → Pages. The line under the headline says when it
   last updated. If it says "hasn't refreshed recently," something's wrong.
2. **Repo → Actions → "Update conditions".** Green runs every 3 hours = fine. A red **health** job means
   water data stopped updating. A red **update** job means the build or tests failed; open it and read
   the first red step.
3. **Scheduled runs missing entirely?** GitHub turns schedules off after 60 days without repo activity.
   Actions tab → "Update conditions" → "Enable workflow".

## Where things live

| Path | What it is |
|---|---|
| `regions/ms.yaml` | **The region.** Stations, river gauges, rain areas, personas, alert rules and thresholds. |
| `msc/` | The Python pipeline. `python -m msc --help` lists the commands. |
| `msc/adapters/` | One file per data source. Each turns its source into rows of (site, variable, date, value). |
| `msc/indicators.py` | Generic alert rules: unusual vs. normal, consecutive days below a threshold, custom. |
| `msc/models/` | Custom logic: virtual sensors, oyster watch, fishing outlook, beaches, shrimp lean. |
| `msc/build.py` | Turns everything into the JSON the site reads, including headlines. |
| `web/` | The site (Astro + TypeScript). Pages in `web/src/pages/`, pieces in `web/src/components/`. |
| `web/public/basemap/` | Depth images and contours for the map (made once, committed). |
| `data/shrimp_openings.csv` | MDMR shrimp season opening dates. **Update every spring** (see calendar). |
| `.github/workflows/update.yml` | The schedule: run, backfill, experiment. |
| `docs/ROADMAP.md` | **What's done and what's next.** Start here before changing anything. |
| `docs/decisions/` | Why things are the way they are. Check here before "fixing" something odd. |
| `docs/architecture.md` | Detailed reference for every piece. |

## Running it on your Mac

One-time setup:

```sh
cd ms-sound-check
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
brew install libomp                     # LightGBM needs it on macOS
(cd web && npm ci)
```

Each session:

```sh
source .venv/bin/activate
python -m msc backfill                  # first time only: pulls ~25 years of history (a few minutes)
python -m msc normals && python -m msc train
python -m msc run                       # pull the latest data and build the JSON
(cd web && npm run dev)                 # site at http://localhost:4321
```

Your local data lives in `data/ms/` and is never committed. Delete it any time; `backfill` rebuilds it.

## Common tasks

**See what the site looked like on a past date.**
`python -m msc build --asof 2019-06-02` (the 2019 spillway disaster: oyster alerts everywhere). Run
`python -m msc build` again to return to today.

**Change a threshold.** Edit the indicator in `regions/ms.yaml` (for example `oyster_fresh_stress`'s
`threshold`, or the oyster watch's `stage_ft`), then `python -m msc build` to see the effect.

**Add or remove a station.** Add or delete its entry under `sites:` in `regions/ms.yaml` (copy a similar
one), then `python -m msc backfill && python -m msc normals && python -m msc train`. Push; then run the
workflow with task `backfill` so CI's data store gets its history too.

**Change what a persona sees first.** Edit that persona's `card_order` (sections) and `map_layers` in
`regions/ms.yaml`. No code change needed.

**Add a new data source.** Write `msc/adapters/<name>.py` returning rows like the others, call it from
`cmd_ingest` in `msc/__main__.py` (wrapped in `_try` so its failure can't break the run), give it a site
entry in the region file, and add a row to the sources table in `docs/architecture.md`.

**Restyle the site.** Colors, spacing and type are tokens at the top of `web/src/styles/global.css`; the
map and charts read them too. To see every section filled in (beach advisories, a rising river, a fishing
forecast) without waiting for real events: `python scripts/dev_fixtures.py apply && python -m msc build`.
**Always** finish with `python scripts/dev_fixtures.py clear && python -m msc build` so sample data never
reaches a commit. Design rules: [docs/decisions/0013](docs/decisions/0013-instrument-panel-design.md).

**Retrain the models.** `python -m msc train` locally, or it happens monthly in CI. The log prints each
station's held-out error; estimates are only published where it's 3.5 ppt or better.

**Run an ML experiment.** Actions → "Update conditions" → Run workflow → task `experiment`. Results show
on the run's summary page. Never touches the live data.

**Redo the depth map.** `python -m msc basemap`, then commit `web/public/basemap/`. Only needed if you
change the map's area.

**Redo the river lines.** `python -m msc rivers`, then commit `web/public/basemap/rivers.geojson`. Needed when
a river's `osm_names` or `ungauged_rivers` in `regions/ms.yaml` change. A new gauged river also needs the
`backfill` workflow task for its history and normals.

**Start or close a sprint.** See `docs/README.md`. Short version: new file in `docs/sprints/`, tick items
as they're done, write the outcome, update `docs/ROADMAP.md` and `CHANGELOG.md`.

## Calendar: things that need a human

| When | What |
|---|---|
| Every spring (March to May) | The Shrimp page shows a season "lean" from spring water temperature. When MDMR announces the opening date, add a row to `data/shrimp_openings.csv` and note in the roadmap whether the lean was right. |
| Monthly (automatic) | CI recomputes normals and retrains the virtual sensors. Glance at that run's log if you're curious. |
| If MDMR revises its shellfish plan | Update the oyster watch's thresholds and `plan_url` in `regions/ms.yaml`, and add a decision record. |

## When something breaks

| Symptom | Likely cause | Fix |
|---|---|---|
| Red **update** job, step "Browser and accessibility tests" | A page broke or got less accessible | Open the log; the test name says which page. Fix, push. |
| Red **update** job, step "Build site", mentions Node | Runner's Node is older than Astro needs | Bump `web/.nvmrc` or check `check-latest` in the workflow. |
| Red **health** job | A source stopped answering for 2+ days | The update log's last lines list "sources that failed this run". Usually the source is down; wait or check its status page. |
| Beaches or the fishing outlook disappeared | Its source hasn't answered for 2+ days, so the section hides rather than show old advisories or forecasts | Same as above; it comes back on the next good fetch. |
| The oyster watch says its reading is more than a day old | The river stage feed stalled | Same as above; the closure criteria still show, without a current reading. |
| Map is a blank box locally | `npm install` not run since a dependency was added | `cd web && npm ci`, restart the dev server. |
| `libomp.dylib` error on Mac | LightGBM needs OpenMP | `brew install libomp`. |
| A station shows "possibly a sensor problem" | Reading beyond what the water can do, or far from what neighbors imply | Usually a USGS sensor issue; it clears when USGS fixes or revises the data. |
| Numbers look wrong for one station | USGS revised provisional data, or the sensor drifted | Check the station page chart against its "expected from neighbors" line. |

## Words you'll see

- **ppt**: parts per thousand, salinity. River water ~0, the open Gulf ~35.
- **cfs**: cubic feet per second, river flow.
- **Typical / normal**: the middle of past readings for that station within a week of this date, every year on record.
- **Virtual sensor**: a model's estimate of what a station should read, from its neighbors, rivers, rain and wind.
- **Persona**: one of the four views (Coast, Oysters, Shrimp, Fishing). Pure configuration.
- **Conditionally approved area**: oyster reefs MDMR opens and closes based on river stage and rainfall.
- **PERL1**: the NWS gauge "Pearl River near Pearl River, LA", the one MDMR's oyster plan uses.
- **Data branch**: the git branch holding the data store. Don't merge it into `main`.
