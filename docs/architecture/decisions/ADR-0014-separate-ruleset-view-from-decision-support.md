# ADR-0014: Separate ruleset views from decision support

Status: Accepted

Date: 2026-09-15

## Context

The initial M4 plan treated ruleset resolution as both a structural knowledge
view and a future mechanism for composing effective costs, yields, unlocks, and
other modifiers. That placed counterfactual rule analysis too close to the
deterministic current-turn controller and execution path.

The execution core has a narrower responsibility: read authoritative live
state, accept an explicit allowlisted action, check its immediate preconditions,
execute it, re-read state, and record whether its postcondition was proven.
Strategic and tactical layers will later need richer rules for comparing
alternatives and explaining consequences, but those rules are coupled to
vertical skills such as research, military, exploration, and city development.

## Decision

M4 is narrowed to a structural ruleset knowledge view owned by the knowledge
module. It may:

- validate an explicit, complete ruleset and match context;
- return canonical detached entities and source provenance;
- resolve structural identity such as default, civilization replacement, and
  explicitly disabled unit or building class members;
- reject missing, unknown, duplicate, ambiguous, or incompatible inputs.

It must not:

- score or rank alternatives;
- predict turns, yields, combat outcomes, or strategic value;
- compose broad effective scalar values without a concrete core consumer;
- infer missing match context;
- select or execute an action.

The existing Python name `RulesetResolver` remains provisional until M7 to
avoid a gratuitous internal rename. Its architectural role is a
`RulesetKnowledgeView`, not an execution-layer planner.

Future effective-rule composition, counterfactual analysis, and route
evaluation belong with the future strategic, tactical, and vertical-skill
layer. They may use deterministic rule functions, but they are not part of this
repository's execution core. Live values reported directly by Civ V remain
authoritative for current-state execution.

## Consequences

- M4 completes with the existing explicit context and structural class-view
  behavior; effective scalar composition is removed from its acceptance scope.
- M5 factual turn-journal implementation becomes the next core milestone.
- The deterministic controller may query stable structural knowledge only when
  needed for an explicit conservative policy. It does not perform strategic or
  tactical rule analysis.
- Future decision-support skills must define consumer-driven queries and retain
  provenance rather than depending on a speculative universal resolver.
- M7 will decide whether the public API renames `RulesetResolver` to make the
  narrowed knowledge-view role explicit.

## Alternatives considered

- Continue building a universal effective-value resolver in the core: rejected
  because no current execution consumer requires it and its natural consumers
  belong to later strategic, tactical, and vertical layers.
- Remove all existing resolution code: rejected because exact context
  validation, immutability, provenance, and civilization class replacement are
  useful deterministic knowledge queries.
- Put scalar analysis directly in the executor: rejected because execution
  should consume explicit actions and authoritative live preconditions, not
  compare hypothetical outcomes.

## Supersedes

This ADR supersedes ADR-0013 only where that decision anticipated later
effective-value APIs inside M4. ADR-0013's explicit-context, canonicalization,
immutability, provenance, and fail-closed requirements remain accepted for the
structural knowledge view.
