# Documentation Index

This page is the canonical map of project documentation. Raw chat transcripts,
temporary investigation output, generated game data, and machine-specific paths
do not belong in the repository.

## Start here

- [Project outline (Chinese)](PROJECT_OUTLINE.zh-CN.md): concise mental model of
  the system, modules, boundaries, and delivery order.
- [Project state](PROJECT_STATE.md): current status, active milestone, blockers,
  and next deliverables.
- [Roadmap](ROADMAP.md): capability-level backlog.
- [Milestones](planning/MILESTONES.md): completion criteria and dependencies.

## Architecture and decisions

- [Architecture](ARCHITECTURE.md): current runtime and dependency structure.
- [Architecture decisions](architecture/decisions/README.md): immutable records
  explaining consequential design choices.
- [Bridge module](modules/bridge.md)
- [Knowledge module](modules/knowledge.md)
- [Journal module](modules/journal.md)
- [Controller module](modules/controller.md)
- [CLI module](modules/cli.md)
- [Module documentation template](modules/TEMPLATE.md)

## Data and API contracts

- [Contract index](contracts/README.md)
- [Live-state contract](contracts/live-state.md)
- [Command contract](contracts/command.md)
- [Knowledge contract](KNOWLEDGE.md)
- [Ruleset resolver contract](contracts/resolver.md)
- [Remaining rules inventory](knowledge/REMAINING_RULES_INVENTORY.md): reviewed
  SQLite families, exclusions, and the completed M3 classification.
- [Journal contract](contracts/journal.md)

The Python implementation and tests remain authoritative for exact executable
behavior. Contract documents define intended compatibility and rejection rules.

## Verification and operations

- [Test strategy](testing/TEST_STRATEGY.md)
- [Verification matrix](testing/TEST_MATRIX.md)
- [Live verification status (Chinese)](testing/LIVE_VERIFICATION_STATUS.zh-CN.md):
  concise record of what has and has not been tested in the real game.
- [Bounded live-test checklist](LIVE_TEST_CHECKLIST.md)
- [Experiment log](EXPERIMENT_LOG.md)
- [Operations index](operations/README.md)
- [Security policy](../SECURITY.md)

An implementation is not described as live-verified unless the experiment log
contains target-machine evidence. Offline unit tests and inspection of bundled
game source must be labeled separately.

## History, research, and risk

- [Development log](development/DEVELOPMENT_LOG.md): concise chronological
  milestones with commit references.
- [Research notes](RESEARCH_NOTES.md): current technical conclusions and open
  questions.
- [Risk register](planning/RISK_REGISTER.md): active technical, security, and
  project-continuity risks.
- [Changelog](../CHANGELOG.md): user-visible release changes; added when the
  first versioned release is prepared.

## Documentation ownership rules

| Change | Documents that must be considered |
|---|---|
| Current status or next task changes | `PROJECT_STATE.md` |
| Milestone scope/status changes | `planning/MILESTONES.md`, `ROADMAP.md` |
| Module responsibility or dependency changes | module document, `ARCHITECTURE.md` |
| Consequential design decision | new ADR; do not rewrite an accepted decision |
| Schema or public behavior changes | corresponding contract and compatibility tests |
| Target-machine experiment | `EXPERIMENT_LOG.md`, `testing/LIVE_VERIFICATION_STATUS.zh-CN.md`, `testing/TEST_MATRIX.md` |
| Security boundary changes | `SECURITY.md`, risk register, relevant ADR/module |
| Meaningful completed development batch | `development/DEVELOPMENT_LOG.md` |

## Growth and archive policy

- Keep `PROJECT_STATE.md` readable in under five minutes and remove stale
  status rather than accumulating history.
- Keep task-level work in GitHub Issues; the roadmap contains outcomes, not a
  duplicate issue list.
- Give decisions IDs such as `ADR-0001`, milestones IDs such as `M3`, risks IDs
  such as `R-001`, and experiments a date plus descriptive title.
- Keep accepted ADRs immutable. A later decision supersedes an earlier ADR by
  linking it from a new record.
- Split experiment and development logs by year or quarter when either becomes
  difficult to scan. Preserve the existing path as an index.
- Avoid duplicating field-by-field schemas in overview documents. Link to the
  owning contract instead.
- Never commit locally generated ruleset bundles, save-game observations, raw
  Codex sessions, private audit logs, or credentials.
