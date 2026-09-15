# ADR-0020: Use a private hash-chained JSONL journal

Status: Accepted

Date: 2026-09-16

## Context

M5 needs a small, inspectable, append-only store that can detect truncation,
tampering, sequence gaps, and cross-match/session mixing. Match events occur at
human game speed, so predictable durability and recovery behavior matter more
than high write throughput. Selective indexing remains a later M7 concern.

## Decision

Use one private JSON Lines file per declared match with journal schema 1:

- sequence 0 is `journal_started` and binds the initial bridge session;
- each canonical JSON record carries `match_id`, optional bound
  `bridge_session_id`, capture time, turn, kind, payload, previous hash, and its
  SHA-256 record hash;
- sequence numbers are contiguous and every record after sequence 0 hashes the
  preceding record;
- records are capped at 4 MiB, end with a newline, reject duplicate keys,
  non-finite values, unknown fields/kinds, unsafe links, and invalid identities;
- appends take an exclusive file lock, revalidate the existing chain, append one
  complete encoded record, and call `fsync` before success;
- reads take a shared lock and reject truncation or any semantic/integrity
  violation;
- observed turn numbers cannot move backwards within one journal; loading an
  earlier branch requires a new declared match journal;
- files use mode `0600`; creation refuses to replace an existing path;
- cross-session continuation is an explicit `session_binding` record under
  ADR-0017.

M5 does not repair automatically. A damaged store is evidence and remains
read-only until an explicit future recovery/export procedure is designed.

## Consequences

- The initial implementation is simple, deterministic, and stream-readable.
- Append cost is linear because the chain is revalidated under lock. This is
  acceptable for the initial expected scale and provides safe multi-process
  behavior; benchmarks will determine whether M7 adds a verified index or
  checkpoint without changing record meaning.
- Large snapshots are duplicated. Retention, compaction, and deduplication stay
  deferred and must preserve the original verifiable history when added.
- Hash chaining detects accidental or deliberate modification but is not a
  digital signature; anyone who can rewrite the whole private file can compute
  a new chain.

## Alternatives considered

- SQLite: deferred because transaction and index benefits do not yet outweigh
  schema/recovery complexity for sequential writes.
- Plain JSONL without a chain: rejected because deletion, reordering, and
  cross-record corruption would be harder to detect.
- Reuse the M2 audit JSONL: rejected by ADR-0019 because it has different scope,
  retention, and failure semantics.
- Automatic truncation repair: rejected because silent repair would destroy
  evidence and could hide a partial write.

## Supersedes

This ADR resolves the initial storage, integrity-chain, flush, and crash
detection choices intentionally deferred by the proposed journal contract.
Selective queries, retention, compaction, and recovery/export tooling remain
deferred.
