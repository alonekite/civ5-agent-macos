# ADR-0043: Drain multi-frame output after an early FireTuner acknowledgement

Status: Accepted

Date: 2026-09-21

## Context

ADR-0042 established that Campaign Edition can acknowledge a FireTuner command
before delivering its Lua output. Its first implementation waited for one
output frame after an early acknowledgement. A repaired M11 C4 target run then
preserved one connection across the first interturn but rotated the bridge
session during the following interturn. The replacement connection produced a
valid snapshot, proving recovery, but failed C4's same-session continuity gate.

The collector still assumed that the first output frame after an early
acknowledgement completed the response. A snapshot program can emit multiple
FireTuner output frames, so that assumption can leave later frames queued for
the next segmented command.

## Decision

Preserve the ordinary output-then-acknowledgement behavior: the acknowledgement
ends collection after output has already been observed.

When the acknowledgement arrives before any output, collect every subsequent
non-lifecycle output frame until the existing bounded idle or total deadline.
Do not treat the first late output frame as the response terminator.

Residual marked-part-before-header corruption retains ADR-0042's fail-closed
behavior: close the connection, rotate `bridge_session_id`, and never retry a
submitted write.

## Consequences

- Multi-frame acknowledgement-first responses are drained before the next
  segmented snapshot command.
- Ordinary output-before-acknowledgement latency and termination are unchanged.
- An acknowledgement-first response uses the existing short idle window to
  prove that no more response frames are immediately available.
- C4 must be rerun on the exact repaired commit; the diagnostic run that
  rotated its session remains partial evidence.

## Alternatives considered

- Stop after the first output frame: rejected because the target run showed
  that recovery can still be required during a multi-program snapshot.
- Sleep for a fixed interturn duration: rejected because it weakens attribution
  without defining a response boundary.
- Preserve the session identity after reconnect: rejected by the session
  identity contract.

## Supersedes

This decision refines ADR-0042's acknowledgement-first collection rule. It does
not supersede ADR-0042's desynchronization recovery or write-uncertainty rules.
