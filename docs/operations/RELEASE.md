# Release, Upgrade, and Rollback

This runbook governs stable source and artifact releases. It does not authorize
an unattended release: the operator chooses the version, reviews the exact
commit, and explicitly creates and pushes the tag.

## Version policy

- Stable versions use `MAJOR.MINOR.PATCH`; Git tags use the matching
  `vMAJOR.MINOR.PATCH` form.
- `src/civ5_agent/__init__.py` and `pyproject.toml` are the two declared version
  locations. `tests/test_release_artifact.py` requires exact equality, and the
  wheel/sdist inspector requires artifact metadata and filenames to match.
- Increment MAJOR for incompatible supported API, schema, or `civ5-turn`
  changes; MINOR for backward-compatible public capability; PATCH for
  backward-compatible fixes. Provisional CLIs do not by themselves determine
  the increment, but their safety and privacy guarantees remain mandatory.
- Tags are annotated, immutable, and never reused. A faulty release is
  superseded by a new patch version rather than moving or deleting its tag.
- The first stable release candidate is version `1.0.0`. Do not create
  `v1.0.0` until its exact commit passes every M8 gate and the operator
  explicitly approves the tag.

## Release prerequisites

Before preparing the release commit, require all of the following:

1. the M5/M6 target-machine gate is recorded as passed in the experiment log
   and verification matrix, including a clean machine restore;
2. every high-impact risk has an explicit controlled, accepted, or closed
   disposition in the risk register;
3. `main` is clean, synchronized with `origin/main`, and contains no generated
   datasets, journals, plans, reports, audit/recovery files, or match data;
4. the changelog describes the stable compatibility surface and any known
   limitations;
5. local warning-enabled tests and artifact checks pass on supported runtimes;
6. GitHub Actions passes for the exact release commit.

Release work must not enable FireTuner, start Civilization V, or alter firewall
state. If a live session is open, finish `live_session restore` and prove
shutdown before continuing.

## Prepare the release commit

Choose the version explicitly, then update both version locations, move the
relevant changelog entries from `Unreleased` into a dated version section, and
replace remaining “pre-1.0” compatibility language where the stable contract
now applies. Do not broaden provisional interfaces merely to remove that label.

Review before committing:

```bash
version=1.0.0
test "$(PYTHONPATH=src python3 -c 'import civ5_agent; print(civ5_agent.__version__)')" = "$version"
PYTHONPATH=src PYTHONWARNINGS=error python3.11 -m unittest discover -s tests
PYTHONPATH=src PYTHONWARNINGS=error python3 -m unittest discover -s tests
git diff --check
git status --short
```

The release commit should contain only reviewed source and documentation. Push
it to `main` without a tag and wait for the Python 3.11 and 3.13 GitHub Actions
jobs to finish successfully. Record its full commit ID; all later commands must
refer to that exact commit.

## Build and inspect the exact release artifacts

Start from a clean checkout of the recorded release commit. Build into two
private temporary directories so repository state cannot influence artifact
selection:

```bash
umask 077
release_one="$(mktemp -d -t civ5-agent-release-one)"
release_two="$(mktemp -d -t civ5-agent-release-two)"

python3.11 -m pip wheel --no-deps --wheel-dir "$release_one" .
python3.11 -c "from setuptools.build_meta import build_sdist; build_sdist('$release_one')"
python3.11 -m pip wheel --no-deps --wheel-dir "$release_two" .
python3.11 -c "from setuptools.build_meta import build_sdist; build_sdist('$release_two')"

python3.11 scripts/check_release_artifact.py \
  "$release_one"/*.whl "$release_two"/*.whl
python3.11 scripts/check_release_artifact.py \
  "$release_one"/*.tar.gz "$release_two"/*.tar.gz
shasum -a 256 "$release_one"/*
```

The inspector must report equal normalized content hashes for the two wheels
and for the two source archives. Compressed-file hashes are release identifiers,
not the reproducibility test, because archive container timestamps may differ.

Install each artifact independently before tagging:

```bash
wheel_venv="$(mktemp -d -t civ5-agent-wheel-venv)"
sdist_venv="$(mktemp -d -t civ5-agent-sdist-venv)"
python3.11 -m venv "$wheel_venv"
python3.11 -m venv "$sdist_venv"
"$wheel_venv/bin/pip" install --no-deps --no-index "$release_one"/*.whl
"$sdist_venv/bin/pip" install --no-deps "$release_one"/*.tar.gz
"$wheel_venv/bin/python" -c 'import civ5_agent.api'
"$sdist_venv/bin/python" -c 'import civ5_agent.api'
"$wheel_venv/bin/civ5-turn" --help
```

Do not publish either build directory. Select only the inspected first wheel
and source archive as release assets and record their SHA-256 hashes in the
release notes.

## Tag and publish

After the exact release commit passes CI and the two selected artifacts pass
inspection and clean installation:

```bash
version=1.0.0
release_commit="$(git rev-parse HEAD)"
test -z "$(git status --porcelain)"
test "$(git rev-parse origin/main)" = "$release_commit"
git tag -a "v$version" "$release_commit" -m "civ5-agent-macos $version"
test "$(git rev-parse "v$version^{}")" = "$release_commit"
git push origin "v$version"
```

The tag push runs CI again. Publish a GitHub release only after that tag run
passes. Attach exactly the inspected wheel and source archive, include their
hashes, link the changelog and security guidance, and state the target game and
macOS scope. Download the published assets into a new private directory and
recompute hashes; publication is complete only when they match.

## Upgrade from a development checkout or earlier release

1. Quit the game and watcher. If FireTuner was prepared, run
   `live_session restore` and require a clean shutdown proof.
2. Keep journals, generated knowledge bundles, audit logs, and recovery files
   private and outside the repository. Back up any journal that matters before
   changing environments.
3. Verify the downloaded artifact hash against the release notes.
4. Install into a new virtual environment rather than overwriting the working
   development environment.
5. Confirm `civ5_agent.__version__`, import `civ5_agent.api`, and run
   `civ5-turn --help` before using live operations.
6. Read schema and CLI compatibility notes. Never rewrite an existing journal
   or knowledge bundle merely to upgrade; retain the original file and create a
   new derived artifact only through an explicitly supported operation.

There is no automatic game-data migration in the first stable release. Live
session recovery state belongs to the host safety procedure, not package
installation, and must never be copied between machines.

## Rollback and withdrawal

Package rollback and machine restoration are separate:

- To restore machine safety after any live failure, quit the game and watcher,
  run `live_session restore`, and require `preflight shutdown` to pass. Changing
  Python versions cannot substitute for this step.
- To roll back code, create a new virtual environment from the previously
  trusted tagged artifact and verify its published hash. Do not install over an
  environment whose state is uncertain.
- Treat journals and generated knowledge as immutable inputs. Older code may
  reject a newer schema; rejection is safer than conversion or truncation.
- If a release artifact is wrong, mark the GitHub release as withdrawn and
  explain the affected hashes. Do not replace an asset under the same version,
  move the tag, or force-push history. Correct the issue on `main`, issue a new
  patch version, and preserve the original evidence.
- If the release introduced a security exposure, use a private GitHub security
  advisory until disclosure is safe; do not publish private host or match data.

Rollback is successful only when the selected tagged package imports, its
supported offline checks pass, private data remains unchanged, and—if a live
session was involved—the target Mac has a clean shutdown proof.
