# Turn-Journal Contract

Status: Proposed for M5; no implementation is committed

## Purpose

Preserve a complete factual and replayable history of one match for future
tactical/strategic history selection, replay, comparison, debugging, and audit,
without summarization, inference, planning, or game-action execution.

## Proposed record families

- validated snapshot;
- observed turn transition;
- command submitted;
- command result;
- verification error;
- correction that explicitly supersedes an earlier record.

M5 must define a versioned record-kind extension boundary. Application
orchestration may later append factual plan receipt, execution transition,
pause, divergence, recovery, and completion events emitted by M6. M5 does not
interpret plan content or supply M6 execution state.

## Required common fields

- journal schema version;
- monotonically increasing record sequence;
- canonical UTC capture timestamp;
- stable game identity;
- turn number;
- record kind;
- live-state/ruleset schema identity where relevant;
- canonical JSON payload;
- previous-record and/or record integrity evidence.

## Required behavior

- Append only. Corrections do not rewrite old records.
- One file/store cannot silently mix game identities.
- Reject truncation, duplicate keys, non-finite values, unknown record kinds,
  sequence gaps, broken integrity, and oversized records.
- Use private local permissions and refuse unsafe symbolic-link targets.
- Reading or replaying a journal never executes a command.
- Journal state never authorizes M6 to resume, skip, retry, or replace an
  action; live state and bridge postconditions remain authoritative.
- A journal write failure is separate from the result of an already verified
  game action and cannot make that action retryable.
- Export is explicit and warns that records may contain private match data.

## Decisions intentionally deferred

- JSONL versus SQLite or a hybrid storage/index format.
- Integrity chain and checkpoint details.
- Flush/durability policy and crash recovery.
- Retention, compaction, and large-snapshot deduplication.
- Public selective-query API.

These choices must be resolved in M5 with benchmarks and corruption/concurrency
tests. An earlier uncommitted JSONL prototype is not an accepted contract.

## Out of scope

Working memory, strategic memory, prompt context, relevance scoring, opponent
inference, plan revision, execution cursors, and execution recovery checkpoints
belong outside M5.
