# Codex Instructions

Target: Civilization V on Apple Silicon macOS.

## Primary objective
Prove a reliable bidirectional bridge:
`Civ V Lua mod ↔ external Python`

Build the project as a reusable Civilization V read/write core. The core consists
of a game bridge, verified actions, ruleset knowledge, a factual turn journal,
and a deterministic turn executor. LLM integration and MCP integration are out
of scope for this project.

## Hard constraints
- Do not assume Windows DLL compatibility.
- Do not assume Civ V Lua has unrestricted io/os/socket/HTTP/filesystem access.
- Treat every IPC mechanism as unverified until tested on the target machine.
- Prefer Civ V-supported Lua APIs.
- Whitelist actions.
- Verify every write action by re-reading state.
- Keep experiments reproducible and logged.
- Do not collect, model, or ship leader/AI flavor or personality parameters.
- Do not require an LLM to read knowledge, choose a legal action, execute an
  action, or verify its result.
- Do not implement working memory or strategic memory in this repository. Design
  them together with the future LLM interaction layer because their selection,
  summarization, and revision semantics are closely coupled to that layer.

## Module boundaries
- `bridge`: transport, live state models, state reads, whitelisted actions, and
  write-after-read verification.
- `knowledge`: versioned ruleset facts that do not belong to a particular saved
  game.
- `journal`: append-only, integrity-checked per-game facts, including full turn
  snapshots and verified action lifecycles. It is an audit/replay source and is
  intended for future tactical/strategic history, replay, comparison, and audit.
  It is not an executor control plane.
- `controller`: provisional package name for current-turn requirement inspection
  and deterministic execution of an explicit turn plan. It may orchestrate only
  whitelisted bridge actions; it does not choose strategy, tactics, research,
  production, movement, or other plan content.
- `cli`: thin commands over the modules above.

Dependencies flow inward: `controller -> bridge` with only narrowly required
structural knowledge queries. Application
orchestration may append bridge observations and verified action results to the
journal. Knowledge must not depend on a live game, journal must not choose
actions, M6 must not require or query journal state, and bridge must not depend
on executor orchestration.

## Ruleset knowledge scope
The knowledge module may cover technologies; policies and ideologies; units and
promotions; great people; religions and beliefs; civilizations, leaders, traits,
and unique replacements; buildings, wonders, national wonders, projects, and
processes; terrain, features, resources, improvements, routes, and yields;
specialists; eras; city, combat, diplomacy, city-state, espionage, trade-route,
archaeology, tourism, World Congress, barbarian, ancient-ruin, and victory rules;
and game-speed, difficulty, map-size, and other ruleset scaling.

Store stable game identifiers, numeric facts, prerequisites, replacements,
unlocks, upgrade paths, constraints, and provenance. Do not store AI flavor or
personality parameters. Avoid redistributing Civilopedia prose, quotes, art,
audio, or other copyrighted game assets.

Treat knowledge as ruleset-specific rather than universally fixed. Every
generated dataset must identify the game family (vanilla, Gods & Kings, or Brave
New World), DLC/mod set, source version, source paths, and reproducible source
hashes. Keep base facts separate from per-game modifiers such as speed,
difficulty, selected civilization, policies, and beliefs.

## Knowledge sources and reuse
Before implementing an extractor or dataset, search existing public repositories
for relevant code and schemas. Do not fork or copy until license compatibility,
data provenance, supported Civ V ruleset, completeness, and maintenance quality
have been recorded. Prefer parsing the user's locally installed Civ V XML and
SQLite data over copying third-party data. Third-party repositories are
references unless their licenses clearly permit reuse.

Any importer must be deterministic, preserve stable identifiers and relations,
validate referential integrity, report unsupported tables/fields, and generate
repeatable output. Hand-authored or model-generated facts are not authoritative.

## Optional local-model assistance
A locally hosted Qwen 8B-class model may assist with bounded development work,
such as proposing extractor code, classifying fields, drafting mappings, or
summarizing schema documentation without consuming Codex quota. It is a build
assistant, not a runtime dependency or source of truth.

Before using it, verify the exact local model, runtime, context limits, and data
handling. Give it only repository and locally installed game data that the user
has authorized. Capture prompts and outputs when they affect generated code or
data. Validate every result with deterministic parsers, schemas, referential
integrity checks, fixtures, and tests before accepting it. The knowledge module
and turn executor must continue to work when the local model is unavailable.

## Engineering order
1. inspect environment
2. prove read
3. prove write
4. add verification
5. add the versioned ruleset knowledge module
6. add the factual turn journal
7. deterministic turn executor
8. stabilize the public read/write API

Steps 6 and 7 are the current delivery order, not a runtime dependency. The
executor must operate without the journal; application orchestration may record
its factual events when a journal is configured.

Do not develop LLM decision-making, working memory, strategic memory, or MCP
integration in this repository.

## Documentation governance

- Use `docs/INDEX.md` as the canonical documentation map.
- Keep `docs/PROJECT_STATE.md` as a short current-state dashboard, not a
  chronological log.
- Record milestone outcomes in `docs/planning/MILESTONES.md` and task-level work
  in GitHub Issues.
- Add an ADR for consequential changes to module boundaries, transport, safety,
  provenance, persistence, or public compatibility. Accepted ADRs are not
  rewritten; supersede them with a new ADR.
- Update the owning module document and contract whenever a responsibility,
  schema, invariant, or public behavior changes.
- Record target-machine evidence only in `docs/EXPERIMENT_LOG.md` and update the
  verification matrix. Do not label offline evidence as live verification.
- Add meaningful completed batches to `docs/development/DEVELOPMENT_LOG.md` with
  commit references; do not paste raw conversations or tool output.
- Never commit generated game datasets, real match snapshots, private logs,
  local recovery files, credentials, or user-identifying absolute paths.

## Definition of done for MVP
`python -m civ5_agent.watch` shows live game-state changes, and
`python -m civ5_agent.command end_turn` advances one turn and returns verified success.
