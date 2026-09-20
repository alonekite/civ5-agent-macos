# ADR-0042: Recover from FireTuner response desynchronization

Status: Accepted

Date: 2026-09-21

## Context

FireTuner returns Lua output and a command acknowledgement as separate frames.
During an M11 controlled interturn, Campaign Edition delivered an
acknowledgement before the corresponding snapshot output. The client treated
the acknowledgement as an unconditional response terminator, leaving the
snapshot header queued for the next segmented command. Later parts then became
permanently shifted and the watcher repeatedly reported that a snapshot part
appeared before its header.

Continuing to use a connection whose response attribution is no longer known
would weaken both read integrity and write-result semantics. Silently retaining
the same bridge-session identity across a reconnect would also violate the
session identity contract.

## Decision

When a FireTuner command acknowledgement arrives before any non-lifecycle
output, the collector continues until it receives the corresponding output or
reaches its existing bounded idle/total timeout. The ordinary output-then-
acknowledgement order remains unchanged.

A marked snapshot part before the snapshot header raises the dedicated internal
`SnapshotStreamDesynchronizedError`. A long-running watcher lets that error
escape the active connection scope, closes the socket, and reconnects through
the normal guarded path. The replacement connection receives a new
`bridge_session_id`; callers must re-read state, and existing plans or command
requests remain bound to the old session and fail closed.

This recovery applies to observation framing only. It never retries a submitted
write, converts an unknown write outcome to success, or binds a replacement
session to an M5 match automatically. One-shot watcher mode continues to report
the read failure rather than hiding it behind a reconnect.

## Consequences

- The common acknowledgement-before-output ordering is drained before another
  segmented command is sent, preserving same-connection snapshot attribution.
- Residual framing corruption causes bounded loss of watcher availability and a
  visible bridge-session rotation instead of an infinite loop on bad framing.
- M6 plans become stale after recovery, and M5 requires the existing explicit
  operator-authorized session binding before recording a replacement session.
- The M11 C4 sequence must be rerun on the repaired implementation; the attempt
  that exposed the defect remains partial diagnostic evidence.

## Alternatives considered

- Keep retrying reads on the same socket: rejected because queued frames can no
  longer be attributed to the command that produced them.
- Reconnect while retaining the old session identity: rejected because the
  connection epoch changed.
- Open a second diagnostic FireTuner connection beside the watcher: rejected
  because the target reliably supports one connection owner.
- Retry writes after reconnect: rejected because submission may already have
  reached the game and its outcome may be unknown.
