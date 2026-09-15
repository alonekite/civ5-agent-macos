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
| [ADR-0014](ADR-0014-separate-ruleset-view-from-decision-support.md) | Separate structural ruleset views from future decision support | Accepted |
| [ADR-0015](ADR-0015-separate-turn-planning-from-execution.md) | Separate turn planning from deterministic execution | Accepted |

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
