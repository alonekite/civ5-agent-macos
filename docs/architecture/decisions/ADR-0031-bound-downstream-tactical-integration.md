# ADR-0031: Bound downstream tactical integration and core evolution

Status: Accepted

Date: 2026-09-16

## Context

The independent `civ5-short-term-tactical-layer` project is the first declared
consumer of this execution core. It owns near-term domain judgment,
cross-domain arbitration, tactical plans, action intents, and consumer-side
adapters. This repository needs an explicit maintenance boundary so downstream
needs can evolve the reusable core without importing tactical policy or private
consumer types.

## Decision

The dependency remains downward-only: the tactical project may depend on this
project's stable public contracts, while this execution core never imports,
calls, packages, or requires tactical-layer code.

This core owns validated live observations, ruleset knowledge and structural
resolution, bridge-session identity, allowlisted commands, `TurnPlan` and
`PlannedAction` contracts, deterministic execution, verified results, and the
factual journal. It does not own `StrategistDirective`, `TacticalContext`,
domain reports, assessments, proposals, `TacticalPlan`, `ActionIntent`, the
Tactical Office, or consumer-side plan/result adapters.

Downstream gaps enter this repository as strategy-neutral core capability
requests. An accepted request must specify reusable observable facts or an
allowlisted mechanic, exact preconditions and postconditions, failure and
unknown-outcome behavior, compatibility impact, offline fixtures, and bounded
target-machine evidence. It must not prescribe a tactical conclusion or
authorize transport or write work in the downstream repository.

Public core changes are released through semantic versioning. Every change to
the aggregate API, schemas, allowlist, validation, result semantics, or limits
requires downstream compatibility review, but downstream documents do not
override this repository's contracts or safety decisions.

## Consequences

- The tactical layer can compile reviewed intent content into core-owned plans
  without becoming a second write authority.
- Core capability growth remains reusable across future strategic or tactical
  consumers.
- Missing capability fails closed until a new core version is implemented,
  tested, target-verified where applicable, and selected by the consumer.
- This repository documents its release capability profile and request process
  without adding a tactical runtime dependency.

## Alternatives considered

- Put tactical planning into the execution core: rejected because it would mix
  policy with legality, transport, and verification.
- Let the tactical project add its own bridge actions: rejected because it
  would create a second write authority and bypass the core allowlist.
- Treat downstream documentation as the core's contract: rejected because
  ownership and compatibility would become circular and ambiguous.
- Accept informal feature requests: rejected because schema, failure, privacy,
  and target-machine evidence requirements would be easy to omit.

## Supersedes

This does not supersede an earlier decision. It applies the module and safety
boundaries established by ADR-0015, ADR-0016, ADR-0018, ADR-0025, ADR-0026,
ADR-0027, and ADR-0030 to the first declared downstream tactical consumer.
