# Command Contract

Status: Evolving

## Envelope

A command contains:

- canonical UUIDv4 `id`;
- allowlisted action name;
- action-specific argument object.

Malformed identifiers, unknown actions, extra/invalid arguments, and unsafe
sessions are rejected before a game write.

## Current allowlist

| Action | Arguments | Postcondition | Evidence |
|---|---|---|---|
| `end_turn` | none | turn number increases | Live-verified |
| `choose_research` | `TECH_*` identifier | selected research matches identifier | Live-verified |
| `set_city_production` | city ID, `unit\|building\|project`, matching stable ID | target city's production matches | Live-verified |
| `skip_unit` | schema 4 owned unit ID | same unit/location/movement; `ready_to_move` becomes false | Live-verified |

Coordinate movement is not implemented and is not part of the allowlist.

## Result

The result carries the command ID, `pending|success|error` status, a bounded
message, and before/after state where available. A successful transport frame
is not sufficient: `success` requires the action-specific postcondition.

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
