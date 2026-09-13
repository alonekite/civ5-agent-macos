# Bounded live-test checklist

Use this checklist only on the target Mac with the original App Store
Civilization V: Campaign Edition. The next session has two goals:

1. verify snapshot schema 3 against a live match;
2. verify one `skip_unit` action without moving the unit.

Do not enable FireTuner until the firewall guard is in place.

## 1. Record the starting state

- Quit Civilization V and stop any watcher.
- Record whether the macOS application firewall was originally on or off.
- Confirm the previous transport is closed:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight shutdown
```

Expected: `ok` is `true`, FireTuner is disabled, TCP 4318 is not listening,
and the agent socket is absent.

## 2. Establish the firewall guard

- In System Settings, turn on the macOS application firewall.
- Add Civilization V: Campaign Edition to Firewall Options if needed.
- Set the Civ V entry to **Block incoming connections**.
- Enable FireTuner only after those two settings are visible:

```bash
bash scripts/configure_firetuner.sh enable
PYTHONPATH=src python3 -m civ5_agent.preflight ready
```

Both commands fail closed if the firewall or explicit Civ V rule cannot be
proved.

## 3. Start the bounded game session

- Start Civilization V manually.
- Load or create a normal single-player match.
- Ensure at least one owned unit still has movement points.
- Close optional research/production prompts with Esc if necessary.
- Verify the live listener and all guards:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight live
```

Do not continue unless `ok` is `true`.

## 4. Verify schema 3

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

## 5. Verify `skip_unit`

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

## 6. Restore the machine

1. Quit Civilization V.
2. Stop the watcher with Ctrl-C.
3. Restore the original game configuration:

```bash
bash scripts/configure_firetuner.sh restore
PYTHONPATH=src python3 -m civ5_agent.preflight shutdown
```

4. Remove the temporary Civ V firewall rule if it did not exist originally.
5. Restore the firewall to the recorded starting state.
6. Re-run `preflight shutdown`; it must remain successful.

Record the command UUID, before/after proof, schema fields observed, and every
restored shutdown condition in `docs/EXPERIMENT_LOG.md`.
