# 0011: Beach status from MDEQ's public feature service, not the website

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
MDEQ's beach site sits behind a Cloudflare bot check; its map reads a public ArcGIS feature service.

## Decision
Read the feature service directly (stations and beach segments) every run.

## Why
It's the documented data behind the official map and needs no bot-check workaround.

## Consequences
If MDEQ moves the service, the adapter fails loudly and the section disappears rather than going stale.
