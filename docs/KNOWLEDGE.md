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

## SQLite technology importer

The initial importer reads the merged `Civ5DebugDatabase.db` with SQLite
`query_only`, URI `mode=ro`, and immutable access. It requires the `Eras`,
`Technologies`, `Technology_PrereqTechs`, and `Technology_ORPrereqTechs` tables.
It selects fixed technology and era gameplay-column allowlists rather than
copying entire rows. Every technology has a validated `belongs_to` edge to an
era entity.

For reproducibility and safety it:

1. refuses a non-empty SQLite WAL;
2. hashes and sizes the source database before reading;
3. validates every scalar and boolean;
4. constructs and validates all technology references;
5. hashes and sizes the database again after reading; and
6. refuses the result if the source changed.

On the tested Campaign Edition cache this produces 81 technology entities,
8 era entities, 135 `requires_all` relations, and 81 `belongs_to` relations.
The observed `requires_any` table is empty.

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
