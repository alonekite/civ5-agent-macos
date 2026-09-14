# Bounded live-test checklist

Use this checklist only on the target Mac with the original App Store
Civilization V: Campaign Edition. The next session has two goals:

1. verify snapshot schema 3 against a live match;
2. verify one `skip_unit` action without moving the unit.

Do not enable FireTuner until the firewall guard is in place.

## 1. Prepare the bounded session

- Quit Civilization V and stop any watcher.
- Run the recoverable preparation command from the host environment:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session prepare
```

Expected: `result` is `prepared` or `already_prepared`, `ok` is `true`, and the
embedded safety result proves FireTuner enabled, firewall enabled, and Civ V
blocked. The command records the original settings and rolls back if readiness
cannot be proved. On macOS, enter the administrator password in the terminal if
`sudo` requests it; only the firewall subcommand is elevated.
If `sudo -v` was run separately, run `prepare` in that same terminal because
macOS may scope the authorization ticket to the terminal session.

Do not run this through a sandbox that hides the host firewall state. The
manual firewall plus `configure_firetuner.sh` sequence is an emergency fallback,
not the normal path.

## 2. Start the bounded game session

- Start Civilization V manually.
- Load or create a normal single-player match.
- Ensure at least one owned unit still has movement points.
- Close optional research/production prompts with Esc if necessary.
- Verify the live listener and all guards:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight live
```

Do not continue unless `ok` is `true`.

## 3. Verify schema 3

Start the persistent watcher and leave it running:

```bash
PYTHONPATH=src python3 -m civ5_agent.watch
```

The first validated JSON snapshot must have `schema_version: 3`. Check:

- `score` and `current_era` are non-negative integers;
- every city has the six `food_*` / `production_*` economy fields;
- every owned unit has `damage`, `max_hit_points`, both strength fields, and
  `range`;
- `diplomacy` is empty in an unmet early game or contains only met major
  civilizations;
- `victory.science_enabled` is boolean and all five project counts are
  integers at least `-1`.

Any missing marker, malformed value, duplicate record, or Lua error is a failed
schema 3 test. Preserve the exact watcher output in the experiment log, but do
not commit player names or save-specific data.

## 4. Verify `skip_unit`

Choose one ready unit from the snapshot and record its ID, coordinates, and
movement points. In a second terminal run:

```bash
PYTHONPATH=src python3 -m civ5_agent.command skip_unit UNIT_ID
```

Success requires all of the following in the returned JSON:

- `status` is `success`;
- before and after contain the same unit ID;
- `x` and `y` are unchanged;
- movement changes from a positive value to zero;
- the result has a command UUID and appears once in the private audit log.

If the game rejects the action or read-back cannot prove every condition, keep
the command marked failed. Do not retry automatically.

## 5. Restore the machine

1. Quit Civilization V.
2. Stop the watcher with Ctrl-C.
3. Restore every recorded setting:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session restore
```

4. Confirm `result` is `restored` or `already_restored`, `ok` is `true`, and
   the shutdown proof is clean. The command removes its private recovery files
   only after the original firewall and Civ V rule states are verified.

Record the command UUID, before/after proof, schema fields observed, and every
restored shutdown condition in `docs/EXPERIMENT_LOG.md`. Then update
`docs/testing/LIVE_VERIFICATION_STATUS.zh-CN.md` and
`docs/testing/TEST_MATRIX.md` with the sanitized result.
