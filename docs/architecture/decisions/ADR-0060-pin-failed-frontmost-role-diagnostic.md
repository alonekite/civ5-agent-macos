# ADR-0060: Pin a failed-frontmost AXRole diagnostic candidate

Status: Accepted for provisional SessionSpec v2 compatibility

Date: 2026-09-23

## Context

The ADR-0059 one-second candidate still failed before the second UI action
with `focus_context=system_cannot_complete` and
`focus_detail=candidate_cannot_complete`. Its existing events do not show
whether any other post-handoff candidate AX attribute was readable. This is
an observability gap, not evidence that `AXFrontmost` may be bypassed.

## Decision

Pin the next provisional SessionSpec v2 candidate to independent framework
commit `70b63426a45f18436aced8f53ae9b535c5092509` and wheel
`local_app_test_automation-0.2.0.dev0-py3-none-any.whl` with SHA-256
`0be1ebe491c80a1bb90e95a8a6fc1a17a096238c61960147c0ba677884f2c0f1`.

Only when the exact, identity-checked candidate's `AXFrontmost` returns
`cannot_complete`, the framework makes one read-only `AXRole` query on the
same AX application element under the existing one-second messaging bound.
It records only a double-allowlisted `focus_probe` category in the private
failure event, never the returned value or raw error. The query requires no
additional operator input, but it also conveys no additional authority:
the original UI identity failure remains terminal, with no click delivery,
retry, foreground substitute, watcher startup, or game-state access. Other
candidate failures do not add this read. The adopted framework v0.1.0 and
execution-core runtime remain unchanged.

## Evidence and limits

- Independent offline review matched the wheel digest and changed source
  bytes, checked ZIP integrity, installed the wheel in a clean Python 3.12
  environment, validated the execution-core SessionSpec v2 through the
  installed public CLI, and passed 52 targeted UI/supervisor tests (two
  host skips). The framework task reports 139 default tests and a passing
  four-cell macOS CI and wheel gate in run `35853948293`.
- There is no target-machine evidence for this exact candidate. The ADR-0059
  failure is still the last live result. A successful role read would prove
  only that one other app-level attribute responded, not foreground status.
  Failure of both sampled attributes would not prove the whole AX service is
  unavailable. Any later target run requires protected-host checks and fresh
  same-task authorization for each UI step; no previous nonce is reusable.

## Supersedes

This decision supersedes ADR-0059 only for the provisional candidate pin and
the closed-set failure diagnostic. Its identity, safety, privacy, and
fail-closed action requirements remain.
