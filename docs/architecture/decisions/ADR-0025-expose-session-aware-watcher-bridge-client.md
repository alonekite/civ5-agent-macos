# ADR-0025: Expose a session-aware watcher bridge client

Status: Accepted

Date: 2026-09-16

## Context

External callers need validated live reads and individual verified actions
without depending on M6 TurnPlan execution. The earlier `Bridge` abstract class
described asynchronous submit/result methods that no implemented path used and
omitted the bridge-session identity required for safe writes. Reusing
`WatcherTurnExecutor` would incorrectly make the bridge API depend on executor
semantics.

## Decision

`civ5_agent.bridge` exposes a runtime-checkable `Bridge` protocol and concrete
`WatcherBridgeClient`. The protocol provides:

- `read_state() -> (bridge_session_id, validated GameState)`;
- `execute_command(Command, bridge_session_id) -> terminal CommandResult`;
- `lookup_command_result(Command, bridge_session_id) -> CommandResult | None`.

Command UUID, allowlist, and exact argument validation are bridge-owned in
`validate_command`. Invalid commands fail before watcher contact. The concrete
client uses only the private watcher socket, validates the echoed session and
command identities, and accepts only terminal results with validated
before/after states. It never connects to FireTuner directly.

`WatcherTurnExecutor` extends this client only to translate explicit
`PlannedAction` values and compose M6 execution/reconciliation. The public
bridge does not import or create TurnPlans.

## Consequences

- Callers can use safe reads and individual writes independently of M6.
- Session targeting is part of every public write and cached-result lookup.
- Action validation has one bridge-owned implementation shared by direct
  command models and TurnPlan admission.
- The old unused asynchronous `submit/get_result` abstraction is removed before
  any 1.0 compatibility promise.
- Domain/transport exception unification remains a separate M7 task.

## Alternatives considered

- Make `WatcherTurnExecutor` the bridge API: rejected because bridge must not
  depend on executor orchestration.
- Expose `FireTunerClient`: rejected because callers could violate single-owner,
  preflight, framing, and allowlist boundaries.
- Omit session identity from methods: rejected because reconnects would allow
  stale writes.
- Preserve the unused asynchronous ABC: rejected because it does not match the
  verified synchronous postcondition contract.

## Supersedes

This replaces the provisional abstract interface described in the bridge module
document. It preserves ADR-0002 single-connection ownership and ADR-0003
allowlist/write-after-read requirements.
