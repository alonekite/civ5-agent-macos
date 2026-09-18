# ADR-0034: Use integer option flags for Campaign Edition `CanBuild`

Status: Accepted

Date: 2026-09-19

## Context

ADR-0033 selected `unit:CanBuild(plot, build_id, bTestVisible, bTestGold)` as
the selection-free legality predicate for ordinary worker builds. Its examples
used Lua booleans for the two option flags.

The second bounded C6 attempt proved that the target Campaign Edition runtime
does not accept a Lua boolean for the third explicit argument. Schema 7 stopped
at its read-only gate with a type error before producing a complete snapshot;
no command or game write ran, and the guarded session restored exactly.

The previously recorded Expansion 2 SDK source at commit
`aa29e80751f541ae04858b6d2a2c7dcca454201e` defines
`CvLuaUnit::lCanBuild` with `luaL_optint` for both option flags. Their defaults
are `0` for `bTestVisible` and `1` for `bTestGold`. This explains the target
runtime error and supplies a deterministic representation without changing the
underlying `CvUnit::canBuild` semantics.

## Decision

Every generated Campaign Edition Lua call to the worker-build legality binding
will use:

```lua
unit:CanBuild(plot, build_id, 0, 1)
```

The same integer flags are required in both selection-free candidate collection
and the game-side pre-submit recheck. Tests must assert the integer form and
reject regression to the boolean form.

This decision changes only the Lua binding representation. It does not change
ADR-0033's visible-state boundary, candidate predicate, exact unit/build/plot
selection, excluded mechanics, stock `Game.HandleAction` submission, or dual
postconditions.

## Consequences

- The target binding receives the numeric types it requires while preserving
  the intended `false`/`true` option meanings.
- Read and write programs become seven bytes shorter per `CanBuild` call and
  retain their existing FireTuner bounds.
- Source-level C++ boolean semantics are not assumed to imply that a legacy Lua
  binding accepts Lua boolean values.
- A fresh bounded C6 remains required; source inspection and offline tests do
  not establish target-machine success.

## Alternatives considered

- Omit both optional flags: rejected because the exact intended values should
  remain explicit in generated action code and regression tests.
- Use Lua booleans and rely on implicit conversion: rejected by direct target
  evidence and by the binding's `luaL_optint` implementation.
- Probe alternative argument shapes in the live session: rejected because the
  frozen C6 procedure prohibits improvised diagnostic Lua after a gate failure.

## Supersedes

This supersedes only the Lua-boolean flag representation shown in ADR-0033.
All other ADR-0033 decisions remain accepted.
