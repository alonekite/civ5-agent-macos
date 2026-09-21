# Architecture Decision Records

ADRs preserve why consequential decisions were made. Accepted ADRs are not
rewritten to match later preferences; a new ADR may supersede an old one.

## Index

| ID | Decision | Status |
|---|---|---|
| [ADR-0001](ADR-0001-use-stock-firetuner-transport.md) | Use stock FireTuner as the verified transport | Accepted |
| [ADR-0002](ADR-0002-single-connection-owner.md) | Give the watcher sole ownership of the game connection | Accepted |
| [ADR-0003](ADR-0003-allowlist-and-readback.md) | Require allowlisted actions and write-after-read verification | Accepted |
| [ADR-0004](ADR-0004-local-ruleset-provenance.md) | Generate ruleset knowledge from local sources with provenance | Accepted |
| [ADR-0005](ADR-0005-exclude-ai-personality-data.md) | Exclude AI flavor and personality data | Accepted |
| [ADR-0006](ADR-0006-separate-journal-from-llm-memory.md) | Separate the factual journal from future LLM-facing memory | Accepted |
| [ADR-0007](ADR-0007-reference-attributes.md) | Add attributes to knowledge references | Accepted |
| [ADR-0008](ADR-0008-contextual-reference-identity.md) | Add typed context to knowledge references | Accepted |
| [ADR-0009](ADR-0009-recoverable-live-session.md) | Manage live tests as recoverable bounded sessions | Accepted |
| [ADR-0010](ADR-0010-segment-live-snapshots.md) | Segment live snapshots below the FireTuner command limit | Accepted |
| [ADR-0011](ADR-0011-embed-non-addressable-rules.md) | Embed non-addressable rules under stable parent entities | Accepted |
| [ADR-0012](ADR-0012-allowlisted-global-define-entities.md) | Model allowlisted global defines as entities | Accepted |
| [ADR-0013](ADR-0013-explicit-ruleset-resolution-context.md) | Require explicit ruleset resolution context | Accepted |
| [ADR-0014](ADR-0014-separate-ruleset-view-from-decision-support.md) | Separate structural ruleset views from future decision support | Accepted; executor-query allowance superseded by ADR-0018 |
| [ADR-0015](ADR-0015-separate-turn-planning-from-execution.md) | Separate turn planning from deterministic execution | Accepted; journal dependency superseded by ADR-0016 and identity wording by ADR-0017 |
| [ADR-0016](ADR-0016-decouple-execution-from-journal.md) | Decouple execution state from the factual journal | Accepted |
| [ADR-0017](ADR-0017-separate-session-and-match-identity.md) | Separate bridge-session identity from match identity | Accepted |
| [ADR-0018](ADR-0018-keep-executor-independent-of-knowledge.md) | Keep deterministic execution independent of ruleset knowledge | Accepted |
| [ADR-0019](ADR-0019-separate-command-audit-from-match-journal.md) | Separate the command audit from the match journal | Accepted |
| [ADR-0020](ADR-0020-use-private-hash-chained-jsonl-journal.md) | Use a private hash-chained JSONL journal | Accepted |
| [ADR-0021](ADR-0021-export-redacted-journal-structure.md) | Export only redacted journal structure by default | Accepted |
| [ADR-0022](ADR-0022-bind-turn-plans-to-live-state-basis.md) | Bind complete-turn plans to one live-state basis | Accepted |
| [ADR-0023](ADR-0023-reconcile-unknown-actions-with-watcher-cache.md) | Reconcile unknown actions without automatic retry | Accepted |
| [ADR-0024](ADR-0024-use-bounded-watcher-only-turnplan-cli.md) | Use a bounded watcher-only TurnPlan CLI | Accepted |
| [ADR-0025](ADR-0025-expose-session-aware-watcher-bridge-client.md) | Expose a session-aware watcher bridge client | Accepted |
| [ADR-0026](ADR-0026-aggregate-pre1-public-api-and-errors.md) | Aggregate the pre-1.0 public API and error taxonomy | Accepted |
| [ADR-0027](ADR-0027-stabilize-turn-cli-only.md) | Stabilize only the bounded TurnPlan CLI before 1.0 | Accepted |
| [ADR-0028](ADR-0028-bound-firetuner-programs-and-preserve-unknown-outcomes.md) | Bound FireTuner Lua and preserve unknown write outcomes | Accepted |
| [ADR-0029](ADR-0029-use-game-defined-no-end-turn-blocker.md) | Use the game-defined no-end-turn blocker | Accepted |
| [ADR-0030](ADR-0030-promote-supported-surfaces-to-stable-1.0.md) | Promote the supported surfaces to stable 1.0 | Accepted; advances ADR-0026/0027 compatibility policy |
| [ADR-0031](ADR-0031-bound-downstream-tactical-integration.md) | Bound downstream tactical integration and core evolution | Accepted |
| [ADR-0032](ADR-0032-use-selected-unit-network-path-for-adjacent-movement.md) | Use the selected-unit network path for adjacent movement | Accepted |
| [ADR-0033](ADR-0033-use-unit-legality-and-selected-action-for-ordinary-worker-builds.md) | Use unit legality and the selected-unit stock action for ordinary worker builds | Accepted |
| [ADR-0034](ADR-0034-use-integer-flags-for-campaign-edition-canbuild.md) | Use integer option flags for Campaign Edition `CanBuild` | Accepted; supersedes ADR-0033's flag representation only |
| [ADR-0035](ADR-0035-publish-runtime-research-forecast-facts.md) | Publish runtime research forecast facts without claiming a ruleset fingerprint | Accepted; public naming superseded by ADR-0036 |
| [ADR-0036](ADR-0036-name-ordinary-research-runtime-facts.md) | Name the schema 8 observation ordinary research runtime facts | Accepted |
| [ADR-0037](ADR-0037-read-exact-research-progress-from-team-techs.md) | Read exact research progress from team technologies | Accepted; supersedes ADR-0035's progress binding only |
| [ADR-0039](ADR-0039-expose-server-enforced-read-only-watcher.md) | Expose a server-enforced read-only watcher mode | Accepted |
| [ADR-0040](ADR-0040-compose-external-supervision-through-json-and-cli.md) | Compose external supervision through JSON and CLI boundaries | Accepted |
| [ADR-0041](ADR-0041-adopt-local-app-test-automation-v0.1.0.md) | Adopt local-app-test-automation v0.1.0 | Accepted |
| [ADR-0042](ADR-0042-recover-from-firetuner-response-desynchronization.md) | Recover from FireTuner response desynchronization | Accepted |
| [ADR-0043](ADR-0043-drain-multiframe-output-after-early-firetuner-ack.md) | Drain multi-frame output after an early FireTuner acknowledgement | Accepted; refines ADR-0042 collection only |
| [ADR-0044](ADR-0044-generate-candidate-session-spec-v2-ui-gates.md) | Generate candidate SessionSpec v2 UI gates at the core boundary | Accepted |
| [ADR-0045](ADR-0045-declare-launcher-game-identity-handoff.md) | Declare the launcher-to-game identity handoff | Accepted |

## Template

```markdown
# ADR-NNNN: Decision title

Status: Proposed | Accepted | Deprecated | Superseded
Date: YYYY-MM-DD

## Context
## Decision
## Consequences
## Alternatives considered
## Supersedes
```
