# ADR-0022: Bind complete-turn plans to one live-state basis

Status: Accepted

Date: 2026-09-16

## Context

M6 must reject a plan aimed at a replaced FireTuner connection, another turn or
player, or state that changed after planning. It must also distinguish a valid
explicit plan from arbitrary data before the first game write without importing
knowledge, journal history, or planner logic.

## Decision

TurnPlan schema 1 is a complete-turn envelope containing:

- canonical UUIDv4 plan and target bridge-session identities;
- expected non-negative turn and active-player identifiers;
- SHA-256 over canonical JSON of the complete validated initial `GameState`;
- one to 64 ordered `PlannedAction` values, each with a unique canonical command
  UUID, an existing allowlisted action, and its exact bounded argument shape;
- one explicit `end_turn`, required as the final action.

The state basis is checked at initial plan admission. During execution, M6 will
re-read and validate authoritative live state before every action, while allowing
earlier verified actions in the same plan to change state. It will not compare
later states to the original digest or predict state through ruleset knowledge.

ExecutionReport schema 1 binds back to the plan and bridge session, carries a
bounded contiguous sequence of action-step results and state digests, and has
exactly one status: `completed`, `paused`, `stale`, `failed`, or
`recovery_required`. `completed` requires every action including final
`end_turn` to have succeeded. A failed report identifies one final failed step;
the other non-complete states contain only already successful steps.

## Consequences

- Plan admission is deterministic, bounded, and independent of M4/M5/LLMs.
- Any connection replacement or initial state change makes the plan stale.
- The initial full-state digest is conservative: even an irrelevant observed
  change requires the producer to issue a fresh plan.
- The digest is an equality token, not a privacy or authenticity mechanism.
  Plans and reports remain private local data.
- Later execution and recovery work must preserve these schema invariants.

## Alternatives considered

- Match only turn/player: rejected because other observed state could change.
- Require the initial digest before every action: rejected because verified plan
  actions intentionally mutate state.
- Arbitrary predicate expressions: rejected as executable policy and an unsafe
  expansion of the plan boundary.
- Use M5 match identity/history: rejected by ADR-0016 and ADR-0017.
- Query M4 to repair or validate action choices: rejected by ADR-0018.

## Supersedes

This finalizes the initial identity, state-basis, action-bound, and report fields
left open by the M6 contract and ADR-0015. It does not change the separation of
planning, execution, knowledge, and journal responsibilities.
