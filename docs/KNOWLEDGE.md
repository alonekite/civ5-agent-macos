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

A knowledge bundle contains:

- `ruleset`: vanilla, Gods & Kings, or Brave New World; exact game version; and
  sorted DLC and mod identifiers.
- `sources`: canonical relative paths, byte sizes, and lowercase SHA-256 hashes.
- `entities`: a lower-snake-case kind, stable uppercase game `Type` identifier,
  gameplay attributes, and one or more source paths.
- `references`: typed, source-backed edges between entities. Schema 2 references
  additionally contain an `attributes` object for deterministic quantities and
  modifiers attached to the edge.

Serialization sorts sources, entities, references, and JSON object keys. The
bundle hash is therefore independent of importer query order. Loading is strict:
unknown fields, duplicate entities or references, dangling references, invalid
paths, invalid identifiers, unsupported value types, non-finite numbers, and AI
parameter fields are rejected.

Schema 1 remains readable and serializes references without `attributes`.
Schema 1 in-memory references must have empty attributes. Schema 2 introduced
reference attributes, which use the same strict JSON and finite-number rules as
entity attributes. See
[ADR-0007](architecture/decisions/ADR-0007-reference-attributes.md).

Schema 3 adds a sorted `context` array to references. Each context item has a
semantic role and a typed entity identifier; context entities must exist and
the complete context participates in reference identity. This permits multiple
otherwise-identical edges whose effects apply under different technologies,
policies, terrain, features, resources, or other typed conditions. Schema 1 and
2 cannot contain context and retain their existing canonical JSON shapes. The
current importer emits schema 3. See
[ADR-0008](architecture/decisions/ADR-0008-contextual-reference-identity.md).

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
`Terrains`, `Features`, `FakeFeatures`, `Improvements`, `Routes`, `Yields`,
`Builds`, direct feature/improvement validity tables, and selected binary
quantity tables. Projects, processes, and victory rules use `Projects`,
`Processes`, `Victories`, their prerequisite and threshold tables, production
conversion yields, and resource requirements.
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
relationships. Unit-combat entities connect units and applicable promotions to
their combat categories. Domain and special-unit entities replace otherwise
unvalidated unit classification strings with typed relationships while the
legacy scalar attributes remain available. Buildings, policies, traits, and
promotions preserve category-specific experience, production, maintenance,
movement, and combat modifiers; trait free promotions use typed unit-combat
context. Promotion relations also preserve combined domain, feature, terrain,
and unit-class attack, defense, movement, impassability, and general combat
modifiers. A separate typed technology context records when an otherwise
impassable feature or terrain becomes passable. Presentation, Pedia grouping,
and hotkey fields remain excluded.
Policy and policy-branch entities include core numeric and boolean effects,
branch membership, AND/OR prerequisites, disables, era gates, and opening and
finishing policies. AI branch delay/mutual-exclusion fields and policy flavors
are excluded. Single-context policy effects preserve building-class or
improvement conditions as typed context; effects requiring more than one
condition remain deferred.
Building and building-class entities include core costs, maintenance, placement
constraints, instance limits, default buildings, and references to known
technology, era, policy-branch, promotion, and replacement-class targets.
Instance limits preserve the distinction among ordinary buildings, national
wonders, team wonders, and world wonders without relying on localized names.
Single-context building effects preserve building-class, feature, resource,
specialist, or terrain conditions. Binary building effects include local,
area, and global yield changes and modifiers, population/religion scaling, and
resource quantities and requirements. Multi-context building effects and
effects needing new target entity families are deferred.
Building theming alternatives have no stable row identifier, so they are stored
as a canonically sorted `theming_bonuses` array on the owning building. Each
entry contains the integer bonus and explicit era, work-kind, owner, and player
constraints. Null source booleans normalize to false; duplicate normalized
rules fail. The localized `Description` and `AIPriority` columns are not read.
Resource and resource-class entities include happiness, usage, initial
quantity, map-placement rules, class membership, reveal/trade/obsolete
technologies, policy reveal, and wonder-bonus obsolescence. AI trade/objective
columns and resource flavors are excluded. Quantity-bearing unit and building
requirements are represented as attributed references.
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
unit class they generate as a great person. Belief yield effects conditioned by
building class, feature, improvement, resource, or terrain use typed context.
Remaining specialist and more complex belief effects are deferred.
Terrain, feature, improvement, route, yield, and build entities contain explicit
gameplay allowlists. `FakeFeatures` supplies stable lake and river identifiers;
they are represented as feature entities with `fake: true`. The importer does
not read the fake-feature `Movement` column because the official database stores
localized text in that nominally integer column. Direct references cover growth
terrain, adjacent-unit promotions, civilization restrictions, improvement
upgrades, build unlocks and outputs, valid terrains/features/improvements, and
the trait improvement combat bonus. Attributed binary relations cover base and
conditional terrain, feature, improvement, and route yields, improvement
yield-per-era values, route technology movement changes, and build technology
time changes. Contextual imports cover improvement yield changes conditioned by
resource or route and technology-enabled base, fresh-water, and no-fresh-water
changes, as well as the single-context belief, building, and policy effects
described above. Binary effects also cover beliefs, policies, buildings,
resources, specialists, and unit/building resource quantities. Projects retain
instance limits, cost, deterministic flags, technology and victory gates,
project prerequisites, resource requirements, and victory thresholds. Processes
retain technology gates and production-conversion percentages. Victory entities
retain deterministic conditions while excluding prose, movies, and audio.
Yield AI weights,
graphical-only flags, prose, hotkeys, and assets are excluded.

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
religions, 69 beliefs, 7 specialists, 9 terrains, 25 ordinary features, 2 fake
features, 29 improvements, 2 routes, 6 yields, 35 build actions, 6 projects, 5
processes, 5 victory types, 14 unit-combat categories, 5 domains, 4 special
unit categories, 2 hurry methods, 4 great-work classes, 3 great-work slot types,
279 great works, and 6 artifact classes. The complete current import contains
1,631 entities and 4,876
references, including 148 unit-domain, 22 special-unit, and 323 additional typed
unit-identifier relationships; 646 binary attributed references from 84
single-value table families, four multi-attribute promotion families, and
project victory thresholds; 213 contextual references, including typed
technology-conditioned promotion passability; and
45 civilization-to-leader, 43 leader-to-trait, 66 unique-unit, 20
unique-building, 45 disabled-unit-class, and 121 disabled-building-class
relationships. Two consecutive imports produced the same canonical bundle
hash. Six specialist types reference a great-person unit class; the installed
database's optional `Unit_GreatPersons` mapping is empty and therefore produces
no invented relationships. No generated bundle or local database is committed.

Fourteen additional plain table families contribute 253 of those relationships:
belief faith-purchase eligibility; building class and local-resource
prerequisites; policy free promotions; resource feature and terrain placement;
trait training restrictions; promotion civilian-unit applicability and random
post-combat upgrades; and unit building-class prerequisites and build actions.
Quantified coverage additionally preserves building-class happiness, culture,
tourism, and production effects; domain experience and production; free units;
building prerequisite counts; adjacent-mountain yields; technology trade-route
range; trait yield and resource modifiers; and yields from unit kills. Trait
yield changes conditioned on an improvement, specialist, or unimproved feature
use typed context.
Sixty-eight improvement/resource rules retain their four related validity,
trade, discovery, and quantity attributes on one edge. The observed technology-
enhanced building yield is joined to `Buildings.EnhancedYieldTech`; an effect
without that declared technology is rejected instead of treated as unconditional.
Two hurry methods retain deterministic production, population, science, and
culture conversion rates. Their building and policy cost modifiers are typed
quantity references; descriptions remain excluded.
Great-work class-to-slot and building-to-slot relationships add 24 typed links.
This slice deliberately excludes individual work titles, descriptions, icons,
images, quotes, and audio.
Great works preserve stable IDs and the archaeology-only flag, with 279 class,
24 era, 30 artifact-class, 233 creator-unit, and one free-building relationship.
The `Unit_UniqueNames.UniqueName` column is not read; only its typed unit/work
mapping is imported.
Ten buildings own 21 validated theming alternatives in the tested database.
They change entity attributes rather than entity/reference counts, and two
consecutive imports remain byte-identical.

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
