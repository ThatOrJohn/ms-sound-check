# 0031: Weekly digest as RSS and a Bluesky post

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

The roadmap asked for a weekly Bluesky post and RSS from the same build. The site is static and rebuilt every 4 hours,
so a feed needs somewhere to keep past weeks, and posting needs credentials the repo doesn't hold.

## Decision

- The scheduled build adds one entry per ISO week to `digest.json` in the data store, on the first run on or after
  Friday 6 AM Central (`digest` in `regions/ms.yaml`), keeping the last 12. A build with `--asof` never adds one.
- An entry is the Coast headline plus up to three general-topic signals it doesn't already say (record lines before
  plain "running low" ones), the beaches if the headline doesn't cover them, and "years like this one" with "not a
  forecast". It's composed from `latest.json`, so it never says anything the page doesn't.
- The site publishes the entries as `digest.xml` (RSS 2.0), linked from every page's head and from About.
- `python -m msc post` posts the newest entry from the last day to Bluesky as text plus a link card using
  `og/index.png` (the history picture). It runs in CI only on the schedule, only with the `BLUESKY_HANDLE` and
  `BLUESKY_APP_PASSWORD` secrets, and `continue-on-error`. Without the secrets it logs that an entry is ready.

## Why

- Friday morning is when anglers and beachgoers plan the weekend; one post a week stays useful without becoming noise.
- Building the post from the same JSON keeps the disclaimers and calm wording the site already has.
- Plain HTTP to the AT Protocol endpoints avoids a new dependency for three calls.

## Consequences

- Nothing is posted until someone creates a Bluesky account and adds the two secrets (an app password, not the
  account password).
- If the post step fails, the entry stays unposted and is retried on the next scheduled run that day; after a day it's
  skipped rather than posted late.
- A missed Friday (Actions down all day) still gets an entry on the next run that week; a fully missed week has none.
