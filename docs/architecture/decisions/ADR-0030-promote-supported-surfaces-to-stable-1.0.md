# ADR-0030: Promote the supported surfaces to stable 1.0

Status: Accepted

Date: 2026-09-16

## Context

M7 identified and contract-tested one aggregate Python import surface and one
bounded machine-readable CLI. M8 has now completed its required target-machine
gate, risk disposition, packaging automation, security documentation, and
release procedure. The first stable release needs an explicit compatibility
boundary without accidentally freezing every historical operator command.

## Decision

Version 1.0 stabilizes `civ5_agent.api` and the documented `civ5-turn`
subcommands, stdout envelopes, nested versioned records, and exit meanings.
Incompatible changes to either supported surface require a new major version;
backward-compatible public capability uses a minor version and compatible fixes
use a patch version.

The other console entry points remain provisional interfaces. Version 1.0 does
not promise their exact arguments, output shape, or diagnostic prose. Their
security, privacy, action allowlist, bounded-input, and write-verification
requirements remain mandatory and cannot be weakened as provisional details.

Versioned persisted and exchanged schemas keep their own documented version
rules. A package-major change is still required when a schema change also
breaks a supported Python or `civ5-turn` consumer.

## Consequences

- Consumers have one stable Python namespace and one stable automation CLI.
- Internal modules, transport details, importers, and provisional operational
  commands may evolve without pretending to be stable public API.
- Release notes must distinguish package compatibility from schema versions and
  must identify provisional commands explicitly.

## Alternatives considered

- Freeze every console script: rejected because setup, diagnostics, extraction,
  and the legacy controller proof have different audiences and inconsistent
  output contracts.
- Keep the entire package pre-stable: rejected because the supported boundaries
  have contract tests and the M8 release gates are complete except for the
  operator-controlled tag.
- Stabilize schemas only: rejected because Python and shell consumers need an
  explicit package-level compatibility promise.

## Supersedes

This advances the pre-1.0 compatibility policies in ADR-0026 and ADR-0027 to
their stable package form. It preserves ADR-0027's decision not to stabilize the
other command-line entry points.
