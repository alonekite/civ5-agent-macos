# ADR-0049: Preserve the final pre-delivery UI readiness reason

Status: Accepted

Date: 2026-09-21

## Context

A fresh target run against framework commit `055d816` waited for the full
300-second pre-delivery deadline and failed with generic
`target_not_ready_timeout`. No `ui.action_delivery_started` event, UI action,
handoff, second checkpoint, watcher, read, or game write occurred. Cleanup and
guarded host restoration both completed exactly.

The controller collapsed a missing candidate, unavailable focused application,
non-frontmost target, missing window or element, unavailable geometry, and
final focus loss into that one timeout reason. This was fail-closed but could
not distinguish which observable readiness condition persisted on the target.

Framework implementation commit
`c47b8cbd1d1a32363058ce528d4991b7f6637be6` preserves that distinction.

## Decision

Pin candidate SessionSpec v2 compatibility to framework commit `c47b8cb`.
Permit a pre-delivery timeout to expose only the last observed reason from a
fixed readiness allowlist: candidate unavailable, focused application
unavailable, target not frontmost, window not ready, element not ready, or
geometry not ready.

Sanitize at readiness-error construction and again at durable identity-error
persistence. Unknown or mutated values become `unspecified`. Never persist
exception text, paths, process values, titles, selectors, Accessibility values,
or other observed target content.

This is diagnostic only. SessionSpec v2, `latp/1`, the report shape, the
300-second deadline, checkpoint authority, activation policy, identity checks,
delivery boundary, handoff, watcher ordering, and post-delivery no-retry rules
do not change.

## Consequences

- The next bounded target run can identify the final readiness class without
  weakening any UI identity or delivery requirement.
- A later behavior change still requires separate evidence and a new decision;
  this change does not introduce a fallback focus source.
- Existing framework event consumers continue to receive the same
  `ui_identity_error` code with a value-free allowlisted reason.

## Alternatives considered

- Return the generic timeout again: rejected because it prevents evidence-led
  diagnosis.
- Persist every intermediate observation: rejected as unnecessary and more
  privacy-sensitive.
- Restore `NSWorkspace.frontmostApplication()` immediately: rejected because
  long-running AppKit clients may observe stale state and the current evidence
  does not yet prove which readiness condition persisted.

## Supersedes

This decision refines ADR-0047 and ADR-0048 only for the final pre-delivery
timeout reason. Their privacy, readiness, authorization, identity, and
no-replay constraints remain authoritative.
