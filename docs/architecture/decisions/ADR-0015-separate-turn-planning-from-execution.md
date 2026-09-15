# ADR-0015: Separate turn planning from deterministic execution

Status: Accepted

Date: 2026-09-15

## Context

The MVP `controller` proved that validated live state could be inspected,
mandatory choices could be reported, and an explicitly invoked end-turn action
could pass through bridge verification. The M6 name “deterministic controller
expansion” nevertheless left two responsibilities ambiguous: deciding what the
game should do and reliably executing a decision already made.

Long-term strategy, short-term tactics, and vertical skills will eventually
choose research, production, movement, diplomacy, and other plan content. The
read/write core must remain usable without those future layers and must never
silently turn execution mechanics into game strategy.

## Decision

M6 is renamed **Deterministic Turn Executor**. It consumes an explicit,
versioned `TurnPlan` supplied by a human or an authorized upper layer. It:

- verifies plan identity, target game/turn/player, and state preconditions;
- executes only ordered, allowlisted bridge commands already named in the plan;
- re-reads and verifies every action before advancing the execution cursor;
- journals plan receipt, command lifecycles, pauses, divergence, and completion;
- pauses on stale state, missing decisions, new blockers, unsupported actions,
  verification failure, or ambiguous crash recovery;
- ends a turn only when `end_turn` is explicitly present as the final planned
  action and Civ V's live preconditions permit it.

M6 may inspect and report factual `TurnRequirement` values such as “research
choice required” or “unit needs orders.” It must not select the technology,
production item, destination, target, strategy, or tactic that satisfies a
requirement. It does not score candidates, revise a plan, or manufacture a
replacement action.

The existing Python package and CLI retain the name `controller` until M7. Its
current `decide()` behavior is treated as an MVP readiness/requirement proof,
not the target tactical policy for M6. New M6 work builds the explicit plan and
execution contracts rather than adding autonomous choices to `decide()`.

## Consequences

- M5 journal identity, integrity, and recovery semantics must exist before M6
  can implement durable execution progress.
- The bridge remains responsible for one-command preconditions and
  write-after-read verification; M6 orchestrates a sequence without bypassing
  the bridge.
- A deterministic tactical policy, if desired, belongs to the future tactical
  layer and produces a `TurnPlan` through the same boundary as any other
  planner.
- Missing decisions are surfaced to the plan producer instead of being filled
  by defaults.
- Replaying a journal never executes a plan. Recovery resumes only when prior
  verified outcomes and the current live state make the next step unambiguous.
- M7 will decide public names and migration from the provisional `controller`
  CLI and module.

## Alternatives considered

- Expand `decide()` into a full deterministic game policy: rejected because it
  would merge tactics with execution and duplicate future vertical skills.
- Let the executor choose harmless defaults for missing actions: rejected
  because “harmless” is a tactical judgment and can alter a match irreversibly.
- Let planners call bridge actions directly: rejected because ordered
  execution, state-drift detection, recovery, and journal evidence would become
  inconsistent across planners.

## Supersedes

This ADR supersedes the earlier M6 plan to expand controller policy. It does not
supersede the verified bridge, allowlist, idempotency, or write-after-read
decisions in ADR-0001 through ADR-0003.
