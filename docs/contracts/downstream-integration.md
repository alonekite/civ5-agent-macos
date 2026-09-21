# Downstream Tactical Integration Contract

Status: Stable capability profile for 1.2.0

## Purpose

Define the supported boundary between this execution core and independent plan
producers such as `civ5-short-term-tactical-layer`. This document describes
what core 1.2.0 exposes, who owns each concept, how a consumer detects
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

## Core 1.2.0 capability profile

The stable aggregate API exposes the facts needed to construct this static
release profile:

| Capability | Core 1.2.0 value |
|---|---|
| Package/API identity | `civ5-agent-macos` 1.2.0; `civ5_agent.api` |
| Live-state schemas | 2, 3, 4, 5, 6, 7 |
| Knowledge schemas | 1, 2, 3 |
| Journal schema | 1 |
| `TurnPlan` schema | 1 |
| `ExecutionReport` and `ExecutionEvent` schema | 1 |
| Plan action limit | 64 |
| Plan execution | Complete-turn plans with explicit final `end_turn` |
| Actions | `choose_research`, `set_city_production`, `skip_unit`, `move_unit`, `worker_build`, `end_turn` |
| Live execution identity | `bridge_session_id`, turn, active player, full state digest |
| Result states | `completed`, `paused`, `stale`, `failed`, `recovery_required` |
| Unknown outcome | Conservative reconciliation; never automatic retry |

Exact byte and message limits are exported by `civ5_agent.api` and owned by
their individual contracts. A consumer must compare package and contract
versions, required action names, and required fields explicitly. A greater
schema or package number never implies an absent field or action.

## Capability discovery in 1.2.0

Core 1.2.0 does not define a serialized capability-manifest wire contract.
Python consumers may construct a detached compatibility profile from
`__version__`, `ALLOWED_ACTIONS`, the exported supported-schema sets, schema
constants, and limit constants. They must not inspect private modules or infer
per-field availability from a package version alone.

The 1.2.0 profile does not export per-action capability versions, field-level
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

The journal is not an execution dependency. Core 1.2.0 exposes verification,
full private replay, and redacted structural export, but no bounded selective
tactical-history query. Consumers must not parse journal storage or treat it as
an execution cursor. A future history view requires its own privacy, ordering,
provenance, bounds, compatibility, and no-write contract.

## Capabilities absent from 1.2.0

- serialized capability manifest;
- selective factual history view;
- autonomous/path movement, combat, worker automation, routes, repair, feature
  removal, and worker-task selection;
- city founding, policy, religion, purchase, citizen, trade-route, diplomacy,
  espionage, and great-person actions;
- tactical scoring, candidate selection, planning, memory, or strategy.

Their absence is a compatibility result, not permission for a consumer-side
workaround. New reusable facts and mechanics follow the core capability request
process.

## 1.2.0 ordinary worker-build capability

M10 adds one strategy-neutral caller-selected ordinary `BUILD_*` action by a
worker already standing on the intended plot. It remains absent from core
1.1.0. The tactical
layer retains worker, plot, improvement, ordering, and purpose selection; the
core request is limited to visible current-plot facts, conservative per-unit
candidates, exact dispatch, and factual verification.

Consumers require package 1.2.0 or later, schema 7 in the supported schema set,
`worker_build` in `ALLOWED_ACTIONS`, and the exact schema/limit constants
published by the aggregate API. Greater version numbers alone remain
insufficient. Core 1.1.0 consumers must report the domain as unsupported and
emit no worker-build action; direct FireTuner access or another consumer-side
write path is not a fallback. See the [worker-build contract](worker-build.md).

The frozen action carries exactly `unit_id`, `x`, `y`, and `build_type`. The
unit's schema 7 record supplies current-plot facts, current build, and zero to
32 factual `{build_type, improvement_type}` candidates. Coordinates identify
the exact caller-authorized plot. Candidate order is not a recommendation, and
the consumer must preserve the paired expected improvement without deriving a
different one.

Only a core `success` backed by the worker-build contract's active-build or
completed-improvement postcondition is success. An accepted marker, selection
change, timeout, or missing evidence is not. The consumer preserves failures
and unknown outcomes and replans only from a later fresh state. See the
[worker-build contract](worker-build.md).

## 1.1.0 movement capability

The accepted M9 contract defines live-state schema 6 and an allowlisted
`move_unit(unit_id, x, y)` action for one explicit adjacent ordinary move.
Core 1.1.0 implements and target-verifies the schema 6 read model and bounded
bridge command path; TurnPlan integration is covered offline.
Each owned unit exposes only the bounded
`ordinary_move_targets` that the core is prepared to admit under that contract.
This does not add path selection,
terrain assessment, combat, worker tasks, or tactical recommendations.

Consumers must require package version 1.1.0 or later, schema 6, and
`move_unit` in the stable aggregate constants before constructing this action.
The tactical layer remains responsible for selecting the unit, destination,
ordering, and any replanning.

## Compatibility and maintenance

## Development 1.3.0 research runtime facts

The development head adds live-state schema 8 and capability/context versions
1. These are authoritative runtime facts when `research_runtime_facts.status` is
`supported`; they are not a complete ruleset manifest. Exact-supported
forecasting and forecast-dependent automatic intent eligibility additionally
require a sufficient, non-conflicting downstream KnowledgeBundle binding.
That binding is not required to expose the live facts and does not, by itself,
prohibit a separately approved core-only/manual-review `choose_research` intent
that makes no exact-forecast claim.

This section is a development compatibility forecast, not part of the stable
1.2.0 profile. Bounded target evidence passes; the 1.3.0 release gate remains
pending.

Incompatible changes to the stable aggregate API or `civ5-turn` require a new
major version. Backward-compatible capability additions require at least a
minor release; compatible fixes use a patch release. A new or changed schema,
action, result meaning, identity rule, or public limit must update its owning
contract, this profile, tests, release notes, and downstream compatibility
assessment in the same batch.
