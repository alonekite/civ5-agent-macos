# ADR-0052: Corroborate macOS frontmost through the exact AX candidate

Status: Accepted

Date: 2026-09-22

## Context

Two operator-present candidate runs successfully answered the first `PLAY`
checkpoint but exhausted the pre-delivery deadline with
`focused_application_unavailable`. Both had zero UI deliveries, handoffs,
later checkpoints, watcher starts, and game access. The execution layer restored
FireTuner while retaining its persistent firewall guard.

The system-wide macOS 26 Accessibility focused-application attribute can have
no value even when the exact launcher candidate is available. AppKit foreground
state is unsuitable because the framework's long-running process previously
observed stale workspace state, and activating the target would expand
authority.

An initial framework candidate incorrectly treated every nonzero system AX
result as absence. Independent execution-layer review rejected it because
failure, cannot-complete, and attribute-unsupported errors could enter the
fallback contrary to the declared fail-closed boundary.

## Decision

Pin candidate SessionSpec v2 compatibility to framework commit
`51cebff18a57929ef888609efe69a1af381841ad` and candidate wheel:

- `local_app_test_automation-0.2.0.dev0-py3-none-any.whl`;
- SHA-256
  `6d0fe2669af58c0a77ce22f47a0c5df03c90e9f77956f67a4eb16aea9c185ee3`.

Continue to query system-wide `AXFocusedApplication` first. Only
`kAXErrorNoValue`, or a successful query with a null value, may enter a
0.25-second `AXFrontmost` query on the exact already verified candidate PID.
A Boolean true corroborates frontmost identity. Boolean false uses the existing
bounded `target_not_frontmost` readiness path. Explicit no-value at the
candidate remains bounded `focused_application_unavailable`.

Every other nonzero AX result, exception, invalid PID, non-Boolean value,
messaging-timeout setup failure, or permission failure is terminal. Apply the
same procedure during final identity revalidation immediately before delivery.

Keep target bundle/process/executable/window identity, checkpoint authority,
deadline, durable delivery boundary, same-process handoff, control protocol,
and no-retry rules unchanged. Do not use AppKit foreground state, window order,
application activation, image matching, or a different PID.

## Consequences

- macOS 26 can proceed only when two Accessibility observations consistently
  bind frontmost state to the same exact candidate.
- System and candidate AX errors cannot be converted into action authority.
- The framework's 119-test host suite covers no-value, successful null,
  failure, cannot-complete, attribute-unsupported, false, and malformed values.
- Another fresh operator-present target run remains required. No framework 0.2
  release is adopted by this decision.

## Alternatives considered

- AppKit `frontmostApplication`: rejected because it reintroduces the observed
  stale run-loop boundary.
- Activating the target: rejected because it adds a UI mutation outside the
  authorized action.
- Treating every nonzero AX result as absence: rejected during independent
  review because query failures are not proof of no focused application.

## Supersedes

This decision supersedes ADR-0051 only for the exact candidate implementation
pin. ADR-0044 through ADR-0051 continue to govern UI gates, identity handoff,
readiness, diagnostics, privacy, control lifetime, and no-retry behavior.
