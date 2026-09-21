# ADR-0046: Wait for target focus before UI action delivery

Status: Accepted

Date: 2026-09-21

## Context

The first live run after ADR-0045 stopped safely before delivering `PLAY`.
The operator had to move focus from the verified launcher to the control client
to authorize the checkpoint. Final revalidation then classified the unchanged
launcher being temporarily non-frontmost as a terminal identity failure. No UI
delivery marker, action, handoff, watcher, or game write occurred.

The independent framework corrected this race on exact commit
`e7bc316bd61d79b4e3ec9c43090dab7ee7a6766e`. Its SessionSpec v2 and `latp/1`
schemas are unchanged.

## Decision

Pin candidate v2 compatibility to framework commit `e7bc316`. Before the
delivery boundary, permit the framework to wait within the existing UI-step
timeout when the same fully verified target is temporarily not frontmost. The
operator authorizes once, returns to the exact target, and keeps it frontmost.

This is readiness, not identity relaxation. PID, process creation time,
executable, bundle identity, resolved bundle path, unique window, and selector
must remain unchanged on every attempt. Changed or ambiguous identity,
permission failure, timeout, and every post-delivery failure remain terminal.
The framework does not activate the application and never replays a delivered
action.

The existing 300,000 ms step timeout is sufficient for the operator to return
focus. No SessionSpec field or execution-core descriptor change is required.

## Consequences

- A checkpoint response no longer races the unavoidable switch to the control
  client.
- The user must return to the verified Civ V window after authorizing; the
  framework will not focus it automatically.
- A timeout before delivery records no delivered action and requires a new
  session rather than reusing the expired authorization.
- Offline compatibility and CI do not replace a new target-machine run.

## Alternatives considered

- Require the launcher to stay frontmost while replying in Codex: rejected as
  impossible for the ordinary GUI workflow.
- Add an arbitrary sleep after authorization: rejected because it creates a
  timing race without proving target readiness.
- Let the framework activate Civ V: rejected because focus mutation remains
  outside the authorized action contract.
- Retry after delivery: rejected because action outcome could be uncertain.

## Supersedes

This decision refines the pre-delivery readiness behavior accepted by
ADR-0044 and ADR-0045. Their UI-step ownership, exact identity, handoff, and
no-replay requirements remain authoritative.
