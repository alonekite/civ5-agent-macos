# Module: controller

Status: Implemented, expansion in progress

## Responsibility

The controller validates a live snapshot, evaluates conservative deterministic
policy, and emits a structured candidate action from the bridge allowlist.

## Non-responsibilities

- Transport or Lua generation.
- Treating an issued command as success.
- Mutating ruleset knowledge.
- Reading the entire future turn journal as decision context.
- LLM decisions, working memory, or strategic memory.

## Public interface

The current module provides state validation, deterministic decision output, and
an opt-in CLI execution path. Its stable public Python interface is deferred to
M7.

## Inputs and outputs

Inputs are validated live `GameState` plus narrowly required structural
knowledge queries. Output is a decision such as wait, choose research, choose
production, issue a unit order, or end turn.

## Dependencies

Controller may depend inward on bridge contracts and structural knowledge-view
APIs. Bridge and knowledge must not depend on controller policy.

## Invariants

- Deterministic inputs produce deterministic decisions.
- Missing or invalid evidence yields wait/refusal, not a guessed action.
- Execution remains opt-in and uses the same verified bridge command path.
- The controller cannot expand the bridge allowlist.

## Failure modes

Invalid snapshot, mandatory unresolved choice, wrong turn ownership, unsupported
knowledge context, or unavailable broker produces a structured refusal/error.

## Security and privacy

No prompt, model, remote decision service, or arbitrary code is used. Controller
output is not proof of successful execution.

## Verification

Unit tests cover policy order, refusal paths, candidate commands, and opt-in
execution. Basic refusal and end-turn execution were live-verified.

## Current limitations

The controller does not yet consume broader structural knowledge queries. It is
a conservative current-turn proof rather than a tactical or strategic planner.

## Planned extensions

Add structural knowledge queries only when a concrete conservative policy needs
them, then stabilize the boundary during M7. Candidate comparison and
counterfactual rule analysis belong to future tactical/strategic skills.
