# ADR-0026: Aggregate the pre-1.0 public API and error taxonomy

Status: Accepted

Date: 2026-09-16

## Context

The implemented modules already expose useful models and operations, but callers
would otherwise depend on implementation paths and unrelated built-in errors.
M7 needs one testable import surface while preserving existing `ValueError`,
`RuntimeError`, and connection-oriented catch behavior during the pre-1.0
transition.

## Decision

`civ5_agent.api` is the supported aggregate pre-1.0 import surface. Its explicit
`__all__` contains bridge, knowledge, journal, TurnPlan/execution, factual
requirement, schema/version, and public size-limit symbols. Raw FireTuner, local
IPC server, watcher-handler, SQLite extractor, and private codec/transition
helpers are not exported.

Public errors share `Civ5AgentError` and one of these categories:

- `ValidationError`, also a `ValueError`, for invalid domain data;
- `ProtocolError`, also a `ValueError`, for explicit or malformed peer
  responses whose operation is not transport-ambiguous;
- `TransportError`, also a `ConnectionError`, for exchanges whose outcome may
  be unknown;
- `SafetyError`, also a `RuntimeError`, for mandatory live-safety failures.

Existing domain error names remain available and inherit the appropriate base.
Wrapped errors preserve their cause. In particular, malformed evidence after a
write is `TransportError` so M6 keeps the outcome unknown rather than classifying
the action as a deterministic rejection.

The package remains version `0.x`: breaking Python-surface changes require a
minor-version increment and compatibility note before 1.0. Versioned persisted
schemas are independent and never change meaning silently; their own version
rules remain authoritative.

## Consequences

- Contract tests can detect accidental export removal, implementation leakage,
  error-category drift, and size/schema constant changes.
- Existing callers catching `ValueError`, `RuntimeError`, or `ConnectionError`
  continue to work for the corresponding categories.
- Submodule imports may remain convenient, but only `civ5_agent.api.__all__` is
  the aggregate supported surface promised by this decision.
- CLI JSON error-code stability remains a separate M7 decision.

## Alternatives considered

- Treat every existing module symbol as public: rejected because transport and
  persistence internals require freedom to change.
- Replace all existing errors immediately: rejected because it would break
  useful catch behavior and obscure recovery semantics.
- Export only a single high-level object: rejected because independent bridge,
  knowledge, journal, and deterministic execution consumers are intentional.

## Supersedes

This finalizes the aggregate import and error-taxonomy gaps identified by the M7
public API inventory. It does not freeze CLI envelopes or declare 1.0 stability.
