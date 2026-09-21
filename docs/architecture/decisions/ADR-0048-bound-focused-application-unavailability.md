# ADR-0048: Bound focused-application unavailability before delivery

Status: Accepted

Date: 2026-09-21

## Context

A third fresh SessionSpec v2 target run against framework commit `cca95b4`
stopped about 1.78 seconds after the operator authorized `PLAY`. Its durable,
allowlisted reason was `focused_application_unavailable`. No action-delivery
marker, handoff, second checkpoint, watcher, FireTuner read, or game write
occurred, and guarded restoration returned the host to its exact baseline.

This distinguishes a temporary macOS Accessibility observation gap from an
observed identity change. Treating every such gap as a terminal identity error
made a valid operator-mediated focus transition impossible, while broadly
retrying identity errors would weaken the fail-closed boundary.

Framework commit `055d81676495acfd625f4eb51ddbe633bc68b54e`
implements the narrow distinction.

## Decision

Pin candidate SessionSpec v2 compatibility to framework commit `055d816`.
Before action delivery, and only while Accessibility permission remains normal,
the exact allowlisted reason `focused_application_unavailable` is temporary
readiness and may be retried within the step's existing deadline.

Focused-application query errors, permission errors, invalid process identity,
target identity changes, ambiguity, timeout, and every post-delivery failure
remain terminal. The framework must not activate the application, extend the
authorization, change SessionSpec v2 or `latp/1`, or replay an action.

## Consequences

- An operator may authorize a checkpoint in Codex and return to the already
  verified Civ V window without a transient empty Accessibility observation
  ending the session immediately.
- Persistent unavailability still expires with zero delivery.
- The core descriptor and public process boundary do not change; only the
  exact compatible framework implementation pin changes.
- A fresh target run remains required before any framework release adoption.

## Alternatives considered

- Treat every unavailable observation as terminal: rejected because the target
  diagnostic isolated a transient, pre-delivery observation gap.
- Retry all UI identity errors: rejected because it would conceal permission,
  query, process, ambiguity, and identity failures.
- Activate Civ V automatically: rejected because it changes focus ownership
  and widens the external framework's authority.

## Supersedes

This decision refines ADR-0046 only for the exact pre-delivery
`focused_application_unavailable` condition and advances ADR-0047's diagnostic
result into a bounded readiness rule. All other identity, privacy, handoff,
authorization, and no-replay decisions remain authoritative.
