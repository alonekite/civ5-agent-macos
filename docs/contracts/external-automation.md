# External automation compatibility contract

Status: Adopted for `local-app-test-automation` v0.1.0

Candidate extension: SessionSpec v2 compatibility is validated against exact
framework development commit `70b63426a45f18436aced8f53ae9b535c5092509`
and candidate wheel SHA-256
`0be1ebe491c80a1bb90e95a8a6fc1a17a096238c61960147c0ba677884f2c0f1`.
It is not an adopted framework release or runtime dependency.

ADR-0060 pins this candidate after the ADR-0059 one-second target run repeated
`system_cannot_complete / candidate_cannot_complete` at selection before
second-action delivery. Only after that terminal candidate AXFrontmost error,
the framework makes one bounded, read-only AXRole query on the same AX
application element. It persists only a closed-set `focus_probe` category,
not the role value or raw error. This diagnostic needs no additional human
input but grants no UI action or read capability. Nonzero candidate AXFrontmost
results remain terminal, with no retry or AppKit foreground substitute.
Post-handoff cleanup may accept the original or
exact successor AppKit executable only after a fresh process probe exactly
matches the tracked successor; PID, bundle identifier, bundle path, and
third-executable refusal remain unchanged. The second click
and watcher startup still have no target evidence. An operator-present target
run of this exact candidate completed gated PLAY and exact-PID handoff but
failed before second-action delivery with
`focus_probe=role_cannot_complete` alongside the existing
`system_cannot_complete / candidate_cannot_complete` selection result. This
does not establish the AX root cause or permit another focus source or retry.
A role-read success would not prove foreground state.
Framework 0.2 remains unadopted.

## Adopted artifact

The execution core formally supports the independently released framework:

- release tag: `v0.1.0`;
- tag target: `bf71fb072d9111d8cc4bbab24c50fc670fc2239c`;
- wheel: `local_app_test_automation-0.1.0-py3-none-any.whl`;
- wheel SHA-256:
  `6c0040ec2e4911c80b318687ad0fd53511972b517ca21dfbb5d0a3cd4af34eb3`;
- release: [local-civ5-test-automation v0.1.0](https://github.com/alonekite/local-civ5-test-automation/releases/tag/v0.1.0).

The wheel digest is the artifact identity. A file with the same name but a
different digest is not the adopted framework.

## Boundary

The integration is process-only. The core does not declare the framework as a
Python dependency and neither repository imports the other. A composition root
uses:

1. `civ5-read-only session-spec` to create private SessionSpec version 1 JSON;
2. the framework v0.1.0 public CLI to validate and run that specification;
3. `civ5-read-only probe` to verify the watcher is server-enforced read-only and
   read one same-session sanitized summary; and
4. the framework public `stop` operation for graceful termination.

The framework owns application/process lifecycle and recovery. The core owns
FireTuner safety, watcher semantics, validated game state, and redaction. No
framework profile, Civ-specific framework code, shared Python object, local
checkout path, or M11/C4 workflow is part of the contract.

The watcher process may start only after guarded live preflight proves TCP 4318
and every firewall condition. Because the target application exposes its
listener after launch, a composition root may use a separate generic
application-launch phase followed by a generated `observe_verified` watcher
session. SessionSpec v1 does not express a Civ-specific readiness dependency,
and the core does not weaken preflight to make simultaneous startup succeed.

## Compatibility

The adopted surface is:

- framework SessionSpec version 1;
- installed `local-app-test` CLI commands `validate`, `run`, `status`, `stop`,
  `report`, and cleanup-only `recover`;
- shell-free absolute process arguments;
- `retain_raw_output: false` and empty inherited environment;
- graceful watcher `SIGINT`;
- framework lifecycle protocol `latp/1`, used only by the framework's own CLI.

The core probe talks only to the core watcher socket; it does not implement or
depend on LATP. Both local sockets remain private and distinct.

Any framework version other than v0.1.0, any SessionSpec version other than 1,
or any artifact digest change requires a new compatibility review and contract
update before adoption. Compatible documentation-only changes in the framework
do not alter the adopted tag or wheel.

## Candidate SessionSpec v2 boundary

Development core 1.4 may emit SessionSpec v2 through the separate
`civ5-read-only ui-session-spec` command. The v1 command and adopted v0.1.0
identity remain unchanged. The candidate descriptor adds exactly two ordered
and independently authorized UI steps before the existing watcher process:

1. exact `AXButton`/`PLAY` activation in the verified launcher window;
2. one caller-calibrated window-relative click after the operator confirms the
   game canvas is showing `Click to Continue`.

The application identity is fixed to bundle ID `com.aspyr.civ5campaign` or the
verified `/Applications/Civilization V Campaign Edition.app` path. Both UI
targets use exact window title `Civilization V: Campaign Edition`. The second
step has no AX fallback because target observation found no actionable canvas
element. Coordinates must be finite and strictly between zero and one and are
private test configuration, not a stable universal game coordinate.

The launcher step additionally requires one `same_process_executable` identity
handoff to the exact verified successor
`/Applications/Civilization V Campaign Edition.app/Contents/MacOS/Civilization V Campaign Edition`.
The framework must durably record the post-delivery pending state, retain the
same PID, process creation time, bundle ID, and resolved bundle path, and admit
only that exact executable before the continue checkpoint or watcher starts.
It must not retry `PLAY` after delivery begins. The continue step declares no
handoff. Missing, mismatched, timed-out, or crash-interrupted handoff state is a
fail-closed recovery condition.

Candidate v2 validation does not amend the adopted release above. Compatibility
is tested through an isolated install of a wheel built from the exact candidate
commit, not through `PYTHONPATH` or a source checkout. Adoption requires a
published framework version and immutable wheel digest.

Human authorization is checkpoint-instance scoped. Only a new same-task
operator message sent after the exact checkpoint ID is created, explicitly
asserting current Mac presence and reproducing the current step plus short
nonce, may be translated to `pass`. Earlier, cross-task, generic, or
presence-ambiguous confirmations are invalid and must not be cached or rebound.
The execution layer's private one-use challenge helper machine-checks the
framework checkpoint UUIDv4, execution-task UUIDv4/UUIDv7, step,
request/creation order, nonce, freshness, file ownership/mode, exact
response, and consumption. It does not change or implement the framework
protocol. Until that protocol carries the nonce itself, the composition root
must forbid direct `pass` calls that bypass the helper.

The repaired candidate's own task reports 124/124 host tests. The suite includes
a real-socket silent-peer case followed by a valid status request and a complete
checkpoint creation/status/response/delivery/cleanup lifecycle, plus strict AX
no-value/error classification at candidate selection and final delivery
revalidation. GitHub Quality run `35663468813` passes the framework gates. At
the core boundary, the exact candidate wheel named above is installed with its
declared dependencies in a fresh Python 3.12 environment. Its installed public CLI
accepts a private mode-0600 v2 descriptor emitted by a separately
wheel-installed core. The core's warning-enabled suite passes 379/379 on Python
3.11 and the default runtime. This is offline compatibility evidence for the
exact-regular AX candidate, not a successful target UI run of that candidate.

After one checkpoint is authorized, the framework may wait within the existing
step timeout for the same fully verified target to become frontmost again. This
is pre-delivery readiness only: it does not activate the app, weaken identity,
extend authorization, or permit action replay. The operator must return focus
to the exact target and keep it frontmost.

During that pre-delivery wait, only the exact allowlisted
`focused_application_unavailable` observation may be treated as temporary
readiness, and only while Accessibility permission remains normal. Focus-query,
permission, PID, identity, ambiguity, timeout, and every post-delivery failure
remain terminal. Persistent unavailability expires with zero delivery; the
framework neither activates the application nor replays authorization.

If that wait expires, only the last closed-set readiness reason may reach the
existing sanitized identity-error event. Candidate absence, focused-application
unavailability, non-frontmost target, and unavailable window, element, or
geometry have distinct value-free tokens. Both construction and persistence
sanitize the token; unknown values become `unspecified`. The deadline,
descriptor, protocol, report shape, and action semantics do not change.

For `ui_identity_error`, durable `session.failure` events may add one
allowlisted, value-free `error_reason`. Both exception construction and event
persistence enforce the allowlist; unknown or mutated values become
`unspecified`. Exception text and observed paths, identities, process values,
titles, AX content, and selectors are excluded. This diagnostic event change
does not alter SessionSpec v2, `latp/1`, or sanitized reports.

Every accepted candidate control connection has a 0.5-second socket I/O
timeout. This bounds an incomplete same-user request so it cannot monopolize
the serialized supervisor loop for the remaining session lifetime. The timeout
does not authorize a request, retry `respond_checkpoint`, replay UI delivery,
or change checkpoint authority, expiry, durable state, or report semantics.

When system-wide `AXFocusedApplication` explicitly has no value or returns the
target-observed `kAXErrorCannotComplete` on macOS 26, the candidate may
corroborate only the exact already verified PID through a 0.25-second
application-level `AXFrontmost` query. Before that query, the candidate must
still have the same bundle identifier, resolved bundle and executable paths,
and regular GUI activation policy. Other nonzero system errors, a nonregular or
changed candidate, candidate AX errors, invalid PIDs, non-Boolean values, and
permission failures are terminal. Boolean false remains bounded
`target_not_frontmost`; no AppKit foreground fallback, application activation,
request retry, or delivery retry is permitted. The entire identity, activation-
policy, and focus sequence repeats at final pre-delivery revalidation.

## Verification evidence

The exact pre-release implementation passed 78/78 framework host tests,
including real Unix sockets and graceful process-group stop. The caller-boundary
suite passed 39/39, the generated SessionSpec was accepted by the installed
framework CLI, and scans found no cross-repository Python imports. GitHub
Quality run `35537130693` passed macOS 26 on Apple silicon and Intel with Python
3.12 and 3.13 plus wheel inspection and clean installation.

The published Release metadata independently reports the wheel name and digest
recorded above. Execution-core regression tests freeze those identifiers and
the generated SessionSpec version.

A bounded target composition launched and identity-verified Civ V, then used a
second `observe_verified` session to start the server-enforced read-only watcher
and pass the sanitized probe. Simultaneous app/watcher startup failed closed
while TCP 4318 was not yet listening, as required. Graceful watcher stop left
the observed application open; the operator exited it before exact host
restoration.
