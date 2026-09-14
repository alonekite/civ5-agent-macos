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
