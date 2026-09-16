# Changelog

All notable user-visible changes will be recorded here once the project begins
versioned releases. Development details belong in
`docs/development/DEVELOPMENT_LOG.md`.

## Unreleased

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
- Aggregate pre-1.0 Python API with explicit validation, protocol, transport,
  and live-safety error categories plus published schema and size limits.
- Supported pre-1.0 `civ5-turn` JSON envelopes and exit meanings; all other
  command-line entry points are explicitly provisional.
- Bounded wheel/source inspection for package coverage, metadata, entry points,
  RECORD integrity, normalized reproducibility, unsafe members, and common
  private material.

### Security

- Fail-closed FireTuner preflight and shutdown checks.
- Explicit action allowlist and write-after-read verification.
- Private local IPC and audit permissions, bounded messages, UUID validation,
  and duplicate-command suppression.

No release has been tagged yet.
