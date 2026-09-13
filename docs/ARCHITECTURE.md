# Architecture

```text
[ Civilization V ]
        │
[ Lua Bridge ]
        │
[ IPC / Storage Adapter ]
        ├──────────────┐
        │              │
[ Ruleset Knowledge ]  │
        │              │
        └──────┬───────┘
               │
    [ Deterministic Controller ]
```

The verified Phase 1 transport is the game's bundled FireTuner server on
localhost TCP 4318. Python performs the Firaxis `APP:`/`LSQ:` handshake, selects
the `InGame` Lua state reported by Civ V, and sends an allowlisted read-only Lua
expression using `CMD:<state-id>:<code>`. Game output and command completion are
returned over the same socket.

The live-verified schema 2 snapshot contains economy, culture, research,
cities, units, and end-turn readiness. Schema 3 adds score, current era, exact
city food/growth and production progress, owned-unit health/base strength/range,
and a record for each alive major civilization the active team has met:
player/team IDs, visible names, score, war state, and the stock UI's approach
estimate. Unmet civilizations are deliberately omitted. Schema 3 is
implemented and offline-tested but not yet live-verified. Its city rates remain
in Civ V's times-100 integer units. Science-victory progress is limited to the
active team's own Apollo Program and spacecraft project counts.

`Modding.OpenUserData()` remains a fallback for a distribution that exposes the
Mods browser. This App Store Campaign Edition discovers custom mods but keeps
them disabled because its vendor UI forcibly hides that browser.

## Connection ownership

This Civ V build reliably services one FireTuner client at a time and may delay
cleaning up a disconnected socket. The long-running watcher therefore owns the
game connection. It exposes a per-user Unix socket with mode `0600` so the
command CLI can share that exact connection. Requests are serialized with the
watcher's reads.

The local protocol accepts one JSON object per line. Requests are capped at
64 KiB and responses at 4 MiB; both peers reject oversized messages. The
server converts malformed JSON, non-object callbacks, serialization failures,
and unexpected callback exceptions into bounded structured errors.

## Write safety

The first live-verified write is `end_turn`. The implementation:

1. captures the complete before-state;
2. checks `IsTurnActive`, `Game.IsProcessingMessages`, and `UI.CanEndTurn`
   inside Civ V;
3. invokes the same `Game.DoControl(GameInfoTypes.CONTROL_ENDTURN)` used by the
   stock `ActionInfoPanel.lua` only if all checks permit it;
4. re-reads state until the turn number increases or verification times out;
5. returns the command UUID, status, message, before-state, and after-state.

## Deterministic policy

`civ5_agent.controller` is deliberately separate from any LLM. It validates the
snapshot, checks turn ownership and mandatory choices in a conservative order,
and produces a structured decision. Execution is opt-in with `--execute` and
still goes through the same Lua preconditions and turn-advance verification.

Initial allowlist:
- end_turn
- choose_research
- set_city_production
- skip_unit (offline-verified; live verification pending)

Research and production use the same stock calls as the bundled Brave New World UI:
`Network.SendResearch(...)` from `TechPopup.lua` and
`Game.CityPushOrder(...)` from `ProductionPopup.lua`. They validate identifier
shape and Civ V capability predicates before writing, then re-read the selected
technology or city production. Both paths are unit-tested and live-verified on
the target Mac.

Each command result is also appended to a mode-0600 JSONL audit log with its
UTC timestamp, operation, canonical UUIDv4, validated arguments, and
before/after snapshots. The watcher owns logging for brokered commands; the CLI
logs direct commands. Audit failure is reported without changing a verified
command into a retryable failure.

For one watcher lifetime, completed command UUIDs are cached together with
their operation, arguments, and response. An identical retry returns that
response with `replayed: true`; reuse with different arguments is rejected.
The lookup, execution, audit, and cache insertion share the connection lock so
concurrent duplicate requests cannot both reach Civ V.

## Ruleset knowledge

`civ5_agent.knowledge` is independent of live-game state. It represents a
versioned ruleset as entities, typed references, and source records containing
relative paths, byte sizes, and SHA-256 hashes. Canonical JSON serialization is
stable across input ordering, and loading rejects unknown fields, broken
references, invalid identifiers, missing provenance, and non-finite numbers.

The first importer reads the game's merged `Civ5DebugDatabase.db` in SQLite
read-only and immutable mode. It currently exports technology and era gameplay
fields plus prerequisite and technology-to-era relations. It uses explicit
column allowlists and
does not export AI weights, flavor tables, Civilopedia prose, quotations, art,
or audio. It refuses a database with a live write-ahead log or one that changes
during import.

The knowledge module is deterministic and never requires an LLM. A local model
may help draft code or mappings during development, but model output is accepted
only after schema, integrity, fixture, and test validation.

Do not expose arbitrary Lua execution to any controller or external decision
system.
