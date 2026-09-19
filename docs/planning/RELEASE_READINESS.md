# Release Readiness

Status: Complete for 1.0.0, 1.1.0, and 1.2.0

Last reviewed: 2026-09-19

This document preserves the first stable-release evidence and records gates for
later compatible releases. It does not replace milestone definitions, the risk
register, contracts, or live experiment evidence.

## 1.2.0 worker-build release gate

| Gate | Current evidence | Remaining work |
|---|---|---|
| Required live verification | C6 passed on 2026-09-19: schema 7 candidate/UI agreement, read purity, stale-source pre-send rejection, one separately authorized active-build result, independent watcher agreement, private audit permission, no observed extra side effect, and exact host restoration | Preserve section 8 of the live checklist for regression use; immediate completion remains offline-only |
| High-impact risk | R-018 is mitigated and monitored after the bounded target-machine proof; earlier release dispositions remain in force | Reopen review if worker scope, eligible plots/builds, game build, or dispatch path changes |
| Public compatibility | Version 1.2.0 adds schema 7, two public worker limits, and `worker_build` through the existing aggregate API and unchanged schema 1 TurnPlan/CLI envelopes; the downstream profile preserves tactical ownership | Keep worker/plot/build selection, movement-to-plot, routes, repair, automation, and strategy outside this release |
| Tests and scans | 335 tests pass warning-enabled on Python 3.11 and the default runtime; documentation and tracked-content scans are clean; exact-commit and tag CI passed on Python 3.11/3.13 | Preserve the gates for later changes |
| Packaging | Two independent exact-commit 1.2.0 wheel and sdist builds had matching normalized contents; both formats installed and imported in separate clean Python 3.11 environments, and the supported CLI started | Preserve the artifact gate for later releases |
| Release | Immutable `v1.2.0` points to `6210a4e`; the GitHub Release contains exactly the inspected wheel and sdist, and downloaded assets match the recorded SHA-256 values | Never move the tag or replace its assets; use a new semantic version for changes |

The 1.2.0 release completed on 2026-09-19 after explicit operator authorization.
Future releases must repeat every gate rather than treating this evidence as a
blanket authorization.

## 1.1.0 movement release gate

| Gate | Current evidence | Remaining work |
|---|---|---|
| Required live verification | C6 passed on 2026-09-17: schema 6 target observation, source-coordinate pre-send rejection, one separately authorized exact adjacent move, private audit permission, and exact host restoration | Preserve section 7 of the live checklist for regression use |
| High-impact risk | R-017 is mitigated and monitored after the bounded target-machine proof; all earlier release dispositions remain in force | Reopen review if movement scope, game build, or dispatch path changes |
| Public compatibility | Version 1.1.0 adds schema 6 and `move_unit` through the existing stable aggregate API and unchanged schema 1 TurnPlan/CLI envelopes; the downstream profile preserves tactical ownership | Keep autonomous path choice, combat, worker tasks, and strategy outside this release |
| Tests and scans | 297 tests pass warning-enabled on Python 3.11 and the default runtime; documentation and tracked-content scans are clean; exact-commit and tag CI passed on Python 3.11/3.13 | Preserve the gates for later changes |
| Packaging | Two independent exact-commit 1.1.0 wheel and sdist builds had matching normalized content; both formats installed and imported in separate clean Python 3.11 environments, and the supported CLI started | Preserve the artifact gate for later releases |
| Release | Immutable `v1.1.0` points to `ad90dbd`; the GitHub Release contains exactly the inspected wheel and sdist, and downloaded assets match the recorded SHA-256 values | Never move the tag or replace its assets; use a new semantic version for changes |

The 1.1.0 release completed on 2026-09-17 after explicit operator authorization.
Future releases must repeat every gate rather than treating this evidence as a
blanket authorization.

## Gate status

| Gate | Current evidence | Remaining work |
|---|---|---|
| Required live verification | Complete: the final combined attempt added a successful command lifecycle and verified automatic turn advance to the earlier failure-path, integrity, replay, export, and restoration evidence | Preserve the [M8 release-gate procedure](../LIVE_TEST_CHECKLIST.md#6-m8-release-gate-combined-m5m6-verification) for regression use |
| High-impact risks | Every high-impact risk has an explicit release disposition; R-003, R-004, R-006, R-014, and R-016 are controlled within the documented scope | Preserve the controls and reopen review if release scope changes |
| Setup/security/recovery docs | README, security policy, reconciled live checklist, recoverable session manager, and release/upgrade/rollback runbook exist | Preserve these controls on the release candidate |
| Public compatibility | ADR-0030 promotes the aggregate Python API and bounded `civ5-turn` contract to stable 1.0; other CLIs remain provisional | Preserve the declared boundary on the exact release candidate |
| Downstream integration | ADR-0031 plus the stable 1.0 tactical integration profile define one-way dependency, ownership, capability discovery, known gaps, and strategy-neutral request intake | Keep consumer-specific policy and adapters out of release artifacts and core runtime |
| Packaging | The selected 1.0.0 wheel and sdist passed bounded inspection and separate clean Python 3.11 installation/import/CLI checks | Preserve the artifact gate for every later release |
| Tests and scans | 260 tests passed warning-enabled on Python 3.11/default runtime; exact-commit and tag GitHub Actions passed on 3.11/3.13; tracked-source and artifact scans were clean | Re-run all gates when source or release scope changes |
| Reproducibility | Two independent wheel builds and two sequential sdist builds had matching normalized content hashes; selected archive hashes are published | Preserve archive hashes and repeat the comparison for every release |
| Release | Immutable `v1.0.0` points to `676b029`; the GitHub release contains exactly the inspected wheel and sdist, and downloaded assets matched the published SHA-256 values | Never move the tag or replace its assets; use a new semantic version for changes |

## Completed live evidence

The required M8 live batch is deliberately narrow:

1. start one guarded watcher with a new private M5 journal;
2. observe at least one validated snapshot and one turn transition;
3. validate an operator-authored, explicit M6 TurnPlan against the same watcher;
4. execute only an already live-verified action, preferably a final
   `end_turn`, and require a completed execution report;
5. stop the game and watcher, restore the machine baseline, then verify the
   private journal and create a redacted structural export offline;
6. record only sanitized conclusions in the experiment log and verification
   matrix; never commit the journal, plan, report, export, audit log, or raw
   snapshot.

The first three 2026-09-16 attempts did not satisfy this gate. The first
exposed Lua truncation and a missing exception-path fact, fixed by ADR-0028. The second
proved compact marker delivery, complete deterministic-failure journaling, and
stale-plan refusal, but exposed an incorrect numeric zero-blocker assumption.
ADR-0029 now uses the game-defined enum and fail-closed requirement inspection.
The third proved that correction and actual stock control execution, but the
large saved match processed automated/deferred units and exposed a worker before
the turn could advance. The fourth attempt completed a newly authored one-action
plan, automatically advanced one turn, recorded the successful command result
and transition, and passed journal integrity, replay, export, permissions, and
exact host restoration. The required live gate is complete.

For any regression repeat, the operator must be present. Automation must not
enable FireTuner, change the firewall, start the game, or infer plan content. Exact private-path setup,
plan-authoring, single-execution, restoration, integrity, replay, export, and
permission checks are fixed in section 6 of the bounded live-test checklist.

## High-impact risk disposition

Before release, each high-impact risk needs one of these explicit outcomes:

- **controlled**: deterministic controls and sufficient evidence reduce the
  release risk while its underlying condition remains possible;
- **accepted**: the limitation is documented, bounded, and knowingly included
  in the release;
- **closed**: evidence shows the risk no longer applies to the released scope.

Mere implementation or an unchecked roadmap item is not a disposition.

The 2026-09-16 review in the risk register explicitly marks R-003, R-004,
R-006, R-014, and R-016 controlled for the first stable release and states the evidence
and scope limits. R-001, R-002, R-005, R-007, and R-013 were already controlled.
R-014's compact path passed the repeat live procedure; any scope change must
reopen the affected row.

## Artifact rules

- Build only from a clean tagged commit.
- Include source code, license, readme, and declared console scripts; exclude
  generated ruleset bundles, databases, journals, audit/recovery logs, plans,
  reports, caches, and machine-specific paths.
- Install-test artifacts in a clean environment on every supported Python
  version.
- Run documentation-link, forbidden-content, credential, private-address, and
  user-path scans on extracted artifact contents.
- Manually review public attribution and URLs for unintended real names or
  account identifiers; automated scans cannot reliably recognize arbitrary
  personal names. Intentional license attribution and repository ownership must
  be recorded as explicit public metadata.
- Record cryptographic hashes for published artifacts and retain the commands
  needed to reproduce them.

The current artifact check is:

```bash
python -m pip wheel --no-build-isolation --no-deps --wheel-dir dist .
python -c "from setuptools.build_meta import build_sdist; build_sdist('dist')"
python scripts/check_release_artifact.py dist/*.whl
python scripts/check_release_artifact.py dist/*.tar.gz
```

CI builds wheel and source artifacts twice and requires identical normalized
member/content hashes. It installs each artifact into a separate clean virtual
environment, imports the aggregate API, and starts the supported `civ5-turn`
entry point from the wheel. Compressed archive hashes are still recorded
separately because container timestamps may differ.

## Completion rule

M8 is complete only when every row above has evidence or an explicit accepted
exception, the exact release commit has passing CI, the worktree is clean, and
the version tag points to that commit. Passing tests alone is insufficient.
