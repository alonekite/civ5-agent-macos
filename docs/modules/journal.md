# Module: journal

Status: M5 implemented offline; bounded live verification pending

## Responsibility

The journal will preserve every supported fact actually captured and validated
while recording one declared match: validated snapshots, observed turn
transitions, submitted command envelopes, command results, before/after states,
verification errors, and optional factual plan/execution events. It does not
claim hidden state, disconnected intervals, or unsupported fields. Its intended
uses include future tactical/strategic history selection, replay, comparison,
debugging, and audit.

## Non-responsibilities

- Selecting important history or generating summaries.
- Inferring opponent intent.
- Maintaining near-term or strategic plans.
- Choosing or executing actions.
- Working memory, strategic memory, or LLM interaction.

## Public interface

`JournalStore.create`, `open`, `read_all`, `append`, and `bind_session` implement
the private schema 1 core. `JournalCapture` optionally records watcher snapshots
and grounded in-memory command results when the user supplies both `--journal`
and `--journal-mode new|resume` with the FireTuner transport. The partial,
unversioned database fallback is not a journal source. Public M7 compatibility
is not yet implemented. See the [journal contract](../contracts/journal.md).
`verify_journal` and `civ5-journal verify` read and validate the complete chain,
then expose only structural counts, turn bounds, identities, and the head hash.
`replay_journal` returns detached events in validated append order; it preserves
corrections as events and never derives executable state from them.
`export_redacted_journal` exclusively writes canonical mode-0600 structural
exports under ADR-0021 without payloads, timestamps, identities, hashes, or
source paths.

## Inputs and outputs

Inputs are already validated bridge observations, action lifecycle results, and
optional bounded execution events delivered by application orchestration.
Records must carry the journal `match_id`, a bound `bridge_session_id` where
applicable, turn, capture time, schema/ruleset identity, monotonic sequence,
canonical payload, and integrity evidence.

## Dependencies

The journal may depend on shared validated models and canonical serialization.
Application orchestration appends records. It must not depend on plan production
or executor policy, and the executor must not import, query, or require the
journal. M6 events may be recorded through an optional orchestration adapter.
Here orchestration is watcher/CLI composition code, not a decision module.

## Invariants

- Append only; corrections supersede rather than rewrite.
- One journal never mixes multiple declared matches.
- Cross-session continuation is explicit and append-only; M5 never infers it
  from mutable snapshot fields.
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

Offline tests cover codec round trips, canonical UUID identities, private
permissions, append/reopen, hash chaining, tampering, truncation, size bounds,
concurrent appends, symlink refusal, correction targets, and unbound/duplicate
session rejection. Adapter tests reject unvalidated snapshots and database-
transport capture. Runtime integration must still prove the target-machine
journal input comes from validated in-memory events rather than the independent
M2 command-audit file.

## Current limitations

Automatic deletion/compaction and selective queries are not implemented.
The hash chain detects modification but is not a digital signature and does not
defend against complete authorized rewriting of the private file.

## Planned extensions

Run bounded target-machine verification, then expose selective read APIs during
M7. Automatic retention remains intentionally absent; the source journal is
operator-controlled and a redacted export is not a backup. M5 and M6 remain
independent.
