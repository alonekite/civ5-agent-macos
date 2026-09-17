# Module: deterministic turn executor

Status: M6 complete; bounded target-machine verification passed

## Responsibility

M6 validates an explicit `TurnPlan`, coordinates its ordered allowlisted actions
through the bridge, re-reads every result, and pauses safely when live state
diverges. The legacy `controller.py` remains only the earlier readiness proof;
the supported M6 surface is exported through `civ5_agent.api`.

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
defined by the M7 aggregate API rather than the legacy controller module.
`civ5_agent.turn_executor` executes only plan-listed actions through injected
read/action capabilities, verifies result state continuity, and returns bounded
terminal reports without importing knowledge or journal modules.
`civ5_agent.turn_executor_adapter.WatcherTurnExecutor` supplies those two
capabilities by extending the bridge-owned `WatcherBridgeClient`. It does not
open a second FireTuner connection or duplicate bridge validation. It also uses
the client's read-only completed-command lookup for recovery reconciliation; a
cache miss never resubmits an action.

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

Independent tactical consumers may produce explicit plan content and construct
the public `TurnPlan` through their own adapter. Their `TacticalPlan`,
`ActionIntent`, arbitration, and result-adapter types never become executor
dependencies. Missing actions are core capability requests, not permission for
a consumer-side lower-level command path.

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

Unit tests cover readiness order, refusal paths, plan schema, drift, pause,
no-journal operation, optional event-sink failure, conservative recovery, and
ordered multi-action execution. Target-machine evidence covers validation,
stale refusal, changed-state failure, and one newly authored plan that completed
with verified automatic turn advancement.

## Current limitations

Automatic continuation after recovered non-final actions is deliberately not
implemented. The current `decide()` function
mixes factual requirement reporting with the legacy end-turn recommendation and
must not grow into a tactical or strategic planner.

## Movement extension

Development head accepts the bridge-owned `move_unit` action in schema 1 plans
without adding route selection. It covers only the matching unit-order
requirement; if the
unit remains ready and no later explicit move or skip covers it, execution
pauses. Keep the bounded live procedure as a regression gate when execution
semantics change. Tactical and strategic layers remain plan producers, not
executor internals.

## Frozen worker-build extension

M10 D2 keeps TurnPlan schema 1 and defines a future exact `worker_build`
action carrying unit ID, source coordinates, and stable build identifier. It
covers only that unit's factual order requirement and remains subject to fresh
schema 7 bridge admission. The executor neither queries knowledge nor chooses a
build or alternate plot. If verified work leaves the unit ready without a
remaining explicit action, execution pauses. Core 1.1 still rejects this action;
implementation and evidence are pending.
