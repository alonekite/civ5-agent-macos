# Module: bridge

Status: Implemented

## Responsibility

The bridge owns transport, validated live-state reads, action argument checks,
internally generated Lua for allowlisted actions, and write-after-read
verification. `WatcherBridgeClient` is the supported live application adapter
over the watcher-owned private socket; `tuner.py` remains its internal game
transport. `storage.py` is the partial database-backed fallback reader;
`models.py`, `actions.py`, and `validation.py` define shared live contracts.

## Non-responsibilities

- Ruleset facts and strategic interpretation.
- Turn planning or executor orchestration.
- Arbitrary caller-supplied Lua.
- Working memory, strategic memory, or LLM interaction.
- Changing the firewall or enabling FireTuner automatically.

## Public interface

`civ5_agent.bridge` exports a runtime-checkable `Bridge` protocol,
`WatcherBridgeClient`, shared state/command/result models, the action allowlist,
and `validate_command`. Reads return the current bridge-session identity with a
validated state. Writes and read-only completed-result lookups require that
identity and a validated `Command`, and accept only a matching terminal result.
The client never opens FireTuner directly.

See [live-state](../contracts/live-state.md) and
[command](../contracts/command.md).

## Dependencies

The bridge may depend on shared models, validation, preflight, transport, and
local IPC. It must not depend on turn-executor orchestration, plan production,
or ruleset knowledge.

## Invariants

- Only `127.0.0.1:4318` is accepted for the verified FireTuner adapter.
- Live use fails closed unless the safety preflight passes.
- One watcher owns the game connection and serializes requests.
- The connection owner issues one `bridge_session_id` per connection epoch;
  it never presents that value as a permanent save or match identifier.
- Schema 5 is collected as bounded header/city/unit/diplomacy/victory/technology
  programs; every part must identify the same turn and active player. Schemas
  2–4 remain readable.
- Every successful write includes a proved postcondition.
- Malformed, oversized, transient, and closing-state responses are bounded.

## Failure modes

Unsafe session, missing in-game Lua state, malformed snapshot, blocked action,
transport closure, verification timeout, audit failure, and duplicate-ID misuse
are distinct errors where their recovery semantics differ.

## Security and privacy

FireTuner is unauthenticated and binds broadly on the tested build. Follow
`SECURITY.md`; never leave it enabled, forward the port, or expose a general Lua
API. Local broker and audit files use private permissions.

## Verification

Read, end turn, research selection, city production, schema 4 early-game state,
schema 5 ordinary technology state, and the game-side effect of unit skip have
target-machine evidence. The offline suite covers framing, segmented-snapshot
consistency, validation, IPC bounds, generated action code, retries, and
postconditions. See the verification matrix.

## Current limitations

Schema 5 free-technology and steal-technology modes remain offline-only. Schema
4's non-empty diplomacy and late-game victory branches remain unverified.
Coordinate movement is not implemented. The standalone legacy command CLI still
has a direct fallback; the supported Python bridge client is watcher-only.

## Planned extensions

Complete pending live checks, add only narrowly specified actions, and finish
the M7 exception and compatibility contract. The session envelope has offline
tests; M5/M6 composition must preserve its fail-closed behavior.
