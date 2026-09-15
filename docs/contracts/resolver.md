# Ruleset Resolver Contract

Status: Initial context-resolution contract implemented

## Input

`ResolutionContext` declares the exact ruleset plus one game-speed, handicap,
world-size, and civilization identifier. Adopted policies and active beliefs
are tuples of stable identifiers and are treated as unordered sets.

## Resolution

`RulesetResolver` validates the source bundle through `KnowledgeIndex`, requires
an exact ruleset match, resolves every selected identifier against its required
entity kind, rejects duplicates, and sorts policy and belief identifiers.

`ResolvedRuleset` contains the canonical context, selected entities, and source
provenance. Its entity values are detached from the indexed base bundle. This
initial contract validates context only; it does not yet calculate effective
costs, yields, replacements, unlocks, or other composed modifiers.

## Failure behavior

Resolution raises `RulesetResolutionError` for a mismatched ruleset, unknown
selected entity, duplicate set member, or malformed policy/belief collection.
It never substitutes a default or ignores an unsupported selection.

## Compatibility

Field names and failure semantics remain provisional until M7 public API
stabilization. Consequential changes before then require documentation and
tests; after M7 they require an explicit compatibility decision.
