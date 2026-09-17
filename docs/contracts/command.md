# Command Contract

Status: Evolving

## Envelope

A command contains:

- canonical UUIDv4 `id`;
- allowlisted action name;
- action-specific argument object.

Malformed identifiers, unknown actions, extra/invalid arguments, and unsafe
sessions are rejected before a game write.

`civ5_agent.bridge.validate_command` is the public bridge-owned argument
validator. `WatcherBridgeClient.execute_command` requires the current
`bridge_session_id`, sends only the normalized allowlisted envelope through the
private watcher socket, validates the echoed session/command identities, and
returns only a terminal `success|error` result with bounded text and validated
before/after states.

At the application boundary, a live command is associated with the current
bridge-owned `bridge_session_id`. This session metadata is distinct from the
command UUID and from any journal `match_id`. Watcher-mediated writes must echo
the identity returned by
`ping`/`read_state`; missing or changed identity is rejected before execution.
Direct commands create one identity for their single connection.

## Current allowlist

| Action | Arguments | Postcondition | Evidence |
|---|---|---|---|
| `end_turn` | none | turn number increases | Direct and compact M6 paths live-verified |
| `choose_research` | `TECH_*` identifier | selected research matches identifier | Live-verified |
| `set_city_production` | city ID, `unit\|building\|project`, matching stable ID | target city's production matches | Live-verified |
| `skip_unit` | schema 4 owned unit ID | same unit/location/movement; `ready_to_move` becomes false | Live-verified |
| `move_unit` | schema 6 owned unit ID and exact bounded `x`, `y` | same unit reaches exact destination in same active turn with lower movement | Offline-only; not released or live-verified |

Development head includes the approved M9 `move_unit` action with exact
arguments `unit_id`, `x`, and `y`. This is an unreleased offline capability,
not part of core 1.0.0 and not live-verified. It enters the released downstream
profile only after the remaining executor, offline, and bounded target-machine
gates in the [unit-movement contract](unit-movement.md) pass.

The target FireTuner accepts only bounded Lua reliably. Every internal program
is rejected before send above 1,000 UTF-8 bytes. `end_turn` additionally
requires an active turn, the game-defined `NO_ENDTURN_BLOCKING_TYPE`, no message
processing, no already-sent multiplayer turn, and `UI.CanEndTurn()` before its
sole write. Numeric zero is not the target runtime's no-blocker value.

## Result

The internal result model can represent `pending|success|error`, but the public
watcher client accepts only terminal `success|error`. It carries the command ID,
a bounded message, and before/after state where available. A successful
transport frame is not sufficient: `success` requires the action-specific
postcondition. A watcher failure after submission without a validated terminal
result is an unknown transport outcome, remains absent from terminal result
lookup, and must enter conservative recovery without retry.

## Retry behavior

For one watcher lifetime, an identical completed UUID/action/argument retry
returns the cached response marked as replayed. Reusing the UUID with different
content is rejected. An audit-write failure is reported separately and never
causes an already-executed game action to be retried.

## Security boundary

No public command accepts Lua source, host, port, predicate, or postcondition
code. Live commands must pass preflight and use the watcher-owned connection
when it is active.

## Change requirements

A new action requires a stable argument schema, internal Lua derived from stock
game behavior, explicit preconditions and postconditions, injection tests,
offline failure tests, documentation, and a bounded live experiment before it
is labeled live-verified.
