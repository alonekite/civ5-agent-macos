# Project State

Last updated: 2026-09-16.

This is the short durable handoff for current work. Detailed completed history
belongs in module documents, milestones, the experiment log, and the
development log.

## Dashboard

- Current milestone: M5 — factual turn journal.
- Active next deliverable: add remaining command-submission,
  verification-error, and explicit turn-transition records, then deterministic
  replay/export.
- Functional baseline: 190 tests pass locally on Python 3.11 and the default
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
  in-memory command results. `new` creates a match journal; `resume` explicitly
  binds a new bridge session. Reconnect never binds automatically.
- A complete-turn plan requires a final explicit `end_turn`; `completed` means
  that action and every preceding action were verified.

## Evidence still optional

- Schema 5 free-technology and steal-technology modes remain offline-only.
- Schema 4 diplomacy has only empty pre-contact live evidence.
- Schema 4 science-victory data has only enabled/zero-progress live evidence.

Future live tests require the user to start the game and explicitly authorize
the documented `live_session prepare`/`restore` procedure. No background work
may enable FireTuner, launch Civ V, or change the firewall.

## Recommended offline order

1. Add remaining submitted-command, verification-error, and explicit
   turn-transition lifecycle records.
2. Add deterministic journal replay/export plus retention guidance without
   weakening append-only integrity.
3. Separately finalize M6 TurnPlan and execution-report schemas against the
   bridge-session, live-state, and command contracts.
4. Implement ordered execution, factual requirements, drift pauses, and
   unambiguous recovery without knowledge or journal dependencies.
5. Stabilize public read/write, knowledge-query, journal, and execution APIs in
   M7.

Steps 1–2 before 3–4 are project scheduling only. M5 and M6 do not depend on
each other.

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

See `docs/architecture/decisions/README.md` for the complete decision index and
`docs/development/DEVELOPMENT_LOG.md` for chronological history.
