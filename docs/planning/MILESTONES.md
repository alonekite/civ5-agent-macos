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
| M5 | Factual turn journal | In progress | M1, M4 |
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

Completed extension: `skip_unit` is live-verified using unit readiness with
unchanged identity, location, and remaining movement.

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
The remaining-rule inventory found no controller-facing effect requiring more
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

- Append validated snapshots, turn transitions, command envelopes, command
  results, before/after states, and verification errors for exactly one game.
- Use versioned canonical records, private permissions, bounded record sizes,
  monotonically increasing sequence numbers, and integrity checks.
- Detect truncation, tampering, broken ordering, and cross-game mixing.
- Provide deterministic replay/export without summarizing or inferring facts.
- Do not implement working memory or strategic memory.

## M6 — Deterministic controller expansion

Acceptance criteria:

- Consume only validated live state and public knowledge-view APIs.
- Emit only explicit allowlisted candidate actions.
- Keep execution opt-in and route every action through bridge verification.
- Cover conservative mandatory-choice and turn-completion policies with tests.
- Never require an LLM.

The existing basic controller satisfies the initial proof; this milestone
remains in progress until concrete conservative policies require and use the
completed structural knowledge interfaces.

## M7 — Public API stabilization

Acceptance criteria:

- Define supported read, action, knowledge-view, and journal APIs.
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
