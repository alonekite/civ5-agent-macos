# Verified Worker Build Development Plan

Status: D0–D3, C0/D1, and C1–C5 complete offline; C6 read/admission evidence is
partial, but write attempts have not reached a verified postcondition; a fresh
C6 requires a published numeric action-index repair and authorization

Target milestone: M10

Expected first compatible release: 1.2.0, only after bounded target-machine
verification

Capability request: [GitHub Issue #2](https://github.com/alonekite/civ5-agent-macos/issues/2),
submitted by the `civ5-short-term-tactical-layer` owner in the project task on
2026-09-17 and normalized here as the durable owning plan.

## Objective

Add a strategy-neutral, allowlisted worker-build capability to the execution
core. A caller supplies an exact active-player unit and stable `BUILD_*`
identifier. The core exposes a conservative set of currently admissible
ordinary builds for that unit on its current plot, validates the request against
fresh live state, submits one stock game action, and establishes the factual
outcome by re-reading state.

The first slice is intentionally narrower than all Civ V worker behavior:

- the worker is already standing on the intended plot;
- the caller chooses the unit and exact build;
- the build creates one ordinary land improvement with an exact observable
  improvement postcondition;
- the command neither moves the unit nor chooses an alternative action;
- route construction, repair, feature-removal-only actions, automation,
  water builds, special/consuming builds, and tactical recommendations are
  excluded until separately requested and verified.

The frozen action is `worker_build(unit_id, x, y, build_type)`. Coordinates
preserve the exact caller-authorized plot; `worker_build` is preferred over
`start_worker_build` because an eligible build may complete immediately and
therefore never remain observable as an active build.

## Capability request

1. **Requester, contract, and domain:** `civ5-short-term-tactical-layer`, its
   future worker-domain adapter, and current-turn worker execution.
2. **Reusable fact/mechanic:** active-player-visible current-plot facts; a
   bounded set of ordinary `BUILD_*` actions currently admissible for a unit;
   its current build; and one verified exact worker-build action.
3. **Current insufficiency:** core 1.1.0 can read and move a unit, but exposes no
   worker-build candidates and admits no construction action.
4. **Identifiers and shape:** exact integer `unit_id`, exact bounded `x` and
   `y`, stable `build_type`, and a sorted list of at most 32
   `{build_type, improvement_type}` candidates associated with that unit.
   Schema 7 field names and the 64-character identifier limit are frozen by
   D2.
5. **Live preconditions/postconditions:** the active turn, player, bridge
   session, state basis, unit identity, current coordinates, unit ownership,
   capability, movement/readiness, current build, and candidate membership must
   still match. Success requires either the requested build to be actively
   observable on the same unit and plot, or the exact requested improvement to
   be observably complete on that plot.
6. **Failure behavior:** malformed, stale, unsupported, unavailable, or
   mismatched requests fail closed. Rejection, timeout, partial/unexpected
   state, and unknown outcome are never converted to success or retried
   automatically.
7. **Information boundary:** expose only facts visible to the active player.
   Do not reveal hidden resources, opponent state, AI personality, or UI
   recommendation values. Preserve bridge-session identity and fresh-state
   binding.
8. **Compatibility impact:** expect live-state schema 7, a new allowlisted
   action, public API/constants and downstream-profile updates, unchanged
   TurnPlan envelope schema if its generic action representation remains
   sufficient, and a backward-compatible 1.2.0 release.
9. **Offline evidence:** deterministic fixtures must cover exact parsing,
   candidate bounds/order/identity, every exclusion, stale source, unsupported
   schema, stock-action lookup, selection mismatch, markers, transient reads,
   active and immediate-completion postconditions, wrong/unchanged outcomes,
   timeout, UUID suppression, recovery, executor continuity, and the 1,000-byte
   generated-program limit.
10. **Target evidence:** a read-only schema/candidate probe, a safe pre-send
    refusal, one separately authorized ordinary improvement on a manually
    confirmed plot, fresh watcher observation, private audit checks, and exact
    host restoration.
11. **Absent/incompatible behavior:** the consumer reports the worker domain as
    unsupported and emits no worker-build `PlannedAction`; it must not call
    FireTuner or another game-write path directly.

## Ownership boundary

The downstream tactical layer owns:

- which worker and plot should be used;
- movement required to reach that plot;
- which improvement serves the current tactical plan;
- ordering, opportunity cost, scoring, alternatives, and replanning;
- interpretation of terrain, yields, resources, threats, and strategic intent.

This execution core owns:

- the minimum active-player-visible facts needed to admit the exact action;
- stable identifiers, bounds, freshness checks, and conservative candidates;
- stock-mechanic dispatch through the single watcher-owned connection;
- duplicate suppression and unknown-outcome handling;
- read-after-write verification and factual result reporting.

The core must never expose or use `IsActionRecommended`, select an improvement,
move the unit, search a route, or continue with an alternate build.

## Design questions that block command code

1. Can the target runtime safely call `unit:CanBuild(unit:GetPlot(), build_id)`
   without UI selection, and is it conservative enough to populate candidates?
2. Can the command select the exact unit, verify the head selection, re-check
   `Game.CanHandleAction(action_index)`, and call `Game.HandleAction` within the
   1,000-byte FireTuner program limit?
3. Which `GameInfo.Builds` fields define the initial ordinary-improvement
   allowlist without admitting repair, routes, removal-only, water, consuming,
   or special actions?
4. Which current-plot fields are both active-player-visible and sufficient to
   prove exact immediate completion without leaking hidden resources?
5. Does selection or build dispatch have deferred behavior requiring bounded
   polling, and which intermediate states are non-terminal rather than success?

D1 must answer these questions from bundled sources, offline probes, and, only
when necessary, a separately authorized read-only target session. Unresolved
questions keep the write unsupported.

## Delivery sequence

### D0 — Register and bound the request

Status: complete.

1. Preserve this complete request in a GitHub Issue and link it here.
2. Confirm the tactical consumer's absent-capability behavior.
3. Keep the first slice limited to an ordinary improvement on the unit's
   current plot.

Exit: the request is durable, strategy-neutral, and has no alternate write
path.

### C0/D1 — Research and decide the stock mechanic

Status: complete under ADR-0033.

1. Inspect the target BNW `UnitPanel.lua`, Lua bindings, released SDK source,
   and local ruleset tables for candidate enumeration, action mapping,
   selection, dispatch, progress, and completion facts.
2. Add bounded read-only probes only if source evidence cannot settle a target
   runtime question.
3. Record ADR-0033 for enumeration, dispatch, exclusions, and verification.
4. Track selection-dependent legality and ambiguous immediate completion under
   R-018.

Exit: the target action path and both success branches are explicit and fit the
transport bound. Otherwise M10 returns to design without command code.

Outcome: selection-free `unit:CanBuild` candidates feed a selected-unit
`Game.HandleAction` submission. The first slice requires blank featureless land
and non-route, non-repair, non-water, non-consuming improvement builds. Exact
active-build and immediate-completion branches are defined. Read-only segment
prototypes measured 688/895 bytes and the worst-case compact write prototype
measured 994 bytes; final strings still require executable bound tests.

### D2 — Freeze contracts

Status: complete. The owning contract is
`docs/contracts/worker-build.md`.

1. Add `docs/contracts/worker-build.md` as the owning semantic contract.
2. Update live-state, command, TurnPlan, bridge, controller, public API, CLI,
   and downstream contracts.
3. Define schema 7 fields, limits, exact exclusions, arguments, preconditions,
   postconditions, polling, terminal states, and compatibility behavior.

Exit: one authoritative contract defines every accepted and rejected state;
the capability is still not advertised as implemented or live-verified.

Outcome: schema 7 adds mandatory current-plot context, current build, and up to
32 sorted ordinary-build candidate pairs per unit. Stable build/improvement
identifiers are capped at 64 characters. `worker_build` carries exact unit,
coordinates, and build type; success requires lower movement plus either the
exact active build or exact completed paired improvement. TurnPlan schema 1,
result/report/event schemas, journal schema, and stable CLI envelopes remain
unchanged. Core 1.1 continues to reject the action.

### D3 — Freeze verification before the write

Status: complete. The exact matrix and evidence allocation are frozen in
`docs/testing/WORKER_BUILD_VERIFICATION.md`; the finite operator procedure is
section 8 of `docs/LIVE_TEST_CHECKLIST.md`.

1. Extend the test strategy and verification matrix with the complete negative
   and uncertainty matrix.
2. Add a finite operator procedure to the live checklist and Chinese evidence
   ledger.
3. Separate read-only candidate proof, safe local rejection, the one authorized
   write, audit verification, and exact restoration.

Exit: the live procedure requires no improvised Lua or private state capture.

Outcome: WB-S01–A02 cover schema, predicates, privacy, arguments, admission,
game-side guards, markers, both success branches, failures, uncertainty,
watcher/audit/UUID semantics, TurnPlan continuity/recovery, compatibility,
artifacts, and privacy. C6 permits only one stale-source rejection and one
separately confirmed candidate write after C1–C5; either success branch may
close the live gate, while the other remains fully covered offline.

### C1 — Implement schema 7 read state

Status: complete offline. Development head emits nine coherent parts and
exports schema/limit constants without adding `worker_build` to the allowlist.

Expose only the contract-approved current-plot context, current build, and
bounded ordinary-build candidates. Validate identifiers, ordering, uniqueness,
unit association, legacy compatibility, multi-part consistency, and payload
bounds. No read operation may change UI selection.

Outcome: two 688/881-byte read programs use active-team resource visibility,
never select a unit, and emit exact current-plot/current-build/candidate facts.
Parser and validation enforce mandatory parts, unit binding, identifier and
count limits, exact nested shape, nulls, stable sorting, duplicates, and schema
2–6 compatibility. The target runtime exposed `GameInfoActions` as an indexed
table rather than a callable iterator during the first C6 attempt; numeric
iteration and a no-call regression assertion now cover that shape while
retaining the sub-900-byte bound. WB-S01–S06 and schema 7 movement
compatibility pass offline.

### C2 — Implement the allowlisted command

Status: complete offline.

Resolve the exact active-player unit and build action, repeat source and
legality guards in game-side Lua, establish and verify exact selection if the
stock path requires it, dispatch once, and return one bounded marker. Preserve
UUID duplicate suppression and no-retry semantics.

Outcome: exact four-field validation and fresh schema 7 admission precede a
991-byte worst-case selected-unit stock program. The program re-resolves the
unit, plot, build and matching action, repeats mutable guards, verifies exact
selection and `CanHandleAction`, calls `Game.HandleAction` once, and emits one
bounded private marker. Watcher forwarding retains its existing session, UUID,
audit, journal and unknown-outcome semantics.

### C3 — Implement factual verification

Status: complete offline.

Use fresh schema 7 state and bounded polling. Multi-turn success requires the
same unit and plot to report the requested active build. Immediate-completion
success requires the same plot to report the exact contract-mapped improvement.
Movement to another plot, a different build/improvement, unchanged state,
identity/turn drift, disappearance, capture, timeout, or malformed evidence is
not success.

Outcome: an accepted marker only begins bounded polling. Success requires the
same schema 7 turn/player/unit/type/coordinates, lower movement, unchanged
non-improvement plot facts, and exactly one active-build or completed-
improvement branch. Explicit refusal and wrong results fail; malformed or lost
post-submission transport remains unknown and is never retried.

### C4 — Integrate deterministic execution

Status: complete offline.

Allow an explicit worker-build action in schema 1 TurnPlans only if the generic
envelope remains sufficient. Preserve ordering and state continuity, cover only
the exact unit requirement, pause on newly uncovered requirements, emit factual
events, journal the existing generic command lifecycle, and apply the same
conservative cached-result recovery rules.

Outcome: schema 1 plans preserve the four exact arguments but require a schema
7 basis when they contain `worker_build`. The action covers only its exact unit,
supports an explicit prior move, and pauses when the unit remains ready without
a later explicit move/build/skip. The executor independently validates both
worker result branches and state continuity. Cached recovery requires the same
command, the same postcondition, and matching fresh state, then pauses before
the next action.

### C5 — Complete the offline gate

Status: complete.

Run the full supported Python matrix, contract checks, release-artifact checks,
sensitive-information scan, generated-program bounds, and all worker-build
negative/recovery cases. No target claim follows from this gate.

Outcome: 335 warning-enabled tests pass on Python 3.11 and the default runtime.
The complete worker matrix covers schema, admission, dispatch, markers, both
result branches, drift, timeout, uncertainty, watcher/audit/journal/UUID
behavior, TurnPlan continuity/recovery, and compatibility. Two independently
built wheel and sdist pairs have matching normalized content, install cleanly,
and expose `1.2.0.dev0`; tracked and unpacked-artifact sensitive-content scans
are clean. No target-machine claim follows.

### C6 — Complete bounded target verification

With the operator present, use the standard recoverable live session. Confirm
schema 7 and a manually inspected ordinary build candidate, prove one safe
pre-send rejection, obtain separate confirmation for one exact build, observe
the active/completed postcondition and watcher update, verify private audit
permissions, exit Civ V, and restore the exact host baseline.

Attempt status: the 2026-09-18 attempt stopped at the first read-only gate when
the candidate segment called target-runtime `GameInfoActions` as a function.
The 2026-09-19 retry passed that point but stopped when the target
`unit:CanBuild` binding required numeric option flags. Neither attempt submitted
a command or write, and exact restoration passed both times. Indexed iteration
and ADR-0034 integer flags are repaired offline; the new repair must be
committed, pushed, and pass CI before a separately authorized restart.

A later attempt passed the repaired schema 7 read gate and manually matched one
candidate to the stock UI. Its stale-source request was rejected before write
submission with unchanged state. The separately authorized write was sent only
once, but the generated Lua joined numeric literals to following `or`/`then`
keywords and failed parsing without a valid marker. The game showed no build or
movement change; the command was not retried and exact restoration passed. C6
therefore remains open until the lexical repair passes the complete offline/CI
gate and a new session proves one exact postcondition branch.

The next fresh attempt passed those read and rejection gates again. Its sole
authorized write parsed and returned explicit `invalid_build` because the
write path indexed the target's numeric `GameInfoActions` table with a build
type string. Before/after state and UI were unchanged, there was no retry, and
restoration passed. The write program must instead perform bounded numeric
iteration with exact Type/SubType/MissionData matching, remain below 1,000
bytes, and pass the complete offline/CI gate before another fresh C6.

The following attempt passed numeric resolution but returned explicit
`blocked`. Installed BNW UI inspection showed the matched table entry's `ID`
is not the value used by the stock click path: both `Game.CanHandleAction` and
`Game.HandleAction` receive the numeric `GameInfoActions` loop index. State and
UI remained unchanged, no retry occurred, and restoration passed. The compact
program must retain and submit that exact index, forbid entry-ID dispatch in
regression coverage, and pass the full offline/CI gate before another C6.

### D4/C7 — Publish the compatible release

Record sanitized evidence, update every owning contract/profile/matrix/log,
prepare 1.2.0 release notes, scan artifacts, run exact-commit and tag CI, and
publish only after explicit release approval. A failed C6 leaves the action
absent from the stable profile.

## Initial source evidence

Evidence level: bundled-source inspection only; not live verification.

The installed BNW `UnitPanel.lua` enumerates `GameInfoActions`, treats
`ACTIONSUBTYPE_BUILD` actions as builds, maps `action.MissionData` to a build
identifier, uses `Game.CanHandleAction(action_index)` for current
executability, and sends a click through `Game.HandleAction(action_index)`. It
reads ongoing work with `unit:GetBuildType()` and build duration with plot
`GetBuildTurnsLeft`/`GetBuildTurnsTotal`. The same UI also reads
`unit:IsActionRecommended`, but recommendation data is explicitly outside this
capability.

This evidence supports the proposed stock path but does not yet prove safe
per-unit candidate enumeration, selection-independent legality, exact
immediate-completion verification, or target-runtime behavior. Those are D1
exit conditions.
