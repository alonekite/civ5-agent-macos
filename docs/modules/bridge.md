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
- Schema 6 is collected as bounded header/city/unit/diplomacy/victory/technology/
  move-target programs; every part must identify the same turn and active
  player. Schemas 2–5 remain readable.
- Schema 7 adds bounded worker-context and worker-build segments without
  changing selection. Parsing, validation, public limits, legacy compatibility,
  and the repaired 688/881-byte generated reads are implemented offline. Two
  target attempts safely stopped before any write: the first exposed indexed
  action-table enumeration, and the second exposed numeric `luaL_optint`
  `CanBuild` flags. Both repairs have regression coverage, and a new bounded
  target attempt remains required.
- Every successful write includes a proved postcondition.
- Every FireTuner Lua program is at most 1,000 UTF-8 bytes; oversized programs
  fail before transport contact.
- End-turn readiness compares the game-defined no-blocker enum in Lua and the
  verified target-build `NO_END_TURN_BLOCKING_TYPE` value in parsed-state
  consumers; UI clickability alone is insufficient.
- Malformed, oversized, transient, and closing-state responses are bounded.

## Failure modes

Unsafe session, missing in-game Lua state, malformed snapshot, blocked action,
transport closure, verification timeout, audit failure, and duplicate-ID misuse
are distinct errors where their recovery semantics differ. Supported callers
can catch `ValidationError`, `ProtocolError`, `TransportError`, or `SafetyError`
from the aggregate API. A malformed result after submitting a write is
transport-ambiguous and must enter recovery rather than deterministic rejection.
The watcher records and command-UUID-caches that uncertainty without presenting
it as a terminal result or allowing an identical request to execute again.

## Security and privacy

FireTuner is unauthenticated and binds broadly on the tested build. Follow
`SECURITY.md`; never leave it enabled, forward the port, or expose a general Lua
API. Local broker and audit files use private permissions.

## Verification

Read, end turn, research selection, city production, schema 4 early-game state,
schema 5 ordinary technology state, and the game-side effect of unit skip have
target-machine evidence. Schema 6 ordinary movement targets have parser,
validation, legacy compatibility, privacy, Lua-bound, and bounded target-machine
evidence. The offline suite covers framing, segmented-snapshot
consistency, validation, IPC bounds, generated action code, retries, and
postconditions. The schema 6 movement write has offline pre-admission,
game-side guard, Lua-bound, and exact-postcondition coverage plus one bounded
target-machine success and safe negative rejection. See the
verification matrix.

## Current limitations

Schema 5 free-technology and steal-technology modes remain offline-only. Schema
4's non-empty diplomacy and late-game victory branches remain unverified.
The schema 6 read model and coordinate movement write are target-verified and
part of the 1.1.0 compatibility surface. The standalone legacy command CLI
still has a direct fallback; the supported Python bridge client is watcher-only.

## Planned extensions

Maintain the 1.1.0 movement contract. M10 C1–C5 implement the schema 7 reads,
exact `worker_build` admission, single stock dispatch, factual read-back,
executor integration, and complete offline gate on the unreleased development
head. C6 now confirms read/UI agreement and stale-source rejection, while
successive no-retry attempts exposed target-specific iterator, flag, lexical,
action-resolution, and entry-ID-versus-loop-index details without changing game
state. Numeric-index stock dispatch is repaired offline; a verified write
postcondition still requires fresh bounded C6 evidence. Optional evidence for
other branches remains separate.
The session envelope and public error semantics have offline
tests; M5/M6 composition must preserve their fail-closed behavior.
