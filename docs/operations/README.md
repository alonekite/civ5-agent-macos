# Operations Index

Operational procedures must be safe to follow without remembering a prior chat.

- [Security policy](../../SECURITY.md): FireTuner exposure and mandatory safety
  boundaries.
- [Bounded live-test checklist](../LIVE_TEST_CHECKLIST.md): ordered target-Mac
  procedure and restoration steps.
- `python -m civ5_agent.preflight ready`: read-only check before starting Civ V.
- `python -m civ5_agent.preflight live`: read-only check before live access.
- `python -m civ5_agent.preflight shutdown`: read-only proof that the transport
  and local broker are closed.

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

## Future release operations

M8 will add reproducible packaging, version/tag rules, artifact scans, upgrade
notes, and rollback procedures. Until then, `main` plus passing CI is the
development baseline, not a stable release promise.
