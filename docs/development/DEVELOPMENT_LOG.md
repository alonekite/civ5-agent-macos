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

## 2026-09-14 — Live-verification ledger

- Added a Chinese manual-test status ledger that separates real-game evidence,
  partial evidence, pending tests, and rejected approaches.
- Linked each summarized conclusion to the detailed experiment log and required
  future live sessions to update the ledger and verification matrix only after
  sanitized evidence is recorded.

## 2026-09-14 — Core map and build knowledge

- Added allowlisted terrain, feature, improvement, route, yield, and build
  entities plus direct validity, unlock, creation, upgrade, and restriction
  relationships.
- Converted the trait improvement bonus identifier into a validated typed
  reference now that improvement entities exist.
- Excluded yield AI weights, graphical-only flags, prose, hotkeys, and assets.
- Imported the real merged database twice with an identical canonical hash:
  1,296 entities and 2,259 references; no generated bundle was committed.

## 2026-09-14 — Quantity-bearing knowledge contract

- Added schema 2 reference attributes for deterministic quantities and
  modifiers while preserving canonical schema 1 read/write behavior.
- Added strict validation for reference attributes, including forbidden AI
  fields and non-finite values, and documented the compatibility decision in
  ADR-0007.

Contract commit: `de60745`.

## 2026-09-14 — Binary quantity-bearing map knowledge

- Imported 15 binary terrain, feature, improvement, route, and build effect
  tables as schema 2 references with validated integer attributes.
- Imported the official `FakeFeatures` lake and river identifiers as feature
  entities marked `fake`, resolving their source-backed yield relationships
  without skipping dangling-looking rows.
- Re-imported the real merged database twice with the same canonical hash:
  1,298 entities, 2,336 references, and 77 attributed references. No generated
  bundle or source database was committed.
- Passed the complete 111-test Python 3.11 suite and the sensitive-information
  scan before submission.

Implementation commit: `2ee9f89`.

## 2026-09-14 — Contextual knowledge relation identity

- Added knowledge schema 3 typed reference context while preserving the exact
  schema 1 and schema 2 serialized shapes.
- Required context roles and entity identifiers to be valid, sorted, unique,
  and referentially complete; included context in duplicate-edge identity.
- Recorded the compatibility and modeling decision in ADR-0008 and added
  round-trip, legacy-shape, ordering, missing-target, and identity tests.
- Passed the complete 116-test Python 3.11 suite and the sensitive-information
  scan before submission.

Implementation commit: `a20bbe6`.

## 2026-09-14 — First contextual knowledge import

- Moved new SQLite imports to schema 3 and imported
  `Improvement_TechYieldChanges` with typed technology context.
- Preserved 18 technology-specific improvement yield rows, including two
  distinct technology contexts for the academy science edge.
- Re-imported the real merged database twice with the same canonical hash:
  1,298 entities, 2,354 references, 95 attributed references, and 18 contextual
  references. No generated bundle or source database was committed.
- Passed the complete 117-test Python 3.11 suite and the sensitive-information
  scan before submission.

Implementation commit: `fb80fa5`.

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
- Added religion identifiers, allowlisted core belief effects, preferred
  religions, specialists, and great-person unit-class relationships. The
  expanded real import contains 1,190 entities and 2,110 references and remains
  byte-repeatable across consecutive runs.

## Archive policy

When this file becomes difficult to scan, move completed entries into
`docs/development/archive/YYYY-QN.md` and leave links plus the current quarter
here. Do not copy raw conversations or command/tool output into this log.
