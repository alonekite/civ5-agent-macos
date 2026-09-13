# ADR-0003: Require allowlisted actions and write-after-read verification

Status: Accepted

Date: 2026-09-12

## Context

A successful Lua call does not prove that Civ V accepted the intended action.
UI state, turn ownership, missing choices, invalid identifiers, and message
processing can block or redirect an operation. An arbitrary Lua endpoint would
also make every caller equivalent to remote code execution inside the game.

## Decision

Expose only named actions with strict argument schemas. For every action:

1. read and validate the before-state;
2. check action-specific Civ V capability predicates;
3. execute only internally generated Lua corresponding to the allowlist;
4. re-read the exact target state;
5. return success only when the documented postcondition is proved.

Ambiguity, timeout, malformed state, or missing evidence is an error.

## Consequences

- Controllers and future external systems cannot execute arbitrary Lua.
- New actions require explicit preconditions, postconditions, fixtures, offline
  tests, and usually a bounded live experiment.
- Retrying commands requires stable UUIDs and duplicate suppression.
- Some seemingly successful UI calls will correctly be reported as failures.

## Alternatives considered

- Trust the Lua call return/completion frame: rejected because it proves command
  completion, not game-state mutation.
- General-purpose Lua passthrough: rejected as incompatible with the security
  objective.

## Supersedes

None.
