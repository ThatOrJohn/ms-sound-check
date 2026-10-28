# 0010: Personas are configuration, not code

- **Status:** Accepted
- **Date:** 2026-10-28

## Context
Different readers (coast public, oyster, shrimp, fishing) need different leads and layouts.

## Decision
A persona is an entry in the region YAML: topic focus order, section order, default map layers. Each
persona gets a pre-rendered page (`/for/<id>/`); the choice is remembered in the browser.

## Why
Adding a persona or reordering what it sees is an edit, not a release of new logic.

## Consequences
Persona-specific content still needs indicators and sections to exist first; config only arranges them.
