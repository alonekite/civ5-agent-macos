# Unit-Movement Contract

Status: Schema 6 read and bounded write implemented offline; not live-verified

Expected compatibility release: 1.1.0

## Purpose

Define the first strategy-neutral coordinate movement capability without giving
the execution core route choice, tactical policy, or a second write path. The
caller selects one active-player unit and one exact destination from fresh
state. The bridge remains the sole authority for admission, submission, and
write-after-read verification.

This contract applies ADR-0032. It does not advertise movement in the current
1.0.0 capability profile.

## Live-state input

M9 schema 6 is implemented offline. It retains every schema 5 field and adds the
following required field to every owned-unit record:

```json
"ordinary_move_targets": [{"x": 12, "y": 8}]
```

The field is a list of zero to six exact coordinate objects. Each object has
only `x` and `y`; both are non-negative integers no greater than 65,535.
Targets are sorted by `(x, y)` and contain no duplicates. An empty list means
that the bridge currently exposes no movement in this deliberately narrow
subset; it does not mean the unit has no legal Civ V mission of any kind.

A listed target is an active-player-visible observation computed from the same
conservative predicate used by command admission. At collection time:

- the active turn is live and the unit is owned, ready, not busy, not
  automated, not delayed-death, non-air, not embarked, and has movement left;
- the target exists at plot distance one, is currently visible to the active
  team, is empty, and is not a city;
- source and target have the same land/water classification; and
- `unit:CanMoveThrough(target)` returns true.

The list excludes attacks, civilian captures, swaps, city entry, air movement,
embarkation, disembarkation, declaration-of-war prompts, automation, and paths
longer than one plot. It exposes neither hidden plots nor route, score, threat,
purpose, or recommendation data.

Schema 2–5 readers remain supported with their existing meaning. They do not
gain an optional movement field and cannot admit `move_unit`.

## Command

The allowlisted command is:

```json
{
  "action": "move_unit",
  "args": {"unit_id": 7, "x": 12, "y": 8}
}
```

`unit_id`, `x`, and `y` must be integers, not booleans. The unit ID is
non-negative; each coordinate is between 0 and 65,535 inclusive. The argument
object has exactly those three fields. A command UUID and bridge-session
identity retain their existing contracts.

Before generating or sending Lua, the Python bridge requires a fresh schema 6
state, finds exactly one owned unit with `unit_id`, and requires `(x, y)` to be
present in that unit's `ordinary_move_targets`. Missing, stale, malformed, or
legacy state is rejection, not permission to probe the game.

The single bounded Lua program then re-resolves the active player, exact unit,
source plot, and target plot, rejects any change from the Python-observed source
coordinates, and repeats the contract predicate. It clears the
selection, selects only that unit, and confirms the head-selected unit ID
before calling `Game.SelectionListMove(target, false, false, false)`. It does
not call `PushMission`, queue a mission, choose another unit/target, restore the
old selection, or retry.

The command marker distinguishes only bounded factual submission outcomes such
as accepted, invalid unit/target, blocked predicate, or selection failure. A
marker is never proof that movement succeeded.

## Success postcondition

The bridge polls fresh validated state within the existing caller-supplied
verification timeout. Success requires all of the following in one schema 6
after-state:

- bridge session, turn, active player, and active-turn status are unchanged;
- exactly one owned unit retains the requested ID and its before-state type;
- that unit moved from its exact before coordinates to exactly `(x, y)`;
- its movement points are strictly lower than before; and
- the complete after-state passes schema validation.

Selection state, a command marker, a mission queue, readiness change, animation,
or any other unit's movement cannot substitute for this proof.

Explicit pre-send rejection returns an error without a game write. A terminal
marker followed by unchanged coordinates, unexpected coordinates, unchanged or
increased movement, disappearance, transformation, turn change, combat,
capture, embarkation, timeout, or malformed read-back is a failed verification.
Loss of transport after submission without a terminal validated result is an
unknown outcome under ADR-0028 and requires recovery; it is never retried
automatically.

## TurnPlan behavior

TurnPlan schema 1 may contain `move_unit` after the 1.1.0 action addition; the
plan schema number does not change because `action` is an existing extensible
allowlist field and older 1.0 packages reject the unknown action. A compatible
consumer must therefore check package version and `ALLOWED_ACTIONS`, not only
the TurnPlan schema number.

A `move_unit` action covers a factual `unit_orders` requirement only for its
exact `unit_id`. It may appear before the final `end_turn` and may repeat for
the same unit with distinct command UUIDs and explicit destinations. Before
each step, normal state-basis continuity and fresh bridge admission apply. If a
unit remains ready and no remaining `move_unit` or `skip_unit` covers it, the
executor pauses; it never invents an additional destination or skip.

Unexpected movement is terminal failure. Recovery of an uncertain non-final
movement uses the existing conservative rule: validate cached result and fresh
state, then pause before the next action rather than continuing automatically.

## Ownership and privacy

The tactical layer owns the unit, destination, route decomposition, purpose,
ordering, and replanning. The core owns only visible candidate facts, exact
argument validation, live legality checks, bounded dispatch, and factual result
classification. Journal records may preserve the private command lifecycle but
never authorize another move.

Real snapshots, coordinates, plans, UUIDs, and match facts remain private and
must not be committed. Fixtures use synthetic coordinates and identities.

## Evidence gate

Parser/validation, legacy-schema, target ordering/bounds/privacy, read-only Lua,
command arguments, repeated game-side guards, 1,000-byte pre-send bound, exact
postcondition, rejection, unexpected-state, and timeout tests pass offline.
Executor requirement coverage, ordered multi-move continuity, factual events,
watcher forwarding, journal composition, CLI/API compatibility, and conservative
cached recovery also pass offline. The full offline matrix is reconciled.
Remaining support requires the bounded target-machine procedure in the
live-test checklist.
Until that evidence passes, documentation and the downstream profile must call
the capability planned or absent, never supported or live-verified.
