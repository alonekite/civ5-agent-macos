# Project State

Last updated: 2026-09-14.

This file is the durable handoff for continuing development without relying on
a particular Codex conversation. It records project facts and accepted design
decisions, not raw chat transcripts.

## Dashboard

- Current milestone: M3 — ruleset knowledge coverage.
- Active next deliverable: quantity-bearing terrain, feature, improvement,
  route, yield, building, policy, belief, and resource effect tables.
- Functional test baseline: 109 tests locally; Python 3.11/3.13 CI last passed
  at documentation-governance commit `a053797` before the current knowledge
  batch.
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
  routes, yields, build actions, and their currently supported relations from a
  local merged Civ V SQLite database.
- The real Campaign Edition database currently yields 1,296 entities and 2,259
  validated references. The new map slice includes 9 terrains, 25 features, 29
  improvements, 2 routes, 6 yields, and 35 build actions. Generated bundles
  remain local and uncommitted.
- The knowledge importer records provenance, validates the active ruleset
  family, rejects broken references, and excludes AI flavor/personality data
  and copyrighted descriptive assets.
- Knowledge schema 2 adds validated attributes to references for quantities and
  modifiers while retaining canonical schema 1 read/write compatibility.
- The test suite contains 109 tests locally. GitHub Actions on Python 3.11 and
  3.13 last passed at commit `a053797`; the current batch must pass CI after it
  is pushed.

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

1. Define schema support for quantity-bearing references, then import dependent
   terrain, feature, improvement, route, building, policy, belief, specialist,
   and resource effect tables.
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

See `docs/architecture/decisions/README.md`. Development history belongs in
`docs/development/DEVELOPMENT_LOG.md`, not in this dashboard.
