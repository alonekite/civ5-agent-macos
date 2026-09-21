# Operations Index

Operational procedures must be safe to follow without remembering a prior chat.

- [Security policy](../../SECURITY.md): FireTuner exposure and mandatory safety
  boundaries.
- [Persistent host hardening](HOST_HARDENING.md): one-time firewall/Civ V
  protection, per-test FireTuner lifecycle, drift handling, and exact rollback.
- [Bounded live-test checklist](../LIVE_TEST_CHECKLIST.md): ordered target-Mac
  procedure and restoration steps, including the operator-present M8 combined
  M5/M6 release gate.
- `python -m civ5_agent.live_session harden`: record the original firewall/rule
  baseline and persist the verified Civ V network guard across tests.
- `python -m civ5_agent.live_session prepare`: record the per-session baseline,
  verify any persistent guard, enable FireTuner, and verify readiness.
- `python -m civ5_agent.live_session restore`: restore the per-session game
  config and retain a recorded persistent guard after the game and watcher stop.
- `python -m civ5_agent.live_session unharden`: restore the exact firewall/rule
  state recorded by `harden`, only after the live session is closed.
- `python -m civ5_agent.preflight hardened`: verify the protected idle state.
- `python -m civ5_agent.preflight ready`: read-only check before starting Civ V.
- `python -m civ5_agent.preflight live`: read-only check before live access.
- `python -m civ5_agent.preflight shutdown`: read-only proof that the transport
  and local broker are closed.
- `python -m civ5_agent.watch --read-only`: expose only ping and validated state
  reads to an external composition root; command lookup, writes, and journal
  capture are rejected by the watcher server.
- `civ5-read-only session-spec` / `probe`: emit a private framework descriptor
  and read one same-session sanitized summary without importing or invoking the
  independently installed, digest-verified v0.1.0 automation framework. See
  [external read-only automation](EXTERNAL_READ_ONLY_AUTOMATION.md).
- `civ5-read-only ui-session-spec`: emit the provisional SessionSpec v2
  two-checkpoint launcher/continue sequence with an exact `PLAY`-only identity
  handoff for exact-commit candidate testing; it does not change the adopted v1
  path.

The live-session commands must run against the host system. A sandboxed process
can receive a false empty/disabled view from `socketfilterfw`; do not weaken the
checks in response. Recovery files live under the current user's Application
Support directory with private permissions and are never repository artifacts.
The Python process remains unprivileged and invokes `sudo` only for the narrow
firewall mutations; macOS may request an administrator password in the terminal.
Sudo tickets may be scoped to one terminal. Run `prepare` or `restore` in the
same interactive terminal that accepts the password; a separate automation
process must not assume it can inherit that authorization.

## Project continuity and recovery

- Source, durable design, and current status live in Git/GitHub.
- Raw Codex sessions and local recovery copies may contain private paths,
  prompts, command output, and account-specific context. Keep them outside the
  repository with private permissions.
- If the Codex UI stops showing recent turns, do not delete the task or clear
  application data. First preserve the corresponding local session JSONL, then
  generate a private user/assistant-only transcript. Restart the application
  only after the backup is verified.
- Recover project direction from `docs/PROJECT_STATE.md`, milestones, ADRs, and
  the development log rather than depending on a transcript.

## Release operations

M8 release gates and current blockers are tracked in
[M8 release readiness](../planning/RELEASE_READINESS.md). The exact operator
workflow is in [release, upgrade, and rollback](RELEASE.md). Until every gate is
complete and an immutable version tag is published, `main` plus passing CI is
the development baseline, not a stable release promise.

The current artifact gate builds without runtime dependencies, validates wheel
and source-archive paths and bounds, checks declared source coverage and wheel
RECORD hashes, scans for common private material, and checks metadata/entry
points against `pyproject.toml`:

```bash
python3.11 -m pip wheel --no-deps --wheel-dir dist .
python3.11 -c "from setuptools.build_meta import build_sdist; build_sdist('dist')"
python3.11 scripts/check_release_artifact.py dist/*.whl
python3.11 scripts/check_release_artifact.py dist/*.tar.gz
```

CI repeats both builds, compares normalized content hashes, and clean-installs
both artifact kinds. The generated `dist/` directories are ignored and must not
be committed. Passing development artifacts are not a release until the exact
candidate completes the remaining version, scan, hash, and tag steps.

## Downstream capability maintenance

The independent tactical layer consumes only the stable public core. Missing
facts or mechanics are reviewed through the
[core capability request process](CORE_CAPABILITY_REQUESTS.md); they are never
implemented as tactical-project transport or write workarounds. Any accepted
public capability ships in a newly versioned core release with owning-contract,
offline-test, target-evidence, capability-profile, and changelog updates.
