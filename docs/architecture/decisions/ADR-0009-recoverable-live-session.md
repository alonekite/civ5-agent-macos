# ADR-0009: Manage live tests as recoverable bounded sessions

Status: Accepted

Date: 2026-09-14

## Context

FireTuner listens on all IPv4 interfaces in the target Campaign Edition build.
Each test therefore needs the application firewall, an explicit Civ V block
rule, a reversible game-config edit, and verified restoration. Repeating those
steps manually caused drift, and macOS may report a firewall application as
either its executable path or its canonical `.app` bundle path.

## Decision

Provide `civ5_agent.live_session` with explicit `prepare` and `restore`
operations. `prepare` records the starting firewall and Civ V rule state in a
private file outside the repository, creates a private configuration backup,
establishes the firewall guard, enables FireTuner, and verifies the ready phase.
Failure triggers rollback. A repeated prepare is accepted only when the saved
session is already safe.

`restore` refuses to run while the game listener or watcher socket remains,
then restores the configuration, Civ V rule, and global firewall state to the
recorded baseline. It deletes recovery files only after verification succeeds.

Both the executable path and the canonical application-bundle path are valid
representations of the same Civ V firewall entry. Operators and automation must
run these commands against the host system, not a sandboxed firewall view.
The Python process stays under the invoking user and applies `sudo` only to the
narrow `socketfilterfw` mutation, so local recovery files and game config do not
become root-owned.

## Consequences

- Starting and ending a live test become repeatable, fail-closed operations.
- Interrupted preparation leaves enough private state for explicit recovery.
- The tool changes OS security settings only when the operator explicitly runs
  `prepare` or `restore`; importing the module and all normal bridge operations
  remain non-mutating.
- The user may still need to authorize host-level firewall changes on macOS.
- Terminal-scoped sudo authorization cannot be inherited by a separate Codex
  execution process; the operator may need to run the command interactively.
- Recovery state and configuration backups are local-only and must never be
  committed.

## Alternatives considered

- Keep a manual checklist only: rejected because repeated stateful operations
  are error-prone and difficult to recover after interruption.
- Leave the firewall enabled permanently: rejected because it does not restore
  the user's original machine state.
- Bind FireTuner to loopback: unavailable in the tested game build.

## Supersedes

The manual preparation and restoration sequence remains useful as an emergency
fallback, but it is no longer the primary operator workflow.
