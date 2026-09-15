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

## CI baseline

- Run the complete warning-enabled `unittest` suite.
- Test the declared minimum Python 3.11 and the current CI runtime Python 3.13.
- Treat warnings, syntax incompatibility, and resource leaks as failures.
- Do not require Civ V, FireTuner, network access, or user-specific game data.

## Target-machine rules

- Never automate enabling FireTuner, starting Civ V, or changing the firewall.
- Follow `docs/LIVE_TEST_CHECKLIST.md` with the user present.
- Capture the exact build/environment, action UUID, before/after evidence, and
  restored shutdown conditions.
- Update `LIVE_VERIFICATION_STATUS.zh-CN.md` only after the detailed experiment
  evidence has been recorded.
- Commit only sanitized conclusions, never raw player-specific snapshots or
  local paths that identify the user.

## Release gate

Before a release: run all CI targets, scan tracked content and artifacts for
secrets/local identifiers, validate documentation links, review open high-impact
risks, and ensure every claimed live capability has experiment-log evidence.
