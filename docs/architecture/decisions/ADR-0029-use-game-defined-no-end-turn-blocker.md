# ADR-0029: Use the game-defined no-end-turn blocker

Status: Accepted

Date: 2026-09-16

## Context

The second bounded M5/M6 target-machine attempt delivered the compact
`end_turn` Lua intact and received a command marker, but rejected a visibly
ready turn because ADR-0028 had assumed that numeric blocker zero meant no
blocker. The target Campaign Edition runtime returned `-1`.

The bundled Brave New World `ActionInfoPanel.lua` and tutorial Lua compare
`Player:GetEndTurnBlockingType()` with
`EndTurnBlockingTypes.NO_ENDTURN_BLOCKING_TYPE`; they do not assume zero. The
same live attempt also showed that the stock Next Turn click can reveal a unit
still needing orders without advancing the turn, so button text alone is not a
verified postcondition.

## Decision

- The live Lua write guard compares directly with the game's
  `EndTurnBlockingTypes.NO_ENDTURN_BLOCKING_TYPE` symbol.
- The parsed target-build value is exposed as
  `NO_END_TURN_BLOCKING_TYPE = -1` for factual requirement inspection and
  public consumers of the numeric live-state field.
- Requirement inspection reports an end-turn blocker whenever the reported
  value is not the no-blocker value, independently of `UI.CanEndTurn()`.
- `end_turn` remains successful only after a later validated snapshot proves
  that the turn number increased. Revealing a unit or other requirement in the
  same turn is a verified failed action, not success and not grounds for retry.

## Consequences

- The compact action retains its sub-one-KiB transport bound while matching the
  stock target UI's named enum semantics.
- A plan cannot be declared ready merely because the UI control is clickable
  while the game reports a blocker.
- Target builds with different parsed enum values require separate evidence;
  the Lua-side symbolic comparison remains authoritative.
- A further guarded live attempt is still required to prove automatic turn
  advance through M6.

## Alternatives considered

- Change the hard-coded value from zero to `-1` only in Lua: rejected because
  the game already supplies a named symbol and Python requirement inspection
  must use the same target-build meaning.
- Trust only `UI.CanEndTurn()` or the visible button label: rejected because
  both can represent an actionable requirement rather than a guaranteed turn
  advance.
- Treat an unchanged turn after `Game.DoControl` as success: rejected because
  the command contract requires observed turn advancement.

## Supersedes

This supersedes only ADR-0028's numeric zero-blocker assumption. ADR-0028's
transport bound and unknown-outcome decisions remain accepted.
