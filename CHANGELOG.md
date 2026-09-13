# Changelog

All notable user-visible changes will be recorded here once the project begins
versioned releases. Development details belong in
`docs/development/DEVELOPMENT_LOG.md`.

## Unreleased

### Added

- Verified macOS Civ V read/write bridge with guarded FireTuner transport.
- Live state watcher and private local command broker.
- Verified end-turn, research-selection, and city-production actions.
- Deterministic controller proof.
- Versioned ruleset knowledge core and partial BNW knowledge importer.
- Structured documentation governance, architecture decisions, module
  boundaries, contracts, milestones, risks, and verification matrix.

### Security

- Fail-closed FireTuner preflight and shutdown checks.
- Explicit action allowlist and write-after-read verification.
- Private local IPC and audit permissions, bounded messages, UUID validation,
  and duplicate-command suppression.

No release has been tagged yet.
