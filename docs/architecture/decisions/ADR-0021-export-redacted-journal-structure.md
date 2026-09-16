# ADR-0021: Export only redacted journal structure by default

Status: Accepted

Date: 2026-09-16

## Context

The private M5 journal can contain player names, city and unit state, command
arguments, timestamps, local match/session identifiers, and content hashes.
Copying the source file or replay output is therefore not a safe default for
sharing, issue reports, or offline structural analysis.

## Decision

The supported file export is a versioned structural document containing only:

- export schema version;
- record count, first/last observed turn, and record-kind counts;
- each record's sequence number, turn, and kind in verified append order.

It excludes payloads, capture timestamps, match and bridge-session identifiers,
previous/record hashes, and source paths. Export validates the complete source
journal first, creates a new mode-`0600` regular file, refuses existing or
symbolic-link destinations, writes canonical JSON, and calls `fsync` before
success. It never modifies the source.

Private full-fidelity inspection remains available only through replay with an
explicit private-payload acknowledgement. The project does not label a
structural export anonymous: turn and event chronology may still reveal play
patterns.

## Consequences

- Routine exports are useful for structural diagnostics without copying direct
  match content or correlatable identities/hashes.
- Structural exports cannot reconstruct game state or verify the original hash
  chain independently; recipients need the private source for those purposes.
- Export destinations are local and explicit. Automatic upload, Git inclusion,
  or retention deletion is not introduced.

## Alternatives considered

- Copy the original JSONL: rejected as an unsafe sharing default.
- Field-by-field payload redaction: deferred because evolving nested live-state
  schemas make omissions easy and privacy claims brittle.
- Hash or pseudonymize identifiers: rejected because stable pseudonyms and
  content hashes remain correlatable.

## Supersedes

This resolves the initial M5 file-export format and privacy default deferred by
ADR-0020. Retention, compaction, automatic deletion, and public selective-query
compatibility remain deferred.
