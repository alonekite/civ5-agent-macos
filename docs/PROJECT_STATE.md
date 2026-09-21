# Project State

Last updated: 2026-09-21.

This is the short durable handoff for current work. Detailed completed history
belongs in module documents, milestones, the experiment log, and the
development log.

## Dashboard

- Current milestone: M11 — runtime research facts — is complete in immutable
  release `v1.3.0`. M10 and the earlier 1.2.0 release remain complete.
- Active next deliverable: monitor downstream integration and route any next
  reusable fact or mechanic through the strategy-neutral capability-request
  process. The post-1.3 provisional SessionSpec v2 adapter is implemented and
  offline-validated. Its first operator-present run exposed external-framework
  lifecycle/readiness blockers before watcher startup; no further live run is
  scheduled until a repaired framework contract and exact commit return. The
  adapter adds no game-state or write capability.
- Functional baseline: 366/366 tests pass warning-enabled in host context on
  Python 3.11 and the default runtime. Two independent 1.3.0 candidate wheel
  and sdist builds have matching normalized contents; each format installs,
  imports, and starts the supported CLI in a separate clean Python 3.11
  environment. Exact-commit and `v1.3.0` tag GitHub Actions pass on Python
  3.11/3.13, and downloaded Release assets match the recorded hashes.
- Blocking issue: none for C4. The exact `95ef3df` rerun preserved one bridge
  session across both interturns and completed the read-only overflow gate.
  The observed `3.19` point difference remains recorded without normalization;
  the action-window science change from `447.21` to `444.55` is a plausible
  cross-turn production explanation, not a proved formula.
- User presence required next: no. Candidate SessionSpec v2 retesting is blocked
  on an external-framework repair; a later operator-present run must obtain new
  bounded authorization and evidence.
- `civ5-watch --read-only` exposes the minimum server-enforced read surface for
  an independent external automation composition root; this repository does
  not own generic application lifecycle or test profiles.
- The provisional `civ5-read-only` process boundary emits SessionSpec v1 JSON
  and one same-session sanitized state summary. Neither repository imports the
  other; the external composition root owns sequencing and graceful stop.
- `local-app-test-automation` v0.1.0 is the adopted optional supervisor,
  identity-pinned by release tag, tag commit, wheel name, and SHA-256. Its
  published wheel passed exact-boundary validation without a core dependency.
- Candidate framework commit `d7784a7` accepts the generated SessionSpec v2
  startup sequence. Target observation verified exact Civ V bundle/window
  identity, one unique launcher `PLAY` AX button, and no actionable AX element
  on the continue canvas. The first live run verified the launcher AX press but
  failed before completing the relative click or starting the watcher. It also
  exposed the launcher's same-PID executable-identity transition. Framework
  repair and a fresh exact-commit run remain pending; no 0.2 release is adopted.
- Canonical planning source: `docs/planning/MILESTONES.md`.
- Canonical verification sources: `docs/testing/TEST_MATRIX.md` and
  `docs/EXPERIMENT_LOG.md`.

## Implemented core

- Published 1.3.0 schema 8 emits and validates exact
  ordinary-research runtime facts and explicit context provenance through
  twelve bounded read-only programs. It preserves schemas 2–7 and every
  write/plan/result contract.
  Corrected runtime bindings, UI agreement, positive overflow, selection
  preservation, later application, and one-session continuity now have bounded
  target evidence.
- ADR-0042 drains Lua output that arrives after a FireTuner command
  acknowledgement. A marked part before its header now ends that connection
  epoch and causes a guarded long-running watcher reconnect with a new
  bridge-session identity; no submitted write is retried.
- ADR-0043 drains every frame of a multi-frame response after an early
  acknowledgement instead of stopping at the first late output frame.

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
  require the same unit/plot and lower movement. The final read programs fit
  their segment bounds, and the 991-byte worst-case compact write fits the
  1,000-byte transport limit; its active-build success branch is target-machine
  verified.
- M10 D2 is complete. The new owning worker-build contract freezes schema 7
  current-plot facts, current build, up to 32 bounded candidate pairs, the
  exact four-field `worker_build` action, both success branches, executor
  coverage/recovery, stable CLI behavior, public constants, and downstream
  absent-capability behavior. Tagged core 1.1 remains unchanged; stable core
  1.2.0 publishes the new capability.
- M10 D3 is complete. WB-S01–A02 freeze the full offline negative,
  uncertainty, executor, compatibility, artifact, and privacy matrix. Live
  checklist section 8 permits only a read-without-selection proof, one stale-
  source pre-send rejection, and one separately authorized candidate write
  after C1–C5. Either exact success branch may close C6; no retry or second
  branch write is allowed.
- M10 C1 is complete offline. Schema 7 now emits and validates exact per-unit
  current-plot facts, nullable current build, and up to 32 sorted factual
  build/improvement candidates through two selection-free 688/881-byte Lua
  programs. Resources use active-team visibility; identifiers, nested shape,
  part identity, unit binding, ordering, duplicates, counts, privacy, and
  schema 2–6 compatibility are covered. The existing movement action remains
  operational on matching schema 6+ states.
- M10 C2–C3 are complete offline. Core 1.2.0 allowlists the
  exact four-field worker command. Fresh schema 7 admission
  precedes one guarded 991-byte stock dispatch; its bounded marker is never
  success by itself. Polling proves either the exact active build or completed
  paired improvement with the same turn/player/unit/plot and lower movement.
  The active-build branch is target-machine verified; immediate completion
  retains offline evidence only.
- M10 C4 is complete offline. Schema 1 TurnPlans admit the exact worker action
  only with a schema 7 basis, preserve all arguments through the watcher,
  independently revalidate both result branches, and cover only the exact unit.
  Ordered move/build is supported; a still-ready unit without a later explicit
  move/build/skip pauses execution. Cached recovery requires exact command and
  fresh-state agreement and pauses before later work.
- M10 C5 is complete offline. Worker-specific drift, ambiguity, transient-read,
  timeout, unknown-outcome, watcher/audit/journal/UUID, CLI and recovery cases
  pass within the 335-test suite. Repeated wheel/sdist contents match, both
  artifact kinds install cleanly, and tracked/unpacked sensitive-content scans
  are empty. This is not live evidence.
- The first M10 C6 attempt on 2026-09-18 stopped safely at the read-only gate:
  Campaign Edition exposes `GameInfoActions` as a table, so the callable-table
  candidate loop failed before a schema 7 snapshot. No command or write ran,
  and exact host restoration passed. The reader now uses the same numeric table
  shape already proven by `skip_unit`, forbids the invalid call in regression
  tests, and retains the sub-900-byte segment bound. Fresh C6 evidence is still
  required after the repair is pushed.
- The 2026-09-19 retry passed indexed action enumeration but stopped safely at
  the same read-only gate because Campaign Edition's `unit:CanBuild` binding
  reads its option flags with `luaL_optint` and rejects Lua booleans. No command
  or write ran and restoration again passed. ADR-0034 now requires integer
  flags `0, 1` in both candidate reads and the game-side pre-submit guard; the
  repaired programs were 881 and 989 bytes. A fresh C6 remained required after
  this second repair is pushed and passes CI.
- A later guarded attempt produced a valid schema 7 candidate matching the UI
  with no read side effect, and its deliberately stale source was rejected
  before submission with identical state. The separately authorized single
  write then failed Lua parsing because interpolated numeric literals touched
  following `or`/`then` keywords. No valid marker was returned, the UI showed
  no build or movement change, no retry occurred, and exact restoration passed.
  The generator now separates those tokens and regression coverage freezes the
  actual boundaries; the complete offline and CI gates must pass before a new
  C6 session.
- The following fresh attempt again passed schema 7/UI agreement and stale-
  source rejection. Its separately authorized write parsed and returned an
  explicit `invalid_build` marker with identical before/after state and no UI
  side effect. The write path had incorrectly used a build-type string key on
  the target's numerically indexed `GameInfoActions` table. No retry occurred
  and exact restoration passed. The repaired 997-byte program now iterates the
  numeric table and matches Type, SubType, and MissionData; the complete offline
  and CI gates remain mandatory before another C6 session.
- The next fresh attempt passed the same read and stale-source gates, resolved
  the action, and returned explicit `blocked` with identical before/after state
  and no UI side effect. Installed BNW UI inspection identified the remaining
  mismatch: stock buttons pass the numeric loop index to `Game.CanHandleAction`
  and `Game.HandleAction`, while the program passed the table entry's `ID`.
  No retry occurred and restoration passed. The 991-byte repair retains and
  submits the matched loop index; full offline and CI gates remain mandatory
  before another C6.
- The final fresh attempt on exact implementation commit `04dd70f` passed
  candidate/UI agreement, read purity, and stale-source rejection. Its one
  separately authorized write returned verified active-build success: the same
  worker stayed on the same plot and active turn, movement fell, the exact
  requested build became active, protected plot facts remained unchanged, and
  the watcher and UI agreed. No popup, movement, other unit action, or turn
  advance occurred. The private audit was mode `600` with the expected two
  records, and shutdown restored the exact baseline. C6 is complete; the
  immediate-completion branch remains offline-only.
- D4/C7 is complete. Immutable tag `v1.2.0` points to release commit
  `6210a4e`; exact-commit and tag CI passed on Python 3.11/3.13, duplicate
  wheel/sdist contents matched, both artifact formats installed cleanly, and
  the two published assets matched their recorded SHA-256 values after a fresh
  download.

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
- `civ5_agent.api` is the contract-tested aggregate Python surface through the
  stable 1.2 capabilities and the 1.3.0 schema 8 release candidate.
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

Future live tests require explicit user authorization for the documented
`live_session prepare`/`restore` procedure and application launch. This
repository does not own background application lifecycle. An independent
external composition root may automate normal launch and quit after that
authorization, but it cannot bypass or weaken the core's host safety checks.

## Recommended order

1. Keep `v1.3.0` immutable and monitor downstream integration feedback.
2. Route future mechanics through the strategy-neutral capability-request
   process before changing the stable core surface.

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
