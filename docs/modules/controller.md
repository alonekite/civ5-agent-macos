# Module: deterministic turn executor

Status: M6 schema 1 admission implemented; execution pending; legacy proof retained

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

The current legacy module provides state validation, mandatory-requirement
reporting, and an opt-in end-turn path. `civ5_agent.turn_plan` now provides
schema 1 TurnPlan/action/report models, canonical state digests, construction,
and strict admission/report validation. `civ5_agent.turn_requirements` provides
ordered factual requirements without selecting actions. Stable public naming is
deferred to M7.

## Inputs and outputs

The target input is a validated live `GameState` plus a versioned explicit
`TurnPlan`. Outputs are factual requirements and a machine-readable execution
report such as completed, paused, stale, failed, or recovery-required. A
requirement is not an action choice.

## Dependencies

The executor depends inward only on bridge action/state/session and command
contracts. Stable identifier shape, live capability, and action legality remain
bridge responsibilities. M6 does not query ruleset knowledge or M5. Knowledge
and journal must not depend on execution policy.

## Invariants

- Deterministic inputs and live observations produce deterministic execution
  transitions.
- Missing or invalid evidence pauses/refuses; it never creates plan content.
- Every action is explicit, opt-in, and uses the verified bridge command path.
- The executor cannot expand the bridge allowlist.
- A complete-turn plan lists `end_turn` as its final action; `completed` is
  impossible until that action is verified.

## Failure modes

Invalid plan/snapshot, mandatory unresolved choice, wrong game/turn/player,
state drift, unsupported action, unavailable broker, failed verification, or
ambiguous recovery produces a structured pause/refusal/error.

## Security and privacy

No prompt, model, remote decision service, or arbitrary code is used. Only a
bridge postcondition is proof of successful execution. Plans and reports are
private bridge-session/match data. M6 may emit factual events for optional
recording, but a journal failure cannot make a verified game action retryable.

## Verification

Existing unit tests cover readiness order, refusal paths, and opt-in execution;
basic refusal and end-turn execution were live-verified. M6 requires plan-schema,
drift, pause, no-journal operation, optional event-sink failure, recovery, and
ordered multi-action tests.

## Current limitations

Ordered plan execution is not implemented. The current `decide()` function
mixes factual requirement reporting with the legacy end-turn recommendation and
must not grow into a tactical or strategic planner.

## Planned extensions

Implement ordered execution, test interruption recovery independently of M5,
and stabilize naming during M7. Tactical and
strategic layers remain plan producers, not executor internals.
