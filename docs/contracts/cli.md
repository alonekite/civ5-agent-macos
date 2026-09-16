# CLI Compatibility Contract

Status: `civ5-turn` supported pre-1.0; all other entry points explicitly provisional

## Compatibility classes

`civ5-turn` is the supported machine-readable pre-1.0 CLI. Its subcommand
names, stdout envelopes, and exit meanings are compatibility-tested. A breaking
change requires a minor-version increment and compatibility note while the
package remains 0.x.

The following commands remain operational previews and carry no pre-1.0 output
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

## Non-goals

This contract does not stabilize error prose, absolute socket paths, Python
tracebacks, stderr warnings from provisional commands, or private data formats
outside their owning versioned contracts.
