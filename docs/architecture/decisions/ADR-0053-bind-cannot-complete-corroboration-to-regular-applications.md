# ADR-0053: Bind cannot-complete corroboration to regular applications

Status: Accepted

Date: 2026-09-22

## Context

An operator-present run of the strict ADR-0052 candidate answered the first
checkpoint and then received `kAXErrorCannotComplete` from the system-wide
`AXFocusedApplication` query. It correctly performed zero UI deliveries, but
could not operate on the target Mac.

A subsequent input-free diagnostic found that application-level `AXFrontmost`
was not unique across every running process. It was unique among the 17 regular
GUI applications that returned a value, with no query errors in that subset.
The diagnostic retained no application identities. Therefore a global
candidate fallback would be unsound, while an exact regular-application
corroboration is a narrower testable boundary.

## Decision

Pin candidate SessionSpec v2 compatibility to framework commit
`b1f99ef988d376b61269e1cdc377e2033d6d736e` and candidate wheel:

- `local_app_test_automation-0.2.0.dev0-py3-none-any.whl`;
- SHA-256
  `cc57a78719507ac65795169d7f87a7c8c58de7d793680f8360bb1de4d2175685`.

The system-wide Accessibility query remains primary. Only
`kAXErrorNoValue`, successful null, or `kAXErrorCannotComplete` may enter
candidate corroboration. Before querying candidate `AXFrontmost`, resolve the
exact PID again, require the same bundle identifier, resolved bundle path and
resolved executable path, and require activation policy
`NSApplicationActivationPolicyRegular`. Nonregular, missing, malformed, or
changed candidates are terminal.

Use the existing 0.25-second bound for candidate `AXFrontmost`. Boolean true
may proceed, Boolean false remains bounded `target_not_frontmost`, and all
other candidate results fail closed. Repeat exact identity, activation-policy,
and focus checks immediately before delivery.

Do not use AppKit foreground state, activate or reorder applications, retry
after delivery, expand checkpoint authority, or inspect any other PID.

## Consequences

- The observed macOS 26 cannot-complete condition can proceed only for the
  unchanged exact regular GUI target with independent Boolean AX evidence.
- Accessory and prohibited processes cannot contribute action authority even
  when they report `AXFrontmost=true`.
- The candidate remains pre-release and requires a fresh operator-present
  target run before any framework 0.2 adoption.
- Independent host inspection confirmed that current AppKit
  `activationPolicy()` values and its regular-policy constant are integer
  values, matching the candidate's strict validation.

## Alternatives considered

- Treat all `AXFrontmost=true` processes as equivalent: rejected because the
  observation was not globally unique.
- Continue treating `kAXErrorCannotComplete` as terminal: safe but known not to
  operate on this target Mac.
- Use AppKit foreground state or activate the target: rejected because these
  reintroduce stale state or unauthorized mutation.

## Supersedes

This decision supersedes ADR-0052 only for the exact candidate implementation
pin and the narrowly classified `kAXErrorCannotComplete` condition. All prior
identity, checkpoint, deadline, delivery, handoff, privacy, control-lifetime,
and no-retry constraints remain in force.
