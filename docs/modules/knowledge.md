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

`KnowledgeBundle`, `KnowledgeIndex`, canonical codec functions, validation, the
SQLite importer, and the explicit per-game `RulesetResolver`. See
[KNOWLEDGE.md](../KNOWLEDGE.md) and the
[resolver contract](../contracts/resolver.md) for executable behavior.

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
total to 84. Promotion-to-domain, feature, terrain, and unit-class relations
also preserve their combined combat, movement, and impassability attributes.
Schema 3 coverage includes 22 quantified and two promotion-grant contextual
table families, plus technology-conditioned promotion passability.
Unit scalar identifiers for capture class, technology gates, ancient-ruin
upgrade, policy, cargo, project, and leader promotion also have validated typed
relationships. Further plain relationships cover faith-purchase eligibility,
building and local-resource prerequisites, resource placement, free and random
promotions, training restrictions, and unit build capabilities.
Improvement/resource rules preserve validity, trade access, discovery chance,
and quantity requirements together. Building technology-enhanced yields derive
their required technology from the validated building row and fail closed when
that context is absent.
Hurry methods are first-class entities with conversion rates and optional policy
requirements; building and policy cost modifiers target those stable IDs.
Great-work classes and slot types are represented by stable identifiers and
typed class/building slot relations. Individual works retain only stable IDs,
the archaeology-only flag, and typed class/era/artifact/creator relationships;
titles and presentation content remain excluded.
Ten buildings preserve 21 canonically ordered theming alternatives as owned
structured rules. Only deterministic bonus and matching constraints are kept;
localized descriptions and AI priorities are excluded.
The remaining-table inventory found no unimported controller-facing gameplay
effect that needs more than one context item. AI formation slots are excluded
under ADR-0005, while natural-wonder placement columns that end in `Type` are
boolean flags rather than identifiers. Nine region entities now support typed
civilization start-region preferences. Build/feature rules preserve time,
production, cost, removal, and optional technology context, and civilizations
also retain free building-class and technology relationships.
Game-speed, handicap, and world-size entities preserve static scaling values;
handicap AI cost and production modifiers are deterministic difficulty effects,
while decision heuristics remain excluded. Ancient-ruin outcome entities retain
numeric and boolean results, typed unit-class results, and handicap availability
without descriptions or sounds.
World Congress entities cover resolutions, decisions, special sessions, league
projects and rewards, and legacy votes. Typed relations preserve decision kinds,
technology gates, enabled projects, reward tiers, processes, eras, buildings,
unit classes, specialists, and policies without presentation fields.
Minor-civilization and minor-trait entities preserve stable IDs and typed trait
membership. Localized names, Civilopedia prose, art, colors, and flavor tables
remain excluded.
Civilizations also retain 44 initial unit-class quantities and coastal-start
flags. The source `UnitAIType` column is not selected; duplicate
civilization/unit-class pairs fail through reference identity instead of being
silently merged across excluded roles.
Fifteen allowlisted `global_define` entities preserve movement, hit-point,
growth, food-consumption, purchase, and upgrade constants. Their stable source
`Name` keys are accepted under ADR-0012; the importer does not bulk-copy
`Defines` or read AI behavior parameters.
Climate and sea-level entities retain allowlisted map-generation parameters,
and game-option entities retain default and single-/multiplayer support flags.
An invisibility category is connected to promotions through typed invisibility
and detection references. Localized text, UI visibility, and calendar display
tables are not imported.
Strategic resources embed their canonically ordered map quantity alternatives;
these source rows have no stable identity independent of the owning resource.

## Planned extensions

M3 coverage is complete under the reviewed positive-allowlist boundary. Policy
and building remainders are prohibited flavor tables; presentation-only
calendars and city-size soundscape categories are excluded; natural-wonder
placement remains explicitly deferred until a controller use case requires it.
M4 adds per-game resolution without mutating base facts. New knowledge families
remain possible, but require the same provenance and semantic review.

The first M4 slice validates and canonicalizes explicit match context and
returns detached selected entities with source provenance. It does not yet
compose effective scalar values or replacements.
