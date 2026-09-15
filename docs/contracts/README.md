# Contract Index

Contracts define data and behavior that cross module boundaries. They are not
implementation tutorials. Exact executable validation lives in Python and
tests; discrepancies are defects that must be resolved explicitly.

| Contract | Status | Owning module |
|---|---|---|
| [Live state](live-state.md) | Evolving; schemas 2–5 supported with documented live evidence limits | bridge |
| [Commands](command.md) | Evolving, core writes live-verified | bridge |
| [Session and match identity](session-identity.md) | Bridge session and journal match binding implemented offline | bridge/application/journal |
| [Knowledge bundle](../KNOWLEDGE.md) | Evolving, implemented | knowledge |
| [Ruleset knowledge view](resolver.md) | Structural M4 contract implemented | knowledge |
| [Turn journal](journal.md) | Schema 1 codec/store implemented offline; capture pending | journal |
| [Turn plan and execution](turn-plan.md) | Proposed for M6 | controller/executor |
| Public Python API | Planned for M7 | cross-module |

## Contract rules

- Every persisted or exchanged object has an explicit schema/version boundary.
- Booleans are not accepted where integers are required.
- Non-finite numbers, unknown required semantics, and oversized data fail
  closed.
- Units and null/unknown meaning are documented for every numeric field family.
- A breaking change requires a version increment, migration/compatibility note,
  and tests for the supported older version where applicable.
- Overview documents link here rather than duplicating complete schemas.
