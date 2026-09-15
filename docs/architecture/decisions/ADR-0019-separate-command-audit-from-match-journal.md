# ADR-0019: Separate the command audit from the match journal

Status: Accepted

Date: 2026-09-16

## Context

M2 already writes a private command audit containing command UUIDs, validated
arguments, and before/after state. M5 also needs verified command lifecycles in
the per-match history. Treating either store as the input or transactional peer
of the other would couple safety evidence, historical capture, and game-action
retry semantics.

## Decision

The stores remain independent consumers of one validated in-memory command
result:

- the M2 audit is local operational and safety evidence for bridge commands;
- the M5 journal is an integrity-checked sequence of supported facts captured
  for one declared match;
- watcher/CLI composition passes the validated result to each configured sink;
- command UUID correlates audit and journal records, but M5 never parses or
  tails the audit file;
- neither store is authoritative for whether the game action succeeded; only
  the bridge postcondition and fresh live state are authoritative;
- failure of either sink is reported separately and never makes a verified
  action retryable;
- no atomic transaction across Civ V, audit storage, and journal storage is
  claimed.

## Consequences

- M5 can be disabled without weakening the established M2 command path.
- Audit retention and journal retention may differ.
- Integration tests must cover either sink failing after a verified action and
  prove that the game write is not duplicated.
- The composition layer owns fan-out and diagnostics but contains no game
  policy or plan production.

## Alternatives considered

- Import audit JSONL into M5: rejected because audit truncation, rotation, or
  format changes would become journal input semantics.
- Replace the M2 audit with M5: rejected because the journal is optional during
  M6 execution and has different match-scoping requirements.
- Require transactional dual writes: rejected because local files and Civ V
  cannot share an atomic transaction, and retry could duplicate an irreversible
  game action.

## Supersedes

This decision clarifies the persistence integration left open by ADR-0016. It
does not change ADR-0016's rule that journal failure cannot control execution.
