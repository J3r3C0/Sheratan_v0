# Sheratan

Private monorepo for the Sheratan system (orchestrator, agents, docs, UI).

## Quickstart
- Browse docs in `docs/` (system, modules, deploy, pitches).
- LocalHub UI lives as release asset. Download from the latest release below.

## Latest Release
- **v1.6 – Docs & Pitch Expansion**: https://github.com/J3r3C0/Sheratan/releases/tag/v1.6-docs-pitch
  - Assets: `Sheratan_Docs_v1_6.zip`, `Sheratan_Pitch_Kit_v1_6.zip`

## Structure
- `docs/` — System overview, module docs, pitches
- `ui/` — LocalHub (static HTML/JS) shipped via release asset
- `core/` — orchestrator & agents (skeleton)
- `scripts/` — utilities

> Secrets go in environment variables or GitHub Secrets, **not** in the repo.

## Next
- Add CI (lint/check docs) under `.github/workflows/`.
- Add LocalHub skeleton files to `ui/` or keep shipping via releases.
