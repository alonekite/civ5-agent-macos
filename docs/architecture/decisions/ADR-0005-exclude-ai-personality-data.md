# ADR-0005: Exclude AI flavor and personality data

Status: Accepted

Date: 2026-09-13

## Context

Civ V ruleset tables contain both deterministic gameplay facts and fields used
to steer built-in AI priorities or leader personality. The project needs the
former to validate and plan actions but does not need the latter for its
read/write core.

## Decision

Do not collect, model, export, or ship leader/AI flavor, personality, objective,
role, trade-preference, or similar behavior parameters. Enforce the boundary
with importer allowlists, forbidden-name validation, synthetic fixtures, and
sensitive/forbidden-field scans.

Leaders, civilizations, traits, unique replacements, and deterministic numeric
effects remain valid knowledge when they do not encode AI behavior.

## Consequences

- Civilization/leader import work must review every source column and relation.
- Unknown fields are reported or rejected, not copied opportunistically.
- Future LLM behavior cannot be initialized from the game's leader-personality
  parameters through this project.

## Alternatives considered

- Import all columns and ignore unwanted fields at query time: rejected because
  prohibited data would still be collected and shipped.
- Maintain a blocklist only: rejected as insufficient; positive allowlists are
  required.

## Supersedes

None.
