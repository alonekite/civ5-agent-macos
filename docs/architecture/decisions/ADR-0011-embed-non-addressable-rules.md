# ADR-0011: Embed non-addressable rules under stable parent entities

Status: Accepted

Date: 2026-09-15

## Context

Some Civ V ruleset rows have no stable `Type` identifier of their own. Building
theming bonuses are the first supported example: several alternative rules can
belong to one building, but each row contains only a localized description,
deterministic constraints, an effect value, and an AI priority. Creating an
entity or reference per row would require invented identifiers, while using the
localized description as identity would import copyrighted presentation text.
Reference attributes also cannot distinguish otherwise-identical edges because
scalar values deliberately do not participate in reference identity.

## Decision

Represent a finite, non-addressable rule set as a canonically sorted structured
attribute on its stable parent entity when all of the following hold:

- the parent has a stable game identifier;
- the source table has no stable rule identifier;
- the rule is wholly owned by that parent and is not independently referenced;
- every retained field is deterministic gameplay data;
- normalized rules are unique and their order is deterministic.

Building theming rules are stored in a building's `theming_bonuses` array. Each
entry retains the integer bonus and explicit boolean era, work-kind, owner, and
player constraints. SQLite null booleans normalize to false. `Description` and
`AIPriority` are neither selected nor exported. Duplicate normalized rules,
invalid values, and missing building parents fail the import.

## Consequences

- The knowledge graph preserves every target ruleset theming alternative
  without synthetic IDs or localized text.
- Consumers retrieve theming rules with the owning building rather than through
  reference traversal.
- The pattern is not a shortcut for addressable or shared concepts: those still
  require typed entities and references.
- Future uses of embedded rule arrays require the same ownership, validation,
  canonical ordering, and copyright/AI-field review.

## Alternatives considered

- Generate synthetic theming-rule IDs: rejected because entity IDs must come
  from stable game identifiers.
- Use `Description` as identity: rejected because it is localized presentation
  text and not a stable gameplay identifier.
- Store one self-reference per building rule: rejected because multiple rules
  can share source, target, and context while scalar attributes are not part of
  reference identity.
- Discard theming constraints: rejected because they affect deterministic
  culture/tourism optimization.

## Supersedes

No previous ADR. This complements ADR-0007 and ADR-0008.
