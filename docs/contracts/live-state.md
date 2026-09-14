# Live-State Contract

Status: Evolving

## Purpose

`GameState` is the validated observation passed from bridge readers to callers
and the deterministic controller. The implementation in `models.py`,
`validation.py`, and tuner marker parser is authoritative for exact fields.

## Version status

| Schema | Evidence | Scope |
|---|---|---|
| Legacy/unversioned | Compatibility-tested | Minimal early reader |
| 2 | Live-verified | Economy, culture, research, cities, units, turn readiness |
| 3 | Compatibility-tested | Score, era, exact city progress, unit condition, met-major diplomacy, science-victory progress |
| 4 | Live-verified for early-game branches | Schema 3 fields plus unit readiness and coherent segmented collection |

## Stable requirements

- `schema_version`, when present, selects validation rules.
- Turn and active-player identity are non-negative integers.
- A schema 4 read contains all four non-header parts exactly once; each part's
  turn and active-player identity must match the header.
- Lists use stable in-game identifiers and reject duplicates where identity must
  be unique.
- Unmet major civilizations are omitted rather than disclosed.
- City rate/progress values preserve Civ V's documented times-100 integer units
  where implemented.
- Unknown/unavailable data uses the documented nullable field, not an invented
  zero.
- Non-finite numbers and malformed nested objects are rejected.

## Compatibility

Readers retain schema 2 and 3 support. A future
breaking shape change increments `schema_version`; it does not reinterpret an
existing field silently.

## Privacy

Live state can contain player, civilization, city, opponent, and match-specific
data. Do not commit real snapshots. Tests use synthetic fixtures.

## Required evidence for changes

1. Parser and validation unit tests.
2. Backward-compatibility tests for supported schemas.
3. Inspection against bundled game APIs/UI source when relevant.
4. Bounded target-machine verification before changing status to live-verified.
