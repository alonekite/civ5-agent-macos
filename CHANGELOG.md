# Changelog

All notable user-visible changes are recorded here. Development details belong in
`docs/development/DEVELOPMENT_LOG.md`.

## Unreleased

### Added

- Candidate SessionSpec v2 generation for the independently owned automation
  framework. It declares two ordered, separately authorized UI steps: the
  target-verified unique launcher `PLAY` AX button and a caller-calibrated
  window-relative continue click. The watcher remains server-enforced
  read-only and starts only after both checkpoints pass.
- Exact launcher-to-game identity handoff for the candidate v2 path. The
  `PLAY` step alone declares the verified same-process successor executable;
  invalid paths and handoff deadlines fail closed, while the released v1
  integration remains unchanged.
- Candidate-framework compatibility now permits bounded waiting for the same
  verified target to regain focus before delivery. Identity changes and every
  post-delivery failure remain terminal and non-retryable.
- Candidate-framework UI identity failures may expose only an allowlisted,
  value-free reason token in durable events. Unknown or mutated values become
  `unspecified`; exception text and target details remain excluded.

## 1.3.0 - 2026-09-21

### Added

- Schema 8 read-only ordinary-research runtime facts: effective
  candidate costs, exact times-100 progress/science, whole-point overflow,
  runtime turns-left, action-window phase, field provenance, and explicit
  runtime context. Complete ruleset fingerprint binding remains downstream;
  no write or TurnPlan contract changes.
- Renamed the unreleased schema 8 object and capability discovery constant to
  `research_runtime_facts` and `RESEARCH_RUNTIME_FACTS_CAPABILITY_VERSION`;
  no provisional-name compatibility alias is shipped.
- Added provisional `civ5-watch --read-only`, a server-enforced tuner mode that
  admits only ping and validated state reads and cannot capture a journal.

### Changed

- Corrected the unreleased exact research-progress binding and provenance from
  `CvPlayer` to the target-verified `CvTeamTechs` owner. The schema, field,
  units, and capability version are unchanged.
- FireTuner collection now accepts bounded multi-frame Lua output delivered
  after its command acknowledgement and drains it to the existing idle/total
  deadline. A still-desynchronized long-running watcher rotates the connection
  and bridge-session identity instead of reusing shifted segmented responses;
  submitted writes are never retried.
- The repaired schema 8 read path passed bounded target verification across two
  interturns with one bridge session, positive overflow, selection-time
  preservation, later application, a zero-record private audit, and exact host
  restoration.

## 1.2.0 - 2026-09-19

### Added

- Schema 7 worker current-plot/current-build facts and conservative ordinary
  build candidates, plus an exact `worker_build(unit_id, x, y, build_type)`
  bridge action with bounded stock dispatch, dual factual verification, and
  deterministic TurnPlan execution/recovery. The complete offline gate passes;
  bounded active-build target-machine verification passes.

## 1.1.0 - 2026-09-17

### Added

- Schema 6 `ordinary_move_targets` observations and a narrowly
  allowlisted adjacent `move_unit(unit_id, x, y)` bridge command with repeated
  game-side guards, exact read-after-write verification, and deterministic
  TurnPlan execution/recovery. The full offline gate and bounded target-machine
  verification pass.

## 1.0.0 - 2026-09-16

### Added

- Verified macOS Civ V read/write bridge with guarded FireTuner transport.
- Live state watcher and private local command broker.
- Verified end-turn, research-selection, and city-production actions.
- Deterministic controller proof.
- Versioned ruleset knowledge core and reviewed BNW knowledge importer.
- Civilization, leader, deterministic trait, and unique/disabled class
  knowledge coverage without AI personality data.
- Religion, core belief, specialist, and great-person class knowledge coverage.
- Core terrain, feature, improvement, route, yield, and build-action knowledge.
- Knowledge schema 2 reference attributes with schema 1 compatibility.
- Knowledge schema 3 typed reference context with schema 1/2 compatibility.
- Binary map/build quantity relations and explicit fake-feature knowledge.
- Single-context belief, building, improvement, and policy yield relations.
- Binary belief, building, policy, resource, specialist, map, build, and
  resource-requirement relations with validated quantities.
- Project, process, and victory entities with prerequisites, thresholds,
  production conversion, and resource requirements.
- Unit-combat categories with unit/promotion applicability, quantified category
  modifiers, and contextual free-promotion grants.
- Typed unit-domain and special-unit classifications.
- Typed unit technology, capture-class, ancient-ruin, policy, cargo, project,
  and promotion relationships.
- Multi-attribute promotion modifiers for domains, features, terrains, and unit
  classes, including typed technology-conditioned passability.
- Typed faith-purchase, prerequisite, resource-placement, promotion,
  training-restriction, and unit build-capability relationships.
- Expanded quantified building-class, domain, free-unit, trade-route, trait,
  and combat-yield rules, including typed trait contexts.
- Multi-attribute improvement/resource rules and fail-closed technology-
  enhanced building yields.
- Hurry-method entities, conversion rates, policy gates, and building/policy
  cost modifiers.
- Great-work class and slot entities with typed class/building slot relations,
  excluding individual work content and presentation assets.
- Great-work and artifact-class stable IDs, archaeology flags, and typed class,
  era, creator-unit, and free-building relationships without titles or assets.
- Canonically ordered building theming rules with deterministic gameplay
  constraints, excluding localized descriptions and AI priorities.
- Structured documentation governance, architecture decisions, module
  boundaries, contracts, milestones, risks, and verification matrix.
- Stable aggregate Python API with explicit validation, protocol, transport,
  and live-safety error categories plus published schema and size limits.
- Stable `civ5-turn` JSON envelopes and exit meanings; all other
  command-line entry points are explicitly provisional.
- Bounded wheel/source inspection for package coverage, metadata, entry points,
  RECORD integrity, normalized reproducibility, unsafe members, and common
  private material.
- Operator runbook for immutable version tags, inspected release artifacts,
  clean-environment upgrades, withdrawal, and rollback.
- Target-machine-verified M5 journal success lifecycle and deterministic M6
  one-action completion with automatic turn advancement.
- Stable downstream tactical integration profile and strategy-neutral core
  capability request process for future cross-project maintenance.

### Security

- Fail-closed FireTuner preflight and shutdown checks.
- Explicit action allowlist and write-after-read verification.
- Private local IPC and audit permissions, bounded messages, UUID validation,
  and duplicate-command suppression.
- FireTuner Lua programs are bounded before send; post-submission uncertainty
  is journaled, mapped to conservative recovery, and duplicate-suppressed.

### Fixed

- Compacted `end_turn` below the target FireTuner command limit after a bounded
  live test exposed truncation of the prior exhaustive expression.
- Preserve failed post-submission command lifecycles as verification errors
  instead of dropping them before journal capture.
- Use Civ V's named no-end-turn-blocker enum instead of an incorrect numeric
  zero assumption, and inspect the blocker independently of UI clickability.

### Compatibility

- `civ5_agent.api` and the documented `civ5-turn` envelopes and exit meanings
  are the stable 1.0 compatibility surfaces. Incompatible changes require a new
  major version.
- Live-state schemas 2–5, knowledge schemas 1–3, and journal, TurnPlan, and
  execution-report schema 1 retain their documented compatibility rules.
- Other command-line entry points remain provisional; their safety, privacy,
  and write-verification guarantees are stable even when their presentation
  changes.

### Known limitations

- Live operation is verified only for the original Civilization V: Campaign
  Edition target on Apple Silicon macOS and requires the guarded FireTuner
  procedure.
- Free/steal technology modes, non-empty diplomacy, and non-zero late-game
  science-victory branches have only partial or offline evidence.
- Coordinate movement, LLM decision-making, working memory, strategic memory,
  and MCP integration are outside this release.
- Core 1.0.0 has no serialized capability manifest or selective tactical-history
  query; consumers use the published static profile and fail closed on gaps.
