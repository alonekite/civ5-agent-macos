# Core Capability Request Process

Status: Accepted maintenance procedure

## Purpose

Provide a repeatable intake path when a downstream tactical or strategic
consumer needs a live fact, knowledge relation, allowlisted action, or public
history view that core 1.0.0 does not expose.

## Required request content

Every request must identify:

1. the requesting repository, contract, and domain;
2. the reusable observed fact or game mechanic required;
3. why the current stable public API is insufficient;
4. the proposed stable identifiers and bounded argument/result shape;
5. required live preconditions and exact postconditions;
6. refusal, failure, timeout, and unknown-outcome behavior;
7. identity, freshness, privacy, and hidden-information constraints;
8. schema, API, CLI, and semantic-version impact;
9. deterministic offline fixtures and negative tests;
10. target-machine verification needed before the capability is advertised;
11. consumer behavior when the capability is absent or incompatible.

Requests describe facts and mechanics, not desired tactical conclusions. For
example, request the live set of legal research identifiers rather than the
technology that a cultural strategy should choose.

## Review sequence

1. Confirm the request belongs in the reusable execution core rather than the
   tactical or strategic policy layer.
2. Confirm the fact is legitimately observable by the active player and does
   not introduce AI flavor, personality, hidden state, copyrighted presentation
   content, or arbitrary Lua.
3. Assign the owning core module and contracts; add an ADR when authority,
   persistence, safety, or public compatibility changes.
4. Design fail-closed validation, bounds, stable identifiers, and explicit
   postconditions before implementing a write.
5. Implement offline fixtures and tests without depending on downstream code.
6. Perform bounded target-machine verification for new live reads or writes.
7. Update public exports, capability profile, test matrix, changelog, and
   semantic version in one release batch.
8. Let the downstream project select the published core version and update its
   own adapter fixtures. Publication does not automatically enable a domain.

## Rejection conditions

Reject or return for revision a request that:

- embeds victory strategy, ranking weights, tactical scoring, or proposal
  arbitration in the core;
- asks the core to infer opponent intent or unavailable information;
- duplicates transport, command execution, or verification downstream;
- has no exact legality, precondition, postcondition, or failure semantics;
- requires an LLM for legality, execution, or verification;
- bypasses the allowlist or asks for arbitrary code execution;
- lacks a safe absent-capability behavior.

## Maintenance record

Task-level requests belong in GitHub Issues and link to the owning contract and
milestone. Accepted architecture changes receive an ADR. Target evidence is
recorded only in the experiment log and verification matrix. Completed batches
are summarized in the development log; private consumer fixtures, real match
state, and raw logs are never copied into this repository.
