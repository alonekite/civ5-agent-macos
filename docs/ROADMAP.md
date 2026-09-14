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
- [ ] diplomacy (schema 3 implemented and offline-tested; live verification pending)
- [ ] victory progress (science projects implemented and offline-tested; live
  verification pending)

## Phase 3 — Write PoC
- [x] Python submits `end_turn`
- [x] Lua sees command
- [x] game advances
- [x] acknowledgement
- [x] Python verifies state change

## Phase 4+
- [x] research selection (live-verified with `TECH_POTTERY`)
- [x] city production (live-verified with `UNIT_SCOUT`)
- [ ] unit skip (implemented and unit-tested; live verification pending)
- [ ] coordinate-based unit movement
- [x] deterministic policy (live-verified refusal and successful execution paths)

## M3 — Versioned ruleset knowledge
- [x] Define canonical entities, references, ruleset metadata, and provenance
- [x] Reject AI flavor/personality data and non-gameplay copyrighted assets
- [x] Import merged technology facts and prerequisite relations from SQLite
- [x] Import eras and connect every technology to its era
- [x] Import allowlisted unit types and gameplay values
- [x] Import unit classes, default units, and class-based upgrade routes
- [x] Import promotion effects, prerequisites, and unit free promotions
- [x] Import policy branches, core policy effects, and prerequisites
- [ ] Import remaining policy effect relation tables (single-context yield
  tables complete)
- [x] Import building classes, core building facts, and known prerequisites
- [x] Import resource classes, resource placement facts, and unlock relations
- [x] Import unit/building resource quantities as attributed references
- [ ] Import remaining building effect relation tables (single-context yield
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
- [ ] Import contextual/ternary effect tables and remaining rules
- [ ] Resolve static knowledge against live game-speed, difficulty, civilization,
  policy, belief, DLC, and mod context
- [x] Expose a validated, deterministic entity/reference query API
- [ ] Integrate ruleset queries into controller decisions

## M5 — Per-game factual journal

- [ ] Define an append-only turn-journal schema and storage interface
- [ ] Record full validated turn snapshots and verified command lifecycles
- [ ] Add canonical serialization, integrity hashes, and recovery tests

The complete journal is an audit and reproduction source, not a wholesale
controller input.

Working memory and strategic memory will be designed together with a future LLM
interaction layer outside this repository. They are not tasks on this roadmap.
See `docs/ARCHITECTURE.md` and `docs/PROJECT_STATE.md`.

LLM decision-making, working memory, strategic memory, and MCP integration are
intentionally outside this repository's scope.
