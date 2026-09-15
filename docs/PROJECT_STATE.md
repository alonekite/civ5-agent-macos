# Project State

Last updated: 2026-09-15.

This file is the durable handoff for continuing development without relying on
a particular Codex conversation. It records project facts and accepted design
decisions, not raw chat transcripts.

## Dashboard

- Current milestone: M5 — factual turn journal.
- Active next deliverable: versioned append-only journal records, canonical
  serialization, integrity checks, and private storage.
- Functional test baseline: 170 tests locally on Python 3.11 and the default
  Python runtime; implementation commit `6848b0b` passed GitHub Actions on
  Python 3.11 and 3.13.
- Blocking issue: none.
- User presence required next: none. Free/steal technology modes, non-empty
  diplomacy, and late-game science-victory checks remain optional live evidence.
- Planning source: `docs/planning/MILESTONES.md`.
- Verification source: `docs/testing/TEST_MATRIX.md` and
  `docs/EXPERIMENT_LOG.md`.

## Completed and verified

- The Campaign Edition environment on Apple Silicon macOS was inspected and
  documented.
- A live Civ V to Python read path was proven through the bundled FireTuner
  protocol.
- The watcher owns the single game connection and brokers local commands over
  a private Unix socket.
- `end_turn` was executed in a live game and verified by re-reading the turn.
- Research selection and city production were executed and verified in a live
  game.
- The legacy deterministic controller proof was live-verified for requirement
  refusal and an explicitly invoked end-turn execution path.
- Schema 4's bounded segmented reader and the corrected `skip_unit` readiness
  postcondition were verified in a live early-game match.
- Schema 5 ordinary researched/researchable technology state and the transition
  from a required choice to selected current research were verified live. The
  session also proved that other end-turn tasks can mask an unselected research
  blocker, so ordinary choice detection now uses current-research presence.
- Command identifiers, duplicate suppression, bounded IPC, private audit logs,
  preflight checks, and write-after-read verification are implemented.
- Recoverable live-session preparation/restoration records the private starting
  firewall state, guards FireTuner, rolls back failed preparation, and verifies
  restoration without committing machine-specific state.
- The complete 2026-09-14 live session returned FireTuner, TCP 4318, watcher
  socket, firewall state, and Civ V rule presence to the recorded baseline; an
  independent shutdown preflight confirmed the result.
- The versioned knowledge core imports eras, technologies, units, unit classes,
  promotions, policy branches, policies, buildings, building classes,
  resources, resource classes, civilizations, leaders, deterministic trait
  effects, unique replacements, disabled class overrides, religions, core
  beliefs, specialists/great-person classes, terrains, features, improvements,
  routes, yields, build actions, projects, processes, victories, unit-combat
  categories, domains, special-unit categories, hurry methods, great-work
  classes, slots, works, and artifact classes, and their currently supported
  relations from a local merged Civ V SQLite database.
- The real Campaign Edition database currently yields 1,842 entities and 5,321
  validated references. The map slice includes 9 terrains, 25 ordinary
  features, 2 fake features, 29 improvements, 2 routes, 6 yields, and 35 build
  actions. Generated bundles remain local and uncommitted.
- The knowledge importer records provenance, validates the active ruleset
  family, rejects broken references, and excludes AI flavor/personality data
  and copyrighted descriptive assets.
- Knowledge schema 2 adds validated attributes to references for quantities and
  modifiers while retaining canonical schema 1 read/write compatibility.
- Knowledge schema 3 adds sorted, referentially validated context items to edge
  identity while retaining canonical schema 1 and schema 2 compatibility.
- Eighty-four single-value binary table families, four multi-attribute promotion
  modifier families, and project victory thresholds add 646 attributed binary
  references. Twenty-two contextual quantity families, two contextual promotion
  grant families, promotion terrain/feature passability, and enhanced-building
  yields add 213 schema 3 contextual references; effects requiring multiple
  context items or new entity families remain deferred.
- Eleven unit identifier columns emit 323 typed, referentially checked
  relationships for technology gates, obsolescence, capture classes, ancient-
  ruin upgrades, policies, cargo categories, projects, and promotions.
- Fourteen additional plain relationship families add 253 validated links for
  faith purchasing, city/building prerequisites, local resources, free
  promotions, resource placement, trait training restrictions, post-combat
  promotions, and unit build capabilities.
- Two hurry-method entities preserve deterministic conversion rates; building
  and policy hurry-cost modifiers target them through validated references.
- Four great-work classes and three slot types are first-class entities; their
  class-slot and building-slot relationships add 24 validated links without
  importing work titles, prose, icons, images, quotes, or audio.
- Stable IDs for 279 great works and six artifact classes add 567 typed class,
  era, artifact, creator-unit, and free-building relationships. Only the
  deterministic archaeology flag and artifact-class numeric value are retained;
  names and presentation content remain excluded.
- Ten buildings preserve 21 canonically ordered theming alternatives with
  deterministic bonus, era, work-kind, owner, and player constraints. Localized
  descriptions and AI priorities are never selected.
- The remaining-table inventory found no unimported core-facing gameplay effect
  requiring more than one typed context. Built-in AI formation slots are
  excluded by ADR-0005; apparent natural-wonder `Type` columns are booleans.
- Nine region entities, 59 build/feature rules, and 112 distinct civilization
  starting-fact references now preserve start-region preferences, free building
  classes and technologies, feature removal, costs, production, timing, and
  optional technology context.
- Four game speeds, nine handicaps, and six world sizes preserve static scaling
  facts. Thirteen handicap AI free-technology relationships retain deterministic
  difficulty effects without decision heuristics or personality data.
- Twenty ancient-ruin outcomes preserve numeric and boolean results, six typed
  unit-class results, and 83 handicap-availability relationships without prose
  or sounds.
- Forty-seven World Congress entities and 68 typed relationships preserve
  resolutions, decisions, sessions, projects, rewards, and votes without
  descriptions, help text, or art.
- Fifty-eight minor civilizations and five minor traits preserve stable IDs and
  58 typed memberships without localized prose, art, colors, or flavor data.
- The policy/building remainder audit found only their prohibited flavor tables
  outside the importer; all non-flavor non-empty relation tables are covered.
- Civilization starting facts now include 44 initial unit-class quantities, 12
  coastal-start preferences, and one first-placement preference. The source AI
  role column is never selected.
- Fifteen allowlisted global defines preserve movement, hit points, city growth,
  food consumption, purchase, and unit-upgrade constants without bulk-importing
  AI behavior parameters.
- Five climates, three sea levels, and 29 game options preserve deterministic
  map-generation and stable ruleset-switch facts. One invisibility category and
  two promotion links preserve invisibility and detection semantics. UI text,
  option visibility, and calendar presentation data remain excluded.
- Six strategic resources preserve nine canonically ordered map quantity
  alternatives as owned numeric rules; invalid, duplicate, and orphaned values
  fail closed.
- M3 is complete: every reviewed non-empty candidate family is imported,
  explicitly deferred with a semantic reason, or excluded by an accepted
  boundary. Further knowledge growth is demand-driven and positive-allowlist.
- M4 is complete as a structural ruleset knowledge view covering exact ruleset,
  game-speed, handicap, world-size, civilization, policy, and belief selection.
  Unknown, duplicate, and incompatible selections fail closed; resolved entity
  values are detached from the base bundle.
- Unit and building classes resolve through the selected civilization to their
  default, unique replacement, or explicit disabled state. Results retain base
  and override references; a real local America check selected the Minuteman
  over the Musketman and left ordinary defaults unchanged.
- Broad effective scalar composition and counterfactual comparison are excluded
  from the execution core under ADR-0014. They belong to future consumer-driven
  strategic, tactical, and vertical skills.
- M6 is replanned as an M2-dependent deterministic TurnPlan executor. It reports
  factual requirements and executes only explicit ordered actions, pausing on
  drift or missing decisions instead of choosing tactics. It does not depend on
  M5; optional orchestration may record its factual events in the journal.
- Schema 5 adds bounded live reads for researched and currently researchable
  technologies plus a research-choice mode. The ordinary branch is
  live-verified, special choices fail closed, and schemas 2–4 remain compatible.
- The test suite contains 170 tests locally on Python 3.11 and the default
  runtime; implementation head `6848b0b` passed CI on Python 3.11 and 3.13.

## Implemented with optional enhanced live evidence pending

- Schema 4 diplomacy has verified the empty pre-contact branch; a non-empty
  observed-major branch remains optional.
- Schema 4 science-victory values have verified the early zero-progress branch;
  non-zero late-game project counts remain optional.

Future live tests require the user to start the game and explicitly authorize
the documented `live_session prepare`/`restore` procedure. No background or
implicit operation may enable FireTuner, launch Civ V, or change the firewall.

## Planned per-game data in this repository

The current core will separate:

1. `live state`: the latest validated observation and current source of truth;
2. `turn journal`: an append-only full record of every turn, command, result,
   and verification outcome, retained for audit but not consumed wholesale by
   the executor.

Ruleset knowledge remains independent of a saved game. The journal stores facts
and verified action lifecycles; it does not summarize, infer, plan, or choose
actions. Its future consumers include tactical/strategic history selection,
replay, comparison, debugging, and audit; it is not M6 execution state.

`working_memory` and `strategic_memory` are postponed to a future LLM
interaction layer outside this repository. Their schemas will be designed with
context selection, prompting, inference, expiry, and plan-revision behavior.
Any future integration must still use the core action allowlist and write
verification.

See `docs/ARCHITECTURE.md` for the detailed boundaries.

## Recommended offline development order

1. Define the factual turn-journal schema, storage interface, canonical
   serialization, retention expectations, and integrity tests.
2. Connect watcher observations and command results to the journal without
   changing the live bridge protocol.
3. Separately finalize the versioned TurnPlan and execution-report schemas
   against live-state and command identities.
4. Implement ordered deterministic execution, factual turn requirements,
   state-drift pauses, and unambiguous recovery without tactical choices.
5. Stabilize the public read/write, knowledge-query, journal, and turn-execution
   APIs.
6. Perform optional non-empty diplomacy or non-zero science-project live
   enhancement checks only when the user is present.

Items 1–2 precede 3–4 as current project scheduling only. M5 and M6 have no
runtime or storage dependency on each other.

LLM decision-making, working memory, strategic memory, and MCP integration
remain out of scope.

## Recent accepted decisions

- ADR-0004: generate knowledge from local sources with ruleset provenance.
- ADR-0005: exclude AI flavor and personality data.
- ADR-0006: keep the factual journal in the core and defer working/strategic
  memory to a future LLM-facing project.
- ADR-0008: include sorted typed context in schema 3 reference identity.
- ADR-0009: manage live tests as explicit, recoverable bounded sessions.
- ADR-0010: segment schema 4 snapshots below the target FireTuner command limit
  and reject cross-turn or cross-player mixtures.
- ADR-0011: embed non-addressable rule sets under a stable owning entity rather
  than inventing identifiers or importing localized descriptions.
- ADR-0012: represent explicitly allowlisted stable global define names as
  ordinary sourced knowledge entities.
- ADR-0013: require explicit, canonically ordered per-game resolution context
  and detach selected result entities from immutable base knowledge.
- ADR-0014: keep M4 as a structural knowledge view and move effective-rule
  analysis to future strategic, tactical, and vertical skills.
- ADR-0015: require explicit TurnPlan input and separate tactical plan creation
  from deterministic current-turn execution.
- ADR-0016: keep M5 as historical fact storage and M6 as an independent
  live-state executor; connect them only through optional event recording.

See `docs/architecture/decisions/README.md`. Development history belongs in
`docs/development/DEVELOPMENT_LOG.md`, not in this dashboard.
