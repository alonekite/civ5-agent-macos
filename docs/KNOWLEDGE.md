# Ruleset Knowledge

The knowledge module contains structured gameplay facts that are independent of
a particular match. It is a deterministic input to the controller, not an AI
memory or a replacement for live state.

## Boundaries

The module may represent technologies, eras, policies, ideologies, units,
promotions, great people, religions and beliefs, civilizations and traits,
buildings and wonders, terrain and features, resources, improvements, routes,
yields, specialists, diplomacy, city-states, espionage, trade, archaeology,
tourism, World Congress, barbarians, ancient ruins, victory rules, and ruleset
scaling.

It must not contain AI flavor, personality, leader-bias, or strategy-weight
parameters. It also excludes Civilopedia prose, quotations, images, audio, and
other nonessential game assets.

## Data contract

A schema-1 bundle contains:

- `ruleset`: vanilla, Gods & Kings, or Brave New World; exact game version; and
  sorted DLC and mod identifiers.
- `sources`: canonical relative paths, byte sizes, and lowercase SHA-256 hashes.
- `entities`: a lower-snake-case kind, stable uppercase game `Type` identifier,
  gameplay attributes, and one or more source paths.
- `references`: typed, source-backed edges between entities.

Serialization sorts sources, entities, references, and JSON object keys. The
bundle hash is therefore independent of importer query order. Loading is strict:
unknown fields, duplicate entities or references, dangling references, invalid
paths, invalid identifiers, unsupported value types, non-finite numbers, and AI
parameter fields are rejected.

`KnowledgeIndex` validates a bundle before indexing it, then provides stable
lookups for entities, entity kinds, typed incoming and outgoing references, and
resolved reference targets. Unknown entities fail closed instead of returning
an empty result that could be mistaken for “no prerequisites.”

## SQLite ruleset importer

The initial importer reads the merged `Civ5DebugDatabase.db` with SQLite
`query_only`, URI `mode=ro`, and immutable access. It requires the `Eras`,
`Technologies`, `Technology_PrereqTechs`, `Technology_ORPrereqTechs`, `Units`,
`UnitClasses`, `Unit_ClassUpgrades`, `UnitPromotions`, and
`Unit_FreePromotions` tables, plus `Policies`, `PolicyBranchTypes`, and the
policy prerequisite/disable tables, `Buildings`, `BuildingClasses`, `Resources`,
and `ResourceClasses`, plus `Civilizations`, `Leaders`, `Traits`, their mapping
tables, and civilization unit/building class overrides. It also requires
`Religions`, `Beliefs`, `Specialists`, `Civilization_Religions`, and
`Unit_GreatPersons` for the religion and great-person slice. The map slice uses
`Terrains`, `Features`, `Improvements`, `Routes`, `Yields`, `Builds`, and direct
feature/improvement validity tables.
Active package IDs come from
`DownloadableContent`; callers cannot silently relabel a BNW database as
vanilla or Gods & Kings.

It selects fixed technology and era gameplay-column allowlists rather than
copying entire rows. Every technology has a validated `belongs_to` edge to an
era entity. It also imports allowlisted gameplay values for unit types while
excluding unit AI roles, flavors, presentation assets, and prose.
Unit classes preserve global/team/player instance limits and connect units to
their class, class defaults, and class-based upgrade targets. Duplicate merged
database upgrade rows are collapsed deterministically.
Promotion entities include an explicit gameplay-effect allowlist, AND/OR
promotion prerequisites, technology prerequisites, and unit free-promotion
relationships. Presentation and hotkey fields remain excluded.
Policy and policy-branch entities include core numeric and boolean effects,
branch membership, AND/OR prerequisites, disables, era gates, and opening and
finishing policies. AI branch delay/mutual-exclusion fields and policy flavors
are excluded. Quantity-bearing effect tables that reference buildings,
improvements, yields, specialists, or unit-combat classes remain deferred until
schema-1 references can represent deterministic scalar attributes.
Building and building-class entities include core costs, maintenance, placement
constraints, instance limits, default buildings, and references to known
technology, era, policy-branch, promotion, and replacement-class targets.
Instance limits preserve the distinction among ordinary buildings, national
wonders, team wonders, and world wonders without relying on localized names.
Detailed yield/resource/specialist effect tables remain deferred until
quantity-bearing references are represented.
Resource and resource-class entities include happiness, usage, initial
quantity, map-placement rules, class membership, reveal/trade/obsolete
technologies, policy reveal, and wonder-bonus obsolescence. AI trade/objective
columns and resource flavors are excluded. Quantity-bearing unit and building
requirements remain deferred until reference attributes are added to the
knowledge schema.
Civilization entities retain only deterministic playability facts; leader
entities retain stable IDs but no personality, competitiveness, diplomacy, or
presentation attributes. Traits include an explicit allowlist of numeric and
boolean gameplay effects and typed references to existing unit classes,
technologies, and buildings. Civilization mappings connect leaders and traits,
unique units and buildings, and disabled default classes. If a merged database
contains both a null and a non-null override for the same slot, the non-null
replacement wins; multiple distinct non-null replacements are rejected. Every
non-null replacement must belong to its declared unit or building class.
Religion entities preserve stable identifiers without prose or art. Beliefs
include category flags, scalar gameplay effects, and references to known eras,
resources, and technologies. Specialists include gameplay rates and link to the
unit class they generate as a great person. Yield-, terrain-, feature-, and
improvement-dependent belief/specialist effects remain deferred until
quantity-bearing references are represented.
Terrain, feature, improvement, route, yield, and build entities contain explicit
gameplay allowlists. Direct references cover growth terrain, adjacent-unit
promotions, civilization restrictions, improvement upgrades, build unlocks and
outputs, valid terrains/features/improvements, and the trait improvement combat
bonus. Yield AI weights, graphical-only flags, prose, hotkeys, and assets are
excluded.

For reproducibility and safety it:

1. refuses a non-empty SQLite WAL;
2. detects active DLC packages and verifies the declared ruleset family;
3. hashes and sizes the source database before reading;
4. validates every scalar and boolean;
5. constructs and validates all references;
6. hashes and sizes the database again after reading; and
7. refuses the result if the source changed.

On the tested Campaign Edition cache this produces 81 technology entities,
8 era entities, 148 unit entities, 83 unit-class entities, and 214 promotion
entities. It contains 135
technology `requires_all` relations, 81 technology-to-era relations, 8 mandatory
promotion prerequisites, 134 alternative promotion prerequisites, 4 promotion
technology prerequisites, 307 unit free-promotion relations, 148 unit-class
memberships, 82 class defaults, and 105 distinct upgrade targets. The observed
technology `requires_any` table is empty.

The same tested database adds 45 civilizations, 44 leaders, 48 traits, 14
religions, 69 beliefs, 7 specialists, 9 terrains, 25 features, 29 improvements,
2 routes, 6 yields, and 35 build actions. The complete current import contains
1,296 entities and 2,259 references, including
45 civilization-to-leader, 43 leader-to-trait, 66 unique-unit, 20
unique-building, 45 disabled-unit-class, and 121 disabled-building-class
relationships. Two consecutive imports produced the same canonical bundle
hash. Six specialist types reference a great-person unit class; the installed
database's optional `Unit_GreatPersons` mapping is empty and therefore produces
no invented relationships. No generated bundle or local database is committed.

## Third-party research

Initial GitHub research found useful references but no complete dependency that
meets this project's provenance and coverage requirements:

- [Civ5-BNW-Modding-Reference](https://github.com/XIIVVIIX246/Civ5-BNW-Modding-Reference)
  documents many BNW XML tables.
- [Gedemon/Civ5-DLL](https://github.com/Gedemon/Civ5-DLL) helps explain database
  relationships and engine behavior, but contains Firaxis source with its own
  copyright notice.
- [neoddish/Civ-TechTree](https://github.com/neoddish/Civ-TechTree) provides an
  MIT-licensed technology graph, but it is incomplete for this project and its
  facts still require verification.

These repositories are references only. No files from them are vendored. The
authoritative input is the user's locally installed game data, transformed by a
reproducible importer.

## Local model assistance

A local Qwen 8B-class model may propose code, field classifications, or mapping
drafts. Its output is never authoritative data. Keep the module usable without
the model, and accept suggestions only after deterministic parsing, integrity
validation, fixtures, tests, and human or higher-capability review.
