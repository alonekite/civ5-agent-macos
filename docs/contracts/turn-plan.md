# Turn-Plan and Execution Contract

Status: Proposed for M6; implementation follows M5 journal foundations

## Purpose

Carry an explicit current-turn plan across the boundary between a human or
future tactical layer and the deterministic execution core. A plan states what
to execute; it does not embed strategy, scoring, model prompts, or executable
code.

## Proposed plan envelope

A versioned `TurnPlan` will contain:

- canonical plan identity;
- expected game identity, turn number, and active player;
- the journal sequence and/or validated state digest on which it was based;
- an ordered, bounded list of existing allowlisted command envelopes;
- explicit preconditions needed to reject stale or misdirected execution.

Exact field names, digest construction, record limits, and recovery tokens will
be finalized after M5 establishes journal identity and canonical integrity
semantics.

## Execution behavior

- Validate the complete plan before the first write.
- Re-read live state before every action and reject a stale turn, player, game,
  or declared precondition.
- Submit only the next explicit action through the existing bridge command
  contract.
- Advance the execution cursor only after the bridge proves the action-specific
  postcondition.
- Append plan and action lifecycle facts to the journal without rewriting prior
  records.
- Pause rather than replan when state diverges, a new mandatory requirement
  appears, or a decision is missing.
- Treat `end_turn` as valid only when explicitly listed last and still permitted
  by the live game.
- Never infer that an interrupted action succeeded; recovery must reconcile its
  command identity, journal evidence, and current state.

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

- `completed`: every action, including an optional explicit final end turn, was
  verified;
- `paused`: execution stopped safely for a missing decision or new requirement;
- `stale`: the plan no longer matches the target state;
- `failed`: an action or verification failed without a safe automatic
  substitute;
- `recovery_required`: prior execution cannot be classified without explicit
  reconciliation.

The final schema must make these states mutually exclusive and machine-readable.

## Security and privacy

- Plans cannot contain Lua, host/port values, predicates, callbacks, loops, or
  arbitrary code.
- Every action remains subject to the bridge allowlist, live safety preflight,
  argument validation, idempotency, and write-after-read proof.
- Plans and execution reports are per-game data and remain private unless the
  user explicitly exports them.

## Non-responsibilities

- Victory strategy or long-term route selection.
- Short-term tactical choice or plan revision.
- Candidate scoring, combat prediction, or effective-value comparison.
- Working memory, strategic memory, prompt construction, or LLM operation.
- Expanding the bridge action allowlist.
