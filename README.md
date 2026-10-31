# Sound Check

A free, plain-language read on what the Mississippi Sound is doing: salinity, water temperature, river flow, rain,
beach advisories, oyster closure context, shrimp notices and a fishing outlook, built on public data and updated every
four hours.

**Live site: <https://thatorjohn.github.io/ms-sound-check/>**

> Sound Check is a hobby project. It is not an official source and no agency reviews or endorses it. It is **not for
> navigation or harvest decisions**. Beach advisories, oyster closures, shrimp seasons and marine forecasts are decided
> by MDEQ, MDMR and the National Weather Service, and where we differ from them, they are right.

## How it works

- A Python pipeline (`msc/`) runs in GitHub Actions every four hours, pulls public data, and writes JSON.
- An Astro + React site (`web/`) renders that JSON as static pages and deploys to GitHub Pages. There is no server.
- The accumulated data store lives on the `data` branch; sites, personas and indicators are config in `regions/ms.yaml`.

More in [QUICKSTART.md](QUICKSTART.md), [docs/architecture.md](docs/architecture.md) and the
[decision records](docs/decisions/).

## Run it locally

Python 3.11+ and Node (version in `web/.nvmrc`).

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m msc run                  # ingest + build JSON into web/public/data/ms/
cd web && npm install && npm run dev   # http://localhost:4321
```

Other commands: `python -m msc build` (rebuild from the local store), `python -m msc check` (health check),
`npm run build` (type check + build), `npm run test:e2e` (Playwright + axe accessibility).

`API_USGS_PAT` is an optional USGS API key that raises rate limits; the pipeline works without it.

## Data sources and attribution

USGS water data, National Weather Service observations and forecasts, NOAA tides and bathymetry, Mississippi Department
of Marine Resources (MDMR) notices, MDEQ beach monitoring, [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), and
OpenStreetMap / OpenFreeMap map data. Readings are provisional and can be revised. The full list, with how each source
reaches the site, is on the site's [About the data](https://thatorjohn.github.io/ms-sound-check/about/) page.

The license below covers this project's code. The data belongs to its publishers and is subject to their terms.

## Feedback

Found a wrong number or confusing wording? [Open an issue](https://github.com/ThatOrJohn/ms-sound-check/issues).
Corrections to anything that sounds like an official closure or advisory are especially welcome.

## Project docs

- [docs/ROADMAP.md](docs/ROADMAP.md): what's done, what's now, what's next
- [docs/seed.md](docs/seed.md): the original idea
- [docs/feasibility.md](docs/feasibility.md): what exists, data health, free stack
- [CHANGELOG.md](CHANGELOG.md): user-visible changes
- `data/shrimp_openings.csv`: MDMR shrimp season opening dates, 2012–2026, with sources
- `scripts/probe_shrimp_signal.py`: does spring salinity predict opening day?

## License

[MIT](LICENSE) © 2026 John Walley
