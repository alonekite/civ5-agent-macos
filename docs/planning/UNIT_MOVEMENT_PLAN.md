# Verified Unit Movement Development Plan

Status: Approved implementation plan; implementation in progress

Progress: D0–D3 and C0–C4 are complete as of 2026-09-17. ADR-0032 selects the
stock selected-unit network path, and schema 6 now implements the bounded
per-unit read model offline. The bounded command and exact read-after-write
verification and deterministic TurnPlan integration now pass offline tests. C5
full offline-gate reconciliation is next. No live or released support is
advertised yet.

Target milestone: M9

Expected first compatible release: 1.1.0, only after target-machine verification

Capability request: [GitHub Issue #1](https://github.com/alonekite/civ5-agent-macos/issues/1)

## Objective

Add a strategy-neutral, allowlisted unit-movement capability to the execution
core. A caller supplies the unit and exact destination. The core validates the
request against fresh live state, submits only a supported Civ V mechanic, and
establishes the outcome by re-reading state.

The initial design target is one explicit move to an adjacent plot. This keeps
route choice outside the core and makes the postcondition bounded. Source and
target-machine evidence may refine that scope before the command contract is
accepted; it must not silently expand to autonomous path choice.

## Ownership boundary

The downstream tactical layer owns:

- which unit should move;
- the ordered adjacent destinations or other explicit route representation;
- tactical purpose, ranking, timing, and alternatives;
- replanning after a terminal core result and fresh observation.

This execution core owns:

- observable unit and plot facts needed for safe admission;
- stable identifiers, coordinate validation, and exact command arguments;
- current legality checks through supported game APIs;
- bounded submission, duplicate suppression, and unknown-outcome handling;
- read-after-write verification and factual result reporting.

The first capability does not attack, capture a civilian, found a city, embark,
disembark, automate, choose a route, choose an alternative destination, or
retry an ambiguous submission. Any of those mechanics needs a separately
reviewed capability.

## Documentation workstream

Documentation changes precede the public implementation contract. A document
must describe only its current evidence level; planned or offline behavior is
never labeled live-verified.

### D0 — Register and bound the capability

1. Maintain the accepted `CoreCapabilityRequest: move_unit` in GitHub Issue #1
   and keep it linked to this plan.
2. Record the requesting tactical contract/domain, the reusable mechanic, the
   current API gap, absence behavior, and target-machine evidence required.
3. Confirm that an adjacent single-step action is sufficient for the first
   downstream integration slice, or record the concrete reason it is not.

Exit: the request is strategy-neutral and has no alternate write path.

### D1 — Research and decide the movement mechanic

1. Inspect bundled Civ V Lua/UI sources for movement, plot lookup, mission
   submission, legality predicates, asynchronous/deferred behavior, and stock
   UI blockers.
2. Record conclusions and unresolved questions in `docs/RESEARCH_NOTES.md`.
3. Add `ADR-0032` defining the movement execution boundary, initial movement
   granularity, verification rule, and treatment of partial or unknown results.
4. Add or update the movement-specific risk in the risk register.

Exit: no command code is written until the proposed game API, scope, and
observable postcondition are explicit.

### D2 — Freeze the contracts before enabling the write

1. Add `docs/contracts/unit-movement.md` as the owning semantic contract.
2. Update the live-state contract for any visible plot or legal-target fields.
3. Update the command contract with exact `move_unit` arguments and bounds.
4. Update the TurnPlan contract for ordering, state continuity, and interruption
   after a movement result.
5. Update bridge, controller, public-API, CLI, and downstream-integration
   documents without advertising live support yet.

Exit: identifiers, fields, schema changes, preconditions, postconditions,
refusal states, timeouts, ambiguous outcomes, and compatibility impact have one
authoritative definition.

### D3 — Define verification before the live session

1. Add offline cases to the test strategy and matrix.
2. Add a bounded movement procedure to the live-test checklist, including
   preparation, observation, one authorized move, expected state deltas,
   negative cases, watcher shutdown, and exact host restoration.
3. Add the pending capability to the Chinese live-verification ledger.
4. Identify which negative branches can be tested safely offline and which
   require a later operator-authorized real-game session.

Exit: the operator can follow one finite procedure without improvising commands
or exposing private match data.

### D4 — Record evidence and release compatibility

After implementation and live testing:

1. record only sanitized conclusions in the experiment log;
2. update the verification matrix and live-status ledger;
3. move `move_unit` from absent to supported in the downstream capability
   profile only after the required live evidence passes;
4. update project state, roadmap, milestone, changelog, development log, public
   API inventory, and release-readiness evidence;
5. release through the existing semantic-version and artifact runbook.

## Code workstream

### C0 — Offline API reconnaissance

- Locate the stock UI path used for ordinary unit movement.
- Determine whether the relevant methods are callable in the verified InGame
  FireTuner context.
- Determine whether command return, immediate coordinates, mission queue,
  movement points, and readiness can distinguish rejection, success, partial
  progress, deferred execution, and unknown outcome.
- Confirm the generated Lua can remain within the 1,000-byte limit.

No live write is authorized in this stage.

### C1 — Extend observable state only as needed

- Add the minimum active-player-visible plot or legal-target facts required by
  the accepted contract.
- Preserve strict schema validation, ordering, bounds, segmentation, and legacy
  schema compatibility where promised.
- Do not expose hidden map, unmet-player, or speculative path information.
- Add malformed, oversized, duplicate, unknown-version, and legacy fixtures.

Gate: the read model must pass offline tests before any movement command exists.

### C2 — Add the allowlisted command

- Add `move_unit` to the command schema only after D1–D2 are accepted.
- Validate stable unit identity and bounded integer coordinates exactly.
- Re-read the current state and reject stale ownership, position, movement,
  destination, or legality assumptions before submission.
- Generate one bounded Lua program using only the selected supported API.
- Preserve UUID duplicate suppression and never retry an unknown outcome.

Gate: command validation and Lua generation pass exhaustive offline positive and
negative tests, including the 1,000-byte pre-send bound.

### C3 — Verify the result

- Re-read state after submission.
- Require the exact accepted postcondition, including unit identity, expected
  destination, and any movement/readiness invariants chosen by the contract.
- Distinguish explicit rejection, unchanged-state failure, stale state, partial
  or unexpected displacement, timeout, and transport ambiguity.
- Treat disappearance, transformation, combat, capture, embarkation, or any
  uncontracted side effect as failure or recovery-required, never success.

Gate: no return marker or transport acceptance alone can establish success.

### C4 — Integrate deterministic TurnPlan execution

- Permit only an explicit plan-listed `move_unit` action.
- Preserve before/after state continuity before advancing the action index.
- Stop on newly surfaced requirements or uncontracted state changes.
- Do not synthesize a destination, reorder route steps, skip a blocked step, or
  replan.
- Cover direct bridge use, TurnPlan execution, event emission, journaling
  composition, cached-result reconciliation, and CLI envelopes.

### C5 — Complete offline verification

At minimum cover:

- valid adjacent move;
- unknown, foreign, stale, immobile, or already-used unit;
- malformed/out-of-range coordinates and non-adjacent destination;
- illegal, hidden, occupied, blocked, combat-producing, embark/disembark, or
  otherwise unsupported target;
- state drift before submission;
- explicit game rejection and unchanged post-state;
- unexpected/partial displacement;
- timeout or missing command marker;
- cached terminal result and no-retry reconciliation;
- multi-action TurnPlan continuity after a verified movement;
- schema compatibility and stable public export behavior.

Run the complete warning-enabled suite on every supported Python runtime before
requesting live verification.

### C6 — Bounded target-machine verification

Only with the user present and explicitly authorizing the documented live
procedure:

1. prepare the guarded FireTuner/firewall session;
2. start one watcher and observe the required state;
3. execute one safe movement in a controlled game state;
4. prove the exact postcondition from a fresh snapshot;
5. exercise only the preselected safe negative branch, if required;
6. quit the game, allow the watcher to close, restore the exact machine
   baseline, and verify shutdown;
7. retain raw state, plans, journals, and audit data privately and commit only
   sanitized conclusions.

An offline pass does not enable the capability in the published profile.

### C7 — Stabilize and release

- Promote the capability through `civ5_agent.api` and `civ5-turn` only as
  specified by the accepted contracts.
- Update the static downstream profile and require downstream adapter fixtures.
- Use at least a minor version because this adds a backward-compatible public
  capability; the planned version is 1.1.0.
- Repeat full tests, scans, duplicate builds, clean installs, exact-commit CI,
  immutable tag CI, publication, and downloaded-asset hash verification.

## Safe batch order

Each numbered batch must be independently reviewable, tested, documented,
committed, and pushed before the next begins:

1. D0 request plus this M9 planning baseline;
2. C0/D1 source research, risk, and ADR-0032 (complete 2026-09-17);
3. D2 contracts and D3 verification design (complete 2026-09-17);
4. C1 read-model implementation and tests (complete 2026-09-17);
5. C2/C3 bridge command and verification with offline tests (complete 2026-09-17);
6. C4 executor, watcher, journal composition, API, and CLI integration (complete 2026-09-17);
7. C5 full offline gate and documentation reconciliation;
8. C6 operator-assisted live verification;
9. D4/C7 stabilization and 1.1.0 release preparation.

If research disproves the proposed API or postcondition, stop after a complete
documented batch and revise the ADR/contract plan before writing around the
failure.

## Definition of done

M9 is complete only when:

- the tactical/execution ownership boundary is preserved;
- the public contracts and schemas are versioned and fail closed;
- one exact supported movement succeeds through direct verified action and an
  explicit TurnPlan;
- every submission outcome is verified, rejected, or conservatively classified
  without automatic retry;
- required positive and negative branches have their stated offline or live
  evidence;
- private match data and host identifiers remain outside source and artifacts;
- the downstream profile advertises only what the released core actually
  supports;
- the release artifacts pass the existing reproducibility and publication
  gates.
