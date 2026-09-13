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

1. Continue the ruleset importer with civilizations, leaders, traits, unique
   replacements, religions, beliefs, great people, specialists, terrain,
   features, improvements, routes, yields, and remaining relation tables.
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
