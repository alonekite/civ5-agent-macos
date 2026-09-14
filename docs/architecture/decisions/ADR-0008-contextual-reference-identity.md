# ADR-0008: Add typed context to knowledge references

Status: Accepted
Date: 2026-09-14

## Context

Schema 2 can attach a quantity to a binary source-to-target relationship, but
many Civ V effect tables are contextual. For example, one improvement can gain
the same yield from several different technologies. Those rows have the same
relation kind, source, and target, so schema 2 correctly rejects them as
duplicates even though their triggering technologies differ.

Storing a technology, policy, terrain, feature, resource, or other condition as
an unvalidated string attribute would lose referential integrity. Creating
synthetic effect entities would also abandon the rule that entity identifiers
come from stable game identifiers.

## Decision

Knowledge schema 3 adds a sorted `context` array to every reference. Each
context item contains a lower-snake-case semantic `role`, an entity `kind`, and
an uppercase stable `type_id`. Validation requires every context entity to
exist, rejects duplicate or unsorted context items, and includes the complete
context tuple in reference identity.

Reference attributes continue to hold scalar values such as quantities and
modifiers. Context identifies the additional typed entities under which that
value applies. Schema 1 and schema 2 remain readable and retain their exact
serialized shapes; they cannot contain context. The SQLite importer remains on
schema 2 until it imports its first contextual table.

## Consequences

- Multiple effects with the same source and target can coexist when their typed
  contexts differ.
- Contextual dependencies remain queryable and referentially validated.
- Consumers must explicitly support schema 3 before using contextual imports.
- Importers must choose precise context roles and sort context items rather
  than encoding arbitrary conditions in scalar attributes.

## Alternatives considered

- Put context IDs in `attributes`: rejected because targets would not be
  referentially validated or discoverable as typed dependencies.
- Include all attributes in identity: rejected because scalar values are facts
  about an effect, not its semantic identity, and corrections would look like
  separate effects.
- Create synthetic effect entities: rejected because they would not have stable
  source-game identifiers and would make common queries indirect.

## Supersedes

This extends ADR-0007. Schema 2's binary reference identity remains unchanged;
schema 3 adds typed context to that identity.
