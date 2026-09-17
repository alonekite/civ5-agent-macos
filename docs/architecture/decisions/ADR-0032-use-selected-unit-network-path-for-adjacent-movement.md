# ADR-0032: Use the selected-unit network path for adjacent movement

Status: Accepted

Date: 2026-09-17

## Context

The tactical consumer needs a reusable movement mechanic, but this core must
not choose units, destinations, routes, or alternatives. Movement is unusually
risky because Civ V dispatches human-unit missions through selection-sensitive,
deferred game messaging. A Lua call returning does not prove which unit moved,
whether a route was accepted, or whether a special mechanic such as attack,
swap, or embarkation occurred.

Installed Brave New World UI code performs ordinary right-click movement with
`Game.SelectionListMove` after operating on the selected unit. The installed
binary contains the corresponding selection and movement symbols and warns
about direct human-unit `PushMission` calls outside a network message. Public
released SDK source corroborates that `selectionListMove` sends a network
mission for the head-selected active-player unit, while the direct Lua
`PushMission` binding bypasses that requirement. The SDK source is supporting
design evidence, not proof of the target macOS runtime.

The same source makes broad pre-validation unsafe: its Lua `GeneratePath`
binding is not implemented, and its `CanMoveOrAttackInto` binding returns an
unassigned false value. `CanMoveThrough` is usable supporting evidence but does
not alone enforce destination stacking.

## Decision

The first `move_unit` capability will accept only an explicit active-player
unit identity and one exact adjacent destination supplied by the caller. The
core will not calculate a route or choose another plot.

The initial supported subset is ordinary non-combat movement to a currently
visible, empty, non-city plot. It excludes attacks, civilian capture, swaps,
air movement, embarkation, disembarkation, automation, queued missions,
multi-step paths, and any move that requires declaring war or accepting a UI
prompt. Exact argument and result schemas remain owned by the contracts added
in the next documentation batch.

Admission will fail closed unless a fresh live read establishes at least:

- the requested unit exists, belongs to the active player, is not busy, and is
  ready with movement remaining;
- the unit is neither air-domain nor embarked;
- source and target exist, differ, and have plot distance exactly one;
- the target is visible to the active team, is not a city, and has no units;
- the move does not cross the land/water boundary; and
- the unit's stock `CanMoveThrough(target)` predicate succeeds without
  declaration-of-war semantics.

Submission will establish the exact unit as the UI head selection with
`UI.SelectUnit(unit)`, immediately verify `UI.GetHeadSelectedUnit()` identifies
that same unit, and then call
`Game.SelectionListMove(target, false, false, false)`. UI selection is an
accepted, visible side effect of this stock path. The core will not use direct
`unit:PushMission`, attempt a preliminary move, or restore selection through a
second game-side command.

Success requires a bounded fresh-state poll that finds the same unit identity,
owner, and type at the exact destination. A return marker, changed selection,
mission queue, or reduced movement alone is insufficient. Rejection, unchanged
state, disappearance, transformation, combat, unexpected displacement,
timeout, or post-submission transport ambiguity is not success. An uncertain
outcome is never retried automatically and follows ADR-0028 recovery semantics.

The read model may expose only active-player-visible facts needed to evaluate
this bounded mechanic. It must not reveal hidden plots, infer a route, or
publish a tactical recommendation. The capability remains absent from the
released downstream profile until offline and target-machine verification pass.

## Consequences

- The command follows the game's ordinary network-backed human-unit path
  instead of creating a second mission-dispatch mechanism.
- Adjacent-only movement yields one exact, promptly observable postcondition
  and keeps route decomposition in the tactical layer.
- Empty non-city targets deliberately reject legal swaps, friendly-city entry,
  combat, captures, and stacking edge cases in the first release.
- Exact selection verification reduces wrong-unit risk but does not eliminate
  asynchronous UI or game-state drift; the live test must exercise this path.
- A future broader movement capability requires a new evidence-backed contract
  and, when it changes this boundary, a superseding ADR.

## Alternatives considered

- Call `unit:PushMission(MISSION_MOVE_TO, ...)`: rejected because human-unit
  missions are expected to arrive through network-message dispatch.
- Call `SelectionListGameNetMessage` directly: rejected for the first slice
  because `SelectionListMove` is the stock higher-level movement entry point
  and retains the game's swap/move dispatch logic behind a narrower interface.
- Use `GeneratePath` or `CanMoveOrAttackInto` as authoritative admission:
  rejected because the inspected released Lua bindings are respectively
  unimplemented and defective.
- Accept arbitrary destinations and verify eventual route progress: rejected
  because partial movement and deferred mission continuation do not provide the
  first slice's exact bounded postcondition.
- Publish all adjacent map state and let the core rank legal moves: rejected
  because hidden-state exposure and tactical selection are outside this core.

## Supersedes

None. This applies ADR-0003, ADR-0028, and ADR-0031 to unit movement.
