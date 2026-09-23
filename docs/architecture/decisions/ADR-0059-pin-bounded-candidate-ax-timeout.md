# ADR-0059: Pin bounded candidate AX frontmost timeout hypothesis

Status: Accepted for provisional SessionSpec v2 compatibility

Date: 2026-09-23

## Context

The ADR-0058 candidate completed gated `PLAY` and exact-PID handoff, but its
second UI action stopped before delivery with `focus_stage=selection`,
`focus_context=system_cannot_complete`, and
`focus_detail=candidate_cannot_complete`. The candidate AXFrontmost query was
bounded to 0.25 seconds. This observation does not prove the error was caused
by that timeout.

## Decision

Pin the next provisional SessionSpec v2 candidate to independent framework
commit `d7a51aafe4d556fe5c3d92634c8981b02d9bed59` and wheel
`local_app_test_automation-0.2.0.dev0-py3-none-any.whl` with SHA-256
`ebe64c31987b3c524ab8dcaf789c625bced01aa11df1aedce225630261847de0`.

Only the exact-candidate AXFrontmost messaging timeout changes from 0.25 to
1.0 seconds. The same verified PID, bundle, regular-application check,
system-wide query, Boolean-true foreground requirement, final pre-delivery
revalidation, one-use authorization, and no-retry rule remain. Any nonzero AX
result is still terminal; it cannot be interpreted as foreground proof or
substituted with AppKit state. The adopted framework v0.1.0 and core runtime
remain unchanged.

## Evidence and limits

- Independent offline review matched the wheel digest and changed source
  bytes, checked ZIP integrity, installed the wheel in a clean Python 3.12
  environment, validated the execution-core SessionSpec v2 through the
  installed public CLI, and passed 34 targeted UI tests. The framework task
  reports 138 default tests and a passing four-cell macOS CI and wheel gate
  in run `35838099522`.
- There is no target-machine evidence for this candidate. The ADR-0058 target
  failure remains the last observed live result. A new target run requires
  independent protected-host checks and fresh same-task authorization at
  both checkpoints; no previous nonce is reusable.

## Supersedes

This decision supersedes ADR-0058 only for the provisional candidate pin and
the exact-candidate AXFrontmost messaging timeout. All diagnostic, identity,
safety, cleanup, privacy, and fail-closed requirements remain.
