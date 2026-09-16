# Downstream Tactical Integration Contract

Status: Stable capability profile for 1.0.0

## Purpose

Define the supported boundary between this execution core and independent plan
producers such as `civ5-short-term-tactical-layer`. This document describes
what core 1.0.0 exposes, who owns each concept, how a consumer detects
compatibility, and which capabilities remain absent. It does not define
tactical policy or authorize a downstream game connection.

## Dependency direction

Dependencies flow from a plan producer to this core. This repository never
imports, calls, packages, or requires a tactical or strategic project. A
consumer may use only the stable `civ5_agent.api` surface and the stable
`civ5-turn` contract; private modules and transport details are not integration
points.

## Ownership

| Concern | Owner |
|---|---|
| Live state collection and validation | Execution core |
| Ruleset knowledge, provenance, and structural resolution | Execution core |
| Bridge-session identity and state digest | Execution core |
| Command allowlist and exact argument validation | Execution core |
| `TurnPlan`, `PlannedAction`, execution, and result semantics | Execution core |
| Read-after-write verification and factual journal | Execution core |
| Strategic directive and victory monitoring | Upstream strategic layer |
| Domain assessment, proposal, and shared-resource arbitration | Tactical layer |
| `TacticalPlan` and `ActionIntent` content | Tactical layer |
| Intent-to-plan and result-to-tactical-state adapters | Tactical layer |

Consumer terms such as `CoreCapabilities` and `VerifiedActionResult` may be
useful adapter views, but they do not replace or redefine the core's exported
objects, status meanings, or success conditions.

## Core 1.0.0 capability profile

The stable aggregate API exposes the facts needed to construct this static
release profile:

| Capability | Core 1.0.0 value |
|---|---|
| Package/API identity | `civ5-agent-macos` 1.0.0; `civ5_agent.api` |
| Live-state schemas | 2, 3, 4, 5 |
| Knowledge schemas | 1, 2, 3 |
| Journal schema | 1 |
| `TurnPlan` schema | 1 |
| `ExecutionReport` and `ExecutionEvent` schema | 1 |
| Plan action limit | 64 |
| Plan execution | Complete-turn plans with explicit final `end_turn` |
| Actions | `choose_research`, `set_city_production`, `skip_unit`, `end_turn` |
| Live execution identity | `bridge_session_id`, turn, active player, full state digest |
| Result states | `completed`, `paused`, `stale`, `failed`, `recovery_required` |
| Unknown outcome | Conservative reconciliation; never automatic retry |

Exact byte and message limits are exported by `civ5_agent.api` and owned by
their individual contracts. A consumer must compare package and contract
versions, required action names, and required fields explicitly. A greater
schema or package number never implies an absent field or action.

## Capability discovery in 1.0.0

Core 1.0.0 does not define a serialized capability-manifest wire contract.
Python consumers may construct a detached compatibility profile from
`__version__`, `ALLOWED_ACTIONS`, the exported supported-schema sets, schema
constants, and limit constants. They must not inspect private modules or infer
per-field availability from a package version alone.

The 1.0.0 profile does not export per-action capability versions, field-level
feature flags, or target-evidence labels. Consumers that require those values
must use a reviewed static compatibility matrix or submit a capability request
for a future public manifest. Absence of a manifest never permits optimistic
execution.

## Compilation and execution boundary

A downstream adapter may create core `PlannedAction` and `TurnPlan` values only
from already approved consumer content. It must preserve core action arguments,
identities, bounds, and state basis exactly and call core validation before
execution. It may not choose tactics, add an action, bypass plan admission,
submit Lua, open FireTuner, call a lower-level command path as a workaround, or
retry an ambiguous action.

Only core `CommandResult` and `ExecutionReport` evidence after live-state
re-reading can establish write success. A consumer adapter must preserve every
terminal status and must not convert acceptance, timeout, missing evidence, or
an assessment into verified success.

## Factual history boundary

The journal is not an execution dependency. Core 1.0.0 exposes verification,
full private replay, and redacted structural export, but no bounded selective
tactical-history query. Consumers must not parse journal storage or treat it as
an execution cursor. A future history view requires its own privacy, ordering,
provenance, bounds, compatibility, and no-write contract.

## Capabilities absent from 1.0.0

- serialized capability manifest;
- selective factual history view;
- coordinate movement, pathing, combat, and worker-task actions;
- city founding, policy, religion, purchase, citizen, trade-route, diplomacy,
  espionage, and great-person actions;
- tactical scoring, candidate selection, planning, memory, or strategy.

Their absence is a compatibility result, not permission for a consumer-side
workaround. New reusable facts and mechanics follow the core capability request
process.

## Compatibility and maintenance

Incompatible changes to the stable aggregate API or `civ5-turn` require a new
major version. Backward-compatible capability additions require at least a
minor release; compatible fixes use a patch release. A new or changed schema,
action, result meaning, identity rule, or public limit must update its owning
contract, this profile, tests, release notes, and downstream compatibility
assessment in the same batch.
