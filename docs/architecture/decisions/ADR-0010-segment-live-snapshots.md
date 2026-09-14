# ADR-0010: Segment live snapshots below the FireTuner command limit

Status: Accepted

Date: 2026-09-14

## Context

The target Campaign Edition accepts a short FireTuner Lua command, but a
monolithic schema 3 snapshot program was truncated at roughly 1 KiB and failed
with a Lua syntax error. The bridge must still read one logical state without
silently combining records from different turns or players.

## Decision

Emit a schema 4 snapshot as five ordered, read-only Lua programs: header,
cities, units, diplomacy, and victory. Keep every encoded program below 900
bytes, leaving margin below the observed target limit.

Schema 4 adds unit readiness to the previously published schema 3 shape. Every
non-header program emits a part marker containing its part name, game turn, and
active-player ID. The parser requires exactly one of every part and rejects a
snapshot if any marker is absent, duplicated, malformed, or disagrees with the
header identity. Schema 2 and schema 3 parsing remain available for legacy
monolithic responses.

## Consequences

- Schema 4 works on the target FireTuner implementation without broadening the
  Lua read allowlist.
- A logical read uses five serialized round trips and is therefore slower than
  the old monolithic read.
- Turn or active-player changes during collection cause an explicit read
  failure instead of a mixed snapshot.
- New snapshot sections must preserve the command-size margin and participate
  in completeness and identity checks.

## Alternatives considered

- Shorten the monolithic command further: rejected because it leaves little
  room for additional state and does not establish a durable bound.
- Accept independently parsed partial state: rejected because commands and the
  controller require one coherent observation.
- Increase the FireTuner limit: unavailable in the stock target build.

## Supersedes

No previous ADR. This refines ADR-0001's stock FireTuner transport decision.
