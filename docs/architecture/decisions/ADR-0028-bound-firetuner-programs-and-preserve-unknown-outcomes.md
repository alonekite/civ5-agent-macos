# ADR-0028: Bound FireTuner programs and preserve unknown write outcomes

Status: Accepted

Date: 2026-09-16

## Context

The target Campaign Edition FireTuner truncates Lua commands near one KiB. A
2,069-byte `end_turn` program passed offline string inspection but arrived in
the live runtime as invalid truncated Lua. The watcher recorded submission but
lost the raised protocol failure before the journal could close the factual
lifecycle. Treating every such post-submission failure as a deterministic
rejection would also permit unsafe retry semantics.

## Decision

- Reject every FireTuner Lua program larger than 1,000 UTF-8 bytes before it is
  sent.
- Keep each internally generated read or action program independently below
  that bound and test the bound.
- Implement `end_turn` with the same conservative facts in a compact form: the
  active turn must be live, the game-reported blocker must be zero, message
  processing and an already-sent multiplayer turn must both be false, and
  `UI.CanEndTurn()` must be true. The sole write remains
  `Game.DoControl(CONTROL_ENDTURN)`.
- If watcher execution raises after command submission and no validated
  terminal result exists, return an explicit unknown-outcome response, map it
  to `TransportError`, record a factual journal `verification_error`, and cache
  that uncertainty by command UUID so an identical request cannot execute
  again. Read-only command-status lookup still returns no terminal result.

## Consequences

- Oversized programs fail locally before contacting the game.
- M6 enters `recovery_required` for post-submission uncertainty rather than
  reporting deterministic action rejection or retrying.
- M5 preserves the incomplete lifecycle without inventing an after-state or a
  command result.
- The numeric zero-blocker check is deliberately conservative for the supported
  target build. Other builds require their own bounded live evidence.

## Alternatives considered

- Keep the exhaustive blocker-name expression: rejected because it exceeds the
  verified transport envelope.
- Rely only on `UI.CanEndTurn()`: rejected because retaining the zero blocker is
  a stricter, fail-closed precondition.
- Split one write action across several Lua commands: rejected because partial
  setup would create state and recovery ambiguity.
- Convert missing markers into terminal rejection: rejected because a failure
  after submission does not generally prove that no game-side effect occurred.

## Supersedes

None. This refines ADR-0003, ADR-0010, and ADR-0023.
