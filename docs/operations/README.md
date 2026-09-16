# Operations Index

Operational procedures must be safe to follow without remembering a prior chat.

- [Security policy](../../SECURITY.md): FireTuner exposure and mandatory safety
  boundaries.
- [Bounded live-test checklist](../LIVE_TEST_CHECKLIST.md): ordered target-Mac
  procedure and restoration steps.
- `python -m civ5_agent.live_session prepare`: record the private baseline,
  establish the Civ V firewall guard, enable FireTuner, and verify readiness.
- `python -m civ5_agent.live_session restore`: restore the recorded game config,
  Civ V rule, and global firewall state after the game and watcher stop.
- `python -m civ5_agent.preflight ready`: read-only check before starting Civ V.
- `python -m civ5_agent.preflight live`: read-only check before live access.
- `python -m civ5_agent.preflight shutdown`: read-only proof that the transport
  and local broker are closed.

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
[M8 release readiness](../planning/RELEASE_READINESS.md). Reproducible packaging, version/tag rules,
artifact scans, upgrade notes, and rollback procedures remain required. Until
they are complete, `main` plus passing CI is the development baseline, not a
stable release promise.

The current offline wheel gate builds without runtime dependencies, validates archive
paths and bounds, checks package-source coverage and wheel RECORD hashes, scans
for common private material, and checks metadata/entry points against
`pyproject.toml`:

```bash
python3.11 -m pip wheel --no-deps --wheel-dir dist .
python3.11 scripts/check_release_artifact.py dist/*.whl
```

The generated `dist/` directory is ignored and must not be committed. A passing
development wheel is not a release until the remaining M8 gates are complete.
