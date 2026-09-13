# Development Log

This log records meaningful completed batches, not every edit. Git history is
the authoritative file-level record; target-machine evidence belongs in
`docs/EXPERIMENT_LOG.md`.

## 2026-09-12 — Environment and bridge MVP

- Inspected the Apple Silicon host, App Store Campaign Edition, Lua runtime,
  sandboxed data paths, DLC footprint, and candidate IPC mechanisms.
- Proved that the stock build discovers but cannot enable a custom mod through
  its vendor-hidden Mods UI.
- Rejected modification of the signed application copy after macOS integrity
  enforcement prevented it from launching.
- Proved read-only in-game state access through the bundled FireTuner protocol.
- Implemented the persistent watcher and local broker architecture.
- Live-verified rich state reads and `end_turn` with write-after-read proof.
- Added and live-verified research selection and city production, plus the first
  deterministic controller path.

Initial repository commit: `71439f0`.

## 2026-09-13 — Safety and schema hardening

- Added read-only preflight checks and enforced firewall/FireTuner safety gates.
- Bounded local IPC requests and responses and closed unsafe endpoint overrides.
- Implemented offline-tested snapshot schema 3 fields for score, era, city
  economy, unit condition, met-major diplomacy, and science-victory progress.
- Added UUID validation, command argument auditing, and duplicate watcher-command
  suppression.

Representative commits: `943fd7d`, `9a828a2`, `c75e98c`, `89b667e`,
`7902321`, `8d9b8e4`, `31b1bd3`, `dc09f67`, `3939583`, `9386303`.

## 2026-09-13 — Versioned knowledge core

- Added canonical ruleset entities, typed references, provenance, validation,
  deterministic serialization, hashing, and query indexing.
- Added read-only immutable SQLite import with source-change and active-WAL
  rejection.
- Imported technologies, eras, units, unit classes, upgrade routes, promotions,
  policies, policy branches, buildings, building classes, wonders, resources,
  resource classes, and supported relations.
- Added DLC-family verification and restored Python 3.11 test compatibility.
- Re-ran sensitive-information checks and GitHub Actions on Python 3.11/3.13.

Commits: `76473f8` through `756ab68`.

## 2026-09-13 — Architecture and documentation governance

- Defined factual live state and future append-only turn-journal boundaries.
- Deferred working memory and strategic memory to a separate future LLM
  interaction layer.
- Added a durable project-state handoff after recovering a locally intact Codex
  session whose UI index temporarily failed to display recent turns.
- Introduced a canonical documentation index, Chinese project outline,
  milestone plan, risk register, ADRs, module documents, contracts, and
  verification matrix.

Related commits before this governance batch: `144291b`, `14daa1d`.
Governance commit: `a053797`.

## 2026-09-13 — Civilization knowledge coverage

- Added allowlisted civilization, leader, and deterministic trait entities.
- Added civilization-to-leader, leader-to-trait, unique unit/building, and
  disabled class relationships.
- Explicitly excluded leader personality values, AI playability, flavor tables,
  prose, and presentation assets.
- Defined deterministic duplicate-slot handling and rejected replacements whose
  declared unit/building class does not match the target entity.
- Imported the target installation's merged database read-only without writing
  a generated bundle to the repository: 1,100 entities and 2,059 references.

## Archive policy

When this file becomes difficult to scan, move completed entries into
`docs/development/archive/YYYY-QN.md` and leave links plus the current quarter
here. Do not copy raw conversations or command/tool output into this log.
