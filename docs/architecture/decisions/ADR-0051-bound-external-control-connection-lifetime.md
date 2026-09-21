# ADR-0051: Bound external control-connection lifetime

Status: Accepted

Date: 2026-09-21

## Context

A target SessionSpec v2 run reached its first human checkpoint, but the one
authorized public `respond_checkpoint` call returned `control_unavailable`.
The checkpoint later expired safely with zero answers, UI deliveries, handoff,
watcher, or game access.

That observation did not identify which client, if any, occupied the server.
Independent review nevertheless found a concrete starvation path in framework
commit `c47b8cb`: the serialized server imposed no receive deadline after
accepting a same-user Unix-socket connection. A client that connected and sent
no complete request could retain the control loop for the remaining checkpoint
lifetime while the socket path still existed.

Framework implementation commit
`f7514afeae7a317f940f204320465e761c2f5312` bounds that connection.

## Decision

Pin candidate SessionSpec v2 compatibility to framework commit `f7514af` and
candidate wheel:

- `local_app_test_automation-0.2.0.dev0-py3-none-any.whl`;
- SHA-256
  `ec9b21d744b0e011df90bb533f516c18cba0de81c10fbfa5313b0aa66b9cbd0e`.

Accept a 0.5-second I/O timeout on each accepted private control connection.
After timeout the server returns to `accept`. The server does not grant new
authority, and clients do not retry requests. In particular, an ambiguous
`respond_checkpoint` remains non-replayable.

Keep `latp/1`, request UUIDs, same-user peer authentication, request/response
bounds, checkpoint identity/expiry, UI delivery boundaries, durable state,
report shape, and cleanup semantics unchanged. The published v0.1.0/SessionSpec
v1 integration remains unchanged and separately pinned.

## Consequences

- One incomplete same-user connection can delay later control requests by no
  more than 0.5 seconds instead of the remaining session lifetime.
- Real-socket framework tests cover a silent peer followed by a legal request,
  and the full checkpoint lifetime through repeated status, one response,
  exactly one delivery, completion, and socket cleanup.
- The repair addresses a proved implementation path but does not claim that
  the earlier live failure had that exact cause.
- Another operator-present target run is still required; no 0.2 framework
  release is adopted by this decision.

## Alternatives considered

- Automatically retry `respond_checkpoint`: rejected because the caller cannot
  know whether mutation preceded a lost response.
- Use a concurrent connection-per-thread server: rejected as unnecessary for
  four serialized commands and a larger concurrency/authority surface.
- Treat the live incident as proof of the starvation client: rejected because
  the retained private evidence did not identify the socket peer or stall.

## Supersedes

This decision supersedes ADR-0049 only for the exact candidate implementation
pin. ADR-0044 through ADR-0049 continue to govern UI gates, identity handoff,
focus/readiness, diagnostics, privacy, and no-retry behavior.

