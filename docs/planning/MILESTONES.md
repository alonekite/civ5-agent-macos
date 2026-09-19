# Milestones

Milestones describe outcomes and acceptance criteria. Task-level work belongs in
GitHub Issues and should link back to one milestone ID.

| ID | Milestone | Status | Depends on |
|---|---|---|---|
| M0 | Environment reconnaissance | Complete | — |
| M1 | Bidirectional bridge MVP | Complete | M0 |
| M2 | Verified action layer | Complete | M1 |
| M3 | Ruleset knowledge coverage | Complete | M1 |
| M4 | Ruleset knowledge view | Complete | M3 |
| M5 | Factual turn journal | Complete | M1, M2 |
| M6 | Deterministic turn executor | Complete | M2 |
| M7 | Public API stabilization | Complete | M4, M5, M6 |
| M8 | 1.0 release readiness | Complete | M7 |
| M9 | Verified unit movement | Complete | M8, M2, M6 |
| M10 | Verified worker build | Release preparation | M9, M2, M6 |

## M0 — Environment reconnaissance

Acceptance criteria:

- Identify the macOS, CPU architecture, game distribution, application build,
  user-data directories, Lua runtime evidence, DLC footprint, and candidate IPC
  mechanisms.
- Distinguish confirmed, rejected, and inconclusive findings.
- Preserve target-machine evidence in the experiment log.

Evidence: `docs/EXPERIMENT_LOG.md`, 2026-09-12 reconnaissance and mod-loading
experiments.

## M1 — Bidirectional bridge MVP

Acceptance criteria:

- `python -m civ5_agent.watch` observes genuine live game-state changes.
- `python -m civ5_agent.command end_turn` advances one turn.
- Python proves success by re-reading game state.
- The original signed application remains unmodified.

Evidence: `docs/EXPERIMENT_LOG.md`, 2026-09-12 FireTuner read and rich-read/end-
turn experiments.

## M2 — Verified action layer

Acceptance criteria:

- Actions use an explicit allowlist and strict argument schemas.
- Every write checks Civ V capability predicates and verifies its result.
- Command UUIDs, audit records, duplicate suppression, bounded IPC, and safe
  failure behavior are tested.
- At least end turn, research selection, and city production are live-verified.

Completed extension: `skip_unit` is live-verified using unit readiness with
unchanged identity, location, and remaining movement.

## M3 — Ruleset knowledge coverage

Acceptance criteria:

- Import stable identifiers, numeric facts, prerequisites, replacements,
  unlocks, upgrade paths, constraints, and provenance for structural queries
  and future decision-support consumers.
- Cover technologies, eras, policies, ideologies, units, promotions, buildings,
  wonders, resources, civilizations, leaders, traits, religions, beliefs, great
  people, specialists, terrain, features, improvements, routes, projects,
  processes, yields, and required global/scaling rules.
- Validate references and declared vanilla/G&K/BNW family.
- Exclude AI flavor/personality data and copyrighted descriptive assets.
- Produce byte-for-byte repeatable canonical output from unchanged sources.

Completed coverage slices: civilizations, leaders, deterministic trait effects,
unique/disabled unit and building class overrides, religions, core beliefs, and
specialists/great-person classes, terrains, ordinary and fake features,
improvements, routes, yields, build actions, projects, processes, victory rules,
their direct relationships, and binary quantity-bearing effects and resource
requirements across 84 single-value table families plus project victory
thresholds. Schema 3 now covers 22
single-context belief, building, improvement, and policy effect-table families.
Unit-combat categories, domains, special-unit categories, unit and promotion
applicability, category modifiers, and contextual trait promotion grants are
also complete. Promotion modifiers against domains, features, terrains, and unit
classes, including technology-conditioned passability, are imported without
Pedia metadata. Unit capture, technology, ancient-ruin upgrade, policy, cargo,
project, and leader-promotion identifiers now have typed references. Resource
placement, faith-purchase eligibility, local prerequisites, training
restrictions, random promotions, and unit build capabilities are also typed.
Additional building-class, domain, free-unit, trade-route, trait, and combat
yield quantities are imported, including three typed trait contexts.
Improvement/resource multi-attribute rules and building yields derived from a
validated enhanced-yield technology are also complete.
Hurry methods and their building/policy cost modifiers are first-class typed
knowledge without importing descriptions.
Great-work classes, slot types, and building slot capacity have typed
relationships without importing individual work content or presentation assets.
Great-work stable IDs, artifact classes, archaeology flags, and typed
class/era/creator relationships are imported while names, quotes, images, and
audio remain excluded.
Building theming bonuses preserve all 21 deterministic matching alternatives
across 10 buildings without descriptions, AI priorities, or synthetic IDs.
The remaining-rule inventory found no core-facing effect requiring more
than one context item; AI role/formation data remains excluded. Region entities,
civilization start facts, and technology-conditioned build/feature rules are
complete. Game-speed, handicap, world-size, and ancient-ruin facts are also
complete without AI decision heuristics or presentation fields. World Congress
resolutions, decisions, sessions, projects, rewards, and votes are complete with
typed relations. Minor-civilization identities and deterministic trait
membership are complete. The policy/building remainder audit found only
prohibited flavor tables outside the importer. The broader map/calendar audit
is complete. Civilization starting facts include initial unit-class quantities
and coastal placement without reading AI roles. Fifteen global constants needed
for movement, health, growth, purchase, and upgrades are allowlisted under
ADR-0012.
Climates, sea levels, and game options now preserve map-generation and stable
ruleset-switch facts, while promotion invisibility/detection targets are typed.
Calendar/date presentation families and city-size soundscape categories are
explicitly outside M3. Nine resource map-quantity alternatives are embedded in
their six owning resources with canonical ordering and strict validation.

M3 completed on 2026-09-15. Every reviewed non-empty candidate family is now
imported, explicitly deferred with a semantic reason, or excluded under an
accepted boundary. New families remain positive-allowlist extensions rather
than reopening the milestone.

## M4 — Ruleset knowledge view

Acceptance criteria:

- Preserve immutable base ruleset facts.
- Validate a complete declared ruleset, game speed, difficulty, map size,
  civilization, adopted-policy set, and active-belief set.
- Return detached canonical entities and source provenance.
- Resolve structural unit/building class identity to its default,
  civilization replacement, or explicitly disabled result.
- Reject incomplete or incompatible context instead of guessing.
- Exclude scalar composition, candidate scoring, prediction, route evaluation,
  strategy, tactics, and action selection from the execution core.

M4 completed on 2026-09-15. The structural view requires exact identifiers,
canonicalizes set-like selections, rejects unknown and duplicate values, and
returns detached selected entities plus source provenance. Unit and building
classes resolve to a default, civilization replacement, or explicit disabled
result while retaining base and override references. ADR-0014 moves effective
scalar and counterfactual analysis to future consumer-driven decision-support
skills rather than the current execution core.

## M5 — Factual turn journal

Acceptance criteria:

- Append every supported snapshot, turn transition, command envelope, command
  result, before/after state, and verification error actually captured and
  validated while recording one declared match.
- Give the journal an explicit `match_id`; reject unbound
  `bridge_session_id` values and require append-only bindings for later sessions.
- Use versioned canonical records, private permissions, bounded record sizes,
  monotonically increasing sequence numbers, and integrity checks.
- Detect truncation, tampering, broken ordering, and cross-game mixing.
- Provide deterministic replay/export without summarizing or inferring facts.
- Define an extensible record-kind boundary so optional application orchestration
  can later record M6 plan/execution events without weakening append-only
  integrity or making M5 an execution dependency.
- Consume validated in-memory command results; correlate the independent M2
  audit by command UUID without parsing it as journal input.
- Do not implement working memory or strategic memory.

Current progress: the schema 1 codec and private hash-chained JSONL store are
implemented offline under ADR-0017, ADR-0019, and ADR-0020. Identity validation,
explicit session binding, locking, fsync, permissions, bounds, corruption,
truncation, concurrency, correction, and reopen behavior have unit coverage.
Opt-in watcher composition records changed validated snapshots and grounded
in-memory command results, with explicit new/resume semantics and independent
audit/journal failure handling. Pre-execution submissions, unsuccessful results,
and observed turn transitions are included. It rejects partial database-fallback
state and unvalidated snapshots. Deterministic verification, explicit private-
payload replay, redacted structural export, and manual retention guidance are
implemented under ADR-0021. All acceptance criteria are implemented offline;
the first target-machine attempt confirmed capture/integrity/replay/export but
exposed an exception-lifecycle gap. ADR-0028 fixed that gap, and the second
attempt live-verified a complete failed-command submission/result/verification
lifecycle plus integrity/replay/export. A fourth attempt completed one explicit
command, captured its successful result and automatic turn transition in the
same private journal, and passed integrity, replay, export, permission, and
exact-restoration checks. M5 acceptance is complete.

## M6 — Deterministic turn executor

Acceptance criteria:

- Consume a versioned explicit `TurnPlan`; never invent missing plan content.
- Validate target bridge session, turn, active player, state basis, action
  ordering, and every declared precondition before writing.
- Execute only plan-listed allowlisted actions through bridge verification and
  advance only after each write-after-read postcondition succeeds.
- Report factual unresolved turn requirements without selecting how to satisfy
  them.
- Pause safely on stale state, new blockers, unsupported actions, failed
  verification, or ambiguous recovery; never replan automatically.
- Emit bounded factual plan/execution events that optional application
  orchestration may append to M5 without affecting execution results.
- Require `end_turn` to be an explicit final plan action.
- Never require an LLM.

The existing `civ5_agent.controller` remains an MVP readiness proof and
provisional compatibility surface. M6 will not expand it into game strategy and
depends only on bridge state/session/action contracts, not M4 knowledge or M5.
The current choice to implement M5 first is project scheduling only. See
ADR-0015 through ADR-0018, ADR-0022, and the turn-plan contract. Schema 1 plan,
action, state-basis, execution-report validation, and factual requirement
inspection are implemented offline. The ordered in-process core re-reads before
every action, proves bridge-result state continuity, pauses on uncovered
requirements/drift, and never retries an ambiguous submission. Optional factual
events are bounded and sink failures cannot alter execution. Watcher/CLI
adaptation is implemented through the existing private watcher socket without
opening another FireTuner connection. Its session-scoped read-only completed-
command lookup never turns a cache miss into a retry. Conservative report
reconciliation validates cached evidence and fresh state, completes a recovered
final end-turn, and pauses after a recovered non-final success. CLI plan loading
and explicit execution are implemented as a strict 64-KiB watcher-only JSON
surface under ADR-0024. All M6 acceptance criteria are implemented offline;
live plan validation is confirmed, but the first execution exposed target
FireTuner truncation. ADR-0028 compacts and pre-bounds the action program
and the second attempt confirmed intact marker delivery plus stale-plan
pre-write refusal. That attempt also exposed an incorrect numeric zero-blocker
assumption. ADR-0029 now uses the game-defined no-blocker enum and checks the
numeric blocker independently of UI clickability. A third attempt proved that
corrected guard and actual stock control execution, then precisely failed when automated/deferred unit activity
surfaced a new worker requirement without advancing. A fourth attempt completed
a newly authored one-action plan and verified automatic one-turn advancement
through the watcher path. M6 acceptance is complete; the earlier attempts
remain useful failure-path evidence.

## M7 — Public API stabilization

Acceptance criteria:

- Define supported read, action, knowledge-view, journal, turn-plan, and
  execution-report APIs.
- Publish schema versions, compatibility guarantees, error semantics, and size
  limits.
- Add contract tests for supported Python versions.
- Separate public interfaces from FireTuner and local-database implementation
  details.

Current progress: the cross-module inventory identifies versioned contracts,
implementation-only internals, and current limits. The session-aware watcher
bridge client exposes live reads, verified individual actions, and cached-result
lookups independently of M6 under ADR-0025. ADR-0026 defines the contract-tested
`civ5_agent.api` aggregate surface, compatible error categories, and initial
change policy. ADR-0027 stabilizes only the bounded `civ5-turn` envelopes and
exit meanings while explicitly retaining all other command-line entry points as
provisional. The current supported consumers are served by `KnowledgeIndex`,
verified journal operations, and the aggregate surface; no demonstrated need
justifies speculative selective queries. ADR-0030 promotes the two supported
surfaces to stable 1.0 compatibility. All M7 acceptance criteria are met.

## M8 — 1.0 release readiness

Acceptance criteria:

- Complete the required bounded live verification matrix.
- Give every high-impact risk an explicit controlled, accepted, or closed
  disposition with evidence and scope limits.
- Provide setup, security, recovery, upgrade, and release documentation.
- Publish the downstream ownership/capability boundary and future core
  capability request procedure.
- Run tests and sensitive-information scans on the release artifact.
- Tag a reproducible version without generated game data or private logs.

M8 completed on 2026-09-16. The exact release commit passed local and GitHub
Actions testing, duplicate artifact inspection, normalized-content comparison,
clean wheel/sdist installation, and sensitive-content review. The immutable
`v1.0.0` tag and published GitHub assets were downloaded and matched their
recorded SHA-256 hashes. ADR-0031, the downstream integration contract, and the
core capability request procedure define the first tactical consumer and future
maintenance boundary. Every high-impact risk has an explicit controlled
disposition, and the release/upgrade/rollback runbook remains authoritative.

LLM interaction, working memory, strategic memory, and MCP are not M-series
milestones. They require a separate future project plan.

## M9 — Verified unit movement

Acceptance criteria:

- Accept only an explicit unit identity and destination supplied by a caller;
  never select a unit, destination, route, or tactical alternative.
- Define and version the minimum visible read state, allowlisted command,
  TurnPlan behavior, verified result, and downstream capability contract.
- Reject stale, malformed, illegal, hidden-information-dependent, combat,
  embarkation, automation, and other unsupported movement requests before
  treating them as successful.
- Bound generated Lua, preserve UUID duplicate suppression, and never retry an
  ambiguous submission automatically.
- Verify every accepted write through fresh state and distinguish success,
  rejection, stale state, unexpected/partial displacement, and unknown outcome.
- Pass the full offline matrix and a bounded operator-authorized target-machine
  procedure, including exact host restoration.
- Publish the capability only through a compatible semantic-versioned release
  after updating the static downstream profile.

Current status: complete. D0, C0/D1 source research, D2 contracts, D3
verification design, and C1–C6 read/command/verification/executor/offline/live-
gate work are complete. ADR-0032 selects the stock selected-unit network path for an explicit
adjacent ordinary move; schema 6 emits and validates the bounded per-unit target
set offline, and the development-head bridge now admits, submits, and exactly
verifies the narrow write. Schema 1 TurnPlans now preserve exact
movement ordering, requirement coverage, continuity, events, and conservative
recovery. The bounded operator-assisted C6 target-machine procedure passed with
one safe pre-send rejection, one authorized exact adjacent move, private audit,
and exact host restoration. D4 compatibility reconciliation is complete, and
the exact-commit and tag CI, duplicate artifacts, clean installs, immutable
tag, GitHub Release, and downloaded-asset verification all passed. The owning
execution order and evidence gates are in
the [verified unit movement development plan](UNIT_MOVEMENT_PLAN.md).

## M10 — Verified worker build

Acceptance criteria:

- Accept only an exact active-player unit and ordinary `BUILD_*` identifier
  supplied by a caller; never select a worker, plot, improvement, route, or
  tactical alternative.
- Limit the first slice to a worker already on the target plot and a contract-
  approved ordinary improvement with an exact observable result.
- Define and version the minimum visible current-plot state, conservative
  per-unit candidates, allowlisted command, TurnPlan behavior, verified result,
  and downstream capability contract.
- Reject stale, malformed, unavailable, hidden-information-dependent, repair,
  route, feature-removal-only, water, consuming, automated, and other
  unsupported requests before treating them as successful.
- Verify both multi-turn active-build and immediate-completion outcomes through
  fresh state; never retry an ambiguous submission automatically.
- Pass the full offline matrix and a bounded operator-authorized target-machine
  procedure, including exact host restoration.
- Publish the capability only through a compatible semantic-versioned release
  after updating the static downstream profile.

Current status: release candidate preparation. The conversation-submitted request is registered as
[GitHub Issue #2](https://github.com/alonekite/civ5-agent-macos/issues/2) and
normalized in the [verified worker build development plan](WORKER_BUILD_PLAN.md).
Bundled BNW UI and released SDK inspection completed C0/D1. ADR-0033 selects
selection-free `unit:CanBuild` candidates plus exact selected-unit
`Game.HandleAction` dispatch, narrows the slice to blank featureless land and
ordinary non-consuming improvements, defines active/completed verification,
and records feasible sub-1,000-byte prototypes. D2 is complete: the
worker-build, schema 7, command, TurnPlan, public API, CLI, module, and
downstream contracts are frozen without changing current implementation. D3 is
also complete: WB-S01–A02 freeze the complete offline matrix and checklist
section 8 freezes one read-only proof, one stale-source rejection, one
separately authorized write, private audit verification, and exact restoration.
C1 is complete offline: schema 7 now reads and validates exact current-plot,
current-build, and bounded candidate facts through two selection-free programs,
retains schema 2–6, and preserves `move_unit` on matching schema 6+ states.
WB-S01–S06 pass. C2–C3 are complete offline: core 1.2.0 validates and admits
the exact command, generates a worst-case
991-byte guarded stock dispatch, treats its marker only as submission evidence,
and verifies both factual schema 7 result branches. C4 is also complete:
schema 1 plans now preserve exact worker arguments, independently verify the
result, cover only the exact unit, support ordered move/build, pause on newly
uncovered orders, and conservatively reconcile cached results. C5 gate
C5 is complete with the full test matrix, repeated artifact inspection, clean
installation, and privacy scans. The first C6 attempt stopped safely during
read-only collection because Campaign Edition exposes `GameInfoActions` as an
indexed table, not a callable iterator. No write ran and restoration passed.
The indexed-loop repair retained the sub-900-byte bound, but the next attempt
exposed `luaL_optint` option flags in the target `CanBuild` binding. ADR-0034
requires numeric `0, 1` flags in read and pre-submit guards; no command ran and
restoration again passed. A later attempt confirmed schema 7 candidate/UI
agreement and safe stale-source rejection, then the sole separately authorized
write failed Lua parsing because interpolated numbers touched `or`/`then`.
There was no valid marker, visible game change, or retry, and restoration
passed. The lexical-boundary repair must pass the full offline/CI gate before a
fresh operator-authorized C6. No stable downstream or live-support claim exists
yet.

A subsequent fresh attempt passed read/UI agreement and stale-source rejection
again. The sole authorized write parsed but returned explicit `invalid_build`
because the write path used a build-type string key on the target's numeric
action table. State and UI remained unchanged, no retry occurred, and exact
restoration passed. Numeric Type/SubType/MissionData action resolution must pass
the complete offline/CI gate before another C6.

The next fresh attempt resolved the action but returned explicit `blocked`.
The installed BNW UI passes the numeric action-table loop index—not the matched
entry's `ID`—to both stock APIs. State/UI remained unchanged, no retry occurred,
and restoration passed. Numeric-index dispatch must pass the complete offline
and CI gates before another C6.

The final fresh attempt on exact implementation commit `04dd70f` passed the
read/UI, stale-source, sole-write, independent read-back, audit-permission, and
restoration gates. The same worker remained on the same plot and active turn,
movement decreased, and the exact requested build became active without any
observed popup, movement, other unit action, or turn advance. C6 is complete
through the active-build branch; immediate completion remains offline-only.
The 1.2.0 compatibility surface and stable version are now prepared for D4/C7.
Exact-commit CI, duplicate artifacts, clean installs, explicit approval, tag
CI, publication, and downloaded-asset verification remain.
