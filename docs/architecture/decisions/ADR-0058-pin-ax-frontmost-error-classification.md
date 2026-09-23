# ADR-0058: Pin closed-set candidate AX frontmost diagnostics

Status: Accepted for provisional SessionSpec v2 compatibility

Date: 2026-09-23

## Context

The ADR-0057 candidate completed gated `PLAY` and the declared executable
handoff on the target Mac, but stopped before the second UI delivery with
`selection / candidate_query_error`. That class did not distinguish the
system-wide focused-application fallback condition from the candidate's own
AXFrontmost failure.

## Decision

Pin the diagnostic-only provisional candidate to framework commit
`04189d3a5da3c9597e391e290dbf97affb93a820` and wheel
`local_app_test_automation-0.2.0.dev0-py3-none-any.whl` with SHA-256
`4b965fefa0eb51d6a7486eedd03ea2c9c093fa4015356c540a47bdd9db057f86`.

The candidate classifies the system-wide fallback as one of
`system_no_value`, `system_cannot_complete`, or `system_success_null`, and
candidate AXFrontmost nonzero errors as a closed-set category. Both fields
are allowlisted before persistence. A candidate query error remains terminal:
it does not establish foreground identity, authorize AppKit-only fallback,
retry a UI action, or start the watcher. The adopted v0.1.0 contract and core
runtime remain unchanged.

## Evidence and limits

- Independent review matched the wheel digest and changed source bytes,
  checked ZIP integrity, installed the wheel offline in a clean Python 3.12
  environment, and validated the generated execution-core SessionSpec v2.
  The framework task reports 138 tests and a passing four-cell macOS CI and
  wheel gate in run `35833990240`.
- A fresh target run completed one authorized `PLAY` delivery and exact-PID
  handoff. After separate authorization for the second step, the framework
  stopped before click delivery with `focus_stage=selection`,
  `focus_context=system_cannot_complete`, and
  `focus_detail=candidate_cannot_complete`. No continue click, watcher start,
  or game-state read occurred. Cleanup-only recovery and independent hardened
  host preflight passed after the game exited.
- This diagnosis does not prove why AX could not complete or that increasing
  its message timeout will fix it. Any behavior change needs separate review,
  offline tests, and fresh target authorization; old nonces cannot be reused.

## Supersedes

This decision supersedes ADR-0057 only for the provisional wheel pin and
focus-query diagnostic categories. Its identity, safety, cleanup, and
no-retry requirements remain in force.
