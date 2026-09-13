# Architecture

```text
[ Civilization V ]
        │
[ Lua Bridge ]
        │
[ IPC / Storage Adapter ]
        │
   [ Live State ] ────────────────┐
        │                         │
 [ Turn Journal ]                 │
        │                         │
 [ Working Memory ]               │
        │                         │
 [ Strategic Memory ]             │
        ├───────────────┐         │
        │               │         │
[ Ruleset Knowledge ]   │         │
        └───────┬───────┘         │
                │                 │
     [ Deterministic Controller ] │
                │                 │
                └── verified action
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
read-only and immutable mode. It currently exports technology, era, unit,
unit-class, promotion, policy, policy-branch, building, building-class,
resource, and resource-class
gameplay facts plus their prerequisite, era, technology, upgrade, default,
free-promotion, and policy-tree relations. It uses explicit column allowlists
and does not export AI
weights, roles, flavor tables, Civilopedia prose, quotations, hotkeys, art, or
audio. It refuses a database with a live write-ahead log or one that changes
during import. Active package IDs are derived from the database and checked
against the declared vanilla/G&K/BNW family.

The knowledge module is deterministic and never requires an LLM. A local model
may help draft code or mappings during development, but model output is accepted
only after schema, integrity, fixture, and test validation.

Do not expose arbitrary Lua execution to any controller or external decision
system.

## Per-game history and memory

Ruleset knowledge and per-game memory are different kinds of data. Knowledge
describes stable facts for a versioned ruleset. Per-game history describes one
particular match and must always carry a game identifier, turn number, snapshot
schema version, and ruleset identity.

The planned persistence design has four distinct layers:

### Live state

The most recent validated snapshot read from Civ V is the source of truth for
the current position. A memory entry or controller plan must never override a
contradicting live observation.

### Turn journal

The turn journal is the complete, append-only record. It stores full validated
snapshots, observed turn transitions, submitted command envelopes, command
results, before/after states, and verification errors. Journal records are for
reproduction, auditing, debugging, and later analysis; the entire journal is
not passed into the controller decision loop.

Records should be committed transactionally and include a monotonically
increasing sequence, capture timestamp, game and turn identifiers, schema and
ruleset versions, canonical payload, and integrity hash. Corrections append a
new record that supersedes an earlier record rather than rewriting history.

### Working memory

Working memory is a bounded, rebuildable view of recent relevant events. It may
track near-term production or research intentions, recent opponent movement,
unresolved mandatory choices, and the outcomes of recent actions. Entries
expire by turn horizon or explicit resolution.

Observed facts, deterministic inferences, intentions, and verified outcomes
must use different record kinds. An inference cites its supporting journal
records and carries a confidence or certainty category so that it cannot be
mistaken for a game observation.

### Strategic memory

Strategic memory contains the current long-horizon plan for one game: victory
objective, approximate technology and policy routes, expansion or military
posture, major constraints, and durable commitments. Plans are versioned.
Changing a plan appends a revision with its evidence and reason, preserving the
previous objective for later review.

Working and strategic memory are controller inputs, not authorities for game
facts. Both must be reconstructable from the journal plus explicit strategic
revisions. Their implementation must be deterministic and remain fully usable
without an LLM.

The intended dependency direction is:

```text
bridge observations + verified action results -> turn journal
turn journal + ruleset knowledge              -> working memory
working memory + strategic memory + knowledge -> controller
controller                                    -> whitelisted bridge action
```

No memory layer may bypass bridge validation, expand the action allowlist, or
turn an unverified inference into a write precondition.
