# Test Strategy

## Evidence levels

1. **Static inspection**: code/schema/API exists or matches bundled source.
2. **Offline unit test**: deterministic behavior is exercised without Civ V.
3. **Offline integration test**: multiple modules or a real local ruleset source
   are exercised without changing a live match.
4. **Bounded live verification**: observed on the target Mac in a controlled
   game session with restoration evidence.

Higher evidence does not replace lower-level regression tests. Documentation
must state the actual level instead of using “verified” without qualification.

## Test layers

- Models/codecs: strict types, canonical serialization, unknown fields,
  non-finite values, corruption, ordering, and version compatibility.
- Bridge parser/transport: framing, async lifecycle frames, size limits,
  timeouts, closing behavior, and state selection.
- Actions: argument injection, capability predicates, exact postconditions,
  transient reads, timeout, duplicate UUID behavior, and audit failures.
- Unit movement: schema 6 target ordering/bounds/privacy, conservative target
  predicates, exact selection, generated-Lua size, wrong-unit and unexpected-
  displacement rejection, no-retry recovery, and TurnPlan requirement coverage.
- Worker build: schema 7 multipart/current-plot/candidate validation, read
  purity and privacy, every ordinary-build exclusion, exact source and selected
  dispatch guards, both factual success branches, uncertainty/no-retry,
  executor continuity/recovery, and compatibility preservation. The complete
  cases are frozen in the
  [worker-build verification specification](WORKER_BUILD_VERIFICATION.md).
- Knowledge: source immutability, active WAL/source change, allowlists,
  provenance, ruleset family, referential integrity, deterministic output, and
  forbidden AI/content fields.
- Controller: deterministic priority, refusal, mandatory choices, allowlisted
  output, and explicit execution.
- CLI/contracts: exit status, structured errors, stable schemas, and supported
  Python versions.
- Journal (M5): permissions, append semantics, crash/truncation recovery,
  concurrency, integrity, match/session isolation, explicit session binding,
  bounds, command-audit independence, and replay safety.
- Read-only watcher boundary: ping/state admission, command/status rejection
  before execution, journal incompatibility, tuner-only admission, and normal-
  mode compatibility.
- External read-only composition: exact SessionSpec v1 arguments, empty
  inherited environment, no raw-output retention, fail-closed capability and
  session checks, bounded summary redaction, CLI exit classes, and black-box
  validation through the digest-verified adopted framework v0.1.0 public CLI.
  Tests freeze the release tag, tag target, wheel name, wheel SHA-256, and
  SessionSpec version without importing the framework package.
- Candidate UI composition: preserve v1 unchanged; validate exact SessionSpec
  v2 step order and selectors, coordinate/time bounds, exact successor and
  bundle identity refusal, `PLAY`-only handoff placement, selector isolation
  from watcher fields, process start-after-UI semantics, and acceptance by an
  isolated wheel installation built from the pinned framework development
  commit without cross-project imports. Target procedure must also prove that
  checkpoint-induced focus loss waits only before delivery and never replays an
  action.

## CI baseline

- Run the complete warning-enabled `unittest` suite.
- Test the declared minimum Python 3.11 and the current CI runtime Python 3.13.
- Treat warnings, syntax incompatibility, and resource leaks as failures.
- Do not require Civ V, FireTuner, network access, or user-specific game data.

## Target-machine rules

- Never enable FireTuner, start Civ V, or change the firewall without explicit
  user authorization and the guarded host procedure. Generic launch/quit
  automation, when used, belongs to an independent external composition root;
  this repository retains the safety checks and domain verification only.
- Follow `docs/LIVE_TEST_CHECKLIST.md` with the user present.
- Capture the exact build/environment, action UUID, before/after evidence, and
  restored shutdown conditions.
- Update `LIVE_VERIFICATION_STATUS.zh-CN.md` only after the detailed experiment
  evidence has been recorded.
- Commit only sanitized conclusions, never raw player-specific snapshots or
  local paths that identify the user.
- For M9, execute only the checklist's source-coordinate negative case and one
  explicitly authorized adjacent target. A changed or unknown outcome ends the
  write portion; never improvise another move.
- For M10, execute only checklist section 8 after C1–C5: one stale-source
  pre-send rejection and one separately authorized candidate. Either exact
  success branch is sufficient live evidence; every unexpected or unknown
  outcome ends the write portion without retry or manual state changes.

## Release gate

Before a release: run all CI targets, scan tracked content and artifacts for
secrets/local identifiers, validate documentation links, confirm every
high-impact risk disposition remains supported by evidence and scope, and
ensure every claimed live capability has experiment-log evidence.
