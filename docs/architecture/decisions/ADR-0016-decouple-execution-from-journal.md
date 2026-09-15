# ADR-0016: Decouple execution state from the factual journal

Status: Accepted

Date: 2026-09-15

## Context

ADR-0015 correctly separated tactical plan production from deterministic turn
execution, but it made M6 durable execution progress depend on M5 journal
identity, integrity, and recovery semantics. That conflated two different kinds
of state.

M5 exists to preserve what happened in a match for later tactical and strategic
history selection, replay, comparison, debugging, and audit. M6 exists to apply
an explicit current-turn plan against authoritative live game state. A factual
history store must not become the executor's control plane.

## Decision

M5 and M6 are independent core modules:

- M5 consumes factual observations and events and stores append-only history.
- M6 consumes a `TurnPlan`, validated live state, and the verified bridge action
  contract. It does not import, query, or require M5.
- M6 owns its short-lived execution cursor, verified command identities, last
  observed state basis, and execution status.
- If cross-process execution recovery is later required, M6 will define a
  separate private checkpoint contract. It will not use the historical journal
  as authoritative execution state.
- M6 emits bounded factual execution events. Application orchestration may
  append them to M5 through an adapter; M6 remains functional when no journal
  is configured.
- A journal write failure is reported separately. It cannot turn a bridge-
  verified action into a failure that may be retried.
- Current live game state and bridge postconditions always outrank journal
  history. M6 never resumes or repeats an uncertain action merely because of a
  journal record.
- Recovery uses the explicit plan, action UUIDs, M6-owned execution state, and
  freshly read game state. Ambiguity produces `recovery_required` and requires
  external reconciliation.

M5 may store received plans and M6 events as historical facts. Those records are
intended for future tactical/strategic consumers and replay/comparison tools;
they do not direct current execution.

## Consequences

- M6 depends on M2 verified actions and live-state/command contracts, not M5.
- M5 and M6 may be implemented in either order or in parallel. Choosing M5 as
  the current project priority is scheduling, not architecture.
- Neutral execution-event schemas must not expose callbacks or create a reverse
  dependency from M5 to M6.
- Integration tests must prove that execution works without M5 and that journal
  failure never duplicates a game write.
- Historical replay remains read-only and cannot resume or execute a plan.

## Alternatives considered

- Use M5 as the durable execution ledger: rejected because history would become
  a control dependency and could conflict with authoritative live state.
- Make journal writes transactional with game writes: rejected because Civ V
  and local storage cannot form one atomic transaction, and retrying after a
  logging failure could duplicate an irreversible action.
- Record no execution events: rejected because verified plan/action lifecycles
  are valuable factual history for later replay and comparison.

## Supersedes

This ADR supersedes only ADR-0015's requirement that M5 exist before M6 durable
execution and its use of journal evidence as an execution-recovery dependency.
ADR-0015's explicit TurnPlan, no-tactical-choice, ordered execution, pause, and
write-after-read requirements remain accepted.
