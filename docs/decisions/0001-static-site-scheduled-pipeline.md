# 0001: Static site rebuilt by a scheduled pipeline, no server

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Hobby project, free to run, updated a few times a day from public data.

## Decision

A Python pipeline runs every 4 hours in GitHub Actions, writes JSON, and a static site is pre-rendered
and deployed to GitHub Pages. No server, no database.

## Why

Every source updates hourly at best, so a 3-hour rebuild loses nothing. Static pages are fast, free,
indexable and can't go down independently of GitHub.

## Consequences

Nothing is truly real-time; the page says how fresh it is and warns when it's stale. Anything needing
per-user state (alerts by email, accounts) would need a different decision.
