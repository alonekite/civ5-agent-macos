# M8 Release Readiness

Status: In progress

Last reviewed: 2026-09-16

This document is the release-gate checklist for the first stable release. It
does not replace milestone definitions, the risk register, contracts, or live
experiment evidence.

## Gate status

| Gate | Current evidence | Remaining work |
|---|---|---|
| Required live verification | M1/M2 bridge reads and four allowlisted actions are live-verified | Run one bounded M5 capture/verify/export and one M6 TurnPlan validate/execute session |
| High-impact risks | Safety, single-owner transport, and write read-back controls are implemented | Explicitly close or accept R-003, R-004, and R-006 using current evidence |
| Setup/security/recovery docs | README, security policy, live checklist, and recoverable session manager exist | Reconcile the checklist with the combined M5/M6 run and add release rollback instructions |
| Public compatibility | M7 aggregate Python API and bounded `civ5-turn` contract are complete | Add upgrade notes for the first stable version and confirm version metadata |
| Packaging | Editable installation and console scripts pass CI; wheel and sdist manifests, bounded inspection, and clean-environment install checks are implemented | Confirm final version/license metadata on the release candidate |
| Tests and scans | 254 tests pass on Python 3.11/3.13/default runtime; tracked-source scans are clean; artifact inspection checks source coverage, metadata, entry points, RECORD integrity, unsafe members, paths, private addresses, and common credentials | Run the final warning-enabled suite and scans against the exact tagged release artifacts |
| Reproducibility | CI builds each artifact twice and requires identical normalized content hashes | Define tag/version rules, publish archive hashes, and document that container timestamps may make compressed bytes differ despite identical contents |
| Release | No release tag exists | Complete every blocking gate, update changelog, tag, and verify rollback from the tagged source |

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
firewall, start the game, or infer plan content. Exact commands and restoration
checks belong in the bounded live-test checklist before this gate is run.

## High-impact risk disposition

Before release, each open high-impact risk needs one of these explicit outcomes:

- **controlled**: deterministic controls and sufficient evidence reduce the
  release risk while its underlying condition remains possible;
- **accepted**: the limitation is documented, bounded, and knowingly included
  in the release;
- **closed**: evidence shows the risk no longer applies to the released scope.

Mere implementation or an unchecked roadmap item is not a disposition.

## Artifact rules to implement

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
