# Roadmap

This is the capability-level backlog. Milestone status, dependencies, and
acceptance criteria are canonical in `docs/planning/MILESTONES.md`; implementation
tasks belong in GitHub Issues.

## Phase 0 — Machine reconnaissance
- [x] Locate Civ V installation
- [x] Locate user/mod directories
- [x] Confirm application version and bundled DLC content
- [x] Test custom Lua mod loading path (mod is scanned, but this App Store build
  forcibly hides the Mods browser; activation/loading is rejected on the stock build)
- [x] Check TCP 4318 (disabled initially; enabled reversibly and verified in-game)
- [x] Add and enforce read-only preflight checks for guarded startup, live use,
  write commands, and shutdown
- [x] Record results

Phase 0 reconnaissance was run on 2026-09-12. See `docs/EXPERIMENT_LOG.md`.
Phase 0 found that this Campaign Edition hides its Mods browser, but also proved
a stock, signed-app route around that product limitation: enable the bundled
FireTuner endpoint in user-owned `config.ini` and use its localhost protocol.
No application-bundle modification is required.

## Phase 1 — Minimal read PoC
- [x] Export turn
- [x] Export active player id
- [x] Export gold
- [x] Python detects turn N → N+1 without screen reading

## Phase 2 — Rich read state
- [x] cities
- [x] research
- [x] units
- [x] diplomacy (schema 4 empty pre-contact branch live-verified; non-empty
  branch remains an enhancement test)
- [x] victory progress (schema 4 enabled/zero-progress branch live-verified;
  non-zero late-game progress remains an enhancement test)

## Phase 3 — Write PoC
- [x] Python submits `end_turn`
- [x] Lua sees command
- [x] game advances
- [x] acknowledgement
- [x] Python verifies state change

## Phase 4+
- [x] research selection (live-verified with `TECH_POTTERY`)
- [x] city production (live-verified with `UNIT_SCOUT`)
- [x] unit skip (live-verified through readiness with unchanged movement and location)
- [x] coordinate-based unit movement (M9; see the bounded
  [development plan](planning/UNIT_MOVEMENT_PLAN.md))
- [x] legacy readiness/refusal and explicit end-turn proof (live-verified)

## M3 — Versioned ruleset knowledge
- [x] Define canonical entities, references, ruleset metadata, and provenance
- [x] Reject AI flavor/personality data and non-gameplay copyrighted assets
- [x] Import merged technology facts and prerequisite relations from SQLite
- [x] Import eras and connect every technology to its era
- [x] Import allowlisted unit types and gameplay values
- [x] Import unit classes, default units, and class-based upgrade routes
- [x] Import promotion effects, prerequisites, and unit free promotions
- [x] Import policy branches, core policy effects, and prerequisites
- [x] Import remaining policy effect relation tables (single-context yield
  tables complete)
- [x] Import building classes, core building facts, and known prerequisites
- [x] Import resource classes, resource placement facts, and unlock relations
- [x] Import unit/building resource quantities as attributed references
- [x] Import remaining building effect relation tables (single-context yield
  tables complete)
- [x] Import civilizations, leaders, traits, and unique/disabled unit and
  building class overrides.
- [x] Import religions, core beliefs, specialists, and great-person unit-class
  relationships
- [x] Import core terrains, features, improvements, routes, yields, build
  actions, and direct validity/unlock relationships
- [x] Import binary terrain, feature, improvement, route, and build quantity
  relations with schema 2 reference attributes
- [x] Define schema 3 typed context for contextual/ternary relation identity
- [x] Import single-context belief, building, improvement, and policy yield
  effects with schema 3 context
- [x] Import binary belief, building, policy, resource, and specialist yield
  effects
- [x] Import projects, processes, victory conditions, prerequisites, thresholds,
  production conversion, and resource requirements
- [x] Import unit-combat categories, unit/promotion applicability, quantified
  category modifiers, and contextual free promotions
- [x] Import unit domains and special-unit categories as validated typed
  relationships
- [x] Convert supported unit technology, capture, ancient-ruin, policy, cargo,
  project, and promotion identifiers into validated typed relationships
- [x] Import multi-attribute promotion modifiers for domains, features,
  terrains, and unit classes, including technology-conditioned passability
- [x] Import plain faith-purchase, prerequisite, resource-placement, promotion,
  training-restriction, and unit build-capability relations
- [x] Import remaining direct building-class, domain, free-unit, trade-route,
  trait, and combat-yield quantities with supported typed contexts
- [x] Import multi-attribute improvement/resource rules and building yields
  conditioned by the building's enhanced-yield technology
- [x] Import hurry methods, conversion rates, policy gates, and building/policy
  cost modifiers
- [x] Import great-work classes, slot types, and building slot relationships
  without individual work content or presentation assets
- [x] Import great-work and artifact-class stable IDs, archaeology flags, and
  typed class, era, creator-unit, and free-building relationships
- [x] Import building theming bonuses and matching constraints without
  localized descriptions, AI priorities, or synthetic identifiers
- [x] Inventory remaining multi-context tables and exclude AI role/formation
  data under ADR-0005
- [x] Import region identities, civilization starting facts, and build/feature
  rules with optional technology context
- [x] Import immutable game-speed, handicap, and world-size scaling facts while
  excluding AI decision heuristics
- [x] Import ancient-ruin outcomes, unit-class results, and handicap availability
  without descriptions or sounds
- [x] Import World Congress resolutions, decisions, sessions, projects, rewards,
  and votes with typed prerequisites and rewards
- [x] Import minor-civilization and minor-trait identities with deterministic
  trait membership
- [x] Import civilization initial unit-class quantities and coastal placement
  without selecting AI role data
- [x] Import the first positive allowlist of deterministic global defines under
  ADR-0012 without bulk-reading AI behavior parameters
- [x] Import climates, sea levels, game options, and typed promotion
  invisibility/detection facts; exclude presentation-only calendar families
- [x] Classify all reviewed remaining rules and import every accepted core or
  future decision-support family, including resource map-quantity alternatives
- [x] Validate explicit game-speed, difficulty, civilization, policy, belief,
  DLC, and mod context as a structural knowledge view
- [x] Define and validate explicit canonical resolution context without
  mutating base knowledge
- [x] Exclude broad effective scalar composition from the execution core and
  defer it to consumer-driven strategic, tactical, and vertical skills under
  ADR-0014
- [x] Resolve civilization replacements and disabled class defaults with base
  and override provenance
- [x] Expose a validated, deterministic entity/reference query API
- [ ] Add structural knowledge queries only when a knowledge-facing API or
  future decision-support consumer requires them

## M5 — Per-game factual journal

- [x] Define and implement the append-only schema 1 journal codec and private
  storage interface under ADR-0020
- [x] Implement the bridge-session envelope under ADR-0017 with strict UUIDv4
  validation and stale/missing-session write rejection
- [x] Implement journal `match_id` and explicit cross-session binding
- [x] Add opt-in watcher capture for changed validated snapshots and grounded
  in-memory command results
- [x] Record command-submission, unsuccessful-result, and explicit observed
  turn-transition lifecycle events
- [x] Add canonical serialization, hash-chain, truncation, tampering,
  concurrency, permission, and reopen tests
- [x] Correlate M2 audit and M5 journal by command UUID without parsing the audit
  file or coupling their failure behavior
- [x] Add deterministic full-chain verification with a payload-free summary
- [x] Add deterministic append-order replay with an explicit private-payload gate
- [x] Add explicit privacy-preserving structural export and retention guidance
- [x] Verify capture, verification, replay, and export in a bounded real-game
  session

The supported captured journal sequence supports future tactical/strategic
history selection, replay, comparison, debugging, and audit. It is not a claim
of hidden or disconnected facts, a wholesale executor input, or an
execution-state store.

## M6 — Deterministic turn executor

- [x] Separate turn planning from execution under ADR-0015
- [x] Draft the TurnPlan, factual requirement, and execution-result boundary
- [x] Finalize TurnPlan identity and state-basis fields against live-state and
  command contracts
- [x] Add bounded complete-plan admission and execution-report consistency
  validation
- [x] Report deterministic factual turn requirements without choosing actions
- [x] Validate complete plans before writing and re-check live state before each
  action
- [x] Execute only ordered plan-listed actions through terminal bridge results
  and before/after state continuity
- [x] Emit bounded factual progress, pause, divergence, recovery, and completion
  events for optional recording
- [x] Require an explicit final `end_turn` action
- [x] Adapt execution to the watcher-owned private IPC without opening another
  FireTuner connection
- [x] Add stale-state, missing-decision, interruption, and core no-retry tests
- [x] Add a session-scoped read-only watcher lookup for completed command UUIDs
- [x] Add explicit ambiguous-outcome reconciliation and recovery tests
- [x] Add bounded watcher-only CLI plan validation and execution
- [x] Verify one explicit plan through successful automatic turn advancement on
  the target Mac

M6 reports requirements but never chooses how to satisfy them. Tactical and
strategic layers are future plan producers and knowledge consumers, not
executor internals. M6 depends on M2 bridge state/session/action contracts, not
M4 or M5; implementing M5 first is scheduling rather than architecture.

Working memory and strategic memory will be designed together with a future LLM
interaction layer outside this repository. They are not tasks on this roadmap.
See `docs/ARCHITECTURE.md` and `docs/PROJECT_STATE.md`.

## M11 — Runtime research forecast facts

- [x] Normalize the downstream request as strategy-neutral read facts
- [x] Freeze schema 8 fields, units, provenance, unsupported behavior, and the
  runtime-context versus complete-ruleset-fingerprint boundary
- [ ] Implement bounded read-only research and runtime-context segments
- [ ] Implement parsing, validation, public capability discovery, and schemas
  2–7 compatibility
- [ ] Complete the frozen offline negative/bounds/artifact matrix
- [ ] Run bounded target verification for read purity, exact units, and the
  controlled interturn overflow sequence
- [ ] Publish core 1.3.0 only after documentation, security scan, exact-commit
  CI, reproducible artifacts, and target evidence pass

M11 adds no write action and does not move forecasting or technology selection
into the execution core. See the
[development plan](planning/RESEARCH_FORECAST_PLAN.md) and
[owning contract](contracts/research-forecast.md).

## M7 — Public API stabilization

- [x] Inventory versioned contracts, candidate public symbols, implementation
  internals, size limits, and error gaps
- [x] Add a bridge-facing watcher client independent of M6 execution semantics
- [x] Define and test the supported Python import surface and exception taxonomy
- [x] Publish complete schema/version/size compatibility guarantees
- [x] Freeze or explicitly qualify CLI JSON and exit-status compatibility
- [x] Assess selective journal/knowledge facades and defer new queries because
  no current supported consumer requires them

## M8 — 1.0 release readiness

- [x] Audit release gates and record current evidence and blockers
- [x] Prepare the bounded combined M5/M6 target-machine verification procedure
- [x] Run the combined M5/M6 procedure with the operator present
- [x] Disposition every open high-impact release risk
- [x] Complete development wheel/sdist build, install, content, and scan checks
- [x] Add version/tag, upgrade, release, and rollback procedures
- [x] Publish the downstream tactical boundary, 1.0 capability profile, and
  core capability request process
- [x] Publish the clean `v1.0.0` release after exact-commit and tag CI, duplicate
  artifact inspection, clean installs, and downloaded-asset hash verification

LLM decision-making, working memory, strategic memory, and MCP integration are
intentionally outside this repository's scope.

## M9 — Verified unit movement

- [x] Define the documentation, implementation, verification, and release plan
- [x] Register the strategy-neutral `move_unit` core capability request
- [x] Research the stock Lua movement path and accept ADR-0032
- [x] Freeze movement, live-state, command, TurnPlan, and downstream contracts
- [x] Implement and test the minimum active-player-visible read model
- [x] Implement bounded allowlisted movement with read-after-write verification
- [x] Integrate explicit movement into deterministic TurnPlan execution
- [x] Complete the full offline verification gate
- [x] Complete bounded operator-authorized target-machine verification
- [x] Publish the verified capability in a compatible 1.1.0 release

## M10 — Verified worker build

- [x] Define the documentation, implementation, verification, and release plan
- [x] Normalize the conversation-submitted strategy-neutral capability request
- [x] Register the request as GitHub Issue #2
- [x] Research candidate enumeration, stock dispatch, exclusions, and exact
  active/completed postconditions; accept ADR-0033
- [x] Freeze worker-build, live-state, command, TurnPlan, and downstream
  contracts
- [x] Freeze the offline and bounded target-machine verification procedures
- [x] Implement and test schema 7 current-plot build state
- [x] Implement bounded allowlisted worker build with read-after-write
  verification
- [x] Integrate the explicit action into deterministic TurnPlan execution
- [x] Complete the full offline verification gate
- [x] Complete bounded operator-authorized target-machine verification
- [x] Publish the verified capability in a compatible 1.2.0 release
