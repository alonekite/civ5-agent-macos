# ADR-0002: Give the watcher sole ownership of the game connection

Status: Accepted

Date: 2026-09-12

## Context

The tested Civ V server reliably services one FireTuner client and may retain a
closed connection until the UI processes another event. Independent watcher and
command connections would race, fail intermittently, or strand the endpoint.

## Decision

The long-running watcher owns the sole FireTuner connection. Other local
processes submit structured requests through a per-user Unix socket with mode
`0600`. The watcher serializes reads and writes over the one game connection.

## Consequences

- State observation and commands share the exact verified session.
- Local IPC needs explicit request/response bounds and malformed-input handling.
- Commands cannot silently open a second FireTuner connection while the watcher
  is active.
- Watcher lifecycle and cleanup become operationally important.

## Alternatives considered

- One FireTuner connection per CLI invocation: rejected after observed
  single-client and delayed-cleanup behavior.
- A remotely reachable command broker: rejected because it expands the attack
  surface without helping the local macOS objective.

## Supersedes

None.
