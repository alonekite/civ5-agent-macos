# M8 Release Readiness

Status: In progress

Last reviewed: 2026-09-16

This document is the release-gate checklist for the first stable release. It
does not replace milestone definitions, the risk register, contracts, or live
experiment evidence.

## Gate status

| Gate | Current evidence | Remaining work |
|---|---|---|
| Required live verification | M1/M2 bridge reads and four allowlisted actions are live-verified; the combined M5/M6 procedure is documented | Run the operator-present [M8 release-gate procedure](../LIVE_TEST_CHECKLIST.md#6-m8-release-gate-combined-m5m6-verification) |
| High-impact risks | Every high-impact risk has an explicit release disposition; R-003, R-004, and R-006 are controlled within the documented scope | Preserve the controls and reopen review if release scope changes |
| Setup/security/recovery docs | README, security policy, live checklist, recoverable session manager, and release/upgrade/rollback runbook exist | Reconcile the live checklist with the completed combined M5/M6 run |
| Public compatibility | M7 aggregate Python API and bounded `civ5-turn` contract are complete; stable-version transition steps are documented | Apply the stable version and compatibility wording on the final release commit |
| Packaging | Editable installation and console scripts pass CI; wheel and sdist manifests, bounded inspection, and clean-environment install checks are implemented | Confirm final version/license metadata on the release candidate |
| Tests and scans | 254 tests pass on Python 3.11/3.13/default runtime; tracked-source scans are clean; artifact inspection checks source coverage, metadata, entry points, RECORD integrity, unsafe members, paths, private addresses, and common credentials | Run the final warning-enabled suite and scans against the exact tagged release artifacts |
| Reproducibility | CI builds each artifact twice and requires identical normalized content hashes; tag/version/hash rules are documented | Execute the runbook on the final candidate and publish selected archive hashes |
| Release | No release tag exists; immutable annotated-tag, publication-verification, withdrawal, and rollback procedures are documented | Complete every blocking gate, update the changelog/version, and execute the runbook |

## Blocking live evidence

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

The operator must be present. Automation must not enable FireTuner, change the
firewall, start the game, or infer plan content. Exact private-path setup,
plan-authoring, single-execution, restoration, integrity, replay, export, and
permission checks are fixed in section 6 of the bounded live-test checklist.

## High-impact risk disposition

Before release, each open high-impact risk needs one of these explicit outcomes:

- **controlled**: deterministic controls and sufficient evidence reduce the
  release risk while its underlying condition remains possible;
- **accepted**: the limitation is documented, bounded, and knowingly included
  in the release;
- **closed**: evidence shows the risk no longer applies to the released scope.

Mere implementation or an unchecked roadmap item is not a disposition.

The 2026-09-16 review in the risk register explicitly marks R-003, R-004, and
R-006 controlled for the first stable release and states the evidence and scope
limits. R-001, R-002, R-005, R-007, and R-013 were already controlled. No
high-impact risk remains open; any scope change must reopen the affected row.

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
python -m pip wheel --no-deps --wheel-dir dist .
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
