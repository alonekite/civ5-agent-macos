# CLI Compatibility Contract

Status: `civ5-turn` stable in 1.0; all other entry points explicitly provisional

## Compatibility classes

`civ5-turn` is the supported stable machine-readable CLI. Its subcommand names,
stdout envelopes, and exit meanings are compatibility-tested. An incompatible
change requires a new package major version; backward-compatible capability
uses a minor version and compatible fixes use a patch version under ADR-0030.

The following commands remain operational previews and carry no stable output
compatibility promise: `civ5-watch`, `civ5-command`, `civ5-controller`,
`civ5-preflight`, `civ5-live-session`, `civ5-knowledge`, and `civ5-journal`.
Their current safety, privacy, and write-verification requirements remain
mandatory; “provisional” permits interface evolution, not weakened safeguards.

## `civ5-turn` input

Supported subcommands are `validate PLAN` and `execute PLAN`. Shared options are
`--socket`, `--timeout`, and `--verify-timeout`. The bounded exact-field
TurnPlan file and watcher-only behavior are defined by the turn-plan contract.

Invalid command-line syntax uses standard `argparse` behavior: exit 2 and a
diagnostic on stderr. This invocation-error output is not JSON and its wording
is not stable.

## `civ5-turn` stdout

For a syntactically valid invocation, stdout contains exactly one UTF-8 JSON
object followed by a newline. Object keys are sorted for reproducibility.

Successful validation has exactly these fields:

- `ok: true`;
- `operation: "validate"`;
- `plan_id`;
- `bridge_session_id`;
- `action_count`.

Execution that produces a report has exactly `ok`, `operation: "execute"`, and
`report`. `ok` is true only when `report.status` is `completed`; the report is
the versioned `ExecutionReport` contract and is present for every safely
classified non-completed result.

Input, validation, filesystem, watcher, protocol, or transport failure has
exactly `ok: false` and bounded human-readable `error`. Error wording is
diagnostic and not a stable programmatic code. The envelope never echoes the
plan file or private live state.

## Exit meanings

- 0: validation succeeded, or execution completed;
- 1: the operation could not produce a valid execution report;
- 2: execution produced a valid non-completed report such as `paused`, `stale`,
  `failed`, or `recovery_required`.

Consumers must inspect the versioned report status when exit 2 is returned.
They must never interpret exit 1 as proof that a submitted action did not run.

M9 does not add a `civ5-turn` subcommand. Core 1.1.0 accepts the newly allowlisted
`move_unit` action in schema 1 plans while the existing validate and execute
envelopes remain unchanged; tagged core 1.0.0 rejects the action. The
provisional `civ5-command` accepts positional unit/coordinate arguments for
operator testing, but its spelling is not a stable integration surface.

M10 likewise adds no stable subcommand or envelope field. Core 1.2.0 has
a provisional `civ5-command worker_build UNIT_ID X Y BUILD_TYPE` spelling for
bounded operator testing, but it is not a supported integration interface.
Schema 1 TurnPlan admission accepts the action only with a schema 7 basis;
tagged core 1.1 rejects it. `validate` and `execute` retain the same stdout and
exit meanings.

## Non-goals

This contract does not stabilize error prose, absolute socket paths, Python
tracebacks, stderr warnings from provisional commands, or private data formats
outside their owning versioned contracts.
