# Module: CLI

Status: Implemented

## Responsibility

CLI entry points translate arguments into calls to core modules and render
structured results for operators and scripts.

Current commands:

- `civ5-watch`
- `civ5-command`
- `civ5-controller`
- `civ5-preflight`
- `civ5-live-session`
- `civ5-knowledge`

## Non-responsibilities

- Defining rules that exist nowhere in a core module.
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

CLI may depend on public bridge, knowledge, controller, preflight, and future
journal interfaces. Core modules must not depend on CLI parsing.

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

## Planned extensions

Add thin journal operations only after its core contract exists, then document
and test stable exit/error behavior during M7.
