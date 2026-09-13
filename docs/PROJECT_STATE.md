# Project State

Last updated: 2026-09-13.

This file is the durable handoff for continuing development without relying on
a particular Codex conversation. It records project facts and accepted design
decisions, not raw chat transcripts.

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
  resources, resource classes, and their currently supported relations from a
  local merged Civ V SQLite database.
- The knowledge importer records provenance, validates the active ruleset
  family, rejects broken references, and excludes AI flavor/personality data
  and copyrighted descriptive assets.
- The test suite contains 102 tests. The last local run passed, and GitHub
  Actions passed on Python 3.11 and 3.13 at commit `756ab68`.

## Implemented but awaiting bounded live verification

- Snapshot schema 3 diplomacy and science-victory fields.
- The allowlisted `skip_unit` action.

Future live tests require the user to start the game and explicitly authorize
the documented temporary firewall and FireTuner procedure. Automated work must
not enable FireTuner, launch Civ V, or change the macOS firewall.

## Planned data architecture

Per-game data will be separated into:

1. `live state`: the latest validated observation and current source of truth;
2. `turn journal`: an append-only full record of every turn, command, result,
   and verification outcome, retained for audit but not consumed wholesale by
   the controller;
3. `working memory`: a bounded and rebuildable view of recent events, opponent
   information, near-term intentions, and unresolved choices;
4. `strategic memory`: versioned victory objectives and approximate technology,
   policy, expansion, and military routes, including reasons for revisions.

Ruleset knowledge remains independent of a saved game. Observations,
inferences, intentions, and verified outcomes must be distinguishable. Memory
cannot bypass the bridge action allowlist or write verification, and no layer
may require an LLM.

See `docs/ARCHITECTURE.md` for the detailed boundaries.

## Recommended offline development order

1. Define the turn-journal schema, storage interface, canonical serialization,
   retention expectations, and integrity tests.
2. Connect watcher observations and command results to the journal without
   changing the live bridge protocol.
3. Add deterministic working-memory projections that can be rebuilt from test
   journals.
4. Add versioned strategic-plan records and explicit revision reasons.
5. Integrate only the minimal memory queries required by controller policies.
6. Continue the ruleset importer with civilizations, traits, religions,
   terrain, improvements, yields, and remaining relation tables.
7. Perform the two pending bounded live verifications only when the user is
   present.

LLM decision-making and MCP integration remain out of scope.
