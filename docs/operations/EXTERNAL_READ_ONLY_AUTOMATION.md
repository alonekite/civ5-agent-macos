# External read-only automation integration

Status: Framework v0.1.0 adopted; caller CLI remains provisional

## Ownership

`local-app-test-automation` is an independent Git repository and package. It
owns macOS application lifecycle, child-process supervision, control, recovery,
and sanitized lifecycle reports. This repository owns the Civ V safety guard,
FireTuner watcher, state validation, and read-only capability boundary.

Neither package imports the other. Codex, an operator tool, or another test
runner is the composition root.

## Adopted framework release

Use [local-civ5-test-automation v0.1.0](https://github.com/alonekite/local-civ5-test-automation/releases/tag/v0.1.0),
whose tag targets `bf71fb072d9111d8cc4bbab24c50fc670fc2239c`.
The adopted asset is
`local_app_test_automation-0.1.0-py3-none-any.whl` with SHA-256:

```text
6c0040ec2e4911c80b318687ad0fd53511972b517ca21dfbb5d0a3cd4af34eb3
```

Download the wheel into a private temporary directory and verify it before
installation:

```bash
shasum -a 256 local_app_test_automation-0.1.0-py3-none-any.whl
python3.12 -m pip install local_app_test_automation-0.1.0-py3-none-any.whl
```

Do not substitute a local checkout, an unverified same-name file, or framework
`main`. The complete adopted surface and upgrade rule are in the
[external automation compatibility contract](../contracts/external-automation.md).

## Generate a private SessionSpec

Use installed absolute executable and runtime paths. The output contains local
paths and must be written only to a mode-0600 temporary file outside the
repository.

```bash
civ5-read-only session-spec \
  --app-bundle-path /absolute/path/to/Civilization.app \
  --watcher-executable /absolute/path/to/civ5-watch \
  --cwd /absolute/path/to/runtime-directory \
  --socket /absolute/private/path/civ5-agent.sock \
  --audit-log /absolute/private/path/command-audit.jsonl
```

The generated framework `SessionSpec` version 1 contains one process:
`civ5-watch --read-only`. It has an empty inherited environment, retains no raw
output, and requests graceful `SIGINT` shutdown. It does not contain an M11,
C4, research, tactical, or other domain workflow.

Validate and run that file with the installed v0.1.0 framework's public
`local-app-test` CLI. Framework command spelling and runtime-root handling are
defined by that project, not this repository.

### Target startup ordering

The generated watcher fails closed while TCP 4318 is absent. On the target,
Civ V does not make that listener available early enough for a single framework
session that launches the application and starts the watcher simultaneously.
The composition root must therefore either:

1. launch and identity-verify the application in a separate generic framework
   phase, wait for guarded live preflight, then run the generated specification
   with `--existing-instance-policy observe_verified`; or
2. have the operator start the application, pass guarded live preflight, and
   then use the same `observe_verified` specification.

The separate launch phase is generic composition, not a Civ/M11 framework
profile, and is not emitted by this repository. Never weaken watcher preflight,
sleep inside the watcher, or start a second FireTuner client to hide readiness.
An observed instance remains open when the framework stops; the composition
root or operator must quit it before `civ5-live-session restore`.

## Read one sanitized state

While the framework-supervised watcher is running, the composition root invokes:

```bash
civ5-read-only probe --socket /absolute/private/path/civ5-agent.sock
```

The probe first requires `read_only: true`, then requires the state read to come
from the same bridge session. Success emits one JSON object containing only the
schema and turn readiness plus city/unit counts and whether research is
selected. It omits the bridge-session ID and all names, stable game identifiers,
coordinates, technology names, resources, diplomacy, and complete state.

Exit meanings are:

- `0`: one sanitized state was read from a verified read-only watcher;
- `1`: watcher availability, read-only capability, session continuity, or
  state validation failed;
- `2`: local arguments were invalid.

The composition root then calls the framework's public graceful-stop command.
The probe is intentionally not a supervised child: framework lifecycle reports
do not expose child output, and the framework must not interpret Civ payloads.

## Safety and privacy

This integration does not prepare the firewall or enable FireTuner. The guarded
`civ5-live-session prepare`, live preflight, and exact restoration procedure
remain mandatory. A SessionSpec, watcher output, audit file, and probe output
are local test artifacts and must never be committed.

Run macOS firewall inspection and private Unix-socket probes in the actual host
execution context. A restricted orchestration sandbox can return a different
firewall view or reject the socket connection with `EPERM`; neither result is
target safety evidence. Never weaken the preflight because of that discrepancy.

The generated process sets `retain_raw_output` to false. The full watcher state
may still pass through its private pipe and is counted then discarded by the
framework; it is not part of the sanitized lifecycle report.

## Offline compatibility check

The core test suite verifies the adopted release identifiers, exact arguments,
fail-closed read-only admission, same-session state reading, summary redaction,
exit classes, and SessionSpec v1 shape. Cross-repository checks invoked the
installed v0.1.0 wheel's public `validate` command against generated JSON and
verified graceful stop. The framework's disposable-app acceptance is not M11
C4 evidence.

## Candidate SessionSpec v2 launcher sequence

The development `ui-session-spec` command is compatibility-tested only against
framework commit `a722aac6dcd7854d5715bdf994115de6ed5c792d` and wheel
SHA-256
`cca1d5b674864e261b9252b67808749e954014c38a8d79b7b2be78541ee357d3`.
Do not substitute it for the adopted v0.1.0 path in unattended or release
workflows.

This pin includes the post-handoff identity continuation reviewed in ADR-0055.
The framework may retain the original AppKit executable URL only while the
process probe reports the exact declared successor with unchanged PID and
creation time. The next UI step and watcher start must recheck that tracked
successor. A completed PLAY action alone does not establish that the continue
click or watcher has been verified on the target; use fresh checkpoints for
both steps in the next operator-present run.

This candidate bounds each accepted private control connection to 0.5 seconds.
The bound releases a serialized control loop from an incomplete same-user
request; it does not retry checkpoint responses, authorize UI delivery, or
change checkpoint expiry and action no-retry rules.

On macOS 26, an absent system-wide focused-application value or the
target-observed `kAXErrorCannotComplete` may be corroborated only by a bounded
`AXFrontmost` Boolean read from the exact verified candidate PID. Before that
read, the framework revalidates exact bundle and executable identity and
requires `NSApplicationActivationPolicyRegular`. Other system or candidate AX
errors, nonregular processes, and identity changes are terminal. This is not
application activation and does not authorize another PID.

Target inspection verified:

- bundle ID `com.aspyr.civ5campaign`;
- optional bundle path `/Applications/Civilization V Campaign Edition.app`;
- launcher executable
  `/Applications/Civilization V Campaign Edition.app/Contents/MacOS/AppBundleExe`;
- same-process game successor executable
  `/Applications/Civilization V Campaign Edition.app/Contents/MacOS/Civilization V Campaign Edition`;
- exact launcher/game window title `Civilization V: Campaign Edition`;
- one unique launcher `AXButton` titled `PLAY`;
- no actionable AX element on the game continue canvas.

Calibrate the continue point with the exact target window configuration. Capture
the window bounds and a reviewed point inside the visible continue target, then
compute `x_ratio = point_x / window_width` and
`y_ratio = point_y / window_height`. Repeat the observation after any display,
resolution, full-screen, window-size, or letterboxing change. Do not reuse a
coordinate merely because it worked in a differently sized screenshot.

Generate a private mode-0600 descriptor only after that review:

```bash
civ5-read-only ui-session-spec \
  --app-bundle-id com.aspyr.civ5campaign \
  --watcher-executable /absolute/path/to/civ5-watch \
  --cwd /absolute/path/to/runtime-directory \
  --socket /absolute/private/path/civ5-agent.sock \
  --audit-log /absolute/private/path/command-audit.jsonl \
  --continue-x-ratio REVIEWED_X_RATIO \
  --continue-y-ratio REVIEWED_Y_RATIO \
  --expected-game-executable \
    "/Applications/Civilization V Campaign Edition.app/Contents/MacOS/Civilization V Campaign Edition"
```

Only `press_launcher_play` declares the bounded
`same_process_executable` handoff. The continue step must not declare one. The
framework records delivery before waiting for the exact successor and must not
advance, start the watcher, clean up the old identity, or retry `PLAY` while the
handoff is pending. Failure after delivery is recovery-required.

Before running, manually grant Accessibility permission to the terminal or
automation host process. The framework will request two checkpoints:

1. bring the exact launcher window to the foreground, visually confirm the
   unique `PLAY` button, then pass the checkpoint for one AX press;
2. wait through game startup, bring the exact game window to the foreground,
   visually confirm `Click to Continue` and the calibrated point, then pass the
   checkpoint for one relative click.

The framework starts the watcher only after both checkpoints pass. The operator
must still observe that the second click reached the intended screen; neither
the framework nor the core performs screenshot/OCR outcome inference. Missing
Accessibility permission, non-unique identity/window/AX target, an expired or
refused checkpoint, invalid coordinates, or absent live preflight fails closed.

A checkpoint answer is valid only after the framework has emitted that exact
checkpoint ID and the execution layer has created a private challenge bound to
that ID, its current step, and this execution-layer task. The operator must then
send the exact nonce-bearing prompt as a new message in this task while
explicitly present at the Mac. A confirmation that predates checkpoint
creation, belongs to another task or session, omits the current step/nonce, or
does not assert current presence is never reusable. Unknown, withdrawn, or
conflicting presence permits only fail, abort, or stop—never `pass`.

Use `civ5-read-only checkpoint-challenge` only after observing
`checkpoint.requested`, then require the operator to copy its exact prompt.
Use `civ5-read-only checkpoint-authorize` to validate and consume the private
mode-0600 ticket before calling the framework's public `respond-checkpoint`.
The ticket is bound to the canonical framework checkpoint UUIDv4, execution-
task UUIDv4/UUIDv7, one supported step, the
recorded request time, an eight-hex nonce, and a maximum five-minute age. It is
deleted on success and cannot authorize a later step.

This local gate cannot prove that a message came from the Codex task because the
current framework protocol carries neither task identity nor nonce. The
composition root must enforce message provenance. A future protocol should
carry a caller nonce in checkpoint creation/response so the framework can
reject bypasses itself; until then, direct `pass` calls that bypass this ticket
are outside the supported procedure.

After replying to a checkpoint in the control client, return to the exact Civ V
window and keep it frontmost. The framework waits up to the step timeout for
that same verified target before delivery. It does not focus the app itself.
Only `focused_application_unavailable` with Accessibility permission intact may
remain in that bounded wait. Permission/query/PID/identity/ambiguity failures
remain terminal, as does every post-delivery failure; no action is retried.
If a UI identity failure occurs, preserve only the framework's allowlisted
`error_reason` token for diagnosis. Never copy exception text or private event
files into this repository.
On a pre-delivery timeout, that token is the last observed closed-set readiness
class, not an authorization to retry or select a different focus source.

### Exact candidate-retest descriptor generation

The repaired framework contract is available at the exact candidate commit
above and has passed execution-core offline review. A new live run still
requires joint review, an operator-present window, and fresh checkpoint
authorization. Install both projects as wheels in separate private virtual
environments; source checkout or `PYTHONPATH` validation is insufficient. Set
the three absolute private paths, re-review the target window and the two
ratios, then generate the mode-0600 descriptor exactly as follows:

```bash
umask 077
export CIV5_CORE_ROOT=/absolute/path/to/civ5-agent-macos
export CIV5_CORE_VENV=/absolute/private/path/to/core-venv
export CIV5_UI_RUN_ROOT=/absolute/private/path/to/ui-run

"$CIV5_CORE_VENV/bin/civ5-read-only" ui-session-spec \
  --app-bundle-path "/Applications/Civilization V Campaign Edition.app" \
  --leave-open-on-success \
  --watcher-executable "$CIV5_CORE_VENV/bin/civ5-watch" \
  --cwd "$CIV5_CORE_ROOT" \
  --socket "$CIV5_UI_RUN_ROOT/civ5-agent.sock" \
  --audit-log "$CIV5_UI_RUN_ROOT/command-audit.jsonl" \
  --continue-x-ratio 0.5 \
  --continue-y-ratio 0.64 \
  --expected-game-executable \
    "/Applications/Civilization V Campaign Edition.app/Contents/MacOS/Civilization V Campaign Edition" \
  > "$CIV5_UI_RUN_ROOT/session.json"
chmod 600 "$CIV5_UI_RUN_ROOT/session.json"
```

The `0.5/0.64` ratios are evidence for the tested window configuration only,
not universal Civ V coordinates. Validate the descriptor with the public CLI
from the separately installed exact-candidate wheel. The framework must still
request fresh per-step authorization before any action.
