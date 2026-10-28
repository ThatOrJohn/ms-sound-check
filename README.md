# ms-sound-check

A plain-language read on what the Mississippi Sound is doing, built on public
USGS/MDMR data. Hobby project.

- `QUICKSTART.md`: **coming back after a while? Read this first**
- `docs/ROADMAP.md`: what's done, what's now, what's next
- `docs/seed.md`: the original idea
- `docs/feasibility.md`: what exists, data health, free stack, build order
- `docs/architecture.md`: how the pipeline, regions, indicators and page fit together
- `regions/ms.yaml`: Mississippi sites, personas and indicators
- `msc/`: the pipeline (`python -m msc run`)
- `web/`: the site (Astro + TypeScript, React + ECharts for charts)
- `data/shrimp_openings.csv`: MDMR shrimp season opening dates, 2012–2026, with sources
- `scripts/probe_shrimp_signal.py`: does spring salinity predict opening day?

## Run the probe

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy requests gsw matplotlib
python scripts/probe_shrimp_signal.py --synthetic   # offline smoke test
python scripts/probe_shrimp_signal.py               # real USGS data (~8 downloads, cached in data/raw/)
```

Results land in `data/probe/` (features, scores, and a scatter of the best feature).
