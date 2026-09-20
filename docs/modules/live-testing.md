# Module: Live testing

Status: Implemented as a provisional application/operations surface

## Responsibility

`civ5_agent.live_testing` supervises bounded, operator-present target-machine
tests. It composes guarded host preparation/restoration, normal Civ V launch and
quit, a server-enforced read-only watcher, private control IPC, and pluggable
checkpoint profiles.

The first profile, `m11-research-runtime-c4`, automates data checks for the M11
C4 procedure and records explicit Codex or user confirmation for UI-only facts.
It does not claim target evidence merely because an offline check passes.

## Commands

- `civ5-live-test start [--profile m11-research-runtime-c4]` runs the single
  foreground supervisor.
- `status` returns a redacted lifecycle/checkpoint summary.
- `checkpoint NAME` performs one fresh, profile-defined data check.
- `confirm NAME --result pass|fail --source codex|user [--note TEXT]` records a
  bounded visual/operator decision.
- `finish` requests orderly shutdown and exact host-baseline restoration.
- `recover` reacquires an interrupted session and either resumes supervision or
  restores an already-closed session.

`start` and a resuming `recover` remain in the foreground. Civ V menu navigation,
save loading, research selection, and turn advancement remain manual.

## M11 checkpoints

The profile exposes `live_state`, `repeated_read`, `ui_agreement`,
`overflow_precondition`, `overflow_completion`, `selection_stability`,
`overflow_application`, and `audit_clean`.

Data checkpoints retain only schema/turn, technology identifiers needed to
correlate the bounded sequence, numeric research values, candidate count,
runtime-context availability labels, and calculated overflow values. They never
persist the complete bridge response. `ui_agreement` requires a `codex` or
`user` confirmation. A failed invariant pauses the session as a data
inconsistency and keeps the game open.

## Dependencies and exclusions

The layer may depend on `live_session`, `preflight`, `ipc`, `watcher_client`, and
validated live-state models. It must not depend on controller, TurnPlan,
command-write orchestration, knowledge, or journal. It never opens FireTuner
directly; the watcher remains the sole game-connection owner.

## Safety, privacy, and recovery

One advisory lock prevents concurrent sessions. Runtime files are private and
live outside the repository. The durable recovery record is atomically replaced
and contains no full snapshot, bridge-session ID, save filename, player name,
unit/city identity, credentials, or arbitrary UI text.

Safety failure triggers a normal application quit request, bounded waiting,
watcher shutdown, and baseline restoration. Failure to observe normal Civ V
exit is reported for operator action; the module never force-kills the game.
Data inconsistency pauses without cleanup so the operator can inspect the exact
scene. `recover` validates private files and refuses ambiguous ownership.

Administrator passwords are entered by the user into the foreground terminal
when macOS `sudo` prompts for the narrow firewall operations. Password data is
never accepted by the CLI or written to state.
