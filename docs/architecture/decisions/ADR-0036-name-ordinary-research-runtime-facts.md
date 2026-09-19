# ADR-0036: Name the schema 8 observation ordinary research runtime facts

Status: Accepted

Date: 2026-09-19

Supersedes: ADR-0035's public naming decision only

## Context

ADR-0035 correctly froze the schema 8 values, units, provenance, support states,
runtime-context boundary, and downstream ruleset-binding responsibility. Its
provisional public name used “forecast,” although every published value is an
authoritative observation returned by the current game runtime. The core does
not project future state, calculate a research route, or recommend a choice.

Because schema 8 and core 1.3.0 have not been released, the misleading name can
be corrected without carrying a compatibility alias into the stable API.

## Decision

The public object is named `research_runtime_facts`. The corresponding
`GameState` attribute is `research_runtime_facts`, and the public discovery
constant is `RESEARCH_RUNTIME_FACTS_CAPABILITY_VERSION`.

The segmented FireTuner protocol uses part name `research_runtime_facts` and
marker `CIV5_AGENT_RESEARCH_RUNTIME_FACTS`. Parser, validator, serialization,
API exports, tests, and current documentation use the same terminology. No old-
name compatibility alias is provided.

This decision changes names only. All field names inside the object, integer
units, provenance, candidate rules, support/failure states, runtime context,
schema number, capability version, and downstream responsibilities remain as
accepted in ADR-0035.

## Consequences

- The public name describes observed game facts and does not imply that the
  deterministic core performs forecasting.
- Schema 8 canonical serialization contains `research_runtime_facts` and never
  the provisional old key.
- Schemas 2–7 retain their exact serialized bytes and state digests because the
  schema-8-only fields remain absent from those payloads.
- Current contract, plan, and verification filenames use
  `research-runtime-facts`; historical development-log language and ADR-0035
  remain immutable records of the earlier decision.
- A downstream layer may use these facts to forecast, but that calculation and
  any KnowledgeBundle compatibility decision remain outside this core.

## Alternatives considered

- Keep the old name: rejected because it attributes consumer computation to a
  factual observation contract.
- Add a compatibility alias: rejected because the capability has not reached a
  stable release and two names would create avoidable ambiguity.
- Change the nested fields or semantics at the same time: rejected because the
  issue is terminology, while ADR-0035's factual design remains valid.
