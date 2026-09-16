# Project State

Last updated: 2026-09-16.

This is the short durable handoff for current work. Detailed completed history
belongs in module documents, milestones, the experiment log, and the
development log.

## Dashboard

- Current offline milestone: M7 — public API stabilization. M5 and M6 bounded
  target-machine verification remain pending.
- Active next deliverable: freeze or explicitly qualify CLI JSON/exit
  compatibility, then assess whether demonstrated consumers need narrower
  knowledge or journal facades.
- Functional baseline: 247 tests pass locally on Python 3.11 and the default
  runtime; the latest implementation batch passed GitHub Actions on Python 3.11
  and 3.13.
- Blocking issue: none.
- User presence required next: none.
- Canonical planning source: `docs/planning/MILESTONES.md`.
- Canonical verification sources: `docs/testing/TEST_MATRIX.md` and
  `docs/EXPERIMENT_LOG.md`.

## Implemented core

- The stock Campaign Edition `InGame` Lua runtime is connected to Python through
  the bundled FireTuner protocol without modifying the signed application.
- A single watcher owns the live connection and brokers bounded commands over a
  private Unix socket.
- Live schemas 2–5 read economy, culture, research, cities, units, diplomacy,
  early science-victory progress, unit readiness, and ordinary technology state
  within their documented evidence limits.
- The allowlisted `end_turn`, `choose_research`, `set_city_production`, and
  `skip_unit` actions validate arguments and live capability, then prove their
  postconditions by re-reading state.
- Command UUIDs, watcher-lifetime duplicate suppression, bounded IPC, private
  M2 audit logs, live preflight, and recoverable FireTuner/firewall sessions are
  implemented.
- The bridge-session envelope is implemented offline: watcher/direct connection
  epochs receive canonical UUIDv4 identities, reads expose them, writes must
  echo them, and stale or missing values fail before execution.
- M5 schema 1 is implemented offline as a mode-0600 JSONL store with canonical
  records, contiguous sequence numbers, explicit session bindings, SHA-256 hash
  chaining, file locking, `fsync`, bounded records, and fail-closed corruption
  detection.
- M3 ruleset knowledge coverage and the M4 structural knowledge view are
  complete offline. Generated bundles remain local; AI flavor/personality and
  copyrighted presentation assets remain excluded.
- The legacy `controller` is only a live-verified readiness/refusal and explicit
  end-turn proof. It is not tactical policy.

## Current architecture

- M5 stores every supported fact actually captured and validated while
  recording one declared match. It does not claim hidden facts, disconnected
  intervals, or unsupported fields.
- M6 consumes an explicit complete-turn `TurnPlan`, depends only on bridge
  session/state/action contracts, and never queries M4 knowledge or M5 history.
- Future tactical, strategic, and vertical-skill layers query knowledge and
  produce plans. They remain outside this repository together with LLM
  integration, working memory, strategic memory, and MCP.
- `bridge_session_id` identifies one connection-owner epoch for safe execution.
  Journal `match_id` identifies one declared history. Cross-session journal
  continuation is explicit and append-only; no permanent save ID is claimed.
- Watcher/CLI composition code may pass validated observations, command results,
  and optional M6 factual events to M5. M5 never parses the independent M2 audit
  log as input, and logging failures never make a verified game action retryable.
- Opt-in watcher capture records changed validated snapshots and grounded
  command lifecycles, including submissions, unsuccessful results, and observed
  turn transitions. `new` creates a match journal; `resume` explicitly binds a
  new bridge session. Reconnect never binds automatically.
- `civ5-journal verify` checks the complete journal and returns only a
  payload-free structural and integrity summary.
- `civ5-journal replay` returns the verified append-order factual record stream
  without executing actions and requires explicit private-payload
  acknowledgement.
- `civ5-journal export` creates a new private structural export that omits
  payloads, timestamps, identities, hashes, and source paths under ADR-0021.
- A complete-turn plan requires a final explicit `end_turn`; `completed` means
  that action and every preceding action were verified.
- TurnPlan schema 1 binds canonical plan/session identities, turn, player, and a
  full validated initial-state digest to at most 64 strictly allowlisted actions.
- Factual requirement inspection deterministically reports research, per-city
  production, per-unit orders, inactive turns, and game-reported blockers
  without selecting any response.
- The ordered M6 core re-reads before each action, enforces continuity with the
  prior verified after-state, pauses on drift/missing requirements, and never
  retries an action whose outcome became unknown.
- Optional bounded execution events remain neutral until state continuity is
  verified; sink failures are reported but cannot affect execution.
- The watcher execution adapter reads state and submits plan-listed actions over
  the existing private watcher socket, preserving bridge session and command
  identities without opening another FireTuner connection.
- A session-scoped, read-only command-status request retrieves terminal results
  already cached by the current watcher. Missing results remain unknown and are
  never automatically resubmitted.
- Conservative report reconciliation validates cached evidence and fresh state.
  A recovered final end-turn can complete; a recovered non-final success pauses
  before the next action rather than automatically continuing the old plan.
- `civ5-turn validate` strictly loads a bounded schema 1 plan and checks it
  against fresh watcher state without writing. `civ5-turn execute` is the
  explicit watcher-only execution entry point and returns the complete report.
- `civ5_agent.bridge` now exposes a session-aware `Bridge` protocol and
  watcher-only client for validated reads, individual verified commands, and
  read-only result lookup independently of M6.
- `civ5_agent.api` is the contract-tested aggregate pre-1.0 Python surface.
  Public errors distinguish validation, protocol, transport-ambiguous, and
  live-safety failures while preserving compatible built-in catch behavior.
  Supported schema sets and byte/count limits are exported constants.

## Evidence still optional

- Schema 5 free-technology and steal-technology modes remain offline-only.
- Schema 4 diplomacy has only empty pre-contact live evidence.
- Schema 4 science-victory data has only enabled/zero-progress live evidence.

Future live tests require the user to start the game and explicitly authorize
the documented `live_session prepare`/`restore` procedure. No background work
may enable FireTuner, launch Civ V, or change the firewall.

## Recommended offline order

1. Freeze or explicitly qualify CLI names, JSON envelopes, and exit semantics.
2. Add selective journal and knowledge queries only where the public API
   inventory demonstrates a concrete need.
3. Run bounded M5/M6 live verification when the user is present.

M5 live verification and M6 implementation are independent workstreams.

## Recent governing decisions

- ADR-0014: M4 is a structural view; effective-value analysis belongs to future
  decision-support consumers.
- ADR-0015: tactical plan production is separate from deterministic execution.
- ADR-0016: M5 history is not M6 execution state.
- ADR-0017: bridge-session identity and journal match identity are separate;
  automatic cross-session match inference is prohibited.
- ADR-0018: M6 does not query M4 knowledge; plan producers do.
- ADR-0019: M2 command audit and M5 journal are independent sinks correlated by
  command UUID.
- ADR-0020: M5 uses private hash-chained JSONL with locked, fsynced appends and
  fail-closed corruption detection.
- ADR-0021: supported file export is structural and redacted by default.
- ADR-0022: complete-turn plans bind to one validated initial live-state basis.
- ADR-0023: unknown actions reconcile through watcher-cache evidence and are
  never automatically retried.
- ADR-0024: TurnPlan files are bounded, exact-field, and executable only through
  the watcher-owned CLI path.
- ADR-0025: the public bridge client is session-aware, watcher-only, and
  independent of M6 orchestration.
- ADR-0026: one aggregate pre-1.0 import surface and explicit error taxonomy
  define supported Python compatibility.

See `docs/architecture/decisions/README.md` for the complete decision index and
`docs/development/DEVELOPMENT_LOG.md` for chronological history.
