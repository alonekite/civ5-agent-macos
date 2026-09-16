# Turn-Journal Contract

Status: M5 contract implemented offline; bounded live verification pending

## Purpose

Preserve an append-only, replayable sequence of every supported fact actually
captured and validated while recording one declared match. The journal supports
future tactical/strategic history selection, replay, comparison, debugging, and
audit without claiming hidden facts, disconnected intervals, or unsupported
fields, and without summarization, inference, planning, or game-action execution.

## Proposed record families

- validated snapshot;
- observed turn transition;
- command submitted;
- command result;
- verification error;
- correction that explicitly supersedes an earlier record;
- bridge-session binding.

M5 must define a versioned record-kind extension boundary. Application
orchestration may later append factual plan receipt, execution transition,
pause, divergence, recovery, and completion events emitted by M6. M5 does not
interpret plan content or supply M6 execution state.

## Required common fields

- journal schema version;
- monotonically increasing record sequence;
- canonical UTC capture timestamp;
- stable journal `match_id`;
- bound `bridge_session_id` for live observations and command lifecycles;
- turn number;
- record kind;
- live-state/ruleset schema identity where relevant;
- canonical JSON payload;
- previous-record and/or record integrity evidence.

## Required behavior

- Append only. Corrections do not rewrite old records.
- One file/store cannot silently mix match identities or unbound bridge
  sessions.
- A record from an unbound bridge session is rejected. Later sessions require an
  explicit append-only binding; they are never inferred from snapshot similarity.
- Reject truncation, duplicate keys, non-finite values, unknown record kinds,
  sequence gaps, backward turn movement, broken integrity, and oversized
  records.
- Use private local permissions and refuse unsafe symbolic-link targets.
- Reading or replaying a journal never executes a command.
- Replay preserves validated append order, including correction records; it does
  not infer a reconstructed game state or execution cursor.
- Verification returns only payload-free structural metadata and the chain head.
- Journal state never authorizes M6 to resume, skip, retry, or replace an
  action; live state and bridge postconditions remain authoritative.
- A journal write failure is separate from the result of an already verified
  game action and cannot make that action retryable.
- Command UUIDs may correlate a journal record with the independent M2 security
  audit, but M5 consumes the validated in-memory result and never parses the
  audit file as its input or source of truth.
- A submitted command whose terminal outcome cannot be validated records a
  `verification_error` with stage `execution_outcome_unknown`; it does not
  invent a `command_result` or after-state.
- Export is explicit and warns that even redacted chronology may be sensitive.

## Implemented storage decisions

- Private mode-0600 JSONL, one file per declared match.
- Contiguous sequence plus SHA-256 previous-record chain.
- Exclusive-lock append, full-chain validation, and `fsync` before success.
- Newline and size bounds that reject partial/truncated records without
  automatic repair.
- Explicit initial and later bridge-session bindings.
- Deterministic verification, append-order replay, and canonical structural
  export under ADR-0021.

## Retention policy

- The private source journal is authoritative and is never deleted, compacted,
  rotated, uploaded, or committed automatically.
- Operators choose retention according to their own privacy and replay needs.
  Verify a source before archiving or intentionally deleting it.
- Preserve source bytes if verifiable history is required. A redacted export is
  a diagnostic/share artifact, not a backup and not proof of the original chain.
- Full-payload replay is local and explicit. Structural export remains
  mode-`0600` and is described as redacted, never anonymous.

## Decisions intentionally deferred

- Automatic retention/deletion, compaction, and large-snapshot deduplication.
- Public selective-query API.

These remaining choices require later benchmarks and compatibility design.
Identity semantics are implemented in the codec/store under ADR-0017. Opt-in
watcher composition records changed snapshots and grounded command results from
memory. It records pre-execution submissions, unsuccessful results, and observed
turn transitions without making persistence an execution precondition. This
adapter accepts only validated FireTuner live state; the partial, unversioned
database fallback is rejected as journal input. Deterministic full-chain
verification and append-order factual replay are implemented; replay requires
explicit private-payload acknowledgement. Canonical structural export excludes
payloads, timestamps, identities, hashes, and paths. Bounded live verification
remains pending.

## Out of scope

Working memory, strategic memory, prompt context, relevance scoring, opponent
inference, plan revision, execution cursors, and execution recovery checkpoints
belong outside M5.
