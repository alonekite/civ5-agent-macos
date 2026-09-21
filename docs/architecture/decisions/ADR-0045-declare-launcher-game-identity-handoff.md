# ADR-0045: Declare the launcher-to-game identity handoff

Status: Accepted

Date: 2026-09-21

## Context

ADR-0044 introduced a provisional SessionSpec v2 sequence for the Aspyr
launcher `PLAY` button and the game `Click to Continue` canvas. The first
bounded target run showed that the application keeps the same process while
its executable changes from the launcher to the game. Treating that transition
as an unexpected identity change correctly forced recovery, but it also made
the intended startup path impossible to complete safely.

The independent framework repaired this boundary on exact development commit
`ccae54ff5c4a3bd2a311a089a12926c8680f23c6`. Its generic handoff contract
requires the caller to declare the exact successor executable. It records a
durable pending state after action delivery, accepts only the same process and
verified application identity with that exact executable, and will not start
the next UI step or child process until the handoff completes. A failure or
crash after delivery remains recovery-required and is never replayed.

## Decision

Keep ADR-0044 and the adopted v0.1.0/SessionSpec v1 path unchanged. For the
candidate v2 path:

1. require the caller to supply the exact verified successor executable
   `/Applications/Civilization V Campaign Edition.app/Contents/MacOS/Civilization V Campaign Edition`;
2. reject every other successor path before descriptor emission;
3. attach one `same_process_executable` handoff only to the launcher `PLAY`
   step, with a bounded explicit timeout;
4. leave the continue step without an identity handoff; and
5. pin compatibility testing to framework commit `ccae54f` until an immutable
   framework release and artifact digest are reviewed.

The executable path is private UI-step configuration. It is not copied into
the watcher process arguments, environment, audit path, or socket path. The
core still does not import, package, or invoke the framework.

## Consequences

- Launcher delivery and game readiness are two durable lifecycle states; the
  framework may not advance between them speculatively.
- The exact same-process executable transition is admitted without weakening
  bundle, process, creation-time, or resolved-bundle-path identity checks.
- An absent, wrong, or late successor fails closed and requires recovery; the
  launcher action is not retried after delivery begins.
- A different Civ V installation path requires new target evidence and a core
  contract change rather than implicit executable discovery.
- Offline compatibility does not constitute a successful target-machine UI
  run or adoption of framework 0.2.

## Alternatives considered

- Permit any executable beneath the application bundle: rejected because it
  broadens identity beyond the observed transition.
- Infer the successor from bundle metadata: rejected because the launcher's
  declared executable is not the observed game successor.
- Attach the handoff to both UI steps: rejected because only `PLAY` causes the
  verified executable transition.
- Retry `PLAY` after an uncertain transition: rejected because delivery may
  already have occurred.

## Supersedes

This decision narrows the post-delivery identity behavior described by
ADR-0044. ADR-0044 remains authoritative for the two UI gates and ownership
boundary.
