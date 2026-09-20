# ADR-0040: Compose external supervision through JSON and CLI boundaries

Status: Accepted

Date: 2026-09-20

## Context

Generic macOS application lifecycle, terminal supervision, recovery, and human
checkpoints belong to the independent `local-app-test-automation` repository.
This core still needs a narrow way for an external composition root to start its
server-enforced read-only watcher and obtain a privacy-bounded observation.

Importing either package into the other would reverse ownership or create a
runtime dependency. Treating watcher stdout as a report would also disclose the
complete live state. The automation framework's sanitized report deliberately
does not expose child output.

## Decision

Integration uses only installed executables, JSON, exit status, and the core's
mode-0600 Unix socket:

- `civ5-read-only session-spec` emits a private `SessionSpec` version 1 for the
  external framework. It declares only `civ5-watch --read-only` and contains no
  domain test procedure.
- `civ5-read-only probe` independently verifies the watcher's ping declares
  `read_only: true`, reads one validated state from the same bridge session, and
  emits a bounded summary without names, identifiers, coordinates, resources,
  technologies, diplomacy, runtime context, or full state.
- The external composition root invokes the framework, invokes the probe, and
  requests graceful stop. Neither repository imports the other.
- The generated SessionSpec sets `retain_raw_output` to false, inherits no
  environment variables, and requests `SIGINT` for graceful watcher stop.

Both commands are provisional. The server-enforced negative capability in
ADR-0039 remains the security boundary; the probe is an additional fail-closed
check, not a replacement.

## Consequences

- The automation framework remains reusable and domain-neutral.
- This repository does not own application lifecycle, process recovery, human
  checkpoints, C4/M11 workflow, or a generic supervisor.
- A composition root must keep the SessionSpec and any live summary private and
  must call the framework's public stop operation after collecting evidence.
- Framework schema changes require an explicit adapter compatibility review;
  they do not silently enter the core runtime.

## Alternatives considered

- Import the framework from the core: rejected because it creates the wrong
  dependency direction and a new runtime dependency.
- Put a Civ-specific profile in the framework: rejected because the framework
  must not know Civ V, M11, C4, or live-state schemas.
- Read supervised watcher stdout: rejected because it is full private state and
  the framework intentionally excludes child output from sanitized reports.
- Reintroduce the removed in-core supervisor: rejected by the repository
  boundary and ADR-0039.
