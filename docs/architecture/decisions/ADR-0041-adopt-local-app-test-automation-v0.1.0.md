# ADR-0041: Adopt local-app-test-automation v0.1.0

Status: Accepted

Date: 2026-09-20

## Context

ADR-0040 established a process-only boundary while the independent automation
framework was still under release review. The framework has now published a
stable v0.1.0 tag and immutable wheel after exact-candidate caller validation,
macOS 26 architecture/Python matrix testing, artifact inspection, and clean
installation.

Continuing to refer to a local checkout or development candidate would make the
execution-core integration ambiguous and non-reproducible.

## Decision

Adopt `local-app-test-automation` v0.1.0 through its public CLI/JSON/process
boundary. Pin the release by tag, tag target, wheel name, and SHA-256 in the
external-automation contract and provisional adapter constants.

Do not add the framework to this package's dependencies. Do not import it from
core code. SessionSpec version 1 remains a caller-generated private document;
the composition root independently installs the verified wheel and sequences
framework start, core probe, and framework graceful stop.

## Consequences

- Operators have one reproducible framework artifact instead of a local path or
  moving candidate reference.
- The execution core remains installable and usable without the framework.
- Framework upgrades or artifact digest changes require a deliberate new
  compatibility review; they are not accepted by version ranges.
- Framework lifecycle behavior remains outside Civ V release claims and does
  not convert disposable-app acceptance into M11/C4 evidence.

## Alternatives considered

- Add a Python dependency: rejected because the integration is deliberately
  process-only and the execution core must not require application automation.
- Track framework `main`: rejected because it is mutable and not reproducible.
- Pin only the tag: rejected because the tag target and release artifact digest
  provide stronger identity and auditability.

## Supersedes

This ADR advances ADR-0040 from pre-release composition to a formally adopted
framework release. It does not supersede ADR-0040's ownership or security
boundaries.
