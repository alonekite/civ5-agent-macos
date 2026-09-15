# Turn-Plan and Execution Contract

Status: Proposed for M6; independent of M5 storage

## Purpose

Carry an explicit current-turn plan across the boundary between a human or
future tactical layer and the deterministic execution core. A plan states what
to execute; it does not embed strategy, scoring, model prompts, or executable
code.

## Proposed plan envelope

A versioned `TurnPlan` will contain:

- canonical plan identity;
- expected bridge-session identity, turn number, and active player;
- the validated live-state digest or equivalent state-basis identity on which it
  was based;
- an ordered, bounded list of existing allowlisted command envelopes;
- explicit preconditions needed to reject stale or misdirected execution.

Exact field names, digest construction, record limits, and recovery tokens will
be finalized within M6 against live-state and command contracts. A plan may
carry an opaque history reference for its producer, but the executor neither
requires nor trusts it as a precondition or recovery source.

## Execution behavior

- Validate the complete plan before the first write.
- Re-read live state before every action and reject a stale bridge session,
  turn, player, or declared precondition.
- Submit only the next explicit action through the existing bridge command
  contract.
- Advance the execution cursor only after the bridge proves the action-specific
  postcondition.
- Emit bounded factual plan/action lifecycle events that optional application
  orchestration may record.
- Pause rather than replan when state diverges, a new mandatory requirement
  appears, or a decision is missing.
- Require `end_turn` as the explicitly listed final action of a complete-turn
  plan and execute it only while the live game still permits it.
- Never infer that an interrupted action succeeded; recovery must reconcile its
  command identity, M6-owned execution state, and freshly read game state.
- Operate correctly when no journal is configured or available.

## Execution state

M6 owns its execution cursor, verified action identities, bridge-session
identity, last live-state basis, and current execution status. The first
implementation may keep this state only for the executor lifetime. Any later
cross-process checkpoint is a separate private M6 contract, not an M5 journal
record.

The journal may contain historical copies of plans and execution events, but
those copies never authorize resumption, skipping, or retrying an action.

## Turn requirements

A requirement inspector may report factual blockers such as:

- ordinary, free, or unsupported research choice required;
- city production required for a specific observed city;
- orders required for a specific observed unit;
- another game-reported end-turn blocker.

Requirements may include observed stable identifiers and legal candidates
already returned by the bridge. They do not select a candidate or create an
action. Resolving a requirement belongs to the plan producer.

## Result states

Execution reports distinguish at least:

- `completed`: every action, including the required explicit final `end_turn`,
  was verified;
- `paused`: execution stopped safely for a missing decision or new requirement;
- `stale`: the plan no longer matches the target state;
- `failed`: an action or verification failed without a safe automatic
  substitute;
- `recovery_required`: prior execution cannot be classified without explicit
  reconciliation.

The final schema must make these states mutually exclusive and machine-readable.
The first M6 contract models complete-turn plans only. A future partial-plan
contract would need a distinct plan kind and terminal result; it cannot reuse
`completed` to mean that a turn was ended.

## Security and privacy

- Plans cannot contain Lua, host/port values, predicates, callbacks, loops, or
  arbitrary code.
- Every action remains subject to the bridge allowlist, live safety preflight,
  argument validation, idempotency, and write-after-read proof.
- Plans and execution reports are private bridge-session/match data and remain
  local unless the user explicitly exports them.
- Journal availability or write success cannot determine whether an action is
  safe or whether a verified action should be retried.

## Non-responsibilities

- Victory strategy or long-term route selection.
- Short-term tactical choice or plan revision.
- Candidate scoring, combat prediction, or effective-value comparison.
- Working memory, strategic memory, prompt construction, or LLM operation.
- Expanding the bridge action allowlist.
