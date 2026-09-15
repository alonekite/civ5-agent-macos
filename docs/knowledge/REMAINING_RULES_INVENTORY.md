# Remaining Rules Inventory

Last reviewed: 2026-09-15 against the local Brave New World merged database.

This inventory records semantic review of non-empty SQLite tables that are not
already covered by the knowledge importer. Counts are evidence from the tested
ruleset, not compatibility promises for another DLC or mod set. No database,
machine path, localized text, or generated bundle is stored here.

## Method

The review compared the importer's positive table and field allowlists with the
target database in SQLite read-only mode. Tables with two or more columns whose
names end in `Type` received manual review; entity tables with one stable `Type`
also received a scope review. Column names alone are not treated as semantics.

Every accepted family must still gain deterministic ordering, value validation,
referential-integrity tests, and repeatability evidence before it is marked
implemented.

## Completed from this review

| Source family | Target rows | Representation |
|---|---:|---|
| `BuildFeatures` | 59 | `build -> feature` rules with time, production, cost, removal, and optional technology context |
| `Regions` | 9 | stable `region` entities without localized descriptions |
| Civilization free building classes | 44 | typed civilization-to-building-class references |
| Civilization free technologies | 45 | typed civilization-to-technology references |
| Civilization start-region avoid/priority | 9 / 15 rows | typed civilization-to-region references; duplicate merged rows collapse canonically |
| `GameSpeeds`, `HandicapInfos`, `Worlds` | 4 / 9 / 6 | immutable scaling entities; descriptions, art, and AI decision heuristics excluded |
| `GoodyHuts` and handicap availability | 20 / 83 | deterministic ancient-ruin outcomes, typed unit-class results, and difficulty availability |
| World Congress families | 47 entities, 68 links | resolutions, decisions, sessions, projects, rewards, legacy votes, and typed prerequisites/rewards |
| Minor civilizations and traits | 58 / 5 | stable identities and deterministic trait membership; prose, art, colors, and AI flavor excluded |
| Civilization initial units and coastal starts | 44 / 12 / 1 | typed unit-class quantities and boolean map-placement facts; `UnitAIType` is never selected |

## Multi-context result

No unimported controller-facing gameplay effect in the reviewed database needs
more than one `ReferenceContext` item.

`MultiUnitFormation_SlotEntries` is the only non-empty table with a genuine
source, target, and two additional stable-ID conditions. Its 132 rows describe
built-in AI formation slots using primary and secondary `UnitAI` roles. ADR-0005
excludes AI roles and behavior parameters, so neither this table nor its
formation/role entity families will be imported.

`Natural_Wonder_Placement` superficially looks multi-context because three
boolean column names end in `PlotType`, `TerrainType`, or `FeatureType`. They are
flags, not foreign identifiers. Its 17 rows are non-addressable placement-rule
objects owned by natural-wonder features. If map-generation support later needs
them, they should be reviewed for an embedded-rule representation under
ADR-0011, not modeled as typed contexts.

## New entity families

Priority is based on the deterministic controller's need for gameplay rules,
not on table size.

| Priority | Entity families | Related target rows | Decision |
|---|---|---:|---|
| Completed | game speeds, handicaps, world sizes | 4 / 9 / 6 | Explicit gameplay-scaling allowlists exclude descriptions, art, and AI decision heuristics |
| Completed | ancient-ruin outcomes | 20 outcomes, 83 handicap links | `GoodyHuts` are deterministic outcomes with typed unit-class and handicap relations |
| Completed | World Congress resolutions, decisions, sessions, projects, rewards, votes | 18 / 10 / 4 / 3 / 9 / 3 | Stable entity families and typed unlock/reward relations exclude UI text and art |
| Completed | minor civilizations and minor traits | 58 / 5 | Stable identities and deterministic trait membership exclude prose, art, colors, and AI flavor |
| Deferred | natural-wonder placement rules | 17 | Consider embedded rules only if deterministic map reasoning needs them |

The scaling review must distinguish deterministic difficulty modifiers applied
by game rules from AI choice parameters. Cost, growth, production, research,
starting-unit, barbarian, and similar numerical effects are candidates. Option
counts, declaration probabilities, attitudes, flavors, roles, objectives, and
strategy weights remain prohibited by ADR-0005.

`GameSpeed_Turns` contains 31 ordered calendar segments without stable row IDs.
It remains deferred until its semantic ordering can be reproduced without using
SQLite `rowid` as invented identity or provenance.

## Explicit exclusions

The following families remain outside the knowledge module:

- flavor tables and leader/civilization approach biases;
- AI city, economic, grand, military, tactical, and specialization strategies;
- unit AI roles and multi-unit formation templates;
- diplomacy response text;
- art definitions, animations, sounds, UI modes, cursors, and controls;
- Civilopedia concepts and all localized descriptions/help text.

## Next implementation slice

Audit the remaining policy and building tables still marked incomplete on the
roadmap. That audit found only `Policy_Flavors` and `Building_Flavors` outside
the allowlist; both are prohibited by ADR-0005, so policy/building table coverage
is closed. Continue the broader M3 audit until every non-empty candidate is
imported, explicitly deferred with a reason, or excluded under an accepted
boundary. Per-game selection and modifier application remain an M4 resolver
responsibility.

The next broader audit targets positive allowlists for deterministic global
`Defines` plus remaining map/calendar families. Large tables are not imported
wholesale: each field must be controller-relevant and must pass the same
copyright and AI-boundary review.
