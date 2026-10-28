# Architecture

The rule that shapes everything: **generalize the plumbing, not the
interpretation.** Fetching, storing, and comparing data to normal works the
same in any bay. What a reading *means* (oyster thresholds, how a state sets
shrimp seasons) is local, so it lives in a region's config file, not in the code.

```
sources ──► adapters ──► store (Parquet) ──► normals
                              │                 │
                              └──► indicators ◄─┘ ──► build ──► static site
                                   (region YAML)       (JSON)    (persona + theme)
```

## Regions

A region is one file, `regions/<id>.yaml`. It lists:

- **sites**: stations, river gauges, weather stations and rain areas, each with
  a `kind` (sound, estuary, river, rain, weather), a `source`, the variables it
  reports, and `drains_from` links (what flows into it). The links drive the
  upstream-first drill-down charts.
- **personas**: who the page is talking to. Each one sets a focus order over
  topics (`general`, `oyster`, `shrimp`, `fish`) and a card order.
- **indicators**: the rules that produce findings (see below).

Mississippi (`regions/ms.yaml`) is the only region today. A second region
means a new YAML file, and a new adapter only if it uses a source we don't
have yet. USGS and the National Weather Service cover the whole US. Don't
build a region picker until a second region exists.

## Data flow

**Adapters** (`msc/adapters/`) turn each source into one shape:
`site, var, date|time, value, source`.

| Source | What | How | Cost |
|---|---|---|---|
| USGS (new OGC API, via `dataretrieval`) | conductance → salinity, water temp, river flow; 15-minute values | `usgs.recent` | free; set `API_USGS_PAT` for higher limits |
| USGS legacy `dv` service | daily history back to 1998 | `usgs.backfill_daily`, one time | free; retired Q1 2027, after which this moves to `waterdata.get_daily` |
| National Weather Service | air temperature at Gulfport-Biloxi airport | `nws.recent` | free, no key |
| NWS National Water Prediction Service | observed and forecast river stage at PERL1 (Pearl River near Pearl River, LA) for the oyster watch | `nwps.recent_and_forecast`, every run; history from USGS 02492600 at backfill | free, no key |
| NWS forecast (api.weather.gov) | 7-day forecast for the Gulfport waterfront: wind, sky, rain chance, temperature | `nws.forecast`, every run | free, no key |
| NOAA CO-OPS | tide predictions (highs and lows) at Bay Waveland, Gulfport Harbor, Pascagoula | `tides.fetch`, every run | free, no key |
| Open-Meteo (wind) | daily wind over mid-Sound: east/north components and peak; ERA5 history at backfill | `openmeteo.wind_*` | free, non-commercial |
| MDEQ Beach Monitoring (public ArcGIS feature service) | beach advisories and closures (bacteria, debris, algal blooms) and beach segments | `beaches.fetch`, every run | free, no key |
| MDMR WordPress REST API | shrimp season notices (press releases, filtered by title) for the Shrimp page | `mdmr.fetch`, every run | free, no key |
| Open-Meteo | observed and forecast daily rain, local and basin-averaged | `openmeteo.*` | free, no key, **non-commercial terms**; revisit if sponsorship happens |

Salinity is computed from specific conductance (PSS-78 via `gsw`), not taken
from USGS's own salinity series, which starts in 2011 and has gaps. Values
outside physical bounds are dropped as sensor junk.

**Store** (`msc/store.py`): plain Parquet, readable by anything (DuckDB,
pandas, Databricks, a notebook).

- `daily/<year>.parquet`: the full daily history, one long table
- `recent.parquet`: the last 45 days at native resolution
- `normals.parquet`: for each site, variable and day of year, the 10th–90th
  percentiles of every past reading within a week of that date
- `rain_forecast.parquet`: the next 7 days of rain

Newer values replace older ones for the same day, because USGS revises
provisional data.

**Indicators** (`msc/indicators.py`) are configured in the region YAML:

| Type | Fires when | Example |
|---|---|---|
| `vs_normal` | the latest reading is outside the 10th–90th percentile band for this time of year | "Pearl River is running high (30,100 cfs vs. a typical 2,970)" |
| `run_below` | a value has stayed under a threshold for N straight days, with watch, warning and alert levels | oyster freshwater stress: under 2 ppt for 5 / 10 / 14 days |
| `custom` | a Python function (`module:function`) returns findings | `msc.models.shrimp:season_lean` |

Each finding has a severity (notice < watch < warning < alert), topic tags, and
a plain-language sentence. Stale data (more than 3 days old) never fires an
indicator. A plain notice is dropped when a stronger finding already covers the
same site and variable. One broken indicator can't take down the build.

**Virtual sensors** (`msc/models/virtual.py`) are LightGBM quantile models, one set per salinity
station. Each predicts what that station *should* read from same-day salinity at the other live
stations, river flow (today and 7/30-day means), basin rain and season. They're trained by
`python -m msc train` at backfill and monthly; models live in the data store (`models/`). Each
training run scores the model on the station's most recent two years before refitting on everything,
then calibrates the ranges on that held-out period (conformalized quantile regression) so a "90% range"
really covers about 90%. The build uses them three ways:

| Use | Rule |
|---|---|
| Estimate for a retired or quiet station | Only where held-out error is ≤ 3.5 ppt (today: Gulfport Light, Pearl River mouth). Shown with its likely range, labeled as an estimate. |
| "Reads saltier/fresher than nearby stations suggest" | Live reading outside the calibrated 90% range. A note only. |
| Suspect: alerts paused | Outside the calibrated 98% range (+0.5 ppt) on 2 of the last 3 days. On the last 400 days this fired on 0 readings that passed the 36 ppt ceiling, so it catches gross failures, not slow drift. |
| Charts | Dotted "expected from neighbors" line with its 90% band. |

First run (2026-10-28), held-out MAE in ppt (vs. averaging the neighbors): Gulfport Light 2.3 (9.0),
Pearl River mouth 2.7 (11.8), Back Bay 3.7 (4.4), Round Island 4.0 (10.4), Merrill Shell 5.0 (6.2),
East Ship Island 7.1 (12.1).

**Build** (`msc/build.py`) writes `web/public/data/<region>/latest.json` (cards,
findings, one headline per persona, rain forecast) and
`web/public/data/<region>/sites/<id>.json` (a year of daily values with normal bands)
for the drill-down. Values are converted to the region's display units at this
step (°F, inches).

## The site

`web/` is an **Astro** site with **TypeScript**, pre-rendered on every scheduled run, so each page is plain
HTML with the current numbers already in it.

| Route | What |
|---|---|
| `/` | Overview for the general coast audience |
| `/for/<persona>/` | The same overview led by that persona's topics (oyster, shrimp, fish) |
| `/station/<slug>/` | One station: current readings, findings, linked history charts, what feeds it and where its water goes |
| `/about/` | Sources, how "typical" is computed, what alerts mean, caveats |

- **JavaScript budget.** Overview, persona and about pages ship no framework code. The theme picker, persona
  picker and "updated X ago" line are small inline scripts. Station pages load **React + ECharts** only when
  the charts scroll into view.
- **Charts** (`StationCharts.tsx`) are a single ECharts canvas with stacked panels sharing one time axis
  (upstream rain → river → station), one crosshair and one tooltip across all of them, normal bands drawn as
  polygons (they work on the log-scale river axis), and 30-day / 4-month / 1-year range buttons.
- **Persona.** Picking one goes to its page and is remembered. Opening `/` with a remembered persona goes
  straight to that persona's page.
- **Theme.** Auto, light or dark, remembered and applied before first paint.
- **The map** (`SoundMap.tsx`, MapLibre, loaded only in the browser): OpenStreetMap coastline from OpenFreeMap
  vector tiles (free, no key) styled in the site palette, NOAA Coastal Relief Model depth shading and contours
  in feet (static files from `python -m msc basemap`, committed in `web/public/basemap/`), river lines widened by
  flow percentile, and stations colored by salinity. The layers (depth, contours, river flow, salinity sketch)
  are toggleable and remembered. The salinity sketch is an inverse-distance estimate between live stations,
  clipped to water and fading out with distance; it's off by default and labeled as a sketch. Two-finger or
  Ctrl+scroll gestures keep the map from trapping page scroll. A west-to-east station list sits under the map
  as the accessible version.
- **Honesty states.** Every reading can show as normal, unusual, stale ("station quiet since…") or suspect
  ("possibly a sensor problem"). The freshness line warns if the page itself hasn't refreshed in 12 hours.
- **Fonts** are self-hosted (Fontsource), so there are no third-party requests.

The headline is composed in `msc/build.py`. Anything at watch level or above leads. Otherwise it's a plain
sentence about the rivers and what that means for the Sound, plus a persona-specific second sentence.

## Schedule and hosting

`.github/workflows/update.yml`:

- runs every 3 hours, plus a monthly normals refresh and a manual `backfill`
- keeps the data store on a `data` branch, force-pushed as a **single commit**,
  so git history doesn't grow by hundreds of MB a year (the Parquet files
  carry their own history)
- builds the Astro site and runs browser and accessibility tests (Playwright + axe,
  desktop and phone) before deploying; a failing test blocks the deploy
- deploys `web/dist` to GitHub Pages straight from the run; built JSON is never
  committed
- runs a health check (`python -m msc check`) that fails the run, so GitHub
  emails you, if the newest water reading is more than 2 days old; the page
  still deploys and shows its own staleness warning
- on pull requests: builds and tests only, with no data push and no deploy

It costs nothing for a public repo. Cloudflare Pages works too, via direct
upload with `wrangler`, but its free plan caps builds at 500 a month, so watch
that if the schedule moves to hourly.

**Known limits**

- GitHub cron is best-effort and runs can be late. That's fine for this cadence.
- GitHub disables scheduled workflows in repos with no activity for 60 days.
  The data branch push counts as activity, but check this after the first quiet
  stretch.
- USGS data is provisional. Fouled sondes produce junk, and the bounds filter
  catches only the impossible values.

## First-time setup

1. Push the repo to GitHub (public).
2. Settings → Pages → Source: **GitHub Actions**.
3. Optional: add an `API_USGS_PAT` repository secret (free key from api.waterdata.usgs.gov).
4. Actions → Update conditions → Run workflow → task: `backfill`.
5. After that, the 3-hourly schedule takes over.

## Local development

```sh
pip install -r requirements-dev.txt                # requirements.txt + basemap tools
brew install libomp                                # macOS only: LightGBM needs the OpenMP runtime
python -m msc basemap                              # one time: depth layers for the map (commit web/public/basemap/)
python -m msc backfill && python -m msc normals   # one time
python -m msc run                                  # ingest + write web/public/data
python -m msc build --asof 2019-06-02              # or replay a date (the 2019 spillway year is a good test)

cd web
npm ci
npm run dev                                        # http://localhost:4321
npm run build && npx playwright test               # what CI runs
```
