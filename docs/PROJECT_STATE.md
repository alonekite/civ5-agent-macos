# Project State

Last updated: 2026-09-14.

This file is the durable handoff for continuing development without relying on
a particular Codex conversation. It records project facts and accepted design
decisions, not raw chat transcripts.

## Dashboard

- Current milestone: M3 — ruleset knowledge coverage.
- Active next deliverable: inventory effect tables that need multiple context
  items, derived context, or new knowledge entities.
- Functional test baseline: 120 tests locally; Python 3.11/3.13 CI passed at
  prior pushed head `d96b693`.
- Blocking issue: none for offline M3 work.
- User presence required next: only the pending schema 3 and `skip_unit` bounded
  live verifications.
- Planning source: `docs/planning/MILESTONES.md`.
- Verification source: `docs/testing/TEST_MATRIX.md` and
  `docs/EXPERIMENT_LOG.md`.

## Completed and verified

- The Campaign Edition environment on Apple Silicon macOS was inspected and
  documented.
- A live Civ V to Python read path was proven through the bundled FireTuner
  protocol.
- The watcher owns the single game connection and brokers local commands over
  a private Unix socket.
- `end_turn` was executed in a live game and verified by re-reading the turn.
- Research selection and city production were executed and verified in a live
  game.
- The deterministic controller was live-verified for refusal and successful
  execution paths.
- Command identifiers, duplicate suppression, bounded IPC, private audit logs,
  preflight checks, and write-after-read verification are implemented.
- The versioned knowledge core imports eras, technologies, units, unit classes,
  promotions, policy branches, policies, buildings, building classes,
  resources, resource classes, civilizations, leaders, deterministic trait
  effects, unique replacements, disabled class overrides, religions, core
  beliefs, specialists/great-person classes, terrains, features, improvements,
  routes, yields, build actions, projects, processes, victories, unit-combat
  categories, domains, special-unit categories, and their currently supported
  relations from a local merged Civ V SQLite database.
- The real Campaign Edition database currently yields 1,337 entities and 4,283
  validated references. The map slice includes 9 terrains, 25 ordinary
  features, 2 fake features, 29 improvements, 2 routes, 6 yields, and 35 build
  actions. Generated bundles remain local and uncommitted.
- The knowledge importer records provenance, validates the active ruleset
  family, rejects broken references, and excludes AI flavor/personality data
  and copyrighted descriptive assets.
- Knowledge schema 2 adds validated attributes to references for quantities and
  modifiers while retaining canonical schema 1 read/write compatibility.
- Knowledge schema 3 adds sorted, referentially validated context items to edge
  identity while retaining canonical schema 1 and schema 2 compatibility.
- Eighty-two single-value binary table families, four multi-attribute promotion
  modifier families, and project victory thresholds add 644 attributed binary
  references. Twenty-two contextual quantity families, two contextual promotion
  grant families, promotion terrain/feature passability, and enhanced-building
  yields add 213 schema 3 contextual references; effects requiring multiple
  context items or new entity families remain deferred.
- Eleven unit identifier columns emit 323 typed, referentially checked
  relationships for technology gates, obsolescence, capture classes, ancient-
  ruin upgrades, policies, cargo categories, projects, and promotions.
- Fourteen additional plain relationship families add 253 validated links for
  faith purchasing, city/building prerequisites, local resources, free
  promotions, resource placement, trait training restrictions, post-combat
  promotions, and unit build capabilities.
- The test suite contains 120 tests locally. GitHub Actions on Python 3.11 and
  3.13 passed at the prior pushed commit `d96b693`; CI for this batch is pending.

## Implemented but awaiting bounded live verification

- Snapshot schema 3 diplomacy and science-victory fields.
- The allowlisted `skip_unit` action.

Future live tests require the user to start the game and explicitly authorize
the documented temporary firewall and FireTuner procedure. Automated work must
not enable FireTuner, launch Civ V, or change the macOS firewall.

## Planned per-game data in this repository

The current core will separate:

1. `live state`: the latest validated observation and current source of truth;
2. `turn journal`: an append-only full record of every turn, command, result,
   and verification outcome, retained for audit but not consumed wholesale by
   the controller.

Ruleset knowledge remains independent of a saved game. The journal stores facts
and verified action lifecycles; it does not summarize, infer, plan, or choose
actions.

`working_memory` and `strategic_memory` are postponed to a future LLM
interaction layer outside this repository. Their schemas will be designed with
context selection, prompting, inference, expiry, and plan-revision behavior.
Any future integration must still use the core action allowlist and write
verification.

See `docs/ARCHITECTURE.md` for the detailed boundaries.

## Recommended offline development order

1. Inventory and import multi-context effects and effects whose targets require
   new knowledge entity families.
2. Add ruleset scaling and per-game modifier resolution without mutating base
   knowledge.
3. Define the factual turn-journal schema, storage interface, canonical
   serialization, retention expectations, and integrity tests.
4. Connect watcher observations and command results to the journal without
   changing the live bridge protocol.
5. Integrate ruleset queries into deterministic controller policies.
6. Stabilize the public read/write, knowledge-query, and journal APIs.
7. Perform the two pending bounded live verifications only when the user is
   present.

LLM decision-making, working memory, strategic memory, and MCP integration
remain out of scope.

## Recent accepted decisions

- ADR-0004: generate knowledge from local sources with ruleset provenance.
- ADR-0005: exclude AI flavor and personality data.
- ADR-0006: keep the factual journal in the core and defer working/strategic
  memory to a future LLM-facing project.
- ADR-0008: include sorted typed context in schema 3 reference identity.

See `docs/architecture/decisions/README.md`. Development history belongs in
`docs/development/DEVELOPMENT_LOG.md`, not in this dashboard.
