# ADR-0027: Stabilize only the bounded TurnPlan CLI before 1.0

Status: Accepted

Date: 2026-09-16

## Context

The repository has eight command-line entry points with different audiences.
Freezing all historical operational commands would preserve inconsistent
envelopes and couple public compatibility to setup, diagnostics, extraction,
and a legacy controller proof. M7 still needs an unambiguous supported CLI for
deterministic plan validation and execution.

## Decision

`civ5-turn` is the sole supported machine-readable pre-1.0 CLI. Its two
subcommands, exact stdout envelope shapes, and exit meanings are documented and
contract-tested. Versioned TurnPlan and ExecutionReport schemas remain the
authoritative nested data contracts. Human-readable error wording is not
stable.

All other console scripts are explicitly provisional before 1.0. They retain
their documented safety and privacy invariants but may evolve without CLI
compatibility guarantees. Standard `argparse` invocation failures remain exit
2 with stderr diagnostics and are outside the JSON envelope contract.

## Consequences

- Automation has one small deterministic CLI instead of depending on legacy or
  operator-oriented output.
- A valid non-completed execution report remains distinguishable from input or
  transport failure.
- Other entry points can be redesigned deliberately before 1.0 without
  pretending their current output is stable.

## Alternatives considered

- Freeze every current CLI: rejected because their purposes and envelopes are
  inconsistent and several are operational or build tools.
- Keep every CLI provisional: rejected because M6 needs one supported
  cross-process plan boundary.
- Stabilize only Python imports: rejected because shell automation is a valid
  consumer of the bounded executor.

## Supersedes

This finalizes the CLI-stability question left open by ADR-0024 and ADR-0026.
It does not change the TurnPlan execution or safety model.
