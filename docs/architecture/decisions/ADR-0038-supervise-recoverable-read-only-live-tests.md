# ADR-0038: Supervise recoverable read-only live tests outside execution

Status: Accepted

Date: 2026-09-20

## Context

M11 C4 requires a repeatable target-machine procedure, but the existing manual
runbook leaves process ordering, private paths, checkpoint bookkeeping, and
failure recovery to the operator. Reusing the deterministic turn executor would
mix evidence collection with gameplay execution and would create an accidental
second policy surface. Persisting watcher snapshots would also violate the
bounded evidence rule.

The automation must still leave menu navigation, save loading, research
selection, and turn advancement to the operator. Visual agreement cannot be
derived solely from bridge data, while data invariants should not depend on a
human judgment.

## Decision

Add the provisional `civ5_agent.live_testing` application/operations layer and
the `civ5-live-test` CLI. One foreground supervisor owns a private control
socket, a single-session lock, the guarded live-session lifecycle, the Civ V
launch/normal-quit lifecycle, and one child watcher. Profiles are explicit and
pluggable; the first profile is `m11-research-runtime-c4`.

The supervisor launches the watcher with a server-enforced `--read-only` mode.
That mode admits `ping` and `read_state` only and rejects every command and
command-status operation before command validation, auditing, journaling, or a
game call. The live-test layer must not import or depend on controller,
`TurnPlan`, command-write orchestration, knowledge, or journal modules.

`start` prepares the guarded host session, launches Civ V, waits for the live
safety boundary, starts the read-only watcher, and then serves until `finish` or
a terminal safety failure. It does not navigate menus or load a save. `status`,
`checkpoint`, and `confirm` use the private control socket. `recover` reacquires
the single-session lock after a supervisor crash, resumes an intact read-only
session when possible, or restores the baseline when the game is already
closed. `finish` asks Civ V to quit normally; forced termination of the game is
prohibited.

Profile checkpoints combine three evidence kinds:

- deterministic checks over fresh validated bridge reads;
- an explicit `codex` visual confirmation when Codex has inspected the screen;
- an explicit `user` confirmation when screen inspection is unavailable or
  ambiguous.

Only bounded, allowlisted summaries, confirmation provenance, and whether an
optional note was supplied are persisted; note text is neither echoed nor kept. Full
snapshots, save names, player names, bridge-session identifiers, local paths,
and credentials are excluded. Runtime files and sockets are mode `0600` inside
a mode-`0700` directory.

Safety-boundary failures request normal game exit, stop the child watcher, and
restore the recorded baseline. A data mismatch instead changes the session to
`paused_data_inconsistency`, preserves the live scene, and requires an explicit
operator decision. Administrator authentication remains an interactive user
action performed by the narrow `sudo` calls in `live_session`; the supervisor
does not collect, forward, or store a password.

## Consequences

- M11 evidence collection becomes reproducible without becoming a game executor.
- Read-only mode is enforced by the watcher server and cannot be weakened by a
  cooperative client.
- The first release remains operator-present and cannot finish C4 without UI
  confirmation and any required manual game actions.
- A foreground supervisor terminal must remain open. This is deliberate: it
  preserves interactive administrator authentication and makes lifecycle
  ownership visible.
- Recovery state is operational metadata rather than a match journal or replay.

## Alternatives considered

- Extend the turn executor: rejected because live-test evidence is not a turn
  plan and must not acquire a write path.
- Automate menus and save loading: rejected for the first version because those
  controls are not verified and would broaden target risk.
- Persist complete snapshots for recovery: rejected because recovery needs only
  lifecycle state and bounded checkpoint summaries.
- Force-kill Civ V on failure: rejected because it can damage user state and is
  unnecessary for bounded recovery.
