# Project State

Last updated: 2026-09-17.

This is the short durable handoff for current work. Detailed completed history
belongs in module documents, milestones, the experiment log, and the
development log.

## Dashboard

- Current milestone: M10 — verified worker build — is implementing the write
  path after completing its read model offline.
  M9 and the immutable 1.1.0 release remain complete.
- Active next deliverable: implement M10 C2 exact allowlisted `worker_build`
  admission, bounded stock dispatch, and marker handling without yet claiming
  success from a marker.
- Functional baseline: 307 tests pass locally on Python 3.11/default runtime
  and in exact-commit/tag GitHub Actions on Python 3.11/3.13.
- Blocking issue: none.
- User presence required next: no. Source research, request registration, ADR,
  contract, and offline work do not require the game. A later C6 write requires
  the operator and separate confirmation.
- Canonical planning source: `docs/planning/MILESTONES.md`.
- Canonical verification sources: `docs/testing/TEST_MATRIX.md` and
  `docs/EXPERIMENT_LOG.md`.

## Implemented core

- The stock Campaign Edition `InGame` Lua runtime is connected to Python through
  the bundled FireTuner protocol without modifying the signed application.
- A single watcher owns the live connection and brokers bounded commands over a
  private Unix socket.
- Every generated FireTuner program is limited to 1,000 UTF-8 bytes before
  transport; submitted commands with no terminal outcome are journaled and
  cached as non-retryable uncertainty under ADR-0028.
- Live schemas 2–6 read economy, culture, research, cities, units, diplomacy,
  early science-victory progress, unit readiness, and ordinary technology state
  within their documented evidence limits.
- The allowlisted `end_turn`, `choose_research`, `set_city_production`,
  `skip_unit`, and bounded adjacent `move_unit` actions validate arguments and
  live capability, then prove their postconditions by re-reading state.
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
- M5's complete successful command lifecycle, automatic turn transition,
  integrity verification, replay, structural export, permissions, and recovery
  are target-machine verified.
- M3 ruleset knowledge coverage and the M4 structural knowledge view are
  complete offline. Generated bundles remain local; AI flavor/personality and
  copyrighted presentation assets remain excluded.
- The legacy `controller` is only a live-verified readiness/refusal and explicit
  end-turn proof. It is not tactical policy.
- M6 is target-machine verified through one newly authored explicit plan that
  completed and automatically advanced exactly one turn.
- M9 source reconnaissance is complete. ADR-0032 selects the stock
  `UI.SelectUnit` plus `Game.SelectionListMove` network-backed path for one
  explicit adjacent ordinary move and rejects direct `PushMission`. This is a
  path. The complete read/write/executor path is implemented on development
  head and now has bounded target-machine evidence. It is published in the
  stable 1.1.0 compatibility profile.
- M9's unit-movement contract is frozen: schema 6 exposes only zero to six
  conservative adjacent `ordinary_move_targets` per owned unit; `move_unit`
  takes exact unit/coordinate arguments and requires identity, destination, and
  decreased-movement read-back. The bounded live procedure passed with a
  separately authorized single write, a safe pre-send rejection, private audit,
  and exact host restoration.
- The schema 6 read model is implemented and covered offline. A seventh
  read-only segment emits active-player-visible `ordinary_move_targets`; parser and validation
  enforce six-target, coordinate, identity, ordering, part-consistency, and
  legacy-schema bounds. A target watcher emitted schema 6 and exposed the
  manually confirmed conservative adjacent target used by the successful C6
  write.
- The C2/C3 movement command is implemented offline. It requires a fresh schema
  6 target admission, repeats source coordinates and conservative legality on
  the game side, verifies exact selection before one `SelectionListMove`, and
  accepts success only when the same unit reaches the exact destination in the
  same active turn with lower movement points. Marker acceptance, unchanged or
  unexpected state, transformation, turn drift, and timeout are not success.
- C4 deterministic integration is implemented offline. Schema 1 plans may list
  only explicit movement coordinates; a move covers `unit_orders` only for its
  exact unit, multiple moves remain explicitly ordered, newly uncovered orders
  pause execution, and cached recovery evidence must independently satisfy the
  exact movement postcondition. Watcher forwarding, factual events, command
  journal composition, and unchanged `civ5-turn` envelopes are covered.
- C5 offline reconciliation is complete: the movement matrix now covers strict
  arguments, legacy/schema drift, unknown/foreign-as-absent units, unlisted and
  unsupported targets, source drift guards, every terminal marker, transient
  reads, unchanged/partial/unexpected results, timeout, duplicate and unknown
  outcomes, multi-action continuity, recovery, CLI/API compatibility, and
  generated-program bounds. Release-artifact checks remain enforced in CI.
- C6 target-machine verification is complete. A source-coordinate request was
  rejected before submission with unchanged state; one separately authorized
  adjacent move reached the exact target in the same turn with lower movement,
  produced a fresh watcher snapshot, and caused no observed extra side effect.
  The private audit was mode `600`, and shutdown restored the exact host
  baseline.
- D4/C7 is complete. Immutable tag `v1.1.0` points to the reviewed release
  commit; exact-commit and tag CI passed on Python 3.11/3.13, duplicate wheel
  and sdist contents matched, clean installations passed, and the two published
  assets matched their recorded SHA-256 values after download.
- M10 began from downstream capability request Issue #2. Its first slice is one
  caller-selected ordinary `BUILD_*` action for a worker already on the target
  plot. C0/D1 is complete under ADR-0033. Unit-level `CanBuild` permits
  selection-free candidate reads; the stock selected-unit
  `Game.CanHandleAction`/`Game.HandleAction` path owns submission. Blank
  featureless land plus ordinary non-consuming improvements avoid popup and
  side-effect ambiguity. Exact active-build and completed-improvement branches
  require the same unit/plot and lower movement. Prototype read segments and
  the worst-case compact write fit the 1,000-byte design limit; final generated
  strings remain subject to executable tests and later live evidence.
- M10 D2 is complete. The new owning worker-build contract freezes schema 7
  current-plot facts, current build, up to 32 bounded candidate pairs, the
  exact four-field `worker_build` action, both success branches, executor
  coverage/recovery, stable CLI behavior, public constants, and downstream
  absent-capability behavior. Core 1.1 implementation and profile remain
  unchanged.
- M10 D3 is complete. WB-S01–A02 freeze the full offline negative,
  uncertainty, executor, compatibility, artifact, and privacy matrix. Live
  checklist section 8 permits only a read-without-selection proof, one stale-
  source pre-send rejection, and one separately authorized candidate write
  after C1–C5. Either exact success branch may close C6; no retry or second
  branch write is allowed.
- M10 C1 is complete offline. Schema 7 now emits and validates exact per-unit
  current-plot facts, nullable current build, and up to 32 sorted factual
  build/improvement candidates through two selection-free 688/895-byte Lua
  programs. Resources use active-team visibility; identifiers, nested shape,
  part identity, unit binding, ordering, duplicates, counts, privacy, and
  schema 2–6 compatibility are covered. The existing movement action remains
  operational on matching schema 6+ states. No worker write action exists yet.

## Current architecture

- M5 stores every supported fact actually captured and validated while
  recording one declared match. It does not claim hidden facts, disconnected
  intervals, or unsupported fields.
- M6 consumes an explicit complete-turn `TurnPlan`, depends only on bridge
  session/state/action contracts, and never queries M4 knowledge or M5 history.
- Future tactical, strategic, and vertical-skill layers query knowledge and
  produce plans. They remain outside this repository together with LLM
  integration, working memory, strategic memory, and MCP.
- `civ5-short-term-tactical-layer` is the first declared downstream plan
  producer. It owns tactical context, domain reports, arbitration, tactical
  plans, action intents, and consumer adapters; this core never imports it.
- Core 1.1.0 publishes a static downstream capability profile through its
  version, schema, allowlist, and limit constants. It does not publish a
  serialized capability manifest or selective tactical-history view.
- Missing downstream facts and mechanics use the strategy-neutral core
  capability request procedure and ship only through a newly versioned core
  release after required offline and target-machine evidence.
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
- Factual readiness treats only the target-build
  `NO_END_TURN_BLOCKING_TYPE` value as no blocker, independently of
  `UI.CanEndTurn()`; the Lua write guard compares the game enum symbol itself.
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
- `civ5_agent.api` is the contract-tested stable 1.1 Python surface.
  Public errors distinguish validation, protocol, transport-ambiguous, and
  live-safety failures while preserving compatible built-in catch behavior.
  Supported schema sets and byte/count limits are exported constants.
- `civ5-turn` is the supported stable machine-readable CLI with exact JSON
  envelopes and exit meanings. All other entry points are explicitly
  provisional without weakening their safety or privacy requirements.

## Evidence still optional

- Schema 5 free-technology and steal-technology modes remain offline-only.
- Schema 4 diplomacy has only empty pre-contact live evidence.
- Schema 4 science-victory data has only enabled/zero-progress live evidence.

Future live tests require the user to start the game and explicitly authorize
the documented `live_session prepare`/`restore` procedure. No background work
may enable FireTuner, launch Civ V, or change the firewall.

## Recommended order

1. Implement C2 allowlisted submission and WB-C01–C04 without accepting any
   marker as verified success.
2. Implement C3–C4 strictly against the frozen contracts and verification IDs.
3. Complete C5 offline evidence, then pause for separately authorized C6 live
   verification before advertising the action or preparing 1.2.0.

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
- ADR-0026 established the aggregate import surface and explicit error taxonomy;
  ADR-0030 advances its compatibility policy to stable 1.0.
- ADR-0027: only the bounded TurnPlan CLI was stabilized before 1.0; all other
  command entry points remain explicitly provisional.
- ADR-0028: FireTuner programs are bounded before transport, and unknown
  post-submission outcomes are recorded and never retried automatically.
- ADR-0029: readiness and writes use the game-defined no-end-turn-blocker
  semantics rather than a numeric zero assumption.
- ADR-0030: the aggregate Python API and `civ5-turn` are stable in 1.0; other
  command-line entry points remain provisional.
- ADR-0031: downstream tactical integration is one-way; reusable capability
  requests evolve the core without importing tactical policy or adapters.
- ADR-0032: adjacent movement uses the exact selected-unit stock network path.
- ADR-0033: ordinary worker builds separate selection-free unit legality from
  exact selected-unit stock action dispatch and dual factual verification.

See `docs/architecture/decisions/README.md` for the complete decision index and
`docs/development/DEVELOPMENT_LOG.md` for chronological history.
