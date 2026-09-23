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
`civ5-read-only` is also an operational preview.
Their current safety, privacy, and write-verification requirements remain
mandatory; “provisional” permits interface evolution, not weakened safeguards.

The provisional `civ5-watch --read-only` option has a mandatory negative
capability boundary: its local server admits only ping and validated state
reads. It rejects completed-command lookup and every write before execution and
cannot be combined with journal capture. Generic application or terminal
automation is not part of this CLI.

The provisional `civ5-read-only` command is the process boundary described by
ADR-0040. `probe` fails unless ping declares `read_only: true` and the following
validated state belongs to the same bridge session. It emits only a bounded
summary and uses exit 0 for success, 1 for watcher/capability/state failure, and
2 for invalid local input. `session-spec` emits framework SessionSpec version 1
JSON but never imports or invokes the framework. Its output is private because
it contains absolute runtime paths. SessionSpec version 1 is compatibility-
tested against the adopted `local-app-test-automation` v0.1.0 wheel identified
by the external automation contract; the framework remains an optional external
executable, not a Python dependency.

Development `ui-session-spec` emits candidate SessionSpec version 2 with the
exact verified Civ V bundle/window identity, a unique launcher AX press, a
caller-reviewed normalized continue click, and the unchanged read-only watcher
process. It requires finite open-interval click ratios, the exact verified game
successor executable, and a bounded `PLAY`-only same-process identity handoff.
It fails closed for an unverified bundle or successor identity. Omitting the
required successor argument is ordinary `argparse` invocation error exit 2.
This candidate is not part of the adopted v0.1.0 framework contract.

Development `manual-ui-session-spec` emits a separate candidate SessionSpec
v2 with only the verified PLAY step and same-process handoff, followed by one
`manual_game_entry` gate before the unchanged read-only watcher. It accepts
no Continue coordinates. It rejects any unverified bundle/successor, invalid
gate timeout, or session timeout too short for the declared UI, handoff, and
manual bounds. Its output must remain private and cannot be used for a target
run until the exact framework candidate and its host safety checks are
reviewed. The old `ui-session-spec` output is unchanged.

Development `play-grant-create` and `play-grant-consume` implement ADR-0061's
single-session PLAY preauthorization. The composition root first verifies a
fresh same-task user initiation and an active framework PLAY checkpoint.
Creation requires their times, framework session/checkpoint IDs, canonical
SessionSpec SHA-256, task ID, and exact initiation text; it writes an owned
mode-0600 file with exclusive creation and at most ten-minute session scope.
Consumption requires the same identifiers and deletes the file before the
framework receives `pass`. The helpers do not themselves authenticate message
provenance or call the framework. They never authorize Continue, the manual
gate, a second PLAY, another session, or reuse of an old nonce.

`checkpoint-challenge`/`checkpoint-authorize` also accept
`manual_game_entry`, whose exact Chinese response states that the operator
personally completed Continue and game entry. The caller may set a bounded
`--max-age-seconds` up to 3600 for that gate only; prior UI-action challenge
limits and phrases are unchanged. A successful gate response is not game-state
proof. `probe --require-active-match` additionally fails with
`active_match_unavailable` unless the server-enforced read-only watcher
returns a same-session validated active player turn.

Development `checkpoint-challenge` and `checkpoint-authorize` implement the
ADR-0054 local operator-presence gate without invoking the framework.
`checkpoint-challenge` exclusively creates one private mode-0600 ticket after a
declared checkpoint request and emits the exact nonce-bearing prompt.
`checkpoint-authorize` accepts only a matching canonical checkpoint UUIDv4 and
task UUIDv4/UUIDv7,
supported step, owned regular file, schema, request/creation order, nonce,
freshness, and response, then deletes the ticket. Both use exit 0 for success
and the existing provisional exit 2 `invalid_input` envelope for rejected local
input. The ticket and prompt are not framework protocol fields; a composition
root must not call framework `pass` unless this gate succeeds.

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
