# Bounded live-test checklist

Use this checklist only on the target Mac with the original App Store
Civilization V: Campaign Edition. The completed 2026-09-14 session used this
procedure for two goals:

1. verify snapshot schema 4 against a live match;
2. verify one `skip_unit` action without moving the unit.

The completed 2026-09-15 bounded session added a third read-only goal: verify
schema 5 ordinary technology state. Keep the procedure below as a regression
check. Free and steal-technology modes remain outside it unless they occur
naturally; do not alter a save to manufacture them.

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

## 3. Verify schema 5 ordinary technology state

Start the persistent watcher and leave it running:

```bash
PYTHONPATH=src python3 -m civ5_agent.watch
```

The first validated JSON snapshot must have `schema_version: 5`. First use a
normal game state in which the stock UI requires an ordinary research choice
and no free or stolen technology is pending. Check:

- `researched_technologies` is sorted, contains only `TECH_*` identifiers, has
  no duplicates, and agrees with at least one known researched technology in
  the stock technology tree;
- `researchable_technologies` is sorted, contains only `TECH_*` identifiers,
  has no duplicates, and agrees with the ordinary choices shown by the stock
  technology popup;
- no identifier appears in both technology lists;
- `research_choice` is `{"required": true, "mode": "normal"}` while the
  ordinary choice is pending;
- the same required choice remains observable when production or unit orders
  temporarily take precedence in the game's single end-turn blocker;
- after manually selecting one ordinary technology in the game UI, a later
  snapshot reports `required: false`, retains `mode: normal`, and exposes that
  technology through the existing `research` record.

Then check the inherited schema 4 fields:

- `score` and `current_era` are non-negative integers;
- every city has the six `food_*` / `production_*` economy fields;
- every owned unit has `damage`, `max_hit_points`, both strength fields, and
  `range`, plus boolean `ready_to_move`;
- `diplomacy` is empty in an unmet early game or contains only met major
  civilizations;
- `victory.science_enabled` is boolean and all five project counts are
  integers at least `-1`.

Any missing marker, malformed value, duplicate record, inconsistent part
turn/player identity, or Lua error is a failed schema 5 test. Record only a
sanitized conclusion in the experiment log; do not commit exact watcher output,
player names, or save-specific data.

Do not invoke `choose_research` in this read-only verification. The existing
write path has separate live evidence; this session verifies authoritative
state and choice-mode reads.

## 4. Optional regression: verify `skip_unit`

Run this only when explicitly included in the session. Choose one ready unit
from the snapshot and record its ID, coordinates, and
movement points. In a second terminal run:

```bash
PYTHONPATH=src python3 -m civ5_agent.command skip_unit UNIT_ID
```

Success requires all of the following in the returned JSON:

- `status` is `success`;
- before and after contain the same unit ID;
- `x` and `y` are unchanged;
- `ready_to_move` changes from `true` to `false`;
- movement remains unchanged;
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

Record the schema fields observed and every restored shutdown condition in
`docs/EXPERIMENT_LOG.md`; record a command UUID and before/after proof only if
the optional write regression ran. Then update
`docs/testing/LIVE_VERIFICATION_STATUS.zh-CN.md` and
`docs/testing/TEST_MATRIX.md` with the sanitized result.

## 6. M8 release gate: combined M5/M6 verification

This is the next required target-machine session. It is separate from the
schema regression above and is deliberately limited to a private journal plus
one explicit `end_turn` TurnPlan. The operator must be present throughout. Do
not run it from unattended automation, and never commit any generated file.

### 6.1 Create private paths

From the repository root, create one private temporary directory. Keep the
same terminal open for the whole session:

```bash
umask 077
export CIV5_LIVE_ROOT="$(mktemp -d -t civ5-agent-live.XXXXXX)"
export CIV5_LIVE_JOURNAL="$CIV5_LIVE_ROOT/match.journal.jsonl"
export CIV5_LIVE_AUDIT="$CIV5_LIVE_ROOT/command-audit.jsonl"
export CIV5_LIVE_PLAN="$CIV5_LIVE_ROOT/end-turn-plan.json"
export CIV5_LIVE_EXPORT="$CIV5_LIVE_ROOT/journal-structure.json"
```

Confirm that `CIV5_LIVE_ROOT` is non-empty and is outside the repository. Do
not print or copy its contents into an issue, chat, or tracked file.

### 6.2 Establish the guarded live session

Follow sections 1 and 2 exactly: quit the game first, run `live_session
prepare`, start the game manually, enter a normal single-player match, and
require a passing `preflight live` result.

Start the watcher in this terminal and leave it running:

```bash
PYTHONPATH=src python3 -m civ5_agent.watch \
  --journal "$CIV5_LIVE_JOURNAL" --journal-mode new \
  --audit-log "$CIV5_LIVE_AUDIT"
```

Wait for the first validated snapshot. In the game UI, manually choose any
required research and production and finish every unit order until the stock UI
allows the turn to end. Do not let a script choose those actions.

### 6.3 Author and validate one explicit plan

In a second terminal, copy only the value of `CIV5_LIVE_ROOT` from the first
terminal, export it, and derive the other four paths with the same commands
from section 6.1. Copying this temporary directory name does not expose its
contents. Then run this bounded plan-authoring snippet. It refuses to create a
plan unless the current state has no reported turn requirement. It chooses no
action: the sole action is explicitly fixed here as the already live-verified
`end_turn` command.

```bash
PYTHONPATH=src python3 - "$CIV5_LIVE_PLAN" <<'PY'
from dataclasses import asdict
import json
from pathlib import Path
import sys
import uuid

from civ5_agent.api import (
    PlannedAction,
    WatcherBridgeClient,
    inspect_turn_requirements,
    make_turn_plan,
)

destination = Path(sys.argv[1])
session_id, state = WatcherBridgeClient().read_state()
requirements = inspect_turn_requirements(state)
if requirements:
    kinds = ",".join(requirement.kind for requirement in requirements)
    raise SystemExit(f"turn is not ready; requirements={kinds}")
plan = make_turn_plan(
    state,
    session_id,
    (PlannedAction(str(uuid.uuid4()), "end_turn", {}),),
)
with destination.open("x", encoding="utf-8") as target:
    json.dump(asdict(plan), target, allow_nan=False, sort_keys=True)
    target.write("\n")
destination.chmod(0o600)
print(json.dumps({"ok": True, "action_count": 1}, sort_keys=True))
PY

PYTHONPATH=src python3 -m civ5_agent.turn_cli validate "$CIV5_LIVE_PLAN"
```

The authoring command and validation must both exit 0. If requirements remain,
resolve them manually in the game and create a new plan at a new private path;
never modify a previously created plan. If validation reports a stale state,
discard that plan and stop to understand what changed before deciding whether
to author another one.

### 6.4 Execute once and observe the transition

Execute the validated plan exactly once:

```bash
PYTHONPATH=src python3 -m civ5_agent.turn_cli execute "$CIV5_LIVE_PLAN"
```

Success requires exit 0, `ok: true`, report status `completed`, exactly one
successful `end_turn` step, and an observed turn advance in both the game and
watcher. If the command exits 1 or 2, times out, or reports
`recovery_required`, do not retry or create another write command. Preserve the
private files and proceed directly to shutdown so the outcome can be analyzed
without risking a duplicate action.

### 6.5 Restore first, then verify journal artifacts offline

Quit Civilization V, stop the watcher with Ctrl-C, and run `live_session
restore` as in section 5. Require a clean restored shutdown proof before doing
anything else. Then run:

```bash
PYTHONPATH=src python3 -m civ5_agent.journal_cli verify "$CIV5_LIVE_JOURNAL"

PYTHONPATH=src python3 - "$CIV5_LIVE_JOURNAL" <<'PY'
from collections import Counter
from pathlib import Path
import json
import sys

from civ5_agent.api import replay_journal

events = replay_journal(Path(sys.argv[1]))
sequences = [event.sequence for event in events]
if sequences != list(range(len(events))):
    raise SystemExit("replay sequence is not contiguous")
print(json.dumps({
    "ok": True,
    "event_count": len(events),
    "kind_counts": dict(sorted(Counter(event.kind for event in events).items())),
}, sort_keys=True))
PY

PYTHONPATH=src python3 -m civ5_agent.journal_cli export \
  "$CIV5_LIVE_JOURNAL" "$CIV5_LIVE_EXPORT"
stat -f '%Lp %N' "$CIV5_LIVE_JOURNAL" "$CIV5_LIVE_PLAN" "$CIV5_LIVE_EXPORT"
```

Verification succeeds only if the full hash chain is valid, replay order is
contiguous, the journal contains validated snapshots plus the command lifecycle
and observed turn transition, the export reports the same structural counts,
and all three files have mode `600`. The replay check intentionally prints only
counts; do not run the payload-emitting replay CLI during this release gate.

Append only a sanitized conclusion to the experiment log, live-status ledger,
and verification matrix. Record the action kind, completion status, turn
advance, event kinds/counts, integrity result, permissions, and clean restore;
do not record paths, UUIDs, hashes, snapshots, player data, or exact match
state. Retain or delete the temporary directory manually after the conclusion
is recorded; project automation must not remove private evidence.
