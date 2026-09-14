# Milestones

Milestones describe outcomes and acceptance criteria. Task-level work belongs in
GitHub Issues and should link back to one milestone ID.

| ID | Milestone | Status | Depends on |
|---|---|---|---|
| M0 | Environment reconnaissance | Complete | — |
| M1 | Bidirectional bridge MVP | Complete | M0 |
| M2 | Verified action layer | Complete | M1 |
| M3 | Ruleset knowledge coverage | In progress | M1 |
| M4 | Ruleset resolver | Planned | M3 |
| M5 | Factual turn journal | Planned | M1 |
| M6 | Deterministic controller expansion | In progress | M2, M3, M4 |
| M7 | Public API stabilization | Planned | M4, M5, M6 |
| M8 | 1.0 release readiness | Planned | M7 |

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

Remaining extension: `skip_unit` is implemented and offline-tested but awaits a
bounded live check; it does not block the completed core milestone.

## M3 — Ruleset knowledge coverage

Acceptance criteria:

- Import the stable identifiers, numeric facts, prerequisites, replacements,
  unlocks, upgrade paths, constraints, and provenance needed by controller
  policies.
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
requirements across 82 single-value table families plus project victory
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
yield quantities are imported, including three typed trait contexts. Current
Improvement/resource multi-attribute rules and building yields derived from a
validated enhanced-yield technology are also complete.
Current next deliverable: effects requiring multiple context items or new target
entity families, followed by scaling rules.

## M4 — Ruleset resolver

Acceptance criteria:

- Preserve immutable base ruleset facts.
- Resolve effective facts for a declared DLC/Mod set and per-game modifiers.
- Support game speed, difficulty, map size, civilization replacements, adopted
  policies, and beliefs where source rules require them.
- Return provenance for both base facts and applied modifiers.
- Reject incomplete or incompatible context instead of guessing.

## M5 — Factual turn journal

Acceptance criteria:

- Append validated snapshots, turn transitions, command envelopes, command
  results, before/after states, and verification errors for exactly one game.
- Use versioned canonical records, private permissions, bounded record sizes,
  monotonically increasing sequence numbers, and integrity checks.
- Detect truncation, tampering, broken ordering, and cross-game mixing.
- Provide deterministic replay/export without summarizing or inferring facts.
- Do not implement working memory or strategic memory.

## M6 — Deterministic controller expansion

Acceptance criteria:

- Consume only validated live state and public knowledge/resolver APIs.
- Emit only explicit allowlisted candidate actions.
- Keep execution opt-in and route every action through bridge verification.
- Cover conservative mandatory-choice and turn-completion policies with tests.
- Never require an LLM.

The existing basic controller satisfies the initial proof; this milestone remains
in progress until it uses the completed knowledge/resolver interfaces.

## M7 — Public API stabilization

Acceptance criteria:

- Define supported read, action, knowledge-query, resolver, and journal APIs.
- Publish schema versions, compatibility guarantees, error semantics, and size
  limits.
- Add contract tests for supported Python versions.
- Separate public interfaces from FireTuner and local-database implementation
  details.

## M8 — 1.0 release readiness

Acceptance criteria:

- Complete the required bounded live verification matrix.
- Close or explicitly accept all high-impact risks.
- Provide setup, security, recovery, upgrade, and release documentation.
- Run tests and sensitive-information scans on the release artifact.
- Tag a reproducible version without generated game data or private logs.

LLM interaction, working memory, strategic memory, and MCP are not M-series
milestones. They require a separate future project plan.
