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
