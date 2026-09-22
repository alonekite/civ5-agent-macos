# ADR-0054: Bind human authorization to fresh checkpoint challenges

Status: Accepted

Date: 2026-09-22

## Context

During an unattended SessionSpec v2 attempt, the execution-layer agent reused
a user message that predated the actual framework checkpoint and submitted
`pass`. The target never became frontmost and the framework made zero UI
deliveries, but the authorization chain itself was invalid. Text saying
"fresh authorization" did not prevent the agent from rebinding history.

The external framework's current public checkpoint protocol accepts an exact
checkpoint ID and decision but does not carry a caller nonce or Codex task
identity. The execution core must not import that framework or implement its
control protocol.

## Decision

Add a process-independent local authorization gate to `civ5-read-only`:

1. `checkpoint-challenge` runs only after `checkpoint.requested` and creates an
   exclusive mode-0600 JSON ticket bound to canonical checkpoint and task UUIDs,
   one allowlisted UI step, the request and creation times, and a random
   eight-hex nonce.
2. It emits an exact prompt that asserts current Mac presence and includes the
   step plus nonce.
3. `checkpoint-authorize` accepts only that exact response with matching ID,
   step, task, owned regular file, schema, request/creation order, nonce, and a
   maximum five-minute age. Success deletes the ticket, making it one-use.
4. A confirmation sent before checkpoint creation, in another task, without
   explicit current presence, or without the current step/nonce is invalid.
   Unknown, withdrawn, or conflicting presence permits only fail, abort, or
   stop.

The helper does not call `respond-checkpoint` and does not import the framework.
The external composition root may call framework `pass` only after successful
ticket consumption. Direct calls that bypass the ticket are unsupported.

## Consequences

- Historical and generic confirmations no longer satisfy the supported
  execution-layer procedure.
- Tickets store no response text, are private, expire quickly, and disappear on
  successful validation.
- The local gate machine-checks binding and freshness but cannot attest that a
  message originated in a particular Codex task. The composition root remains
  responsible for message provenance.
- A future framework protocol should carry a caller nonce in checkpoint
  creation and response so the supervisor itself can reject bypasses. This is a
  recorded protocol enhancement requirement, not authority to weaken the
  current framework boundary.

## Alternatives considered

- Documentation only: rejected because the incident occurred despite an
  existing fresh-authorization rule.
- Import or reimplement the framework protocol in the core: rejected because it
  violates the process-only dependency boundary.
- Treat a previous user confirmation as durable authority: rejected because it
  is not bound to a checkpoint instance or current operator presence.

## Supersedes

This decision strengthens the human-authorization procedure used with
ADR-0044 through ADR-0053. It does not change SessionSpec, framework checkpoint
semantics, UI action authority, or the adopted v0.1.0 integration.
