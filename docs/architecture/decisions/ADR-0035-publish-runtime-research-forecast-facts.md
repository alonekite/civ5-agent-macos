# ADR-0035: Publish runtime research forecast facts without claiming a ruleset fingerprint

Status: Accepted

Date: 2026-09-19

## Context

The downstream tactical layer needs exact, strategy-neutral facts for ordinary
research timing. Live-state schema 5 exposes technology identifiers, whole-unit
current progress and cost, and whole-unit science per turn. It does not expose
the precision, overflow, phase, or provenance needed to distinguish an exact
runtime forecast from a synthetic approximation.

The target runtime and bundled UI/source evidence expose candidate-specific
`GetResearchCost`, `GetResearchProgressTimes100`, `GetScienceTimes100`,
`GetOverflowResearch`, and `GetResearchTurnsLeft(tech_id, true)` bindings. The
same sources expose stable setting identifiers for game speed, handicap, world
size, map script, and active civilization. They do not expose a verified,
complete cryptographic manifest of every enabled ruleset input.

## Decision

Live-state schema 8 will add a mandatory `research_forecast` object and a
mandatory `runtime_context` object. They are read-only observations. They do
not add an action or change `choose_research`, `TurnPlan`, command-result, or
journal schemas.

`research_forecast` is exact-supported only during the ordinary active-player
action window, after interturn research resolution. It publishes:

- `science_per_turn_times100` directly from `GetScienceTimes100`;
- `overflow_research` directly from `GetOverflowResearch` in whole research
  points, with no fabricated times-100 precision;
- current and candidate technology `cost`, `progress_times100`, and
  `turns_left_with_overflow` from their named runtime bindings;
- a fixed field-provenance map naming each binding and the phase predicates.

Free-technology, technology-steal, inactive-turn, message-processing, missing-
binding, and malformed results are explicit unsupported/unavailable states and
never exact-supported forecasts. Schema 8 does not infer a recently completed
technology because no reliable runtime fact has been identified for it.

`runtime_context` publishes only identifiers obtained from runtime APIs and
`GameInfo` lookups. Every dimension carries its own `available`, `unavailable`,
or `unsupported` status. The `ruleset_fingerprint` dimension is always
`unsupported` in schema 8. A fixed product string, zero, local installation
path, or inferred DLC set must never substitute for a runtime fact.

A downstream adapter may bind this context to a selected, provenance-bearing
`KnowledgeBundle` and compute its own complete ruleset fingerprint. Incomplete
or conflicting binding must fail closed for exact-supported forecasting and
forecast-dependent automatic intent eligibility. Binding is not required to
expose the core's authoritative live facts, and it does not by itself prohibit
a separately approved core-only manual intent that makes no exact-forecast
claim.

## Consequences

- Core 1.3.0/schema 8 can provide exact runtime research timing inputs without
  becoming a tactical forecaster.
- Overflow preserves the actual whole-point precision of the exposed binding;
  multiplying it by 100 would change representation, not add information, so
  no `overflow_research_times100` field is published.
- The context object supports explicit compatibility checks but is not a
  cryptographic ruleset proof.
- Schema 2–7 readers remain supported unchanged. Consumers require schema 8,
  capability version 1, supported status, and sufficient external ruleset
  binding before claiming exact forecasting or forecast-dependent automation.
- Target-machine evidence remains required before schema 8 is described as
  live-verified.

## Alternatives considered

- Derive costs and overflow from a knowledge bundle: rejected because the live
  game already owns the effective runtime values and modifiers.
- Publish a hard-coded BNW/Campaign Edition fingerprint: rejected because it
  would not prove active DLC, scenarios, mods, or runtime database contents.
- Publish overflow as times-100 by multiplying the integer binding: rejected
  because this suggests precision that was never observed.
- Put forecast calculations in the deterministic executor: rejected because
  the executor executes explicit plans and must not choose or score research.
