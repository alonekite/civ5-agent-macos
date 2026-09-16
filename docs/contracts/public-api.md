# Public API Inventory

Status: M7 inventory complete; compatibility surface not yet frozen

## Purpose

Identify which existing interfaces are candidates for supported external use,
which versioned data contracts already carry compatibility guarantees, and
which implementation details must remain private before the 1.0 surface is
stabilized. This inventory does not turn every listed Python symbol into a
stable API by itself.

## Existing versioned contracts

| Area | Version boundary | Current compatibility |
|---|---|---|
| Live state | `GameState.schema_version` | Schemas 2–5 supported; legacy input retained where documented |
| Knowledge | `KnowledgeBundle.schema_version` | Schemas 1–3 readable; current importer emits schema 3 |
| Journal | journal record `schema_version` | Schema 1 only; unknown versions fail closed |
| Turn plan | `TurnPlan.schema_version` | Schema 1 complete-turn plans only |
| Execution report/event | `schema_version` | Schema 1 only |
| Bridge session | canonical UUIDv4 envelope | One watcher/direct-connection epoch; never a match identity |

Existing schema compatibility rules remain authoritative even while Python
import paths and CLI names are provisional.

## Candidate supported Python surface

### Bridge data and validation

- `civ5_agent.models.GameState`
- `civ5_agent.models.Command`
- `civ5_agent.models.CommandResult`
- `civ5_agent.validation.validate_live_state`

Gap: live watcher reads and single verified writes do not yet have a dedicated
bridge-facing public client. `WatcherTurnExecutor` currently wraps those
capabilities for M6, but a public bridge API should not require executor
semantics.

### Ruleset knowledge

The explicit exports in `civ5_agent.knowledge.__all__` are the candidate public
surface: versioned models and codec, `validate_bundle`, `KnowledgeIndex`, and
the structural `RulesetResolver` types. SQLite extraction remains a build/CLI
facility rather than the runtime query API.

### Factual journal

The explicit exports in `civ5_agent.journal.__all__` are the candidate public
surface: store/capture models and errors, verification, append-order replay, and
redacted export. Selective query semantics are not yet defined; M7 must not add
them without a concrete consumer and privacy contract.

### Turn plan and deterministic execution

- schema models and validation in `civ5_agent.turn_plan`;
- `turn_plan_from_dict` for strict detached JSON decoding;
- `execute_turn_plan` and `reconcile_turn_plan` with injected bridge
  capabilities;
- `WatcherTurnExecutor` as provisional watcher composition;
- `inspect_turn_requirements` and `TurnRequirement` as factual inspection.

The legacy `civ5_agent.controller.decide` readiness proof is not the M6 API and
must not become a planner.

## CLI surface

Current entry points are listed in the CLI module document. Their output is
machine-readable JSON where documented, but names and detailed error behavior
remain provisional until M7 completes. `civ5-turn` is already bounded and
watcher-only under ADR-0024.

## Implementation-only surface

The following are not candidates for external compatibility guarantees:

- raw FireTuner framing, handshake, marker parsing, and Lua builders;
- local Unix-socket server internals and watcher request handlers;
- concrete SQLite table/column extraction helpers;
- journal codec/hash/lock helpers below the exported store operations;
- private executor transition helpers;
- filesystem discovery and target-machine experiment helpers.

Public modules may delegate to these implementations, but callers must not need
them to use the supported core.

## Current size limits

| Boundary | Limit |
|---|---:|
| Local watcher request | 64 KiB |
| Local watcher response | 4 MiB |
| TurnPlan actions | 64 |
| TurnPlan JSON file | 64 KiB |
| Execution message | 1,024 characters |
| Execution event-sink errors | `2 * MAX_PLAN_ACTIONS + 2` |
| Journal record | Contract/code constant; must be published before freeze |
| Knowledge bundle | No public byte limit yet; deterministic validation required |

## Error inventory

Current callers may encounter domain errors (`TurnPlanError`, `JournalError`,
`KnowledgeValidationError`, `RulesetResolutionError`, identity/state validation
errors) and transport/filesystem errors (`ConnectionError`, `TimeoutError`,
`OSError`). These are not yet organized under one public hierarchy. CLI commands
map them to bounded JSON and nonzero exit status, but exact cross-command error
codes are not frozen.

## M7 work derived from this inventory

1. Define a bridge-facing watcher client independent of M6 and its supported
   read/action methods.
2. Define a small public exception taxonomy without hiding existing causal
   errors needed for recovery.
3. Publish exact schema, size, and compatibility guarantees from one supported
   import surface and add import/behavior contract tests on Python 3.11 and 3.13.
4. Decide whether existing knowledge and journal exports need narrower facades;
   add selective queries only for demonstrated consumers.
5. Freeze CLI names, JSON envelopes, and exit semantics or document deliberate
   provisional exceptions before M8.
