# Architecture

```text
[ Civilization V ] ↔ [ Lua Bridge ] ──► [ Live State ]
                           ▲                    │
                           │                    ▼
                    verified action   [ Deterministic Turn Executor ]
                           ▲                    ▲
                           └────────────────────┤
                                        [ explicit TurnPlan ]
                                                ▲
[ Ruleset Knowledge ] ─► [ Structural View ] ─► [ future plan producer ]

[ bridge observations / verified results / executor facts ]
                           │
                           ▼
             [ watcher/CLI application composition ] ─► [ Turn Journal ]
```

The verified Phase 1 transport is the game's bundled FireTuner server on
localhost TCP 4318. Python performs the Firaxis `APP:`/`LSQ:` handshake, selects
the `InGame` Lua state reported by Civ V, and sends an allowlisted read-only Lua
expression using `CMD:<state-id>:<code>`. Game output and command completion are
returned over the same socket.

The live-verified schema 2 snapshot contains economy, culture, research,
cities, units, and end-turn readiness. Schema 3 added score, current era, exact
city food/growth and production progress, owned-unit health/base strength/range,
and a record for each alive major civilization the active team has met:
player/team IDs, visible names, score, war state, and the stock UI's approach
estimate. Schema 4 adds unit readiness and bounded segmented collection with
per-part turn/player consistency. Its early-game branches are live-verified;
non-empty diplomacy and non-zero science projects remain optional enhancement
tests. Unmet civilizations are deliberately omitted. City rates remain in Civ
V's times-100 integer units. Science-victory progress is limited to the active
team's own Apollo Program and spacecraft project counts.

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

The provisional `civ5-watch --read-only` mode narrows that server protocol to
`ping` and `read_state`. It rejects command lookup and all writes before they
reach execution. This is the execution core's only automation-facing addition;
generic application lifecycle, PTY supervision, visual observation, profiles,
and recovery belong to an independent project and are composed externally.

That independent repository may supervise the watcher through installed
executables and a private SessionSpec v1 JSON file. The provisional
`civ5-read-only` adapter emits the descriptor and reads one same-session,
server-verified, sanitized summary. The external composition root—not either
package—sequences framework start, probe, and graceful stop. There is no Python
import dependency in either direction, and no C4/M11 profile belongs to this
boundary. The formally adopted external implementation is
`local-app-test-automation` v0.1.0, pinned by tag target and wheel digest under
ADR-0041; it remains an optional process-level tool rather than a package
dependency. See the external automation compatibility contract.

The M7 `WatcherBridgeClient` is the bridge-facing Python surface over this
private socket. It exposes validated session-aware reads, individual verified
commands, and read-only completed-result lookup without importing TurnPlan or
opening FireTuner. `WatcherTurnExecutor` extends it only for M6 composition.

## Write safety

The first live-verified write is `end_turn`. The implementation:

1. captures the complete before-state;
2. checks `IsTurnActive`, `Game.IsProcessingMessages`, and `UI.CanEndTurn`
   inside Civ V;
3. invokes the same `Game.DoControl(GameInfoTypes.CONTROL_ENDTURN)` used by the
   stock `ActionInfoPanel.lua` only if all checks permit it;
4. re-reads state until the turn number increases or verification times out;
5. returns the command UUID, status, message, before-state, and after-state.

## Deterministic turn execution

The current `civ5_agent.controller` is an MVP readiness proof. It validates the
snapshot, checks turn ownership and mandatory choices in a conservative order,
and can submit an explicitly requested end turn through the verified bridge.
It is not the target tactical policy for M6 and must not grow by choosing
research, production, movement, targets, or strategy.

M6 introduces a deterministic turn executor around an explicit versioned
`TurnPlan`. A human or independent tactical layer supplies every ordered action. The
executor validates the plan's bridge session, turn, player, and state basis,
sends only the next allowlisted action, advances only after write-after-read
proof, emits bounded factual events, and pauses rather than replans on drift or
missing decisions. It operates without M5; optional application orchestration
may record its events. A complete-turn plan must list `end_turn` last and is not
`completed` until that action is verified.

Schema 1 admission is implemented under ADR-0022. The complete validated
initial live state is canonically hashed; a session, turn, player, or digest
mismatch rejects the plan before writing. The digest is not reapplied after the
plan's own verified mutations. The in-process ordered core instead requires
each command result's before-state to match the latest observation and uses the
verified after-state as the next basis. It never retries an unknown submission.
Optional neutral lifecycle events are emitted through a bounded sink whose
failure cannot affect execution. The watcher adapter now supplies state reads
and plan-listed writes through the existing private Unix socket, preserving
session and command identities without creating another FireTuner client.
The same socket now supports a session-scoped read-only lookup of completed
command UUIDs. A miss never executes or retries a command; full report
reconciliation validates a hit against the prior basis and fresh live state.
A recovered final end-turn can complete, while a recovered non-final action
pauses before the next write under ADR-0023. The bounded `civ5-turn` CLI loads
strict schema 1 JSON and reaches M6 only through the watcher adapter under
ADR-0024; it does not plan actions or open a direct FireTuner connection.

M6 does not query the structural knowledge view. Stable identifier shape, live
capability, and action legality are bridge command responsibilities. Knowledge
is available to the human or future plan producer that chooses explicit plan
content, not to the executor applying it.

Initial allowlist:
- end_turn
- choose_research
- set_city_production
- skip_unit (live-verified with readiness and unchanged movement/location)

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

This M2 command audit is local safety evidence, not the M5 match journal. M5
receives the same validated in-memory command result through application
composition; it never reconstructs history by parsing the audit file. Command
UUIDs correlate the two records. Either store may fail independently, and
neither logging failure changes a bridge-verified game result.

For one watcher lifetime, completed command UUIDs are cached together with
their operation, arguments, and response. An identical retry returns that
response with `replayed: true`; reuse with different arguments is rejected.
The executor adapter instead uses the read-only `command_status` request when
an earlier submission has an unknown outcome. A matching cache hit returns the
terminal result; a miss does not take any write path.
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

The completed M4 structural knowledge view validates an explicit per-game
selection against the immutable ruleset bundle. Its contract covers exact
ruleset identity, game speed, difficulty, map size, civilization, adopted
policies, and active beliefs. It fails closed on missing or incompatible
identifiers, returns detached entity values plus source provenance, and resolves
unit/building class defaults and civilization replacements. M7 retained
`RulesetResolver` in the supported aggregate API, and ADR-0030 promotes that
surface to the stable 1.0 contract.

It does not compose broad effective scalar values, compare candidates, predict
outcomes, or choose actions. Those operations belong with future strategic,
tactical, and vertical-skill decision support outside this execution core. When
Civ V reports a current effective value directly, the live observation is
authoritative.

Do not expose arbitrary Lua execution to any executor or external decision
system.

## Downstream planning boundary

The independent `civ5-short-term-tactical-layer` project is the first declared
plan-producing consumer. Dependency direction is one way:

```text
long-term strategy -> short-term tactics -> this execution core -> Civ V
```

This core owns observable state, ruleset knowledge, stable identifiers,
allowlisted mechanics, `TurnPlan`, execution, verification, and factual history.
It does not own `StrategistDirective`, `TacticalPlan`, `ActionIntent`, domain
reports, proposal scoring, Tactical Office arbitration, or consumer-side
adapters. A downstream adapter may construct public core objects, but cannot
broaden the allowlist, reinterpret results, open FireTuner, or bypass plan
admission.

Core 1.2.0 publishes a static capability profile through exported version,
schema, allowlist, and limit constants, including schema 7 and the exact
`worker_build` action. It does not publish a serialized
capability manifest or selective tactical-history view. Missing reusable facts
or mechanics follow the strategy-neutral capability request procedure and ship
only in a newly versioned core release after their own verification.

## Session and match identity

The current game APIs used by this project do not provide a target-verified ID
that is known to remain stable across saving, loading, reconnecting, and process
restart. The architecture therefore does not use one ambiguous “game ID”:

- the bridge creates a `bridge_session_id` for one connection-owner epoch;
- M6 targets that session plus turn, active player, and state basis;
- M5 creates a separate `match_id` for one declared journal history;
- a later bridge session joins that journal only through an explicit append-only
  binding; automatic cross-session inference is prohibited for now.

This fail-closed split is defined by ADR-0017 and the session-identity contract.
Live-state schemas 2–5 predate the envelope; the bridge now carries session
identity beside the unchanged state payload and M5 enforces explicit bindings.

## Per-match factual history

Ruleset knowledge and per-match history are different kinds of data. Knowledge
describes stable facts for a versioned ruleset. Per-match history describes one
declared match and carries `match_id`, the bound bridge-session identity, turn
number, snapshot schema version, and ruleset identity where applicable.

The current core separates live state from one durable history layer:

### Live state

The most recent validated snapshot read from Civ V is the source of truth for
the current position. Cached data or a TurnPlan must never override a
contradicting live observation.

### Turn journal

The turn journal is the append-only sequence of all supported facts actually
captured and validated while recording is active. It stores validated
snapshots, observed turn transitions, submitted command envelopes, command
results, before/after states, and verification errors. It does not claim hidden
game facts, events missed while disconnected, or fields outside the supported
schema. Journal records are for
future tactical/strategic history selection, replay, comparison, auditing,
debugging, and later analysis. The journal is not an executor control plane and
is not passed wholesale into the executor loop.

Schema 1 records are appended under an exclusive lock and fsynced before
success. They include a monotonically
increasing sequence, capture timestamp, match/session and turn identifiers,
schema and ruleset versions where applicable, canonical payload, and integrity
hash. Corrections append a
new record that supersedes an earlier record rather than rewriting history.
Each record hashes its canonical content and the previous record hash; reads
fail closed on truncation, tampering, sequence gaps, or invalid bindings.

The intended dependency direction is:

```text
bridge observations + verified action results -> application -> turn journal
live state                                     -> turn requirements
explicit TurnPlan + live state                 -> deterministic turn executor
deterministic turn executor                    -> plan-listed bridge action
deterministic turn executor factual events     -> application -> turn journal
```

“Application” here means composition code in the watcher and CLI entry points.
It wires modules together and handles optional sinks; it is not a core policy,
planning, or decision module.

The initial opt-in watcher adapter records changed validated snapshots and
grounded in-memory command results. It requires paired `--journal` and
`--journal-mode new|resume` arguments, never parses the command audit, and never
automatically binds a replacement connection after reconnect. It is restricted
to the validated FireTuner transport; the partial, unversioned database fallback
cannot write a journal.

Full-chain verification is payload-free. Replay preserves append order and
requires explicit acknowledgement before printing private payloads. Supported
file export is the canonical redacted structure defined by ADR-0021: sequence,
turn, and event kind only, with private/correlatable content removed. It is not
a replacement for the authoritative hash-chained source.

The journal does not infer intentions, summarize opponents, select context, or
choose actions. It preserves the facts needed to reproduce those operations
later.

## Future LLM interaction layer

Working memory and strategic memory are deliberately deferred to a future
LLM-facing layer outside this repository:

- working memory will select recent relevant changes, observed opponent
  information, and near-term production, research, and unit intentions;
- strategic memory will maintain victory objectives, approximate technology and
  policy routes, expansion, diplomacy, military direction, and revision history.

That future layer also owns `TurnPlan` production and consumer-driven research,
military, exploration,
city-development, and other vertical skills. Their deterministic rules may
compare alternatives or calculate counterfactual effective values for strategy
and tactics; those analyses are not responsibilities of the current executor or
the M4 structural knowledge view.

Some working-memory content will be derived from factual journal records, but
its selection, summarization, inference, expiry, and prompt representation are
closely coupled to LLM interaction. Strategic-memory revisions are similarly
coupled to planning conversations. Their data contracts should therefore be
designed together with that future layer rather than embedded in the current
read/write core.

That future layer may read public core APIs and submit candidate intentions, but
it must not bypass bridge validation, expand the action allowlist, or turn an
unverified inference into a write precondition.
