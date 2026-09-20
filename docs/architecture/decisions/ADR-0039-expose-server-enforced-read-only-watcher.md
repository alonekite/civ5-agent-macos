# ADR-0039: Expose a server-enforced read-only watcher mode

Status: Accepted

Date: 2026-09-20

## Context

External operator tooling may need to supervise a bounded live test without
gaining access to the execution core's command surface. A client-side promise
not to send commands is insufficient because the normal watcher socket admits
allowlisted writes and completed-command lookup.

General application lifecycle and terminal automation are owned by an
independent project. This repository must expose only the minimum execution-
core capability that an external composition root can safely invoke.

## Decision

`civ5-watch --read-only` starts the existing FireTuner watcher with a server-
enforced local protocol restriction. The handler admits only `ping` and
`read_state`. It rejects `command_status` and every write operation before
command validation, execution, audit append, or journal composition.

Read-only mode is available only with the verified tuner transport and cannot
be combined with journal capture. Normal watcher mode remains unchanged. The
ping response declares whether the watcher is read-only so a caller can verify
the selected boundary.

## Consequences

- External automation can supervise the process and consume validated state
  without receiving a game-write capability.
- This repository does not launch or quit applications, manage generic PTYs,
  define test profiles, or depend on an automation framework.
- Domain verification such as M11 C4 remains in this repository's testing
  contracts and is not encoded in watcher mode.
- The option is provisional; its safety invariant is mandatory even though its
  exact diagnostic wording is not stable.

## Alternatives considered

- Trust the caller not to send writes: rejected because the server would still
  expose the capability.
- Add a second read-only FireTuner client: rejected because the target build
  reliably supports one connection owner and a duplicate transport path would
  weaken session identity and serialization.
- Keep a general automation framework here: rejected because application
  lifecycle, PTY automation, visual confirmation, and generic recovery belong
  to an independent project.
