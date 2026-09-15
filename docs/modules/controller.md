# Module: deterministic turn executor

Status: M6 replanned; legacy `controller` proof implemented

## Responsibility

The target M6 module validates an explicit `TurnPlan`, coordinates its ordered
allowlisted actions through the bridge, re-reads every result, and pauses safely
when live state diverges. The current Python package remains named `controller`
until M7 and supplies only the earlier readiness proof.

## Non-responsibilities

- Transport or Lua generation.
- Treating an issued command as success.
- Mutating ruleset knowledge.
- Reading the entire future turn journal as decision context.
- Selecting research, production, unit destinations, targets, tactics, or
  strategy.
- Scoring candidates, revising plans, or replacing failed actions.
- LLM decisions, working memory, or strategic memory.

## Public interface

The current module provides state validation, mandatory-requirement reporting,
and an opt-in legacy end-turn path. M6 will add the proposed `TurnPlan` and
execution-report boundary after M5. Stable public Python naming is deferred to
M7.

## Inputs and outputs

The target input is a validated live `GameState` plus a versioned explicit
`TurnPlan`. Outputs are factual requirements and a machine-readable execution
report such as completed, paused, stale, failed, or recovery-required. A
requirement is not an action choice.

## Dependencies

The executor depends inward on bridge action/state contracts and M5 journal
interfaces. It may use a narrow structural knowledge query only to validate an
explicit stable identifier. Bridge, knowledge, and journal must not depend on
execution policy.

## Invariants

- Deterministic inputs and live observations produce deterministic execution
  transitions.
- Missing or invalid evidence pauses/refuses; it never creates plan content.
- Every action is explicit, opt-in, and uses the verified bridge command path.
- The executor cannot expand the bridge allowlist.
- `end_turn` executes only when listed as the final action and still legal.

## Failure modes

Invalid plan/snapshot, mandatory unresolved choice, wrong game/turn/player,
state drift, unsupported action, unavailable broker, failed verification, or
ambiguous recovery produces a structured pause/refusal/error.

## Security and privacy

No prompt, model, remote decision service, or arbitrary code is used. Only a
bridge postcondition is proof of successful execution. Plans and reports are
private per-game data.

## Verification

Existing unit tests cover readiness order, refusal paths, and opt-in execution;
basic refusal and end-turn execution were live-verified. M6 requires plan-schema,
drift, pause, journal, recovery, and ordered multi-action tests.

## Current limitations

The explicit plan executor is not implemented. The current `decide()` function
mixes factual requirement reporting with the legacy end-turn recommendation and
must not grow into a tactical or strategic planner.

## Planned extensions

After M5, finalize the TurnPlan schema against journal identities, implement
requirement inspection and ordered execution, test interruption recovery, and
stabilize naming during M7. Tactical and strategic layers remain plan producers,
not executor internals.
