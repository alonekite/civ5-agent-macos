# Module: knowledge

Status: Implemented, coverage in progress

## Responsibility

The knowledge module represents versioned Civ V ruleset facts as entities,
typed references, source provenance, canonical JSON, deterministic hashes, and
validated query indexes. Its importer reads the user's local merged SQLite data
without modifying it.

## Non-responsibilities

- Live or saved-game state.
- Controller strategy or action choice.
- Per-game working or strategic memory.
- AI flavor/personality data.
- Civilopedia prose, quotations, art, audio, or copied game databases.

## Public interface

`KnowledgeBundle`, `KnowledgeIndex`, canonical codec functions, validation, and
the SQLite importer. See [KNOWLEDGE.md](../KNOWLEDGE.md) for the current
executable contract.

## Inputs and outputs

Inputs identify the ruleset family, game version, relative source label, and
local SQLite path. Output is a canonical bundle containing source hashes,
entities, and relations. Generated bundles are local artifacts and are not
committed.

## Dependencies

Knowledge depends only on standard-library data/SQLite functionality and its own
models, codec, validation, and index. It must not depend on a live bridge or
controller.

## Invariants

- Unchanged inputs produce byte-identical canonical output.
- Every entity and reference has valid source provenance.
- Every reference target exists.
- Declared family matches detected active expansion packages.
- Unknown and forbidden fields are not copied opportunistically.

## Failure modes

Unsupported table/column, missing entity, broken reference, invalid value,
wrong DLC family, active WAL, changing source, non-finite number, and forbidden
field are hard failures.

## Security and privacy

Store relative source labels rather than user paths. Never copy the source
database. Import allowlists and validation enforce the prohibited AI and asset
boundaries described by ADR-0005.

## Verification

Synthetic SQLite fixtures test schema and edge cases. The importer has also
been exercised against the target installation's real local merged database;
canonical counts and relations were checked without committing generated data.

## Current limitations

Coverage currently stops after eras, technologies, units/classes, promotions,
policies/branches, buildings/classes, and resources/classes plus supported
relations.

## Planned extensions

M3 next imports civilizations, leaders, traits, and unique replacements, then
religion/great-person/map/effect/scaling families. M4 adds per-game resolution
without mutating base facts.
