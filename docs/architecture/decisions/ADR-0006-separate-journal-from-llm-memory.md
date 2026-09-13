# ADR-0006: Separate the factual journal from future LLM-facing memory

Status: Accepted

Date: 2026-09-13

## Context

The core needs a complete record of per-turn observations and verified actions
for audit and replay. Working memory and strategic memory have different
semantics: they select, summarize, infer, expire, and revise information in
close interaction with an LLM context and planning loop.

## Decision

Add only a factual `journal` module to this repository. It will append full
validated snapshots and verified action lifecycles without summarization,
inference, or action choice.

Design `working_memory` and `strategic_memory` later with a separate LLM
interaction layer. They are not modules or roadmap tasks in this repository.
The future layer may read public state, knowledge, and journal APIs and submit
candidate intentions, but verified actions remain controlled by the core.

## Consequences

- The core remains deterministic and usable without an LLM.
- Journal records provide evidence from which future memory can derive facts.
- Memory schemas are not prematurely fixed before context selection, prompt
  representation, inference, expiry, and plan-revision behavior are designed.
- The public API must eventually support safe, selective journal access.

## Alternatives considered

- Implement working and strategic memory as deterministic controller modules:
  rejected because their principal behavior is coupled to future LLM
  interaction.
- Put complete turn history directly into LLM context: rejected for relevance,
  size, cost, and fact/inference-boundary reasons.

## Supersedes

The memory ordering described in commit `144291b`; the corrected boundary was
recorded in commit `14daa1d`.
