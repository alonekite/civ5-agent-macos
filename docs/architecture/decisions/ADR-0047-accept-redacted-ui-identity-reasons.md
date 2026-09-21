# ADR-0047: Accept redacted UI identity failure reasons

Status: Accepted

Date: 2026-09-21

## Context

A second handoff-capable target run again stopped before `PLAY` delivery with
the generic `ui_identity_error`. It recorded no action-delivery marker, started
no watcher, terminated the application normally, and restored the host
baseline, but the generic code could not distinguish a focused-application
query failure from an identity, window, or element failure.

Framework commit `8f57a53` first added reason strings, but caller review found
that arbitrary values could reach durable metadata despite documentation
claiming a closed set. Framework implementation commit
`cca95b4a5f3b7d69d64a710bc5e3c567c657c9e4` corrects that boundary.

## Decision

Pin candidate SessionSpec v2 compatibility to framework commit `cca95b4`.
Permit `session.failure` events for `ui_identity_error` to include one stable
`error_reason` from the framework's explicit allowlist. Enforce the allowlist
both when constructing the error and at durable event persistence. Unknown or
mutated values become `unspecified`.

Exception messages, paths, bundle identifiers, process values, window titles,
AX roles, selectors, and observed AX content must never be persisted. Sanitized
reports remain unchanged. SessionSpec v2 and `latp/1` do not change, so the
execution-core descriptor requires no new field.

## Consequences

- A future bounded diagnostic run can identify which identity check failed
  without retaining target-specific or user-specific values.
- The execution core consumes no diagnostic event at runtime; the reason exists
  only for external-framework evidence and maintenance.
- Any new reason requires an explicit framework allowlist and test update.
- This diagnostic improvement does not authorize another UI action or weaken
  identity, focus, handoff, or no-replay constraints.

## Alternatives considered

- Persist exception text: rejected because it may contain paths, titles,
  selectors, or process values.
- Trust internal callers to use constants: rejected because the durable
  privacy boundary must enforce the documented closed set.
- Omit diagnostics entirely: rejected because repeated safe pre-delivery
  failures cannot otherwise be distinguished on the target machine.

## Supersedes

This decision extends ADR-0044 through ADR-0046 only for sanitized failure
diagnosis. Their action, identity, handoff, readiness, and ownership decisions
remain authoritative.
