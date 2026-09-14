# Module: knowledge

Status: Implemented, coverage in progress

## Responsibility

The knowledge module represents versioned Civ V ruleset facts as entities,
typed references with optional scalar attributes and typed context, source
provenance, canonical JSON, deterministic hashes, and validated query indexes.
Its importer reads the user's local merged SQLite data without modifying it.

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
- Schema 1 and schema 2 remain canonically readable; schema 3 adds typed context
  without reinterpreting the earlier schemas.
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

Coverage now includes core terrains, features, improvements, routes, yields,
and build actions in addition to the earlier entity families. It also imports
the game's `FakeFeatures` rows as feature entities marked `fake`, projects,
processes, victory conditions, and 51 single-value binary effect and
resource-quantity table families. It also covers unit-combat categories,
domains, special-unit categories, unit/promotion applicability, and seven
category-specific quantified effect families, bringing the single-value binary
total to 58. Promotion-to-domain, feature, terrain, and unit-class relations
also preserve their combined combat, movement, and impassability attributes.
Schema 3 coverage includes 19 quantified and two promotion-grant contextual
table families, plus technology-conditioned promotion passability.
Unit scalar identifiers for capture class, technology gates, ancient-ruin
upgrade, policy, cargo, project, and leader promotion also have validated typed
relationships.
Effects that need multiple context items or new target entity families are
deferred.

## Planned extensions

M3 next inventories effects requiring multiple context items or new target
entity families, extends schema 3 coverage, and then imports scaling families.
M4 adds per-game resolution without mutating base facts.
