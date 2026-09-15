# Module: bridge

Status: Implemented

## Responsibility

The bridge owns transport, validated live-state reads, action argument checks,
internally generated Lua for allowlisted actions, and write-after-read
verification. `tuner.py` is the verified live adapter; `storage.py` is the
database-backed fallback reader; `models.py` and `validation.py` define shared
live contracts.

## Non-responsibilities

- Ruleset facts and strategic interpretation.
- Controller policy.
- Arbitrary caller-supplied Lua.
- Working memory, strategic memory, or LLM interaction.
- Changing the firewall or enabling FireTuner automatically.

## Public interface

The abstract direction is represented by `GameBridge.read_state()` and
`GameBridge.execute(command)`. Current CLIs also use the concrete watcher broker
and FireTuner client while the public API remains pre-stable.

See [live-state](../contracts/live-state.md) and
[command](../contracts/command.md).

## Dependencies

The bridge may depend on shared models, validation, preflight, transport, and
local IPC. It must not depend on controller policy or ruleset knowledge.

## Invariants

- Only `127.0.0.1:4318` is accepted for the verified FireTuner adapter.
- Live use fails closed unless the safety preflight passes.
- One watcher owns the game connection and serializes requests.
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
Coordinate movement is not implemented. The abstract public interface is not
yet the only path used by CLI code.

## Planned extensions

Complete pending live checks, add only narrowly specified actions, and hide
transport details behind the M7 public API.
