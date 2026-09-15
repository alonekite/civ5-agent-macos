# Module: journal

Status: Planned (M5)

## Responsibility

The journal will preserve the complete factual history of exactly one game:
validated snapshots, observed turn transitions, submitted command envelopes,
command results, before/after states, verification errors, and optional factual
plan/execution events. Its intended uses include future tactical/strategic
history selection, replay, comparison, debugging, and audit.

## Non-responsibilities

- Selecting important history or generating summaries.
- Inferring opponent intent.
- Maintaining near-term or strategic plans.
- Choosing or executing actions.
- Working memory, strategic memory, or LLM interaction.

## Public interface

Not implemented. The future interface will append versioned records and read or
export a verified sequence. See the proposed [journal contract](../contracts/journal.md).

## Inputs and outputs

Inputs are already validated bridge observations, action lifecycle results, and
optional bounded execution events delivered by application orchestration.
Records must carry game identity, turn, capture time, schema/ruleset identity,
monotonic sequence, canonical payload, and integrity evidence.

## Dependencies

The journal may depend on shared validated models and canonical serialization.
Application orchestration appends records. It must not depend on plan production
or executor policy, and the executor must not import, query, or require the
journal. M6 events may be recorded through an optional orchestration adapter.

## Invariants

- Append only; corrections supersede rather than rewrite.
- One journal never mixes multiple games.
- Record ordering and integrity are checkable offline.
- Private data is never committed by default.
- Replaying records does not execute game actions.
- Journal contents never control an execution cursor or action retry.

## Failure modes

Truncation, tampering, unsupported schema, oversized record, sequence break,
cross-game mixing, and storage failure must be explicit.

## Security and privacy

Full snapshots may contain player names and match-specific information. Local
storage must use private permissions, bounded records, and an explicit retention
and export policy. No automatic Git inclusion is permitted.

## Verification

M5 will require codec, corruption, concurrency, permission, recovery, and replay
tests before integration with watcher output.

## Current limitations

No journal implementation is committed. An accidentally early prototype was
removed from the working tree and preserved privately outside the repository;
it is not an accepted design or release artifact.

## Planned extensions

Implement M5 for historical capture and later tactical/strategic selection,
replay, and comparison, then expose selective read/export capabilities during
M7. M5 and M6 may be implemented in either order; the current M5 priority is a
schedule choice, not a dependency.
