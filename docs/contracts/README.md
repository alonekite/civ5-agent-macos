# Contract Index

Contracts define data and behavior that cross module boundaries. They are not
implementation tutorials. Exact executable validation lives in Python and
tests; discrepancies are defects that must be resolved explicitly.

| Contract | Status | Owning module |
|---|---|---|
| [Live state](live-state.md) | Evolving; schemas 2–5 supported with documented live evidence limits | bridge |
| [Commands](command.md) | Evolving, core writes live-verified | bridge |
| [Unit movement](unit-movement.md) | Approved M9 contract; not implemented or live-verified | bridge/executor |
| [Session and match identity](session-identity.md) | Bridge session and journal match binding implemented offline | bridge/application/journal |
| [Knowledge bundle](../KNOWLEDGE.md) | Evolving, implemented | knowledge |
| [Ruleset knowledge view](resolver.md) | Structural M4 contract implemented | knowledge |
| [Turn journal](journal.md) | M5 implemented; bounded live verification passed | journal |
| [Turn plan and execution](turn-plan.md) | Schema 1 execution/recovery and bounded CLI implemented offline | controller/executor |
| [Public Python API](public-api.md) | Stable 1.0 aggregate surface and error contract implemented | cross-module |
| [CLI compatibility](cli.md) | `civ5-turn` stable in 1.0; other entry points provisional | cli |
| [Downstream tactical integration](downstream-integration.md) | Stable 1.0 capability and ownership profile | cross-module |

## Contract rules

- Every persisted or exchanged object has an explicit schema/version boundary.
- Booleans are not accepted where integers are required.
- Non-finite numbers, unknown required semantics, and oversized data fail
  closed.
- Units and null/unknown meaning are documented for every numeric field family.
- A breaking change requires a version increment, migration/compatibility note,
  and tests for the supported older version where applicable.
- Overview documents link here rather than duplicating complete schemas.
