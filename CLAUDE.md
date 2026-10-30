# ms-sound-check

Free, plain-language Mississippi Sound conditions site. A Python pipeline (`msc/`) pulls public data every 4 hours in
GitHub Actions, writes JSON, and an Astro + React site (`web/`) renders it to GitHub Pages.

Read first: `QUICKSTART.md` (how it all fits), `docs/ROADMAP.md` (what's next), the current sprint in
`docs/sprints/`, and `docs/decisions/` before changing anything a decision record covers.

## Commands

```bash
source .venv/bin/activate                     # Python 3.11+, deps in requirements.txt (+ requirements-dev.txt)
python -m msc run                             # ingest + build JSON into web/public/data/ms/
python -m msc build                           # rebuild JSON from the local store only (fast)
python -m msc check                           # health check CI runs
cd web && npm run dev                         # http://localhost:4321
cd web && npm run build                       # astro check + build (must pass with 0 errors)
cd web && npm run test:e2e                    # Playwright + axe; gates deploys
python scripts/dev_fixtures.py apply|clear    # sample beach advisories / rising river / forecasts for UI work
```

Node: version in `web/.nvmrc` (>= 22.23.4).

## Layout

- `regions/ms.yaml`: stations, personas (`card_order`, `map_layers`), indicators. Prefer config over code.
- `msc/adapters/`: one module per source; `msc/models/`: virtual sensors, oyster, fishing, beaches, shrimp;
  `msc/indicators.py`: findings; `msc/build.py`: JSON output and headlines.
- `web/src/`: `components/Overview.astro` (home), `pages/`, `lib/types.ts` (mirrors build.py output),
  `styles/global.css` (all design tokens).
- `.github/workflows/update.yml`: update / deploy / health / experiment jobs. The data store lives on the `data` branch.

## Rules

- Oyster wording must never say an area "is closed". Only MDMR decides closures; we compare readings to their plan.
- Not for navigation or harvest decisions; keep that disclaimer and plain, non-alarmist language.
- Don't bypass bot checks (e.g. Cloudflare on beaches.mdeq.ms.gov); use public APIs/feature services only.
- `API_USGS_PAT` is passed only to the USGS backfill/ingest steps. Keep it that way.
- Every new source call goes through `_try` in `msc/__main__.py` so one failure can't break a run, and stale data
  (past its `fetched_at` max age) hides rather than shows old numbers.
- Never commit sample data: run `dev_fixtures.py clear && python -m msc build` after UI work. `data/` and
  `web/public/data/` are gitignored.
- UI: follow `docs/decisions/0013-instrument-panel-design.md`. Colors only via tokens in `global.css`; keep map
  tokens hex (SoundMap.tsx parses them). Both themes must pass axe contrast.
- Astro: keep `compressHTML: true`; build sentences as strings in JSX (inline whitespace gets dropped otherwise).
- When you finish a feature: tick the sprint checklist, update `CHANGELOG.md` (user-visible changes only) and
  `docs/ROADMAP.md`, and add a decision record for anything a future reader would ask "why?" about.
