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
- For sustained development, install and verify the one-time persistent guard
  according to `docs/operations/HOST_HARDENING.md`. When it is installed,
  `preflight hardened` must pass before session preparation.
- Run the recoverable preparation command from the host environment:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session prepare
```

Expected: `result` is `prepared` or `already_prepared`, `ok` is `true`, and the
embedded safety result proves FireTuner enabled, firewall enabled, and Civ V
blocked. The command records the per-session settings and rolls back if
readiness cannot be proved. Under persistent hardening it does not change the
firewall. Without hardening it retains the temporary compatibility path and may
request the administrator password for its narrow firewall subcommand.
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

This required target-machine gate passed on 2026-09-16 and is retained as the
regression procedure. It is separate from the schema regression above and is
deliberately limited to a private journal plus one explicit `end_turn`
TurnPlan. The operator must be present throughout. Do not run it from unattended
automation, and never commit any generated file.

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

Prefer a minimal early-game state with very few units and no automated or
deferred unit tasks. A large saved match can report no blocker before the stock
end-turn control processes automated movements, then expose a new unit order
without advancing. That is a valid failed action but cannot close this success
gate.

Start the watcher in this terminal and leave it running:

```bash
PYTHONPATH=src python3 -m civ5_agent.watch \
  --journal "$CIV5_LIVE_JOURNAL" --journal-mode new \
  --audit-log "$CIV5_LIVE_AUDIT"
```

Wait for the first validated snapshot. In the game UI, manually choose any
required research and production and finish every unit order until the stock UI
shows Next Turn. Do not let a script choose those actions. The button label is
not itself proof that the next click will advance: plan validation must also
observe the game-defined no-blocker value and no reported unit requirement.

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
private files and proceed directly to shutdown without manually ending the turn
or otherwise changing the live state, so the outcome can be analyzed without
risking a duplicate action or confounding the evidence.

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

## 7. M9 gate: one verified adjacent ordinary move

Status: ready for operator-assisted execution after the C1–C5 offline gate.
Do not run unattended. The user must be present and explicitly authorize the
write portion. This gate permits one rejected source-coordinate request and one
accepted adjacent move; it does not authorize exploration, combat, embarkation,
or retries.

### 7.1 Prepare a controlled state

Follow sections 1 and 2 exactly. Prefer a normal single-player save with one
idle land unit on open friendly terrain, no enemy or civilian on the intended
target, no city target, no automation, and no pending animation. Do not use an
irreplaceable or tactically important save.

Create a private temporary audit path outside the repository, start exactly one
watcher, and leave it running:

```bash
umask 077
export CIV5_MOVE_ROOT="$(mktemp -d -t civ5-agent-move.XXXXXX)"
export CIV5_MOVE_AUDIT="$CIV5_MOVE_ROOT/command-audit.jsonl"
PYTHONPATH=src python3 -m civ5_agent.watch --audit-log "$CIV5_MOVE_AUDIT"
```

Require a validated schema 6 snapshot. Select one non-air, non-embarked unit
whose `ordinary_move_targets` contains at least one coordinate. In a second
terminal, copy the temporary root only if needed and set these values from that
single snapshot; do not paste them into tracked files or an issue:

```bash
export CIV5_MOVE_UNIT='UNIT_ID'
export CIV5_MOVE_SOURCE_X='SOURCE_X'
export CIV5_MOVE_SOURCE_Y='SOURCE_Y'
export CIV5_MOVE_TARGET_X='TARGET_X'
export CIV5_MOVE_TARGET_Y='TARGET_Y'
```

Confirm manually that the chosen target is the intended adjacent empty plot.
Do not proceed if the unit or target changes, the UI opens a prompt, another
unit moves, or the watcher emits a new basis before the negative check.

### 7.2 Prove the bounded negative branch

Submit the unit's current source coordinate, which can never be an adjacent
target:

```bash
PYTHONPATH=src python3 -m civ5_agent.command move_unit \
  "$CIV5_MOVE_UNIT" "$CIV5_MOVE_SOURCE_X" "$CIV5_MOVE_SOURCE_Y"
```

Expected: nonzero exit and a bounded error stating that the destination is not
in the unit's current `ordinary_move_targets`. A subsequent watcher snapshot
must show the same unit at the same coordinates with unchanged movement. This
is a pre-send rejection; any movement, command acceptance, or unknown outcome
fails the gate and ends the write portion.

### 7.3 Execute exactly one authorized move

Reconfirm that a fresh schema 6 snapshot still lists the chosen target. Ask the
user for explicit confirmation immediately before this command, then execute it
once:

```bash
PYTHONPATH=src python3 -m civ5_agent.command move_unit \
  "$CIV5_MOVE_UNIT" "$CIV5_MOVE_TARGET_X" "$CIV5_MOVE_TARGET_Y"
```

Do not repeat the command, even if the terminal appears idle. Success requires
all of the following:

- the command returns `status: success` with one UUID;
- its before-state contains the selected unit at the source coordinate;
- its after-state contains the same unit ID and type at exactly the target;
- turn, active player, and active-turn status remain unchanged;
- movement points strictly decrease; and
- the game UI and a later independent watcher snapshot show that same unit on
  the target, with no combat, capture, swap, embark/disembark, prompt, or
  movement by another unit.

An error, timeout, disappearance, unexpected coordinate, unchanged/increased
movement, turn change, or mismatch between command and watcher evidence fails
the gate. If the outcome is unknown, preserve the private evidence, make no
further game action, and do not retry or move the unit manually.

TurnPlan integration is covered offline in the first M9 gate. A separate live
multi-action plan is not required for this one-write experiment because it
would add unrelated skip/end-turn writes to satisfy the complete-turn schema.

### 7.4 Restore and record

Quit Civilization V, allow or stop the watcher, and run `live_session restore`
as in section 5. Require the exact clean shutdown proof. Check locally that the
private audit file has mode `600`; never commit it.

Only after restoration, append a sanitized experiment conclusion and update the
verification matrix, Chinese status ledger, project state, and risk R-017. The
conclusion may state the schema, action, rejection/success classifications,
exact-postcondition result, audit permission, and restoration result. It must
not contain coordinates, unit IDs or names, command/session UUIDs, player/save
data, raw snapshots, audit content, hashes, or local paths.

## 8. M10 gate: one verified ordinary worker build

Status: frozen procedure; do not execute until C1–C5 pass on the exact
implementation commit. Do not run unattended. The operator must be present and
must separately authorize the sole live build. This gate permits one stale-
source rejection and one accepted candidate only. It does not authorize worker
movement, route/repair/feature clearing, improvement replacement, automation,
water or consuming builds, turn advancement, or retries.

### 8.1 Prepare a controlled worker state

Follow sections 1 and 2 exactly. Use a normal single-player save that can be
discarded. Choose one idle active-player worker already standing on blank,
featureless land with no improvement, no current build, movement remaining, no
automation, and no pending animation or popup. The intended stock worker action
must be visibly available. Do not use a tactically important save or plot.

Create one private audit path outside the repository, start exactly one watcher,
and leave it running:

```bash
umask 077
export CIV5_BUILD_ROOT="$(mktemp -d -t civ5-agent-build.XXXXXX)"
export CIV5_BUILD_AUDIT="$CIV5_BUILD_ROOT/command-audit.jsonl"
PYTHONPATH=src python3 -m civ5_agent.watch --audit-log "$CIV5_BUILD_AUDIT"
```

Require a validated schema 7 snapshot. The chosen unit must report the same
coordinates and current-plot facts as the visible game state,
`current_build_type: null`, and exactly one intended entry in
`ordinary_build_actions`. The entry's `build_type` must match the enabled stock
UI action and its paired `improvement_type` must describe the expected result.
Merely reading this state must not change selected unit, UI mode, movement,
plot, or any unit order.

In a second terminal, set these values from that one snapshot. They are private
match data and must not be pasted into tracked files, issues, or the experiment
log:

```bash
export CIV5_BUILD_UNIT='UNIT_ID'
export CIV5_BUILD_X='SOURCE_X'
export CIV5_BUILD_Y='SOURCE_Y'
export CIV5_BUILD_TYPE='BUILD_TYPE'
export CIV5_BUILD_IMPROVEMENT='IMPROVEMENT_TYPE'
if [ "$CIV5_BUILD_X" -lt 65535 ]; then
  export CIV5_BUILD_REJECT_X="$((CIV5_BUILD_X + 1))"
else
  export CIV5_BUILD_REJECT_X="$((CIV5_BUILD_X - 1))"
fi
```

Stop before any command if the UI and schema disagree, the candidate is no
longer listed, the unit/plot changes, a prompt appears, another action runs, or
the read changes selection. This read-only observation fails the gate but does
not authorize a diagnostic Lua probe.

### 8.2 Prove the safe pre-send rejection

After implementation, use the provisional operator command with the deliberately
wrong source `x` and the real `y`:

```bash
PYTHONPATH=src python3 -m civ5_agent.command worker_build \
  "$CIV5_BUILD_UNIT" "$CIV5_BUILD_REJECT_X" "$CIV5_BUILD_Y" \
  "$CIV5_BUILD_TYPE"
```

Expected: nonzero exit and a bounded stale-source error before any build-write
Lua is submitted. A later watcher snapshot and the game UI must show the same
unit, coordinates, movement, current build, and plot improvement. Selection
must not change as a result of this rejection. Any accepted marker, changed
state, or unknown outcome fails the gate and ends the write portion.

### 8.3 Execute exactly one authorized build

Require a fresh schema 7 snapshot that still lists the exact candidate and
matches all five private variables. Manually reconfirm the enabled stock action
and blank plot. Ask the user for explicit confirmation immediately before the
following command, then execute it exactly once:

```bash
PYTHONPATH=src python3 -m civ5_agent.command worker_build \
  "$CIV5_BUILD_UNIT" "$CIV5_BUILD_X" "$CIV5_BUILD_Y" \
  "$CIV5_BUILD_TYPE"
```

Do not repeat the command even if the terminal appears idle. Success requires
one command UUID and all common worker-build contract conditions: unchanged
session, turn, active player and active-turn status; the same unit ID/type at
the same coordinates; strictly lower movement; unchanged terrain, feature,
visible resource, route, ownership, hills, water, and fresh-water facts; and a
fresh independent watcher snapshot agreeing with the command result.

Exactly one result branch must then hold:

- **active build:** `current_build_type` equals `CIV5_BUILD_TYPE` and the plot
  still has no improvement; or
- **immediate completion:** `current_build_type` is `null` and the plot
  improvement equals `CIV5_BUILD_IMPROVEMENT`.

The game UI must agree with the observed branch. Exact unit selection is an
allowed submission side effect; movement, another unit's action, a popup,
alternative build, changed plot fact, or turn advancement is not. Do not end a
turn to finish an active build: the active branch is already the full live
proof. The other branch remains offline-tested and does not justify a second
live build.

An error, timeout, malformed result, mismatch, or transport loss fails C6. If
the outcome is unknown, preserve the private files, make no further game action,
do not retry, do not issue a new command UUID, and do not change the plot
manually.

TurnPlan ordering, alternate success branch, timeout, duplicate UUID, and
recovery behavior remain offline-only. Adding them to this session would create
unnecessary writes or deliberate uncertainty.

### 8.4 Restore and record

Quit Civilization V without advancing the turn. Allow the watcher to close or
stop it, then run `live_session restore` as in section 5. Require the exact clean
shutdown proof before inspecting artifacts. Check only private structure:

```bash
stat -f '%Lp' "$CIV5_BUILD_AUDIT"
wc -l < "$CIV5_BUILD_AUDIT"
```

The audit file must be mode `600` and contain exactly the two attempted command
records: one rejected and one terminal live result. Inspect them locally only
if needed to confirm the action and classification; never copy their payloads.

Only after restoration, append a sanitized experiment conclusion and update the
verification matrix, Chinese status ledger, project state, and R-018. Record
the exact implementation commit, schema, read-without-selection result,
pre-send rejection classification, which one success branch was observed,
independent watcher agreement, audit permission/count, and restoration result.
Do not record unit/player names, IDs, coordinates, build UUIDs, command/session
UUIDs, save data, raw snapshots, audit content, hashes, or local paths.
