# Development Log

This log records meaningful completed batches, not every edit. Git history is
the authoritative file-level record; target-machine evidence belongs in
`docs/EXPERIMENT_LOG.md`.

## 2026-09-12 — Environment and bridge MVP

- Inspected the Apple Silicon host, App Store Campaign Edition, Lua runtime,
  sandboxed data paths, DLC footprint, and candidate IPC mechanisms.
- Proved that the stock build discovers but cannot enable a custom mod through
  its vendor-hidden Mods UI.
- Rejected modification of the signed application copy after macOS integrity
  enforcement prevented it from launching.
- Proved read-only in-game state access through the bundled FireTuner protocol.
- Implemented the persistent watcher and local broker architecture.
- Live-verified rich state reads and `end_turn` with write-after-read proof.
- Added and live-verified research selection and city production, plus the first
  deterministic controller path.

Initial repository commit: `71439f0`.

## 2026-09-13 — Safety and schema hardening

- Added read-only preflight checks and enforced firewall/FireTuner safety gates.
- Bounded local IPC requests and responses and closed unsafe endpoint overrides.
- Implemented offline-tested snapshot schema 3 fields for score, era, city
  economy, unit condition, met-major diplomacy, and science-victory progress.
- Added UUID validation, command argument auditing, and duplicate watcher-command
  suppression.

Representative commits: `943fd7d`, `9a828a2`, `c75e98c`, `89b667e`,
`7902321`, `8d9b8e4`, `31b1bd3`, `dc09f67`, `3939583`, `9386303`.

## 2026-09-13 — Versioned knowledge core

- Added canonical ruleset entities, typed references, provenance, validation,
  deterministic serialization, hashing, and query indexing.
- Added read-only immutable SQLite import with source-change and active-WAL
  rejection.
- Imported technologies, eras, units, unit classes, upgrade routes, promotions,
  policies, policy branches, buildings, building classes, wonders, resources,
  resource classes, and supported relations.
- Added DLC-family verification and restored Python 3.11 test compatibility.
- Re-ran sensitive-information checks and GitHub Actions on Python 3.11/3.13.

Commits: `76473f8` through `756ab68`.

## 2026-09-13 — Architecture and documentation governance

- Defined factual live state and future append-only turn-journal boundaries.
- Deferred working memory and strategic memory to a separate future LLM
  interaction layer.
- Added a durable project-state handoff after recovering a locally intact Codex
  session whose UI index temporarily failed to display recent turns.
- Introduced a canonical documentation index, Chinese project outline,
  milestone plan, risk register, ADRs, module documents, contracts, and
  verification matrix.

Related commits before this governance batch: `144291b`, `14daa1d`.
Governance commit: `a053797`.

## 2026-09-14 — Live-verification ledger

- Added a Chinese manual-test status ledger that separates real-game evidence,
  partial evidence, pending tests, and rejected approaches.
- Linked each summarized conclusion to the detailed experiment log and required
  future live sessions to update the ledger and verification matrix only after
  sanitized evidence is recorded.

## 2026-09-14 — Core map and build knowledge

- Added allowlisted terrain, feature, improvement, route, yield, and build
  entities plus direct validity, unlock, creation, upgrade, and restriction
  relationships.
- Converted the trait improvement bonus identifier into a validated typed
  reference now that improvement entities exist.
- Excluded yield AI weights, graphical-only flags, prose, hotkeys, and assets.
- Imported the real merged database twice with an identical canonical hash:
  1,296 entities and 2,259 references; no generated bundle was committed.

## 2026-09-14 — Quantity-bearing knowledge contract

- Added schema 2 reference attributes for deterministic quantities and
  modifiers while preserving canonical schema 1 read/write behavior.
- Added strict validation for reference attributes, including forbidden AI
  fields and non-finite values, and documented the compatibility decision in
  ADR-0007.

Contract commit: `de60745`.

## 2026-09-14 — Binary quantity-bearing map knowledge

- Imported 15 binary terrain, feature, improvement, route, and build effect
  tables as schema 2 references with validated integer attributes.
- Imported the official `FakeFeatures` lake and river identifiers as feature
  entities marked `fake`, resolving their source-backed yield relationships
  without skipping dangling-looking rows.
- Re-imported the real merged database twice with the same canonical hash:
  1,298 entities, 2,336 references, and 77 attributed references. No generated
  bundle or source database was committed.
- Passed the complete 111-test Python 3.11 suite and the sensitive-information
  scan before submission.

Implementation commit: `2ee9f89`.

## 2026-09-14 — Contextual knowledge relation identity

- Added knowledge schema 3 typed reference context while preserving the exact
  schema 1 and schema 2 serialized shapes.
- Required context roles and entity identifiers to be valid, sorted, unique,
  and referentially complete; included context in duplicate-edge identity.
- Recorded the compatibility and modeling decision in ADR-0008 and added
  round-trip, legacy-shape, ordering, missing-target, and identity tests.
- Passed the complete 116-test Python 3.11 suite and the sensitive-information
  scan before submission.

Implementation commit: `a20bbe6`.

## 2026-09-14 — First contextual knowledge import

- Moved new SQLite imports to schema 3 and imported
  `Improvement_TechYieldChanges` with typed technology context.
- Preserved 18 technology-specific improvement yield rows, including two
  distinct technology contexts for the academy science edge.
- Re-imported the real merged database twice with the same canonical hash:
  1,298 entities, 2,354 references, 95 attributed references, and 18 contextual
  references. No generated bundle or source database was committed.
- Passed the complete 117-test Python 3.11 suite and the sensitive-information
  scan before submission.

Implementation commit: `fb80fa5`.

## 2026-09-14 — Expanded quantified knowledge effects

- Expanded schema 3 coverage to 19 single-context belief, building,
  improvement, and policy effect-table families.
- Expanded binary attributed coverage to 48 table families, including belief,
  building, policy, resource, and specialist yields plus unit/building resource
  quantities and requirements.
- Made the synthetic SQLite fixture exercise every configured binary and
  single-context table mapping.
- Re-imported the real merged database twice with the same canonical hash:
  1,298 entities, 2,762 references, 503 attributed references, and 159
  contextual references. No generated bundle or source database was committed.
- Passed the complete 117-test suite on Python 3.11 and the local default Python
  runtime, and scanned the submitted diff for secrets and local identifiers.

Implementation commit: `18bba03`.

## 2026-09-14 — Project, process, and victory knowledge

- Added deterministic project, process, and victory entities while excluding
  descriptive, movie, audio, and presentation fields.
- Added technology and victory gates, project prerequisites, resource
  requirements, production conversion, and multi-attribute victory thresholds.
- Re-imported the real merged database twice with the same canonical hash:
  1,314 entities and 2,781 references, including 16 new entities and 19 outgoing
  project/process references. No generated bundle or source database was
  committed.
- Passed all 118 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `a014fdc`.

## 2026-09-14 — Unit-combat knowledge

- Added 14 unit-combat category entities plus typed unit membership and
  promotion applicability relationships.
- Imported category-specific building, policy, trait, and promotion quantities,
  and modeled trait/policy free promotions with typed unit-combat context while
  excluding Pedia grouping fields.
- Re-imported the real merged database twice with the same canonical hash:
  1,328 entities and 3,262 references, including 444 unit-combat targets and 37
  contextual promotion grants. No generated bundle or source database was
  committed.
- Passed all 118 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `be1c293`.

## 2026-09-14 — Unit domain and special classifications

- Added domain and special-unit entities and typed unit relationships while
  retaining the legacy scalar identifiers for compatibility.
- Re-imported the real merged database twice with the same canonical hash:
  1,337 entities and 3,432 references, including 148 unit-domain and 22
  special-unit links. No generated bundle or source database was committed.
- Passed all 118 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `3ae348b`.

## 2026-09-14 — Typed unit identifier relationships

- Converted 11 allowlisted unit identifier columns into typed relationships for
  capture class, technology gates and obsolescence, ancient-ruin upgrades,
  policy requirements, cargo categories, projects, and leader promotions.
- Corrected `Units.Capture` to target a unit class after strict validation of
  the real database rejected the initial unit-type interpretation.
- Re-imported the real merged database twice with the same canonical hash:
  1,337 entities and 3,755 references, including 323 new unit relationships. No
  generated bundle or source database was committed.
- Passed all 118 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `332595e`.

## 2026-09-14 — Promotion environment modifiers

- Imported promotion modifiers against domains, features, terrains, and unit
  classes as multi-attribute typed references while excluding Pedia metadata.
- Represented technology-conditioned feature and terrain passability as a
  separate typed context instead of incorrectly conditioning the other modifier
  attributes.
- Re-imported the real merged database twice with the same canonical hash:
  1,337 entities and 3,789 references, including 33 new multi-attribute
  modifiers and one passability context. No generated bundle or source database
  was committed.
- Passed all 119 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `a1f68c5`.

## 2026-09-14 — Expanded plain knowledge relations

- Added a declarative importer for 14 plain relationship tables covering faith
  purchasing, building and local-resource prerequisites, free/random
  promotions, resource placement, training restrictions, and unit build
  capabilities.
- Re-imported the real merged database twice with the same canonical hash:
  1,337 entities and 4,042 references, including 253 new typed links. No
  generated bundle or source database was committed.
- Passed all 119 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `cdac7e5`.

## 2026-09-14 — Expanded quantified rules

- Added 24 direct quantity table mappings for building-class, domain, free-unit,
  prerequisite, trade-route, trait, and combat-yield rules.
- Added typed improvement, specialist, and unimproved-feature context to three
  trait yield table families.
- Re-imported the real merged database twice with the same canonical hash:
  1,337 entities and 4,214 references, including 157 new binary quantities and
  15 new contextual quantities. No generated bundle or source database was
  committed.
- Passed all 119 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `f467161`.

## 2026-09-14 — Improvement resources and derived building yields

- Preserved improvement/resource validity, trade, discovery, and quantity values
  together on 68 typed multi-attribute references.
- Joined technology-enhanced building yields to the building's declared
  `EnhancedYieldTech` and made missing context a hard import error.
- Re-imported the real merged database twice with the same canonical hash:
  1,337 entities and 4,283 references, including the 68 resource rules and one
  technology-conditioned building yield. No generated bundle or source database
  was committed.
- Passed all 120 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `d7255db`.

## 2026-09-14 — Hurry-method knowledge

- Added gold- and population-based hurry methods as typed entities with
  deterministic conversion rates and optional policy prerequisites.
- Added building and policy hurry-cost modifiers while excluding descriptions.
- Re-imported the real merged database twice with the same canonical hash:
  1,339 entities and 4,285 references, including two hurry entities and two
  cost-modifier links. No generated bundle or source database was committed.
- Passed all 120 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `e11357a`.

## 2026-09-14 — Great-work class and slot knowledge

- Added four great-work classes and three slot types as stable entities plus
  typed class-to-slot and building-to-slot relationships.
- Excluded individual works, titles, descriptions, icons, images, quotes, and
  audio from this copyright-safe slice.
- Re-imported the real merged database twice with the same canonical hash:
  1,346 entities and 4,309 references, including 24 new slot links. No generated
  bundle or source database was committed.
- Passed all 120 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `571ad96`.

## 2026-09-14 — Copyright-safe great-work knowledge

- Added 279 great-work stable IDs and six artifact classes, retaining only the
  archaeology flag and artifact-class numeric value as scalar facts.
- Added typed class, era, artifact, creator-unit, and free-building relations;
  `UniqueName`, titles, descriptions, quotes, images, and audio are not read.
- Re-imported the real merged database twice with the same canonical hash:
  1,631 entities and 4,876 references, including 567 new typed links. No
  generated bundle or source database was committed.
- Passed all 120 tests on Python 3.11 and the local default Python runtime, and
  scanned the submitted diff for secrets and local identifiers.

Implementation commit: `097542f`.

## 2026-09-13 — Civilization knowledge coverage

- Added allowlisted civilization, leader, and deterministic trait entities.
- Added civilization-to-leader, leader-to-trait, unique unit/building, and
  disabled class relationships.
- Explicitly excluded leader personality values, AI playability, flavor tables,
  prose, and presentation assets.
- Defined deterministic duplicate-slot handling and rejected replacements whose
  declared unit/building class does not match the target entity.
- Imported the target installation's merged database read-only without writing
  a generated bundle to the repository: 1,100 entities and 2,059 references.
- Added religion identifiers, allowlisted core belief effects, preferred
  religions, specialists, and great-person unit-class relationships. The
  expanded real import contains 1,190 entities and 2,110 references and remains
  byte-repeatable across consecutive runs.

## 2026-09-14 — Recoverable live-test sessions

- Added explicit, idempotent `live_session prepare` and `restore` operations
  that record a private baseline outside the repository, guard FireTuner with
  the macOS application firewall, and verify restoration before deleting the
  recovery state.
- Kept the Python process unprivileged while elevating only narrow firewall
  mutations, and added rollback for failed preparation.
- Accepted both executable and canonical `.app` paths returned by
  `socketfilterfw`, including path-line whitespace observed on the target Mac.
- Added ADR-0009 and updated the security policy, CLI ownership, operations
  index, risk register, and live-test checklist.
- Passed all 127 tests on Python 3.11 in the host environment. End-to-end
  prepare/restore still requires one interactive administrator authentication
  on the target Mac.

Implementation commit: `bc2cd1d`.

Follow-up commit `7cca72e` made rollback state-aware after a target-Mac sudo
authorization failure. If the first mutation is denied, unchanged firewall
boundaries are no longer touched during rollback, and private recovery state is
cleaned without requiring a second authorization. The full Python 3.11 suite
then passed with 128 tests.

Follow-up commit `4177103` corrected the target-Mac creation sequence after a
real prepare attempt proved that `socketfilterfw --blockapp` does not create a
missing entry. Preparation now adds and immediately blocks Civ V while the game
and FireTuner are stopped, verifies that rule, and only then enables the
firewall and FireTuner. The failed attempt returned the machine to its clean
shutdown baseline.

## 2026-09-14 — Segmented live state and unit readiness

- Replaced the over-limit monolithic live snapshot with five read-only programs
  capped below 900 bytes.
- Added mandatory part completeness plus turn/player identity checks so a turn
  transition cannot silently produce a mixed snapshot.
- Preserved legacy schema 2 and 3 parsing and assigned the segmented,
  readiness-bearing shape schema 4.
- Corrected `skip_unit` verification to require `ready_to_move` true-to-false
  while unit identity, coordinates, and remaining movement stay unchanged.
- Live-verified early-game expanded state and one complete skip before/after
  lifecycle; the original zero-movement assumption was disproved by both game
  observation and stock UI API usage.
- Passed all 137 tests on Python 3.11 and the local default Python runtime.

Implementation commit: `429b50f`.

Follow-up commit `54efd81` corrected live-session restoration to remove the
exact executable-path firewall entry created by preparation. The target Mac
then restored to its recorded baseline and passed an independent shutdown
preflight.

## 2026-09-15 — Copyright-safe building theming rules

- Added all 21 target-database theming alternatives to their 10 owning building
  entities with canonical ordering and strict integer/boolean normalization.
- Preserved bonus, era, work-kind, owner, and player matching constraints while
  never selecting localized descriptions or AI priorities.
- Rejected duplicate normalized rules, invalid booleans, and missing building
  parents; documented the non-addressable owned-rule pattern in ADR-0011.
- Re-imported the real merged database twice with the same canonical hash:
  1,631 entities, 4,876 references, and 21 embedded theming rules. No generated
  bundle or source database was committed.
- Passed all 141 tests on Python 3.11 and scanned the submitted diff for
  secrets, local identifiers, generated data, and forbidden AI fields.

Implementation commit: `a86078e`.

## 2026-09-15 — Remaining ruleset and scaling coverage

- Reviewed all non-empty multi-identifier tables and recorded the classification
  in the remaining-rules inventory. No unimported controller-facing rule needs
  more than one typed context; built-in AI role/formation data remains excluded.
- Added region identities, civilization starting facts, and 59 build/feature
  rules with deterministic values and optional technology context.
- Added immutable game-speed, handicap, and world-size facts while excluding AI
  decision heuristics, personality parameters, prose, and art.
- Added ancient-ruin outcomes and World Congress resolutions, decisions,
  sessions, projects, rewards, and votes with validated typed relationships.
- Added minor-civilization and minor-trait identities and membership without
  localized or flavor data. The policy/building audit found only prohibited
  flavor tables outside the importer.
- Re-imported the real merged database twice with equal output: 1,789 entities
  and 5,275 references. No generated bundle or source database was committed.
- Passed all 147 tests on Python 3.11 and the default runtime, and found no local
  paths, IP addresses, credentials, or tokens in the repository scan.

Implementation commit: `1a0a784`.

Follow-up commit `172db99` added 44 typed civilization initial-unit quantities
and coastal-start flags. The importer deliberately does not select the source
`UnitAIType` field and fails on duplicate civilization/unit-class identity
instead of conflating excluded roles. The real database now imports as 1,789
entities and 5,319 references with repeatable output; all 148 tests pass on
Python 3.11 and the default runtime.

Follow-up commit `e5f0aa5` added 15 explicitly allowlisted global gameplay
defines for movement, health, growth, food consumption, purchase, and upgrade
calculations. ADR-0012 documents use of stable source `Defines.Name` keys as
entity identity. The remaining 1,688 definitions and `PostDefines` are not
bulk-imported, preventing AI behavior parameters from crossing the knowledge
boundary. The real import is byte-repeatable at 1,804 entities and 5,319
references; all 150 tests pass on both supported local runtimes.

Follow-up commit `0274324` completed the main map/calendar classification and
imported five climates, three sea levels, 29 game options, one invisibility
category, and two typed promotion invisibility/detection links. Descriptions,
help text, option UI visibility, calendar/date presentation data, and city-size
soundscape categories remain outside the knowledge boundary. The real import is
byte-repeatable at 1,842 entities and 5,321 references; all 152 tests pass on
Python 3.11, the default runtime, and GitHub Actions on Python 3.11 and 3.13.

Follow-up commit `12427c1` embedded nine canonically ordered, positive map
quantity alternatives in their six owning strategic resources, with invalid,
duplicate, and orphaned source rows rejected. The resulting real import remains
byte-repeatable at 1,842 entities and 5,321 references. This closes M3 after
classifying every reviewed non-empty candidate as imported, deferred with a
semantic reason, or excluded by an accepted boundary. All 155 tests pass on
both local runtimes and GitHub Actions on Python 3.11 and 3.13.

## 2026-09-15 — Explicit ruleset resolution context

- Added immutable input and result contracts for exact ruleset, game-speed,
  handicap, world-size, civilization, adopted-policy, and active-belief
  selection.
- Canonicalized set-like selections and rejected mismatched rulesets, unknown
  entities, duplicate identifiers, and malformed collections instead of
  substituting defaults.
- Returned detached selected entities and source provenance so resolver clients
  cannot mutate indexed base facts through a result.
- Documented the boundary in ADR-0013 and a dedicated resolver contract.
- Passed all 160 tests locally and in GitHub Actions on Python 3.11 and 3.13;
  the sensitive-data scan remained clean.

Implementation commit: `e33e358`.

Follow-up commit `3649c05` resolves unit and building classes through the
selected civilization. Each result identifies the base default, effective
member or explicit disabled state, and civilization override provenance.
Offline use against the real local database selected America's Minuteman over
the Musketman and retained ordinary defaults. All 163 tests pass locally and in
GitHub Actions on Python 3.11 and 3.13.

## 2026-09-15 — Live technology-state schema foundation

- Inspected the installed BNW technology popup, tree, and end-turn panel to
  identify stock read APIs and blocker semantics.
- Added schema 5 researched and researchable `TECH_*` sets plus an observed
  normal, free-technology, or unsupported choice mode in a sixth 874-byte
  read-only segment.
- Preserved schema 2–4 parsing, enforced stable ordering, identifier uniqueness,
  cross-set consistency, mandatory part identity, and malformed-input rejection.
- Kept free and steal technology choices manual-only in the controller.
- Passed all 170 tests locally and in GitHub Actions on Python 3.11 and 3.13;
  sensitive-data scanning found no local paths, addresses, or credentials.

Implementation commit: `5669973`. Live schema 5 verification remains pending.

Follow-up commit `4d802b2` converted the next live check into a bounded,
read-only procedure: compare ordinary researched/researchable technology state
before and after one manual UI selection, then restore the recorded machine
baseline. Free and stolen technology modes are not manufactured or auto-run.

## 2026-09-15 — Live ordinary technology-state verification

- Verified schema 5 researched and researchable technology sets against the
  stock game UI through a guarded, read-only target-machine session.
- Observed the ordinary choice transition through one persistent connection:
  the choice was required before a manual UI selection, then current research
  matched the selected stable identifier and the requirement cleared.
- Confirmed that Civ V exposes only one prioritized end-turn blocker: production
  or unit work can mask an unselected ordinary technology. Corrected ordinary
  choice detection to use empty current research plus at least one legal
  candidate, while preserving special free/steal blocker overrides.
- Added a validation invariant so contradictory normal choice state fails
  closed, retained the 900-byte command bound, and kept special modes
  manual-only.
- Restored FireTuner, its listener, firewall enablement, and Civ V rule presence
  to the recorded baseline after the game exited.
- Passed all 170 tests on Python 3.11 and the default runtime. Repository and
  diff scans found no user paths, device identifiers, local IP addresses,
  credentials, tokens, live snapshots, or recovery artifacts.

Implementation and evidence commit: `6848b0b`.

## 2026-09-15 — M4 structural knowledge-view boundary

- Re-evaluated M4 against the layered design in which long-term strategy,
  short-term tactics, vertical skills, and deterministic current-turn execution
  have distinct responsibilities.
- Narrowed M4 from a planned universal effective-value resolver to a structural
  knowledge view: explicit context validation, detached canonical entities,
  provenance, and civilization unit/building class replacement remain in the
  core.
- Moved scalar composition, counterfactual comparison, prediction, route
  analysis, and candidate scoring to future consumer-driven strategic,
  tactical, and vertical skills. The executor continues to prefer authoritative
  live values and does not perform those analyses.
- Added ADR-0014 without rewriting ADR-0013. The new decision retains
  ADR-0013's fail-closed context and immutability requirements while superseding
  its anticipated in-core effective-value expansion.
- Marked M4 complete, advanced the active milestone to M5 factual turn journal,
  and synchronized the architecture, contracts, roadmap, module ownership,
  verification matrix, and Chinese project outline.
- Documentation link tests and formatting checks passed; scans found no local
  identifiers, credentials, tokens, snapshots, or recovery artifacts.

Architecture governance commit: `edd98ec`.

## 2026-09-15 — M6 deterministic turn-executor boundary

- Replaced the planned “deterministic controller expansion” milestone with a
  deterministic current-turn executor that consumes an explicit versioned
  `TurnPlan`.
- Separated factual requirement inspection from action choice: the core may
  report missing research, production, or unit orders but cannot select how to
  satisfy them.
- Required complete plan validation, live-state checks before every action,
  bridge write-after-read proof, explicit final `end_turn`, safe pause on drift
  or missing decisions, and unambiguous recovery.
- Added ADR-0015 and a proposed TurnPlan/execution contract. The current
  `controller` package and CLI remain an MVP readiness/end-turn proof until M7;
  they are no longer an expansion point for tactical policy.
- Made M6 depend on M5 journal identity, integrity, and recovery semantics, and
  reserved extensible factual journal records for later plan execution events.
- Updated repository instructions, architecture, milestones, roadmap, module
  boundaries, contracts, verification status, README, and Chinese project
  outline. No runtime code changed in this governance batch.
- Documentation link and formatting checks passed; scans found no local
  identifiers, credentials, tokens, snapshots, or recovery artifacts.

Architecture governance commit: `7ef686d`.

## 2026-09-15 — M5/M6 dependency correction

- Corrected the M5/M6 boundary after reviewing their different purposes: M5 is
  factual historical storage for future tactical and strategic context
  selection, replay, comparison, debugging, and audit; it is not an execution
  control plane.
- Made M6 depend on M2 live-state and verified-command contracts only. M6 owns
  its execution cursor and recovery state and must operate when M5 is absent or
  unavailable.
- Kept integration one-way and optional: application orchestration may append
  neutral factual events emitted by M6 to M5, but journal success or failure
  cannot authorize a retry or change the result of a bridge-verified game
  action. Fresh live state remains authoritative.
- Added ADR-0016, which supersedes only the journal-dependency portions of
  ADR-0015, and synchronized repository instructions, architecture, contracts,
  milestones, roadmap, module documents, verification status, and the Chinese
  project outline.
- Documentation tests and formatting checks passed; scans found no local user
  or device identifiers, credentials, tokens, snapshots, or recovery artifacts.

Architecture correction commit: `2e5165f`.

## 2026-09-16 — Architecture correction and M5 journal foundation

- Resolved remaining cross-document contradictions: distinguished bridge
  sessions from declared journal matches, removed the false M6 dependency on
  M4 knowledge and M5 history, separated the M2 security audit from the M5
  factual journal, and made explicit final `end_turn` part of a complete plan.
- Added a canonical UUIDv4 bridge-session envelope. Reads expose the current
  session, writes must echo it, and missing or stale identities fail before a
  game action can execute.
- Implemented the private schema 1 journal with explicit `match_id`, append-only
  session bindings, canonical JSON, contiguous sequence numbers, SHA-256 hash
  chaining, locked and fsynced writes, record bounds, turn monotonicity, and
  fail-closed corruption checks.
- Connected optional FireTuner watcher capture for changed validated snapshots
  and grounded in-memory command results. New versus resumed histories are
  explicit, reconnect never auto-binds, independent audit/journal failures do
  not retry actions, and the partial database fallback cannot write a journal.
- Passed all 190 tests on Python 3.11 and the default Python 3.14 runtime.
  Scans found no user paths, local addresses, credentials, tokens, real match
  snapshots, or recovery artifacts in the submitted changes.

Architecture correction commit: `b7f82ad`. Session-envelope commit: `bd5a186`.
Journal-store commit: `5af502d`. Watcher-integration commit: `908f053`.

## 2026-09-16 — Complete factual watcher lifecycle capture

- Recorded command submissions before bridge execution without making journal
  persistence an execution precondition.
- Added unsuccessful execution/postcondition facts and explicit turn-transition
  records derived from consecutive validated watcher snapshots.
- Preserved fail-safe behavior: lifecycle write failures are returned as
  warnings and cannot block or retry the associated game action.
- Passed all 191 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `f51c5fd`.

## 2026-09-16 — Payload-free journal verification

- Added deterministic full-chain journal verification and a `civ5-journal
  verify` CLI command.
- The verification summary exposes structural counts, turn bounds, identities,
  and the chain head without exposing snapshot or command payloads.
- Passed all 193 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `ad3ee4e`.

## 2026-09-16 — Deterministic factual journal replay

- Added a read-only replay API that validates the entire journal before
  returning detached factual events in original append order.
- Preserved correction records as events rather than inferring reconstructed
  state or an execution cursor.
- Added `civ5-journal replay` with mandatory acknowledgement before private
  snapshot and command payloads can be printed.
- Passed all 195 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `58f0f6c`.

## 2026-09-16 — Redacted journal export and M5 offline completion

- Added canonical structural export containing only sequence, turn, and event
  kind plus aggregate counts; payloads, timestamps, match/session identifiers,
  hashes, and source paths are excluded.
- Required a nonexistent destination, mode-0600 regular file, canonical output,
  `fsync`, and cleanup after partial-write failure. Repeated exports are byte
  identical.
- Added ADR-0021, journal privacy guidance, and an operator-controlled retention
  policy. Redacted exports are explicitly not anonymous and not backups.
- Marked all M5 acceptance criteria implemented offline; bounded target-machine
  capture/verify/export evidence remains pending.
- Passed all 199 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `3d389b0`.

## 2026-09-16 — TurnPlan schema 1 admission boundary

- Finalized bounded complete-turn plan, planned-action, execution-step, and
  execution-report models under ADR-0022.
- Bound plans to canonical plan/session UUIDs, turn, active player, and SHA-256
  of the complete validated initial live state.
- Added strict admission for the existing four-action allowlist, exact argument
  shapes, unique command IDs, a 64-action limit, and one required final
  `end_turn`.
- Added mutually exclusive completed/paused/stale/failed/recovery report
  invariants without adding game execution or M4/M5 dependencies.
- Passed all 206 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `d59d291`.

## 2026-09-16 — Factual turn-requirement inspection

- Added deterministic requirement inspection for inactive turns, ordinary or
  special research choices, individual cities without production, individual
  units needing orders, and the game-reported end-turn blocker.
- Preserved stable city/unit ordering and exposed ordinary research candidates
  only when the bridge identifies ordinary choice mode.
- Refactored the legacy readiness proof to map the first factual requirement to
  its existing compatibility message without adding action selection.
- Passed all 210 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `066e95e`.

## 2026-09-16 — Ordered TurnPlan execution core

- Added an in-process executor over injected state-read and single-action bridge
  capabilities, with no knowledge or journal dependency.
- Re-read authoritative state before each action, matched each bridge result's
  before-state to the executor observation, and carried the verified after-state
  forward as the next basis.
- Paused before writes for uncovered requirements, rejected state drift, kept
  explicit bridge failure terminal, and classified connection loss after
  submission as recovery-required without retry.
- Required verified turn advance before a final end-turn can complete a plan.
- Passed all 217 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `1e85043`.

## 2026-09-16 — Optional bounded executor events

- Added schema 1 factual events for plan receipt, action start, neutral bridge-
  result receipt, deterministic rejection, unknown outcome, and terminal status.
- Avoided claiming action success before the core validates before/after state
  continuity.
- Kept the event sink optional and independent of M5; bounded sink failures are
  returned in the report and cannot block, alter, or retry an action.
- Passed all 219 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `aa8bd0c`.

## 2026-09-16 — Watcher-owned TurnPlan execution adapter

- Added a narrow M6 adapter that supplies the deterministic executor's state-
  read and single-action capabilities through the existing private watcher
  socket rather than opening a second FireTuner connection.
- Preserved the plan's bridge-session identity and command UUID across the IPC
  boundary, validated watcher responses, and treated unavailable initial state
  as a safe pause rather than an invalid plan.
- Added an end-to-end mocked watcher-protocol execution test plus changed-
  session and timeout rejection tests.
- Passed all 222 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `7971ddd`.

## 2026-09-16 — Read-only command-outcome lookup

- Added a session-scoped `command_status` watcher request that retrieves only
  terminal command results already cached during the current watcher lifetime.
- Serialized lookup with command execution so it cannot race cache insertion;
  a missing result remains unknown and never enters a write or retry path.
- Added adapter validation for exact planned action, arguments, command UUID,
  and bridge-session identity before returning a cached result.
- Passed all 225 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, addresses, credentials, tokens, or
  real match data.

Implementation commit: `138ee49`.

## 2026-09-16 — Conservative unknown-outcome reconciliation

- Added deterministic reconciliation for `recovery_required` reports using the
  watcher adapter's read-only cached-result lookup and a fresh validated state.
- Allowed a recovered final end-turn to complete only after fresh turn-advance
  confirmation; recovered non-final success advances the factual cursor but
  pauses before the next write.
- Kept cache misses, unavailable lookups, malformed results, session changes,
  and contradictory fresh state non-retryable and explicitly classified.
- Accepted ADR-0023 to make these recovery and no-automatic-retry semantics
  durable without introducing knowledge or journal dependencies.
- Passed all 230 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no local paths, private addresses, credentials,
  tokens, or real match data.

Implementation commit: `74fca9d`.

## 2026-09-16 — Bounded watcher-only TurnPlan CLI

- Added exact-field schema 1 TurnPlan decoding with a 64-KiB file bound,
  structural validation before watcher contact, and rejection of unknown fields
  and non-finite JSON values.
- Added `civ5-turn validate` for fresh read-only admission and explicit
  `civ5-turn execute` for complete-plan execution through the existing private
  watcher socket only.
- Kept plan production, M4/M5 access, direct FireTuner fallback, and arbitrary
  predicates outside the CLI; valid non-completed reports have a distinct exit
  status from malformed input or transport failure.
- Accepted ADR-0024 and marked every M6 acceptance criterion implemented
  offline; M7 public API stabilization is now the active offline milestone.
- Passed all 236 tests on Python 3.11 and the default Python 3.14 runtime; the
  submitted diff contained no user paths, private addresses, credentials,
  tokens, generated datasets, or real match data.

Implementation commit: `4f93642`.

## 2026-09-16 — M7 public API inventory

- Catalogued existing live-state, knowledge, journal, TurnPlan, execution, and
  session schema boundaries separately from provisional Python and CLI names.
- Identified candidate exported symbols, implementation-only FireTuner/IPC/
  SQLite internals, current byte/count limits, and the unresolved public error
  taxonomy.
- Derived the next M7 batches: a bridge-facing watcher client independent of
  M6, supported import and exception contracts, complete compatibility limits,
  and deliberate CLI stability decisions.
- Corrected the knowledge overview so it no longer claims M6 consumes knowledge;
  plan producers and decision-support consumers remain its clients.
- Documentation link validation and sensitive-information scanning passed.

Implementation commit: `a78d560`.

## 2026-09-16 — Session-aware public watcher bridge client

- Replaced the unused pre-session asynchronous bridge prototype with a
  runtime-checkable protocol matching verified synchronous reads, writes, and
  read-only result lookup.
- Added `WatcherBridgeClient` as a watcher-only public bridge surface that
  validates commands before contact and validates returned session/command
  identities, terminal status, bounded messages, and before/after states.
- Centralized bridge-owned action allowlist and exact argument validation so
  TurnPlan admission and individual bridge commands share one implementation.
- Refactored `WatcherTurnExecutor` to extend the bridge client only for M6
  PlannedAction translation and execution/recovery composition.
- Accepted ADR-0025; all 241 tests passed on Python 3.11 and the default Python
  3.14 runtime, and sensitive-information scanning found no private material.

Implementation commit: `a680c16`.

## 2026-09-16 — Aggregate pre-1.0 API and error taxonomy

- Added `civ5_agent.api` as the contract-tested aggregate Python import surface
  for bridge, knowledge, journal, TurnPlan, and deterministic execution clients.
- Introduced compatible validation, protocol, transport, and safety error bases;
  malformed evidence after a submitted write now preserves unknown-outcome
  recovery semantics rather than appearing as a deterministic rejection.
- Published supported live/knowledge schema sets and command, execution, IPC,
  plan, event-sink, and journal bounds as importable constants.
- Accepted ADR-0026 and updated M7 planning, contracts, module ownership,
  changelog, project state, and verification evidence.
- Passed all 247 tests on Python 3.11 and the default Python 3.14 runtime. The
  repository scan found no private paths, network addresses, credentials,
  tokens, generated datasets, or real match records; the public repository
  owner name remains intentionally present only in the existing license.

Implementation commit: `81c58ab`.

## 2026-09-16 — Bounded CLI compatibility and M7 completion

- Accepted ADR-0027 and stabilized only `civ5-turn` as the supported
  machine-readable pre-1.0 CLI; every other entry point is explicitly
  provisional while retaining mandatory safety and privacy behavior.
- Defined exact validation, execution-report, and failure JSON envelopes plus
  exit meanings for success, operation failure, and valid non-completion.
- Added named exit constants and strengthened contract tests for exact envelope
  keys and statuses.
- Confirmed that current supported consumers need no speculative selective
  knowledge or journal facade, completing all M7 acceptance criteria and moving
  the active milestone to M8 release readiness.
- Passed all 247 tests on Python 3.11 and the default Python 3.14 runtime. The
  submitted diff contained no private paths, network addresses, credentials,
  tokens, generated datasets, or real match records.

Implementation commit: `6577365`.

## 2026-09-16 — M8 release-readiness audit

- Audited M8 against live evidence, open high-impact risks, setup/security/
  recovery documentation, packaging, artifact scans, reproducibility, and
  release/tag requirements.
- Added a canonical release-readiness checklist and moved M8 to in progress;
  the combined M5/M6 live run, risk disposition, artifact automation, and
  release procedures remain explicit blockers.
- Reconciled current architecture, module, resolver, identity, operations,
  README, roadmap, changelog, and risk-register language after M7 completion.
- Documentation-link validation and the sensitive-content scan passed; no live
  machine state was changed and no offline result was labeled live evidence.

Implementation commit: `f4d487c`.

## 2026-09-16 — Bounded wheel release gate

- Added package description, README metadata, and the repository URL while
  retaining the existing Python 3.11 minimum and console-script declarations.
- Added a bounded pure-Python wheel inspector that verifies source coverage,
  archive paths/types/sizes, metadata, entry points, RECORD hashes, and scans
  contents for user paths, private addresses, email/MAC addresses, credentials,
  tokens, and private keys.
- Extended CI to build the wheel, inspect it, install it without dependencies
  into a clean virtual environment, import the aggregate API, and start the
  supported `civ5-turn` entry point on Python 3.11 and 3.13.
- Built and inspected the real wheel locally, then clean-installed and imported
  it with Python 3.11 and 3.14. All 251 tests passed warning-enabled on both
  local runtimes; sensitive-data review found only deliberate synthetic scanner
  fixtures and the intentional public license/repository attribution.

Implementation commit: `d7e40e9`.

## 2026-09-16 — Source artifact and normalized reproducibility gate

- Added an explicit source-distribution manifest containing release
  documentation, scripts, package sources, and tests while excluding local
  caches, generated game data, journals, databases, and logs.
- Extended artifact inspection to bounded tar archives, rejected links and
  unexpected members, and required packaged source and license bytes to match
  the checked-out project rather than checking filenames alone.
- Added normalized member/content hashes and two-build comparison for both
  wheel and source archives; compressed archive hashes remain separate because
  container timestamps may differ.
- Extended CI to double-build and compare both artifacts, then install each in
  a separate clean environment. Local double builds had identical normalized
  content, the source artifact clean-installed successfully, and all 254 tests
  passed warning-enabled on Python 3.11 and 3.14.
- Sensitive-data review found no private material outside deliberate synthetic
  scanner fixtures; public license and repository attribution remain explicit.

Implementation commit: `dd5f74a`.

## 2026-09-16 — Combined M5/M6 live release-gate procedure

- Added a self-contained, operator-present target-Mac procedure for capturing a
  private M5 journal while validating and executing exactly one explicit
  `end_turn` M6 TurnPlan through the watcher-owned path.
- Fixed private temporary paths, mode-0600 artifacts, manual readiness,
  fail-without-retry behavior, mandatory host restoration, payload-free
  integrity checks, detached structural replay, redacted export, and sanitized
  evidence rules without changing FireTuner, firewall, or game state.
- Reconciled the release checklist, roadmap, project dashboard, operations
  index, live-status ledger, and verification matrix so implementation is not
  mistaken for live evidence.
- All 254 tests passed warning-enabled on Python 3.11 and the default Python
  3.14 runtime. The documentation diff passed link and sensitive-content checks.

Implementation commit: `35aadc7`.

## 2026-09-16 — Stable release, upgrade, and rollback runbook

- Defined synchronized package-version locations, semantic increment rules,
  immutable annotated tags, and the explicit first-stable `1.0.0` transition
  without changing the current development version or creating a tag.
- Added exact release prerequisites, double artifact builds, normalized-content
  comparison, clean-environment installs, SHA-256 publication checks, and
  exact-commit/tag verification.
- Documented clean-environment upgrade, separation of package rollback from
  host safety restoration, immutable journal/knowledge handling, release
  withdrawal, and patch-version recovery.
- Reconciled the documentation index, operations index, roadmap, milestones,
  release gates, project dashboard, and changelog. Documentation and artifact
  contract tests passed, and the diff contained no private material.

Implementation commit: `75d87a5`.

## 2026-09-16 — M8 high-impact risk disposition

- Audited R-003 against the four-action allowlist, stock-API capability checks,
  exact read-back postconditions, offline failures, and target-build live
  evidence; marked it controlled only for the documented release scope.
- Audited R-004 against exact ruleset context, active-DLC detection, immutable
  source reads, source size/SHA-256 provenance, change detection, and local-only
  generated bundles; marked it controlled by provenance without claiming
  semantic equivalence between source hashes.
- Audited R-006 against ADR-0005, positive importer allowlists, generic
  flavor/personality rejection, adversarial fixtures, the completed remainder
  inventory, and release scans; marked it controlled while requiring renewed
  field review for every extension.
- Reconciled M8 planning and current state. All 78 focused documentation,
  knowledge, artifact, and tuner tests passed warning-enabled; sensitive-data
  scanning found no private material.

Implementation commit: `9a4adf1`.

## 2026-09-16 — M8 status-language reconciliation

- Audited roadmap, milestones, release readiness, project state, test strategy,
  module status, contracts, and the Chinese project outline after the M8
  release-control batches.
- Standardized high-impact outcomes as controlled, accepted, or closed; removed
  stale wording that still treated completed risk disposition as future work;
  and made the operator-present M5/M6 run the sole pre-candidate blocker.
- Documentation-link validation and sensitive-content scanning passed. No
  implementation, machine safety state, version, or release tag changed.

Implementation commit: `a73f07f`.

## 2026-09-16 — Bound FireTuner writes and preserve unknown outcomes

- Recorded the sanitized result of the first combined M5/M6 target-machine
  attempt: journal integrity, replay, redacted export, permissions, schema-5
  capture, observed turn transition, and M6 plan validation worked, while the
  oversized `end_turn` program was truncated before the action could execute.
- Added ADR-0028, a 1,000-byte pre-send FireTuner program limit, a compact
  fail-closed `end_turn` program, and regression coverage for every generated
  read/write program.
- Preserved submitted commands without a validated terminal result as journal
  verification errors, watcher-lifetime non-retryable uncertainty, and M6
  transport recovery rather than deterministic rejection.
- Reconciled M5/M6 verification status, the command/journal/public contracts,
  the release gate, risk R-014, milestones, project state, and the live-test
  procedure without claiming the operator's manual turn advance as automated
  success.
- All 259 tests passed warning-enabled on Python 3.11 and the default Python
  3.14 runtime and in GitHub Actions on Python 3.11/3.13. Documentation links,
  shell syntax, compilation, artifact checks, clean installs, diff checks, and
  sensitive-content scanning passed without private live artifacts.

Implementation commit: `c1dc935`.

## 2026-09-16 — Use the game-defined no-end-turn blocker

- Recorded the sanitized second combined M5/M6 target-machine attempt. It
  confirmed compact command-marker delivery, a complete failed-command journal
  lifecycle, stale-plan refusal before a second write, private integrity/export
  controls, and exact host restoration, but not automatic turn advancement.
- Traced the deterministic rejection to an incorrect numeric zero-blocker
  assumption. The target runtime returned the no-blocker value as `-1`, and the
  bundled Brave New World UI/tutorial Lua uses the named
  `NO_ENDTURN_BLOCKING_TYPE` enum.
- Added ADR-0029, changed the Lua guard to the game enum, exposed the verified
  parsed target value through the bridge/public API, and made factual readiness
  inspect the blocker independently of UI clickability.
- Reconciled the live ledger, test matrix, milestones, risks, release gate,
  contracts, project dashboard, outline, checklist, and changelog without
  treating the operator's stock-UI click as an automatic transition.
- All 260 tests passed warning-enabled on Python 3.11 and the default Python
  3.14 runtime. Compilation, shell syntax, documentation links, diff checks,
  and sensitive-content scanning passed without private live artifacts.

Implementation commit: `f3fa05c`.

## 2026-09-16 — Deferred-unit end-turn live evidence

- Recorded the sanitized third combined M5/M6 target-machine attempt. The
  named no-blocker guard invoked the stock control, but automated/deferred unit
  processing changed several unit states and surfaced one ready worker without
  advancing the turn.
- Confirmed exact failure semantics: M6 retained distinct before/after state,
  waited for the turn-advance postcondition, returned one failed step, and did
  not retry. M5 captured the submission, failed result, verification error, and
  private integrity/export evidence.
- Corrected the second attempt's evidence wording: its missing background turn
  transition alone could not establish whether the operator's later stock click
  changed turns. The third attempt independently proved the same-turn branch.
- Updated the release-gate procedure to prefer a minimal early-game state with
  no automated or deferred unit tasks; a large saved match remains a valid
  failure-path test but cannot reliably close the one-action success gate.
- Documentation-link validation, diff checks, and sensitive-content scanning
  passed. No private paths, identities, hashes, snapshots, or raw match data
  were committed.

Evidence commit: `41aa550`.

## 2026-09-16 — Complete the M5/M6 target-machine gate

- Recorded the sanitized successful combined live run: a newly authored
  one-action TurnPlan passed validation, completed once, and automatically
  advanced the game by one turn while the watcher observed the new schema-5
  state.
- Confirmed the same private M5 journal contained the successful command
  lifecycle and observed transition. Full-chain verification, contiguous
  replay, structural export, mode-`0600` permissions, and exact host
  restoration all passed.
- Marked M5 and M6 complete across their owning module documents, contracts,
  milestones, roadmap, verification ledger and matrix, release readiness,
  risks, project dashboard, outline, checklist, operations guidance, and
  changelog. The bounded procedure remains available for regression testing.
- Both warning-enabled 260-test suites passed on Python 3.11 and the default
  Python 3.14 runtime. Documentation links, diff checks, and added-line scans
  for local paths, user names, private addresses, live identities, hashes, and
  common credentials passed. No raw journal, plan, report, export, audit data,
  snapshot, private path, identity, or state hash was committed.

Evidence commit: `8ec902d`.

## 2026-09-16 — Prepare the 1.0.0 release candidate

- Advanced both declared package-version locations from 0.1.0 to 1.0.0 and
  moved the completed change set into the dated 1.0.0 changelog section with
  explicit compatibility and known-limitations notes.
- Added ADR-0030. The supported `civ5_agent.api` aggregate namespace and
  bounded `civ5-turn` interface are now the stable package surfaces; all other
  command-line entry points remain provisional while retaining mandatory
  safety, privacy, and write-verification controls.
- Reconciled the public contracts, architecture, project dashboard, milestone,
  release-readiness, operations, test-matrix, index, and README wording without
  rewriting the historical ADR-0026/0027 decisions.
- Both warning-enabled 260-test suites passed on Python 3.11 and the default
  Python 3.14 runtime. Documentation links, version equality, diff checks, and
  added-content scans for private paths, user names, private addresses, live
  identities, long hashes, private keys, and common credentials passed.
- No release tag or GitHub release was created; final candidate CI, duplicate
  artifact builds, clean installations, archive hashes, and explicit operator
  tag approval remain separate gates.

Implementation commit: `3449464`.

## 2026-09-16 — Define the downstream tactical integration boundary

- Reviewed the architecture, boundaries, contracts, glossary, ownership map,
  implementation plan, and current-state documentation in the independent
  `civ5-short-term-tactical-layer` project.
- Added ADR-0031 and a stable 1.0.0 downstream capability profile. They preserve
  one-way dependency, assign planning and consumer adapters outside the core,
  identify the exact public schemas/actions/limits available to consumers, and
  explicitly list absent capabilities.
- Added a strategy-neutral core capability request procedure for future facts,
  history views, and allowlisted mechanics, including privacy, failure,
  compatibility, offline-test, and target-machine evidence requirements.
- Reconciled architecture, module, API, release, risk, milestone, roadmap,
  verification, index, README, changelog, and repository-governance documents.
- Both warning-enabled 260-test suites passed on Python 3.11 and the default
  Python runtime. Documentation links, public capability constants, diff checks,
  and added-content scans for local paths, user names, private addresses,
  private keys, and common credentials passed without private artifacts.

Implementation commit: `5534544`.

## 2026-09-16 — Publish 1.0.0

- Published the immutable annotated `v1.0.0` tag at `676b029` after the exact
  commit and tag runs both passed GitHub Actions on Python 3.11 and 3.13.
- Built two independent wheels and two sequential source archives; both pairs
  matched by normalized content, passed bounded artifact inspection, and the
  selected wheel and sdist passed separate clean Python 3.11 installations.
- Published exactly the inspected wheel and sdist with SHA-256 hashes in the
  GitHub release notes, downloaded both assets again, and confirmed their
  hashes matched. The release is neither a draft nor a prerelease.
- No live-game setting, FireTuner state, firewall rule, private game data, or
  generated local dataset was changed or published during release work.

## 2026-09-17 — Plan verified unit movement

- Added M9 and an ordered unit-movement plan covering documentation, stock-source
  research, contracts, minimum read state, allowlisted write/verification,
  deterministic execution, offline tests, bounded live evidence, and a future
  compatible release.
- Bounded the first design target to a caller-selected adjacent single step.
  The tactical layer retains unit, destination, route, purpose, and alternative
  selection; the core retains legality, bounded submission, and read-after-write
  result authority.
- Registered the strategy-neutral work as GitHub CoreCapabilityRequest #1 and
  made unsupported capability the required downstream behavior until a released
  profile advertises verified support.
- Updated the five-hour heartbeat automation to follow the M9 plan's first
  unfinished safe batch, ignore weekly quota, stop before 85% five-hour use,
  require complete tested commits, and pause for explicit authorization before
  any real-game operation.
- Documentation-link tests, diff checks, and added-content scans passed. The
  only user-name match is the intentional public repository URL; no private
  path, address, credential, match state, or generated data was added.

Planning commit: `1de7f36`.

## 2026-09-17 — Decide the adjacent movement boundary

- Inspected the installed Brave New World UI and target binary read-only, then
  used the public released SDK mirror as corroborating reference rather than
  copied code or target-runtime proof.
- Accepted ADR-0032: the first movement slice uses exact unit selection plus
  the stock network-backed `SelectionListMove` path for one caller-selected
  adjacent, visible, empty, non-city plot. Direct `PushMission`, attacks,
  swaps, embarkation, air movement, automation, and multi-step paths remain
  outside the slice.
- Recorded the released bindings that make `GeneratePath` and
  `CanMoveOrAttackInto` unsuitable as authoritative admission checks, and kept
  exact fresh identity-and-coordinate read-back as the success authority.
- Added open risk R-017 for selection drift and deferred mission behavior;
  target-machine evidence remains required before support or release is
  claimed.
- Updated M9 planning, roadmap, milestone, and project-state documents. All 260
  warning-enabled offline tests and documentation links passed. Added-content
  scans found no private path, local address, credential, match state, or
  generated game data; the public repository and reference URLs are intentional.

Decision commit: `4bf347f`.

## 2026-09-17 — Freeze unit-movement contracts and live-test design

- Added the owning unit-movement contract for planned schema 6 and the exact
  `move_unit(unit_id, x, y)` action. Each unit exposes at most six sorted,
  active-player-visible `ordinary_move_targets`; this is the conservative core
  subset, not general map/pathing data or a tactical recommendation.
- Froze pre-send admission, exact selected-unit submission, identity/location/
  decreased-movement postconditions, terminal failure branches, and unknown-
  outcome no-retry behavior without adding the command to the current allowlist.
- Defined how schema 1 TurnPlans will admit the future action, cover only the
  matching unit-order requirement, pause when more orders remain, and preserve
  conservative non-final recovery.
- Reconciled live-state, command, public API, CLI, downstream, bridge, executor,
  milestone, state, roadmap, strategy, matrix, and Chinese status documents.
- Added a bounded live procedure that is explicitly disabled until offline
  implementation passes. It permits only a source-coordinate pre-send rejection
  and one user-authorized adjacent move, followed by exact host restoration.
- All 260 warning-enabled offline tests and documentation links passed.
  Added-content scans found no private path, local address, credential, match
  state, or generated game data.

Contract commit: `e6e74a0`.

## 2026-09-17 — Add the schema 6 movement-target read model

- Upgraded the current snapshot to schema 6 while preserving schema 2–5
  parsing and validation. A seventh independently bounded read-only segment
  computes the conservative adjacent `ordinary_move_targets` for each owned
  unit without exposing hidden plots or choosing a destination.
- Required active turn, readiness, remaining movement, non-busy/non-automated/
  non-delayed state, non-air and non-embarked status, current visibility, empty
  non-city destination, unchanged land/water classification, and the stock
  `CanMoveThrough` predicate.
- Added strict parser and model checks for the required segment, unit binding,
  zero-to-six count, exact coordinate fields, the public 65,535 coordinate
  bound, deterministic ordering, duplicates, and malformed records.
- Exported the schema set and coordinate bound through the stable aggregate
  surface, while keeping `move_unit` absent from the action allowlist.
- Added legacy, malformed, incomplete, privacy-predicate, read-only, aggregate-
  export, and Lua-size coverage. The seven generated programs are all below the
  1,000-byte transport limit; the largest remains 875 bytes.
- All 266 warning-enabled offline tests and documentation links passed.
  Added-content scans found no private path, local address, credential, match
  state, or generated game data. No game, FireTuner, or firewall operation ran.

Implementation commit: `cde1b55`.

## 2026-09-17 — Implement bounded movement submission and verification

- Added the exact `move_unit(unit_id, x, y)` command schema with strict integer,
  boolean, field, and coordinate bounds on development head.
- Required a fresh validated schema 6 snapshot, exact active-player unit, and a
  destination already present in that unit's conservative
  `ordinary_move_targets` before generating a write.
- Added a 973-byte worst-case tested Lua program that rechecks the observed
  source coordinates and all narrow ordinary-move guards, selects and verifies
  the exact unit, and calls `Game.SelectionListMove` once without `PushMission`.
- Added exact write-after-read success requiring the same turn, player, active
  turn, unit ID/type, destination, and strictly lower movement points. Marker
  acceptance, unchanged state, unexpected displacement or movement spend,
  disappearance, transformation, turn drift, schema drift, and timeout remain
  errors.
- Routed the direct bridge command through watcher duplicate suppression,
  uncertainty handling, audit/journal composition, and the provisional command
  CLI. Kept TurnPlan admission closed until the separate C4 executor batch.
- All 278 warning-enabled offline tests passed on the default runtime, including
  Unix-socket IPC tests outside the sandbox. Documentation links, diff checks,
  and tracked-content scans passed; no private path, local address, credential,
  real match state, or generated game data was added. No game, FireTuner, or
  firewall operation ran.

Implementation commit: `0d886f2`.

## 2026-09-17 — Integrate movement into deterministic turn execution

- Enabled exact `move_unit` actions in schema 1 TurnPlans without adding route,
  unit, destination, or alternative selection to the executor.
- Made movement cover `unit_orders` only for the matching unit ID. A unit that
  remains ready must have another explicit move/skip later in the plan or the
  executor pauses before further writes; multiple moves retain declared order.
- Added executor-side defense-in-depth for both immediate and cached movement
  results: schema 6 on both sides, admitted before-state target, changed source,
  preserved unit identity/type, exact destination, lower movement, and unchanged
  active turn/player are all required.
- Covered successful move/end-turn execution, repeated movement, wrong-unit and
  uncovered-order pauses, invalid bridge claims, factual events, watcher
  argument forwarding, journal command composition, unchanged CLI envelopes,
  successful non-final recovery, and invalid cached recovery evidence.
- All 290 warning-enabled offline tests passed on the default runtime, including
  Unix-socket IPC tests outside the sandbox. Documentation links, diff checks,
  and tracked-content scans passed; no private path, local address, credential,
  real match state, or generated game data was added. No game, FireTuner, or
  firewall operation ran.

Implementation commit: `629f0a8`.

## 2026-09-17 — Complete the movement offline gate

- Reconciled every C5 branch against executable tests and the verification
  matrix: malformed/bounded arguments, legacy and schema-drift refusal,
  unknown or foreign-as-absent units, unlisted/unsupported targets, exact
  source guards, every terminal marker, explicit rejection, transient reads,
  unchanged/partial/unexpected state, timeout, and missing markers.
- Added movement-specific UUID replay/no-retry coverage, exact provisional CLI
  forwarding, public allowlist compatibility, and retained the C4 multi-action,
  journal, event, recovery, and executor-continuity evidence.
- Marked the bounded live checklist executable only as an operator-assisted
  procedure. It still permits just one source-coordinate pre-send rejection and
  one separately authorized adjacent ordinary move, with no retry after any
  uncertain outcome.
- All 297 warning-enabled tests passed on Python 3.11 and the default runtime;
  documentation links and diff checks passed. Tracked-content scans found no
  private path, local address, credential, real match state, or generated game
  data. No game, FireTuner, or firewall operation ran.

Implementation commit: `ed7daea`.

## 2026-09-17 — Record the bounded movement live gate

- Completed C6 on the target Campaign Edition build with one guarded schema 6
  watcher, one source-coordinate pre-send rejection, and one separately
  authorized adjacent ordinary move.
- The accepted move reached the exact admitted target in the same active turn,
  reduced movement points, produced a fresh watcher snapshot, and caused no
  observed combat, capture, swap, embark/disembark, prompt, or movement by
  another unit.
- Confirmed the private command audit remained mode `600` and restored
  FireTuner, listener, agent socket, firewall, and Civ V rule to the recorded
  host baseline.
- Reconciled the experiment log, verification matrix, Chinese live ledger,
  project dashboard, milestone/roadmap, risk R-017, bridge and public contracts,
  downstream compatibility forecast, and changelog. Development head is now
  live-verified but remains absent from the released 1.0.0 profile until D4/C7
  completes the planned 1.1.0 release.
- All 297 warning-enabled tests passed on Python 3.11 and the default runtime.
  Documentation links, diff checks, and tracked-content scans passed; no raw
  snapshot, private path, local address, credential, real identifier, map
  coordinate, UUID, or private audit data was committed.

Evidence commit: `15a54b1`.

## 2026-09-17 — Publish verified unit movement in 1.1.0

- Prepared the 1.1.0 compatibility surface with schema 6 and the bounded
  `move_unit` action while preserving the existing stable aggregate API,
  TurnPlan schema, CLI envelopes, module boundaries, and downstream ownership.
- The release commit passed all 297 tests locally on Python 3.11 and the default
  runtime, plus exact-commit and annotated-tag GitHub Actions on Python
  3.11/3.13. CI also repeated artifact inspection and clean installation.
- Two independent exact-commit wheel builds and two independent source archives
  had matching normalized content. Separate clean Python 3.11 environments
  installed both formats, imported the aggregate API at version 1.1.0, and
  started the supported `civ5-turn` CLI.
- After explicit operator authorization, immutable tag `v1.1.0` was created at
  `ad90dbd` and the GitHub Release published exactly the inspected wheel and
  source archive. Downloaded assets passed the artifact inspector and matched
  the recorded SHA-256 values: wheel
  `78e308bfe3c0cadb38252860a4a809b796da58c4337ea2771965750c75fee6f2` and
  source archive
  `2e4f9b199be6e60dfa5c2c301933ddb4adec1437735aba3f79ebb2c8835a76d5`.
- No generated dataset, match snapshot, journal, audit log, plan, private path,
  local address, credential, unit identity, coordinate, or session identity was
  committed or published.

Release commit: `ad90dbd`; tag: `v1.1.0`.

## 2026-09-17 — Register and plan the worker-build capability

- Registered downstream CoreCapabilityRequest Issue #2 and introduced M10 as
  a strategy-neutral verified worker-build milestone targeting a compatible
  1.2.0 release only after bounded live evidence.
- Limited the first slice to one caller-selected ordinary `BUILD_*` action for
  a worker already standing on the intended plot. Worker/plot/improvement
  choice, movement, scoring, recommendations, routes, repair, removal-only,
  automation, water, and consuming/special builds remain excluded.
- Added the D0–D4/C0–C7 development plan, acceptance criteria, downstream
  absent-capability behavior, verification-matrix forecast, and R-018.
- Recorded bundled BNW source evidence for action mapping, capability checks,
  dispatch, active-build, and progress APIs without claiming live support.
  Per-unit read-only candidate enumeration and immediate-completion proof remain
  C0/D1 blockers before ADR-0033, frozen contracts, or command code.
- All 297 warning-enabled tests passed on Python 3.11. Documentation links and
  diff checks passed; the changed files contain no local path, address,
  credential, private match state, or generated game data. No game, FireTuner,
  or firewall operation ran.

Planning commit: `2f4bc54`.

## 2026-09-17 — Decide the ordinary worker-build mechanism

- Completed M10 C0/D1 against the installed BNW UI and supporting released SDK
  source at the already recorded exact commit; no third-party source was
  copied.
- Accepted ADR-0033: enumerate exact per-unit candidates with selection-free
  `unit:CanBuild`, then select and re-check the exact unit before the stock
  `Game.CanHandleAction`/`Game.HandleAction` network-backed submission.
- Restricted the first slice to blank featureless land and non-route,
  non-repair, non-water, non-consuming improvement builds. This excludes the
  overwrite popup and feature-removal side effects.
- Defined separate exact success branches for an active requested `BUILD_*`
  and an immediately completed paired `IMPROVEMENT_*`; both retain the same
  unit and plot and require lower movement.
- Measured design prototypes at 688 and 895 bytes for the two read-only
  segments and 994 bytes for a worst-case compact write. Final generated
  strings remain subject to executable bounds and target-machine evidence.
- All 297 warning-enabled tests passed on Python 3.11. Documentation links,
  diff checks, and changed-file sensitive-content scans passed. No game,
  FireTuner, firewall, or live write operation ran.

Decision commit: `a526974`.

## 2026-09-17 — Freeze worker-build contracts

- Added the owning worker-build contract and froze schema 7 current-plot
  context, current build, and bounded factual build/improvement candidates.
- Defined the exact four-field `worker_build` request, conservative admission,
  selected-unit stock dispatch, and separate active-build and
  completed-improvement success branches.
- Kept TurnPlan schema 1 and the existing result, report, event, journal, and
  stable CLI envelopes unchanged; core 1.1.0 continues to reject the action.
- Updated module, public API, downstream, roadmap, milestone, project-state,
  and verification-matrix documents. Implementation begins only after the D3
  offline and bounded-live procedures are frozen.
- All 297 tests passed. Documentation links, diff checks, and changed-file
  sensitive-content scans passed. No game, FireTuner, firewall, or live write
  operation ran.

Contract commit: `dd03351`.

## 2026-09-17 — Freeze worker-build verification gates

- Added WB-S01–A02 as the complete offline schema, candidate, privacy,
  command, verification, uncertainty, watcher, executor, compatibility,
  artifact, and privacy matrix for M10.
- Added a finite operator-assisted procedure that permits only read-without-
  selection proof, one stale-source pre-send rejection, and one separately
  authorized candidate build after C1–C5 pass.
- Defined either exact active-build or immediate-completion branch as
  sufficient live evidence while retaining the other branch offline-only;
  unknown outcomes end the write portion without retry.
- Updated the test strategy/matrix, Chinese evidence ledger, project state,
  roadmap, milestone, and R-018. No game, FireTuner, firewall, or live write
  operation ran.
- All 297 tests, documentation links, diff checks, and changed-file sensitive-
  content scans passed.

Verification-design commit: `fb65a12`.

## 2026-09-17 — Implement schema 7 worker-build reads

- Implemented two selection-free schema 7 segments for exact per-unit current-
  plot context/current build and conservative ordinary build/improvement
  candidates. Final generated sizes are 688 and 895 UTF-8 bytes.
- Added strict multipart parsing and state validation for active-team-visible
  resources, identifier/null/type bounds, exact nested shape, unit binding,
  sorting, duplicate rejection, and the 32-candidate limit while retaining
  schemas 2–6.
- Exported the frozen schema and size limits without adding `worker_build` to
  the action allowlist. Reads never use recommendation/personality data or UI
  selection.
- Preserved the released movement capability by accepting matching schema 6+
  before/after states in direct and deterministic-executor verification.
- WB-S01–S06 pass within a 307-test warning-enabled baseline. Documentation
  links, diff checks, and changed-file sensitive-content scans passed. No game,
  FireTuner, firewall, or live write operation ran.

C1 commit: `f65ece8`.

## 2026-09-17 — Implement worker-build submission and factual verification

- Added the exact four-field `worker_build` action on the unreleased
  `1.2.0.dev0` surface, with schema 7 candidate/source admission before any
  game write.
- Added one worst-case 996-byte selected-unit stock program that re-resolves
  the unit, plot, build and action, repeats mutable guards, checks exact
  selection and `Game.CanHandleAction`, and calls `Game.HandleAction` once.
- Kept private markers as submission evidence only. Fresh polling now proves
  the same turn/player/unit/type/plot, lower movement, unchanged supported plot
  facts, and exactly one active-build or completed-improvement branch.
- Preserved watcher session binding, exact UUID replay, audit/journal
  composition, and non-retryable unknown-outcome handling. TurnPlan admission
  remains gated for C4 and the stable 1.1.0 downstream profile is unchanged.
- All 319 warning-enabled tests passed on Python 3.11 and the default runtime.
  Documentation links, diff checks, release metadata checks, and tracked-file
  sensitive-content scans passed. No game, FireTuner, firewall, or live write
  operation ran.

C2–C3 commit: `1d19416`.

## 2026-09-17 — Integrate and package-gate worker builds

- Added `worker_build` to schema 1 TurnPlans only when the validated state
  basis is schema 7, preserving exact four-field argument validation and
  exact-unit action coverage.
- Integrated worker builds into deterministic execution, including explicit
  move-then-build sequencing, pause behavior for still-ready workers,
  independent postcondition validation, event emission, and conservative
  cached-result recovery without resubmission.
- Completed the C5 offline matrix for mutable preconditions, all supported
  plot-fact drift, ambiguous/wrong/missing success branches, transient polling,
  unchanged-state timeout, brokered CLI forwarding, private audit records,
  journal lifecycle, UUID replay, and unknown-outcome suppression.
- All 335 warning-enabled tests passed on Python 3.11 and the default runtime.
  Two independent wheel/source builds had matching normalized contents; both
  formats installed and imported in clean Python 3.11 environments, and the
  supported CLI started successfully.
- Artifact and tracked-content scans found no private paths, local addresses,
  credentials, generated game data, or real match state. No game, FireTuner,
  firewall, or live write operation ran. C6 remains a separately authorized
  target-machine gate.

C4–C5 commit: `c070459`.

## 2026-09-18 — Repair the schema 7 target-runtime iterator

- Ran the first bounded M10 C6 attempt through guarded preparation and live
  preflight. The watcher stopped safely at its first read-only schema 7 gate
  because Campaign Edition exposes `GameInfoActions` as a table rather than a
  callable iterator; no command or game write ran, and host restoration matched
  the recorded baseline.
- Replaced the invalid callable-table loop with numeric table iteration already
  used by a target-verified action path, and added a regression assertion that
  explicitly forbids the failed call form.
- Compact local aliases retain every candidate predicate while reducing the
  repaired worker-build segment to 888 UTF-8 bytes, below the independent
  900-byte read-segment bound.
- All 335 warning-enabled tests passed on Python 3.11 and the default runtime.
  Documentation/release checks, diff checks, and tracked/diff sensitive-content
  scans passed. A fresh separately authorized C6 remains required.

Repair commit: `cb8187b`.

## 2026-09-19 — Match worker legality flags to the target Lua binding

- Ran a fresh guarded C6 retry after the indexed-action repair. It passed the
  prior failure point and stopped safely at the read-only candidate predicate
  because Campaign Edition requires numeric option flags for `unit:CanBuild`.
  No command or write ran, and host restoration again matched the baseline.
- Confirmed from the locked Expansion 2 SDK source that
  `CvLuaUnit::lCanBuild` reads the two options with `luaL_optint`, defaulting to
  `0` and `1`; ADR-0034 records the target-specific representation correction
  without changing ADR-0033's capability boundary.
- Updated both selection-free candidate collection and the game-side
  pre-submit recheck to `CanBuild(..., 0, 1)`. Exact-form regressions cover both
  paths; the read and worst-case write programs are now 881 and 989 bytes.
- All 335 warning-enabled tests passed on Python 3.11 and the default runtime.
  Documentation/release checks, diff checks, and tracked/diff sensitive-content
  scans passed. A fresh separately authorized C6 remains required.

Binding-fix commit: `f596516`.

## 2026-09-19 — Repair worker-build Lua token boundaries

- Ran a fresh guarded C6 attempt on exact implementation commit `28469a3`.
  Schema 7 candidate facts matched the enabled stock action without read side
  effects, and the stale-source request was rejected before submission with
  unchanged state.
- Sent the separately authorized build exactly once. The target parser rejected
  generated Lua where interpolated numeric literals touched following `or` and
  `then` keywords. No valid marker was returned, the UI showed no build or
  movement change, the command was not retried, and host restoration matched
  the recorded baseline.
- Added explicit whitespace at every affected numeric/keyword boundary and
  regression assertions over the actual generated source. The worst-case
  program is 992 bytes and remains below the 1,000-byte transport limit.
- All 335 warning-enabled tests passed on Python 3.11 and the default runtime.
  Repeated wheel/source builds had matching normalized contents, and the wheel
  installed, imported, and started its CLI in a clean Python 3.11 environment.
  Diff and tracked-file scans found no private live IDs, coordinates, local
  paths, credentials, generated game data, or match snapshots.

Repair and sanitized-evidence commit: `b15e967`.

## 2026-09-19 — Resolve worker actions through the target table shape

- Ran a new guarded C6 session on exact implementation commit `74ba4d1`.
  Schema 7/UI agreement and stale-source rejection passed again. The separately
  authorized single write parsed but returned explicit `invalid_build` because
  the write path indexed `GameInfoActions` with a build-type string.
- Before/after state and the game UI agreed that no build, movement loss,
  popup, other unit action, or turn advance occurred. The command was not
  retried, and host restoration matched the recorded baseline.
- Replaced string-key action lookup with the target-proven bounded numeric table
  iteration, requiring exact build Type, build SubType, and MissionData before
  selection or dispatch. The generated program retains every mutable guard,
  contains one `Game.HandleAction`, and is 997 bytes at worst-case inputs.
- Added regression coverage forbidding the failed lookup form and requiring the
  exact numeric iteration/mapping predicates. All 335 warning-enabled tests
  passed on Python 3.11 and the default runtime. Repeated wheel/source contents
  matched, and the wheel installed, imported, and started its CLI in a clean
  Python 3.11 environment.
- Diff and tracked-file scans found no private session IDs, unit IDs,
  coordinates, snapshots, local paths, credentials, or audit contents.

Repair and sanitized-evidence commit: `f28a9b4`.

## 2026-09-19 — Dispatch worker builds with the stock action index

- Ran a fresh guarded C6 session on exact implementation commit `4a6433f`.
  Candidate/UI agreement and stale-source rejection passed again. Numeric
  action resolution reached the executability guard, but the separately
  authorized single write returned explicit `blocked`.
- Before/after state and UI confirmed no build, movement loss, popup, other
  unit action, or turn advance. The command was not retried and restoration
  matched the recorded baseline.
- Re-inspected the installed BNW `UnitPanel.lua`: stock buttons retain the
  numeric `GameInfoActions` loop index and pass that value to both
  `Game.CanHandleAction` and `Game.HandleAction`. The table entry's `ID` is not
  the stock click-path argument.
- Changed the compact program to retain and submit the matched numeric index,
  and added exact regressions forbidding entry-ID guard or dispatch calls. The
  worst-case generated program is 991 bytes and contains one stock write.
- All 335 warning-enabled tests passed on Python 3.11 and the default runtime.
  Repeated wheel/source contents matched, the wheel installed/imported/started
  its CLI in a clean Python 3.11 environment, and sensitive-content scans found
  no private live data, identities, paths, credentials, or audit contents.

Repair and sanitized-evidence commit: `9ee4e55`.

## 2026-09-19 — Close the bounded worker-build live gate

- Recorded the successful schema 7 C6 run on exact implementation commit
  `04dd70f`: read/UI agreement, read purity, stale-source pre-send rejection,
  one separately authorized active-build result, independent watcher evidence,
  private audit permissions, no observed extra side effect, and exact host
  restoration all passed.
- Updated the worker-build contract, downstream profile, module boundaries,
  milestone, roadmap, risk register, test matrix, live-verification ledger,
  project dashboard, experiment log, and changelog. The unobserved immediate-
  completion branch remains offline-only; D4/C7 release preparation is next.
- All 335 warning-enabled tests passed on Python 3.11 and the default runtime;
  documentation links and Python 3.11 compilation passed. Sensitive-content
  scans found no real session or unit IDs, local user paths, terminal identity,
  credentials, tokens, or raw snapshots in the committed evidence.

Sanitized C6 evidence commit: `138fa20`.

## 2026-09-19 — Publish stable worker-build release 1.2.0

- Prepared exact release commit `6210a4e` with version 1.2.0, dated changelog,
  stable schema 7/`worker_build` contracts, downstream capability profile, and
  offline release runbook that does not require dependency downloads.
- All 335 warning-enabled tests passed on Python 3.11 and the default runtime.
  Exact-commit and annotated-tag GitHub Actions passed on Python 3.11/3.13.
- Two independent exact-commit wheel and sdist builds had matching normalized
  contents. Both formats installed, imported, and started the stable CLI in
  separate clean Python 3.11 environments; artifact and sensitive-content
  checks passed.
- After explicit authorization, immutable tag `v1.2.0` was pushed and the
  inspected wheel and source archive were published. Fresh downloads matched
  the recorded SHA-256 values:
  - wheel: `f7ee5e040de0c87e11d0c5a7c72238f1effe5137de3c7b8ecf19e242664bdf31`;
  - sdist: `3131ee72ca024fb471d9429ce69cecb1393d0237221d64ad8f575282cb5d7da3`.
- The release adds only the caller-selected ordinary worker-build slice. The
  immediate-completion result branch remains offline-only, and tactics,
  movement-to-plot, automation, routes, repair, and build choice remain outside
  the core.

## 2026-09-19 — Freeze M11 runtime research facts design

- Normalized the first post-1.2 downstream request as read-only, strategy-neutral
  runtime facts rather than a forecast engine or executor responsibility.
- Accepted ADR-0035 and froze the schema 8/core 1.3.0 contract: exact effective
  candidate costs, times-100 progress and science, whole-point overflow,
  runtime turns-left, explicit action-window phase, and field provenance.
- Separated runtime context identity from a complete ruleset proof. Missing
  game-family/build/content dimensions and the full ruleset fingerprint remain
  explicit unavailable/unsupported values. A downstream adapter must fail
  closed on binding gaps or conflicts for exact-supported forecasts and
  forecast-dependent automation, without erasing core runtime facts or
  prohibiting a separately approved non-forecast manual intent.
- Registered M11 and its staged C1–C5 plan. Implementation and target evidence
  remain pending; schemas 2–7 and all write, plan, executor, result, and journal
  contracts are unchanged by this design batch.

## 2026-09-19 — Implement M11 schema 8 offline

- Added three bounded read-only programs for ordinary-research forecast status,
  candidate facts, and runtime context. Twelve total snapshot programs remain
  below the 1,000-byte transport limit; the largest is 981 bytes.
- Added schema 8 parsing and strict validation for effective cost, times-100
  progress/science, whole-point overflow, runtime turns-left, action-window
  phase, field provenance, explicit context availability, and the unsupported
  ruleset-fingerprint boundary.
- Exported capability/context version 1 on development version `1.3.0.dev0`.
  Existing worker-build admission and verification now accept a matching schema
  7+ state so the extension does not disable the published action.
- Preserved schemas 2–7 wire and digest shape by omitting schema-8-only fields
  from legacy serialization. KnowledgeBundle binding remains a downstream
  exact-forecast/automation concern and is not required to validate live facts.
- All 346 tests pass on Python 3.11. Repeated wheel and source distributions
  have equal normalized contents, both artifact scans pass, and a clean wheel
  installation imports the new public constants. Target-machine evidence is
  still pending.

## 2026-09-19 — Rename schema 8 public research facts

- Accepted ADR-0036, which supersedes only ADR-0035's provisional public
  naming decision. The values, units, provenance, support states, runtime
  context, and downstream boundary remain unchanged.
- Renamed the unreleased live-state field, capability constant, segmented
  protocol part/marker, parser and validation helpers, current contract, plan,
  and verification specification to `research_runtime_facts` terminology.
- Added canonical schema 8 key coverage and pinned canonical bytes/digests for
  schemas 2–7. No compatibility alias, live write, target experiment, tag, or
  release was added in this batch.

Implementation and contract commit: `c67e096`.

## 2026-09-19 — Prepare bounded M11 target verification

- Added a read-only schema 8 target procedure with guarded session setup,
  watcher-summary commands, UI/unit comparison, a controlled 20-remaining and
  22-produced overflow sequence, zero-command audit checks, exact host
  restoration, stop conditions, and a sanitized evidence template.
- Corrected the M11 verification status to distinguish completed C1–C3 offline
  evidence from pending C4 target evidence. No game, firewall, bridge write,
  tag, or release action was performed.
- All 347 tests passed on Python 3.11; documentation links, diff hygiene, and
  sensitive-content checks passed.

Procedure and status commit: `d9c2a20`.

## 2026-09-19 — Correct the schema 8 research-progress binding

- The first bounded C4 attempt on development commit `bd5ba1e` confirmed schema
  8 framing and visible read purity, then failed closed because Campaign Edition
  does not expose `GetResearchProgressTimes100` on `CvPlayer`.
- A separately authorized, bounded read-only diagnostic located the exact
  times-100 method on the active team's `CvTeamTechs` object. ADR-0037 records
  the corrected binding and provenance without changing the schema, field,
  units, capability version, or any write contract.
- Updated both schema 8 read programs and added a regression that requires the
  team-technologies owner. All twelve programs remain within the verified
  FireTuner limit; the largest is 990 bytes.
- All 348 tests passed on Python 3.11 and compilation passed. Two wheel builds
  and two source builds had matching normalized contents; clean installations
  from both formats imported successfully. Sensitive-content and diff-hygiene
  checks passed.
- The private command audit was not independently inspected during the first
  attempt, so the corrected full C4 target gate remains pending.

Implementation, ADR, and sanitized diagnostic-evidence commit: `41b06e3`.

## 2026-09-20 — Separate generic automation from the execution core

- Reverted the misplaced generic automation implementation from unpushed
  commits `080baab`/`41aeb32` without rewriting local history. Generic
  automation is owned by an independent repository and composed externally.
- Retained only the execution-core `civ5-watch --read-only` capability under
  ADR-0039. Its server admits ping and validated state reads, rejects command
  lookup and every write before execution, and prohibits journal capture.
- Preserved the M11 exact positive-overflow procedure as domain verification:
  20/22 is illustrative, fractional surplus remains evidence, and a qualifying
  case must produce at least one positive whole research point of overflow.
- Removed its mixed entry point, implementation, tests, module/operations
  documents, and every architecture, roadmap, status, testing, and changelog
  claim about that ownership.

## 2026-09-20 — Add the independent automation process boundary

- Added a provisional `civ5-read-only` adapter without adding the external
  automation package as a Python or runtime dependency.
- Added a fail-closed probe that requires server-declared read-only mode and a
  same-session validated state, then emits only a bounded non-identifying
  summary.
- Added pure SessionSpec v1 JSON generation for supervising only
  `civ5-watch --read-only`; it inherits no environment, retains no raw child
  output, and contains no C4/M11 or other domain workflow.
- Recorded the independent-repository and external-composition-root boundary in
  ADR-0040, CLI/security/operations documentation, and the verification matrix.

## 2026-09-20 — Adopt local-app-test-automation v0.1.0

- Replaced development-candidate/local-checkout assumptions with the published
  v0.1.0 release identity: tag target, wheel name, and Release SHA-256.
- Accepted ADR-0041 and added an external-automation compatibility contract for
  SessionSpec v1, public CLI/process composition, artifact verification, and
  explicit upgrade review.
- Kept the framework optional and external: no Python import, package
  dependency, shared live object, or Civ/M11/C4 framework profile was added.
- Verified the published wheel digest and installed CLI, then repeated the
  caller integration and complete execution-core regression gates.

## 2026-09-21 — Recover FireTuner snapshot framing after interturn

- Ran the corrected M11 C4 procedure through a naturally qualifying
  positive-overflow precondition. Repeated schema 8 reads and UI agreement
  passed; the manual interturn then exposed a persistent snapshot-part-before-
  header error, so no post-completion overflow result was inferred.
- Confirmed the private audit remained mode `600` with zero records and restored
  the exact host baseline. Recorded only sanitized values and conclusions in
  the experiment log.
- Accepted ADR-0042. FireTuner collection now retains Lua output delivered after
  an early command acknowledgement, while residual marked-part/header
  desynchronization ends the connection epoch and causes a guarded watcher
  reconnect with a new bridge-session identity. No submitted write is retried.
- Recorded the target automation ordering constraint: simultaneous application
  and watcher startup fails closed before TCP 4318 readiness; a separate
  generic launch phase followed by `observe_verified` successfully supervised
  the server-enforced read-only watcher without adding a framework profile.
- Relevant tests passed 95/95 and the complete suite passed 361/361. Repeated
  wheel and source-distribution contents matched, artifact inspection passed,
  and the tracked sensitive-content scan was empty.

Implementation, ADR, and partial target-evidence commit: `ff63552`.

## 2026-09-21 — Drain multi-frame output after early FireTuner acknowledgement

- Repeated M11 C4 on repaired commit `57c92a9`. The first interturn preserved
  the connection and exposed positive whole-point overflow; selection preserved
  it, and the following interturn applied it, but that second interturn rotated
  the bridge session and therefore failed the continuity gate.
- Recorded only sanitized target evidence. The private audit remained mode
  `600` with zero records, and guarded shutdown restored the exact host
  baseline.
- Accepted ADR-0043 and changed acknowledgement-first collection to drain every
  subsequent output frame to the existing bounded idle/total deadline. Ordinary
  output-before-acknowledgement behavior and fail-closed reconnect semantics are
  unchanged.
- Added a multi-frame acknowledgement-first regression. Relevant transport and
  watcher tests passed 89/89; the complete host-context suite passed 362/362.
- Repeated wheel and source-distribution builds matched normalized content with
  hashes `8b127fc2593729ec6e9178dd89104821a5b663f4a251899daf1bd0c2b177e67e`
  and `31f994744d9b25eefeafd4d7cefc702ae84f5714d3363e579b992e2bbb2b16cc`.
  Artifact inspection, compilation, documentation links, diff checks, and the
  tracked sensitive-content scan passed.

Implementation, ADR, and partial target-evidence commit: `d99209d`.

## 2026-09-21 — Complete M11 same-session target verification

- Repeated the full C4 sequence on exact commit `95ef3df` after ADR-0043.
  Stable schema 8 reads agreed with the stock UI and one bridge session
  persisted across both interturns.
- Observed positive whole-point overflow `144`, preservation through manual
  technology selection with exact progress still zero, and later application
  as `59174` times-100 progress with overflow cleared.
- Preserved the `3.19` point surplus/overflow difference without inventing a
  formula. Science changed from `447.21` before completion to `444.55` in the
  following action window, which is recorded only as a plausible production-
  change explanation.
- Confirmed the private audit was mode `600` with zero records, removed the
  watcher socket, and restored the exact host baseline. The generic supervisor
  launched and observed the application, but its published v0.1.0 does not own
  product-specific launcher/continue actions. A direct exit-confirmation click
  missed and the operator completed that confirmation manually.
- Reconciled the owning contract, bridge and downstream profiles, roadmap,
  plan, verification matrix, live ledger, changelog, and project dashboard.
  Corrected the old contract wording so the 20-remaining/22-produced case is
  illustrative rather than the only valid controlled fixture.
- Documentation links, diff checks, and the tracked sensitive-content scan
  passed.

Sanitized target-evidence and reconciliation commit: `7e28b05`.

## 2026-09-21 — Prepare the 1.3.0 release candidate

- Promoted the package and public compatibility documents from development
  version `1.3.0.dev0` to the untagged `1.3.0` release candidate while
  preserving schemas 2–7 and every write, plan, result, executor, and journal
  contract.
- Reconciled project state, milestones, release readiness, module ownership,
  downstream capability discovery, and the M11 risk disposition. The release
  remains pending exact-commit CI and explicit tag/Release authorization.
- The complete host-context suite passed 362/362 warning-enabled tests on both
  Python 3.11 and the default runtime. Tracked sensitive-content and diff
  checks passed.
- Two independent wheel builds had normalized content SHA-256
  `69b8f36eefd453a4e87200026db4984cac137cc714e133beb732636cf5976b7f`;
  the two source distributions had normalized content SHA-256
  `9223ae52634d1d4902f9816f29367b375bdbc98d7027a26099dac9d3aaae97d6`.
  Both formats passed bounded artifact inspection and installed, imported, and
  started the supported CLI in separate clean Python 3.11 environments. These
  are working-tree rehearsal artifacts; the gate must be repeated from the
  exact clean release commit.

## Archive policy

When this file becomes difficult to scan, move completed entries into
`docs/development/archive/YYYY-QN.md` and leave links plus the current quarter
here. Do not copy raw conversations or command/tool output into this log.
