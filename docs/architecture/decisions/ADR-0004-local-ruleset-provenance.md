# ADR-0004: Generate ruleset knowledge from local sources with provenance

Status: Accepted

Date: 2026-09-13

## Context

Public Civ V repositories differ by ruleset, DLC, Mod set, completeness,
maintenance, and license. Hand-authored or model-generated facts can silently
introduce errors. The installed game already contains merged SQLite/XML ruleset
data appropriate to the user's build.

## Decision

Prefer deterministic import from the user's locally installed Civ V data.
Every generated bundle identifies its vanilla/G&K/BNW family, DLC/Mod set, game
version, relative source labels, sizes, and SHA-256 hashes. Importers use
explicit gameplay-field allowlists, preserve stable identifiers and typed
relations, and validate referential integrity.

Third-party repositories are prior art unless license, provenance, ruleset,
completeness, and maintenance have been recorded and permit reuse.

## Consequences

- Generated datasets can be reproduced from known local inputs.
- The repository does not need to redistribute game databases or assets.
- Import output is ruleset-specific rather than universal.
- Importers must fail on unsupported schemas, live WAL state, changing sources,
  and broken relationships.

## Alternatives considered

- Copy a third-party dataset: rejected as the default because provenance and
  compatibility cannot be assumed.
- Hand-author facts: rejected as authoritative data; acceptable only for test
  fixtures clearly separated from generated output.
- Use a local or cloud model as source of truth: rejected.

## Supersedes

None.
