# ADR-0007: Add attributes to knowledge references

Status: Accepted
Date: 2026-09-14

## Context

Many Civ V rules are quantities attached to a relationship rather than to one
entity. Examples include a terrain yielding two food, a technology adding one
production to an improvement, or a building requiring two units of a resource.
Schema 1 references identify only their source, target, kind, and provenance.
Discarding the quantity would make the knowledge incorrect, while synthesizing
fake effect entity IDs would violate the stable-identifier model and complicate
queries.

## Decision

Knowledge schema 2 adds an `attributes` object to every reference. The object is
subject to the same deterministic JSON, finite-number, and forbidden-AI-field
validation as entity attributes. A reference's identity remains its kind,
source, and target; duplicate identities are rejected even if their attributes
differ.

The importer emits schema 2. The codec continues to read and reproduce schema 1
bundles without adding a field to their serialized references. Schema 1
references must have empty in-memory attributes. New quantity-bearing imports
use schema 2 rather than changing the meaning of schema 1.

## Consequences

- Yield changes, requirements, modifiers, and other scalar edges can retain
  their values and provenance.
- Existing schema 1 bundles remain readable and canonically stable.
- Consumers must explicitly support schema 2 before using new generated
  bundles.
- Conflicting duplicate rows fail instead of being silently ordered or summed.

## Alternatives considered

- Reinterpret schema 1 references: rejected because it silently breaks the
  serialized contract.
- Create synthetic effect entities: rejected because their IDs are not Civ V
  stable type identifiers and N-ary queries become unnecessarily indirect.
- Store quantities on either endpoint entity: rejected because one entity can
  have different values for many targets and contexts.

## Supersedes

None.
