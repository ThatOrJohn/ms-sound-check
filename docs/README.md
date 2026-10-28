# Docs

| File | What it's for |
|---|---|
| [../QUICKSTART.md](../QUICKSTART.md) | **Coming back after a while? Read this first.** What does what, common tasks, troubleshooting. |
| [ROADMAP.md](ROADMAP.md) | **Then this.** What's done, what's in the current sprint, what's next, known issues. |
| [sprints/](sprints/) | One file per sprint: goal, checklist, notes, outcome. Closed sprints stay as history. |
| [decisions/](decisions/) | Architecture decision records: one short file per significant choice and why. |
| [../CHANGELOG.md](../CHANGELOG.md) | User-visible changes, newest first. |
| [architecture.md](architecture.md) | How the system works today (pipeline, regions, indicators, site, CI). |
| [feasibility.md](feasibility.md) | Original research, probe results and ML experiments. |
| [seed.md](seed.md) | The original idea. |

## How the tracking works

- **Sprints are a week.** A sprint file is named `YYYY-MM-DD-sNN-short-name.md` by start date. It holds the
  goal, a checklist (`- [ ]` / `- [x]`), notes as work happens, and an outcome when it closes.
- **The roadmap is the index.** It links the current sprint, lists done sprints in one line each, and holds
  the backlog in three buckets: Next (likely in the coming sprint or two), Later (wanted, not scheduled) and
  Parked (considered and set aside, with a pointer to why).
- **Decisions get a record when they're expensive to reverse or likely to be questioned later.** Copy
  `decisions/TEMPLATE.md`, number it, and link it from wherever the decision shows up. Never edit an
  accepted decision's reasoning; supersede it with a new record.
- **The changelog is for things a visitor or operator would notice.** Internal refactors don't go there.
- **Closing a sprint:** tick or move every item (unfinished items go to the next sprint or back to the
  roadmap), write the outcome in two or three lines, update the roadmap, add changelog entries.
