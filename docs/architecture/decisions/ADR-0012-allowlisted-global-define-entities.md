# ADR-0012: Model allowlisted global defines as entities

Status: Accepted

Date: 2026-09-15

## Context

Civ V stores engine-wide numeric rules in `Defines(Name, Value)` rather than in
a table with a `Type` column. `Name` is nevertheless the stable uppercase game
identifier for each definition. Importing the complete table would collect more
than 1,700 unrelated values, including hundreds of AI behavior parameters.
Discarding it entirely would omit constants needed for deterministic movement,
health, growth, purchase, and upgrade calculations.

## Decision

Represent an explicitly allowlisted define as a `global_define` entity whose
`type_id` is the source `Name` and whose sole attribute is its validated numeric
`value`. This is allowed only when the name is a stable uppercase source key,
the value has a declared integer or finite-number type, and the fact is needed
by the read/write core or deterministic controller.

The importer requires every allowlisted key, selects no other `Defines` row,
and fails on a missing key or invalid value. Expanding the allowlist requires
field-level gameplay, copyright, and ADR-0005 review. `PostDefines` and bulk
define import remain unsupported.

## Consequences

- Global constants retain ordinary entity provenance and canonical ordering.
- Consumers can query them through the existing knowledge API without a second
  unvalidated key/value channel.
- A database with a missing or type-changed required constant fails closed.
- AI flavor, role, objective, strategy, and personality values are not imported.
- The knowledge contract permits stable source keys outside a literal `Type`
  column only through an explicit importer allowlist and documented decision.

## Alternatives considered

- Import every define: rejected because it violates positive allowlisting and
  would collect AI behavior parameters unrelated to the core.
- Store one synthetic aggregate entity: rejected because it invents identity
  and weakens per-fact provenance and lookup.
- Add a separate untyped dictionary: rejected because it bypasses entity
  validation, canonicalization, and query behavior.

## Supersedes

None. This complements ADR-0004 and ADR-0005.
