# ADR-0024: Use a bounded watcher-only TurnPlan CLI

Status: Accepted

Date: 2026-09-16

## Context

M6 needs an operator and script entry point without turning CLI parsing into a
planner, weakening TurnPlan validation, or opening a second FireTuner client.
TurnPlan files contain live bridge-session data and can authorize several game
writes, so unbounded or permissive loading would enlarge the safety boundary.

## Decision

Expose `civ5-turn` with two explicit operations:

- `validate PLAN` strictly decodes a bounded TurnPlan file, reads current state
  through the existing private watcher socket, and checks plan admission without
  executing an action;
- `execute PLAN` performs the same strict decode and delegates the complete plan
  to `WatcherTurnExecutor`.

The input must be one JSON object no larger than 64 KiB with exactly the schema
1 TurnPlan and PlannedAction fields. Unknown fields, non-finite numbers,
malformed identifiers, invalid action arguments, and incomplete plans fail
before watcher contact. The CLI does not accept executable predicates, generate
actions, read M4 or M5, or offer direct FireTuner fallback.

Output is one bounded JSON object. Exit status 0 means validation succeeded or
execution completed; 1 means input, watcher, or transport failure; 2 means the
executor returned a valid non-completed report such as paused, stale, failed, or
recovery-required.

## Consequences

- Invoking `execute` is an explicit request to perform every plan-listed write,
  still subject to fresh-state admission and bridge verification.
- The single watcher remains the only FireTuner connection owner.
- File syntax cannot add policy or expand the bridge action allowlist.
- CLI naming and compatibility remain provisional until M7.
- Recovery reports are machine-readable, but cross-process recovery input is
  not added until a separate bounded persistence contract exists.

## Alternatives considered

- Execute a plan through a new direct FireTuner connection: rejected because
  this build reliably services only one client and ADR-0002 gives ownership to
  the watcher.
- Accept stdin or arbitrary callbacks: rejected to keep authority explicit and
  input bounded to a local file with a fixed schema.
- Generate missing actions in the CLI: rejected because plan production is not
  an M6 or CLI responsibility.
- Treat every non-completed report as malformed input: rejected because paused,
  stale, failed, and recovery-required are valid executor outcomes.

## Supersedes

This finalizes the provisional M6 CLI surface described by ADR-0015 and the
TurnPlan contract without changing their planner/executor separation.
