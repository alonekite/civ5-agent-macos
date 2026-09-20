# External automation compatibility contract

Status: Adopted for `local-app-test-automation` v0.1.0

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
