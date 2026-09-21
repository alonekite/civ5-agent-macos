# Runtime Research Facts Development Plan

Status: C1–C4 complete; D2/C5 release gate pending

Target milestone: M11

Compatible release: 1.3.0

## Objective

Add the strategy-neutral schema 8 facts defined by the
[research-runtime-facts contract](../contracts/research-runtime-facts.md). The first slice
is ordinary research only and introduces no write action.

## Delivery sequence

### D0 — Normalize the capability request

Status: complete.

- Preserve the downstream need as runtime facts rather than tactical advice.
- Reject a fabricated complete ruleset fingerprint.
- Keep free technology, stolen technology, recent-completion inference, and
  write behavior outside the first slice.

### D1 — Freeze fields and provenance

Status: complete under ADR-0035, with public naming superseded by ADR-0036 and
the target research-progress binding corrected by ADR-0037.

- Freeze exact names, units, null/unsupported behavior, phase, provenance, and
  runtime-context semantics.
- Require downstream KnowledgeBundle binding for any complete fingerprint.

### C1 — Implement schema 8 collection and parsing

Status: complete offline and target-verified through the aggregate schema 8 state.

- Add independently bounded, read-only research and runtime-context segments.
- Preserve schemas 2–7 unchanged.
- Reject malformed, duplicate, mismatched-turn/player, and incomplete parts.

### C2 — Implement validation and public discovery

Status: complete offline.

- Validate the complete nested shapes, units, identifiers, candidate equality,
  stable order, source labels, and fail-closed unsupported states.
- Export capability/context versions and limits from `civ5_agent.api`.
- Update public and downstream compatibility profiles.

### C3 — Complete the offline gate

Status: complete offline; the full suite and artifact gate pass.

- Add the negative and compatibility matrix required by the owning contract.
- Preserve authoritative core facts when downstream KnowledgeBundle binding is
  absent or conflicting; fail closed only for exact/forecast-dependent paths.
- Confirm deterministic state serialization and unchanged state digests.
- Measure every generated Lua program below 1,000 UTF-8 bytes and responses
  below the existing protocol limit.
- Run the complete suite and release-artifact checks.

### C4 — Bounded target-machine verification

Status: complete on target commit `95ef3df`.

- Prove schema 8 reads without selection, popup, movement, write, or turn
  advancement.
- Confirm exact source units and UI agreement.
- Run the controlled overflow/interturn sequence if a suitable save can be
  prepared without debug writes.
- Record only summarized evidence; never commit the real snapshot or save.
- Restore the FireTuner/firewall baseline exactly.
- Require bridge-session continuity for the controlled sequence; a recovered
  replacement connection is useful diagnostics but not inferred match
  continuity.
- Preserve one bridge session across both interturns; the repaired run retained
  the same private identity through completion, selection, and later overflow
  application.

See the [operator procedure and evidence template](../testing/RESEARCH_RUNTIME_FACTS_LIVE_TEST.md).

### D2/C5 — Release 1.3.0

Status: pending.

- Update contracts, capability profile, matrix, changelog, project state, and
  development log.
- Scan tracked and built artifacts for secrets, user paths, IP addresses, and
  private match data.
- Tag only after exact-commit CI, reproducible artifacts, clean-install checks,
  and required target evidence pass.

## Stop conditions

Stop and keep the capability unsupported if any exact binding is absent,
overflow units cannot be established, action-window phase cannot be observed
coherently, a generated read exceeds its bound, or the context shape would need
an invented identifier. No consumer-side FireTuner fallback is permitted.
