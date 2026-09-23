# ADR-0057: Pin focus diagnostics and post-handoff cleanup candidate

Status: Accepted for provisional SessionSpec v2 compatibility

Date: 2026-09-23

## Context

The ADR-0056 candidate completed the one-use `PLAY` delivery and exact-PID
executable handoff on the target Mac. It created a second checkpoint, but
after fresh authorization a `focused_application_query` error occurred before
the second UI delivery boundary. No continue click or watcher startup occurred.
Saved events could not distinguish the initial frontmost check from the final
pre-delivery revalidation, nor whether cleanup's `identity_changed` resulted
from a changed process snapshot or a stale AppKit candidate executable.

## Decision

Pin the provisional SessionSpec v2 candidate to framework commit
`192391eb30de35c99ad49a4e5e12434bcc2bd6fd` and wheel
`local_app_test_automation-0.2.0.dev0-py3-none-any.whl` with SHA-256
`3ad709c60f7a375e75b88a2e13b23b3d6afc084bee71b584124a1b37907a2a5a`.

The focus-query error remains terminal. Failure metadata may add only
allowlisted `focus_stage` and `focus_detail` categories; no raw AX code, PID,
path, title, or input is persisted. After a declared handoff, cleanup may
accept the original or declared successor AppKit executable only when a fresh
process probe exactly equals the tracked successor identity. The original
PID, creation time, bundle identifier/path, and third-executable refusal
remain mandatory. Cleanup mismatch sources are closed-set diagnostics, not
permission to terminate a mismatched process. Neither UI action is retried.

## Evidence and limits

- The exact wheel digest, ZIP integrity, source-byte match for application and
  UI modules, isolated Python 3.12 installation, and public validation of the
  execution core's SessionSpec v2 passed independent offline review.
- The framework task reports 137 default tests (eight host-environment skips)
  and passing four-cell macOS CI plus wheel/clean-install gate in run
  `35802740842`.
- No target test of this exact candidate has yet proved a continue click or
  read-only watcher startup. A fresh operator-present run with independent
  one-use authorization for each UI step is required. Framework 0.2 remains
  unadopted; the adopted v0.1.0 path is unchanged.

## Supersedes

This decision supersedes ADR-0056 only for the provisional candidate pin,
focus-query diagnostics, and post-handoff cleanup behavior. All other
identity, authorization, safety, privacy, and no-retry requirements remain.
