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
- `civ5-turn`
- `civ5-read-only`

`civ5-watch` also accepts the paired opt-in arguments `--journal PATH` and
`--journal-mode new|resume`. `new` refuses an existing path; `resume` explicitly
binds the new bridge session to an existing declared match. Journal capture is
restricted to `--transport tuner`; the partial database fallback is rejected.
`civ5-watch --read-only` is a server-enforced tuner mode that admits only
`ping` and `read_state`. It rejects command lookup and all write operations,
cannot be combined with journal capture, and reports the selected mode in its
ping response. It does not manage application or terminal lifecycle.
`civ5-journal verify PATH` validates the entire private journal and emits a
payload-free JSON summary; it never executes actions or exports match contents.
`civ5-journal replay PATH --include-private-payloads` emits the validated
append-order record stream. The mandatory flag makes private output explicit.
`civ5-journal export SOURCE DESTINATION` exclusively creates a mode-0600
structural export with private payloads and correlatable metadata removed.
`civ5-turn validate PLAN` strictly loads at most 64 KiB of schema 1 JSON and
checks it against fresh watcher state without writing. `civ5-turn execute PLAN`
is the explicit write operation and delegates the complete plan to the
watcher-owned executor. It never opens a direct FireTuner connection or creates
missing plan content.
`civ5-read-only probe` verifies that the watcher declares server-enforced
read-only mode, reads one validated same-session state, and emits a bounded
non-identifying summary. `civ5-read-only session-spec` emits the independent
automation framework's version-1 JSON descriptor for the read-only watcher.
Neither operation launches an app, supervises a process, invokes the framework,
or encodes a domain test procedure. The descriptor is compatibility-tested
against the separately installed, digest-verified framework v0.1.0 wheel; no
framework import or package dependency is added.

## Non-responsibilities

- Defining rules that exist nowhere in a core module.
- Choosing plan content or interpreting journal history.
- Bypassing validation, preflight, audit, or write verification.
- Providing a remote unauthenticated service.
- LLM or MCP integration.

## Public interface

Console scripts are declared in `pyproject.toml`; equivalent module execution is
supported during development. `civ5-turn` is the sole supported stable
machine-readable CLI under ADR-0027 and ADR-0030. Its exact JSON envelopes and
exit meanings are in the CLI compatibility contract. Other entry points,
including `civ5-read-only`, are explicitly provisional;
their safety and privacy invariants are not provisional.

## Inputs and outputs

Inputs are bounded command-line arguments and local paths. Outputs are JSON
state/results or concise diagnostics. Exit status must distinguish success from
invalid input, unsafe session, and failed action.

`civ5-live-session prepare` and `restore` are the only CLI operations that
deliberately modify the macOS firewall. They persist a private baseline outside
the repository, verify every boundary after mutation, and roll back failed
preparation.

## Dependencies

CLI may depend on public bridge, knowledge, deterministic executor, preflight,
and journal interfaces. Core modules must not depend on CLI parsing.

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

`civ5-controller` is the legacy readiness/end-turn proof; it is not the future
M6 tactical planner and remains provisional.
Cross-process recovery-report loading is not exposed without a separate bounded
persistence contract.

## Planned extensions

Assess provisional commands individually when a demonstrated consumer requires
stability rather than freezing them as a group. Journal capture consumes
validated in-memory results and never parses the independent M2 audit file.
M10 may add a provisional operator-facing worker-build command, but supported
downstream integration remains the unchanged schema 1 `civ5-turn` plan surface.
