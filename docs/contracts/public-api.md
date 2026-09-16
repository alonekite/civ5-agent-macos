# Public API Inventory

Status: Supported aggregate pre-1.0 surface implemented; bounded CLI classified

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

Existing schema compatibility rules remain authoritative. `civ5_agent.api` is
the supported aggregate Python import path under ADR-0026; ADR-0027 separately
stabilizes `civ5-turn` and explicitly classifies every other CLI as provisional.

## Candidate supported Python surface

### Bridge data and validation

`civ5_agent.bridge.__all__` exposes the bridge surface:
the `Bridge` protocol, watcher-only `WatcherBridgeClient`, `GameState`,
`Command`, `CommandResult`, `ALLOWED_ACTIONS`, `validate_command`, and
`CommandValidationError`. `NO_END_TURN_BLOCKING_TYPE` exposes the verified
target-build numeric value used by the live-state field and factual requirement
inspection. Live reads and individual verified writes no longer require M6
types.

## Supported aggregate import

`civ5_agent.api.__all__` is contract-tested as the supported aggregate pre-1.0
surface. It re-exports the documented module models, operations, errors, schema
versions, supported schema sets, and byte/count limits. Raw FireTuner, IPC
server, watcher-handler, importer, and private codec helpers are deliberately
absent.

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

Current entry points are listed in the CLI module document. `civ5-turn` is the
supported machine-readable pre-1.0 boundary under ADR-0027. Every other entry
point is explicitly provisional even where its current output is JSON.

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
| Internal FireTuner Lua program | 1,000 UTF-8 bytes |
| TurnPlan actions | 64 |
| TurnPlan JSON file | 64 KiB |
| Command-result or execution-report message | 1,024 characters |
| Execution event-sink errors | 130 |
| Journal record | 4 MiB |
| Knowledge bundle | No fixed public byte limit; deterministic validation and source integrity are mandatory |

## Error inventory

All supported domain errors inherit `Civ5AgentError`. Validation errors retain
`ValueError` compatibility, safety errors retain `RuntimeError`, protocol errors
retain `ValueError`, and transport-ambiguous exchanges use `TransportError`,
which retains `ConnectionError`. Wrapped failures preserve `__cause__`. CLI
commands map errors to bounded JSON and nonzero exit status, but exact
cross-command error codes are not frozen.

## Facade assessment

Current supported consumers do not require narrower knowledge or journal
facades. `KnowledgeIndex` supplies stable identifier/relation lookup, while
journal verification, replay, and redacted export cover the supported factual
history workflows. Selective queries remain deferred until a concrete consumer
can define privacy, ordering, and compatibility requirements.
