# Live-State Contract

Status: Evolving

## Purpose

`GameState` is the validated observation passed from bridge readers to callers,
requirement inspection, and deterministic execution. The implementation in `models.py`,
`validation.py`, and tuner marker parser is authoritative for exact fields.

## Version status

| Schema | Evidence | Scope |
|---|---|---|
| Legacy/unversioned | Compatibility-tested | Minimal early reader |
| 2 | Live-verified | Economy, culture, research, cities, units, turn readiness |
| 3 | Compatibility-tested | Score, era, exact city progress, unit condition, met-major diplomacy, science-victory progress |
| 4 | Live-verified for early-game branches | Schema 3 fields plus unit readiness and coherent segmented collection |
| 5 | Live-verified for ordinary research | Schema 4 plus researched/researchable technology sets and research-choice mode; free/steal modes remain offline-only |
| 6 | Live-verified; added in 1.1.0 | Schema 5 plus bounded per-unit `ordinary_move_targets` |
| 7 | Implemented offline on development head; target evidence pending | Schema 6 plus current unit-plot context, current build, and bounded ordinary worker-build candidates |

## Stable requirements

- `schema_version`, when present, selects validation rules.
- Turn and active-player identity are non-negative integers.
- A schema 4 read contains all four non-header parts exactly once; schema 5 adds
  a mandatory `technologies` part, and schema 6 adds a mandatory
  `move_targets` part. Schema 7 adds mandatory `worker_context` and
  `worker_builds` parts. Each part's turn and active-player identity must match
  the header.
- Lists use stable in-game identifiers and reject duplicates where identity must
  be unique.
- Unmet major civilizations are omitted rather than disclosed.
- City rate/progress values preserve Civ V's documented times-100 integer units
  where implemented.
- Unknown/unavailable data uses the documented nullable field, not an invented
  zero.
- Non-finite numbers and malformed nested objects are rejected.

## Schema 5 technology state

- `researched_technologies` is the stable-sorted, duplicate-free list of
  `TECH_*` identifiers for which the active player's team reports `IsHasTech`.
- `researchable_technologies` is the stable-sorted, duplicate-free list produced
  by the active player's live `CanResearch` capability. During a free-technology
  choice it is additionally filtered by `CanResearchForFree`.
- A technology cannot appear in both lists, and the current research cannot
  already be researched.
- For `normal` mode, `research_choice.required` is true exactly when the active
  player has no current research and at least one researchable technology. It
  is deliberately independent of the single end-turn blocking type because
  production or unit orders can temporarily take precedence over an unselected
  ordinary technology.
- `research_choice.mode` is `free_technology` for the game's free-tech blocker
  and `unsupported` for the steal-tech blocker; those special blockers override
  the ordinary current-research rule. Otherwise the mode is `normal`. A
  non-required choice must use `normal`.
- Validation rejects a normal choice whose `required` value disagrees with the
  presence or absence of the current `research` record.
- The current requirement inspector never auto-executes `free_technology` or
  `unsupported`; both produce `manual_required`. Future M6 execution requires
  every action to be explicit in a TurnPlan.

## Compatibility

Schema 6 requires each unit to carry zero to six sorted, unique coordinate
objects in `ordinary_move_targets`. The exact conservative meaning, coordinate
bounds, privacy limit, and legacy behavior are defined by the
[unit-movement contract](unit-movement.md). It is not a general pathing or map
schema.

Collection uses a seventh independently bounded read-only Lua segment. All
seven parts must identify the same turn and active player.

Readers retain schema 2–6 support. A future
breaking shape change increments `schema_version`; it does not reinterpret an
existing field silently.

## Frozen schema 7 worker state

Schema 7 requires every unit to carry an exact `current_plot` object, nullable
`current_build_type`, and zero to 32 sorted `ordinary_build_actions`. Candidate
objects bind one stable `BUILD_*` to its exact resulting `IMPROVEMENT_*`.
Identifiers are prefix-validated and limited to 64 characters. Resources are
looked up for the active team so hidden resources remain `null`.

The complete field shape, ordinary-build predicate, null meanings, candidate
ordering, privacy boundary, and command relationship are frozen by the
[worker-build contract](worker-build.md). Schema 7 parsing, validation, bounded
reads, and public limits are implemented and covered offline on development
head. They are not live-verified and are not part of the stable 1.1.0 profile.

Collection uses two additional independently bounded read-only Lua segments,
688 and 881 UTF-8 bytes in the current generator, for nine total schema 7
segments. Schema 2–6 compatibility remains unchanged. Existing `move_unit`
admission and executor verification accept matching schema 6+ states so the
schema extension does not disable the released movement action.

## Session metadata

Schemas 2–7 do not expose a stable save or match identifier, and their state
payload does not contain the bridge connection epoch. Per ADR-0017, the bridge
now attaches a separate `bridge_session_id` beside the unchanged payload rather
than pretending that mutable state fields identify a match. M6 targets that
session identity; M5 separately owns its future `match_id`. See the
[session and match identity contract](session-identity.md).

## Privacy

Live state can contain player, civilization, city, opponent, and match-specific
data. Do not commit real snapshots. Tests use synthetic fixtures.

## Required evidence for changes

1. Parser and validation unit tests.
2. Backward-compatibility tests for supported schemas.
3. Inspection against bundled game APIs/UI source when relevant.
4. Bounded target-machine verification before changing status to live-verified.
