# ADR-0013: Require explicit ruleset resolution context

Status: Accepted

Date: 2026-09-15

## Context

Static knowledge records facts for an entire ruleset, while a match selects one
game speed, difficulty, map size, civilization, and sets of adopted policies and
active beliefs. Applying modifiers without a complete declared selection could
silently combine facts from incompatible rulesets or guess missing match state.
Returning the base entity objects would also let a consumer mutate the bundle's
nested attribute containers.

## Decision

The resolver accepts one immutable `ResolutionContext` containing the exact
`Ruleset` identity and stable identifiers for the selected game speed,
difficulty, map size, civilization, adopted policies, and active beliefs. It
requires an exact ruleset match, rejects unknown or duplicate identifiers, and
canonically sorts set-like selections.

The initial `ResolvedRuleset` returns validated selected entities and source
provenance. Selected entities are detached deep copies so consumer mutation
cannot alter the indexed base bundle. Later effective-value APIs will build on
this context and must retain both base and modifier provenance.

## Consequences

- Missing or incompatible context fails closed instead of producing defaults.
- Equivalent policy and belief sets resolve to the same canonical ordering.
- The base knowledge bundle remains unchanged during and after resolution.
- Live-state adapters must translate observed match settings into stable game
  identifiers before requesting effective values.
- Modifier application can be added incrementally without changing the context
  identity contract.

## Alternatives considered

- Infer omitted settings from common defaults: rejected because saves and mods
  can legitimately differ.
- Mutate a copied full bundle: rejected because it obscures base facts and
  modifier provenance.
- Accept untyped dictionaries: rejected because missing, misspelled, and
  duplicate selections would be harder to reject consistently.

## Supersedes

None.
