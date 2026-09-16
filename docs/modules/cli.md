# Module: CLI

Status: Implemented

## Responsibility

CLI entry points translate arguments into calls to core modules and render
structured results for operators and scripts.

Together with the watcher process, CLI composition is the application layer
that may fan validated observations and command results out to optional audit
and journal sinks. This wiring is not a policy or planning module.

Current commands:

- `civ5-watch`
- `civ5-command`
- `civ5-controller`
- `civ5-preflight`
- `civ5-live-session`
- `civ5-knowledge`
- `civ5-journal`

`civ5-watch` also accepts the paired opt-in arguments `--journal PATH` and
`--journal-mode new|resume`. `new` refuses an existing path; `resume` explicitly
binds the new bridge session to an existing declared match. Journal capture is
restricted to `--transport tuner`; the partial database fallback is rejected.
`civ5-journal verify PATH` validates the entire private journal and emits a
payload-free JSON summary; it never executes actions or exports match contents.
`civ5-journal replay PATH --include-private-payloads` emits the validated
append-order record stream. The mandatory flag makes private output explicit.

## Non-responsibilities

- Defining rules that exist nowhere in a core module.
- Choosing plan content or interpreting journal history.
- Bypassing validation, preflight, audit, or write verification.
- Providing a remote unauthenticated service.
- LLM or MCP integration.

## Public interface

Console scripts are declared in `pyproject.toml`; equivalent module execution is
supported during development. JSON-producing commands should keep success and
failure machine-readable.

## Inputs and outputs

Inputs are bounded command-line arguments and local paths. Outputs are JSON
state/results or concise diagnostics. Exit status must distinguish success from
invalid input, unsafe session, and failed action.

`civ5-live-session prepare` and `restore` are the only CLI operations that
deliberately modify the macOS firewall. They persist a private baseline outside
the repository, verify every boundary after mutation, and roll back failed
preparation.

## Dependencies

CLI may depend on public bridge, knowledge, provisional controller/executor,
preflight, and future journal interfaces. Core modules must not depend on CLI
parsing.

## Invariants

- CLI cannot weaken a module's validation.
- Dangerous defaults are prohibited; live writes are explicit.
- User-specific absolute paths are not embedded in repository defaults or
  generated documentation.

## Failure modes

Argument errors, unsafe session, unavailable watcher, transport failure, invalid
knowledge source, and failed verification propagate as bounded diagnostics.

## Security and privacy

Do not print credentials or arbitrary private files. Full state and audit data
remain local unless the user explicitly exports them.

## Verification

Unit tests exercise parsing, request construction, validation, and error status.
The primary watch and command flows have bounded target-machine evidence.

## Current limitations

The public CLI compatibility policy is not frozen before M7.
`civ5-controller` is the legacy readiness/end-turn proof; it is not the future
M6 tactical planner. M7 may rename it when the TurnPlan executor is public.

## Planned extensions

Add a private file-export journal operation, then add an explicit TurnPlan
execution entry point and stabilize names/error behavior in M7. Journal capture
consumes validated in-memory results and never parses the independent M2 audit
file.
