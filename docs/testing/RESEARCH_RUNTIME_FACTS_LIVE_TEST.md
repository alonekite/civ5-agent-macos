# M11 Runtime Research Facts Live-Test Procedure

Status: Ready for repaired bounded rerun; partial target evidence recorded

Milestone: M11 C4

This procedure verifies schema 8 read behavior on the target Mac. It does not
authorize a core write action, debug mutation, save edit, tag, or release. The
operator performs any research selection and turn advancement manually in the
stock game UI.

## Evidence boundary

- Keep watcher output, temporary files, session identifiers, player names, and
  save-specific data outside the repository.
- Commit only a concise result in `docs/EXPERIMENT_LOG.md` and the verification
  ledgers. Do not commit a snapshot, audit file, save, local path, or screenshot.
- Offline tests and installed-source inspection are not target evidence.
- A partial run may close read-purity and UI-agreement rows while leaving the
  controlled overflow rows pending.

## 1. Preconditions

Before starting:

- use the exact development commit under test and record its short commit ID;
- quit Civilization V and stop every watcher;
- choose a normal single-player save with ordinary research, not a free-tech or
  steal-tech choice;
- do not manufacture an overflow case with a debug command or edited save;
- keep two terminals available in the repository root.

Run the guarded preparation command in terminal 1:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session prepare
```

Require `ok: true`, FireTuner enabled, the firewall enabled, and Civ V explicitly
blocked for incoming connections. Stop if preparation cannot prove every guard.

Start Civilization V manually, load the chosen match, wait for the ordinary
active-player action window, and run:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight live
```

Do not continue unless `ok` is `true` and TCP 4318 is listening.

## 2. Start the read-only watcher

In terminal 1, create a private temporary location and start the watcher:

```bash
umask 077
export CIV5_M11_ROOT="$(mktemp -d -t civ5-agent-m11.XXXXXX)"
export CIV5_M11_AUDIT="$CIV5_M11_ROOT/command-audit.jsonl"
PYTHONPATH=src python3 -m civ5_agent.watch \
  --audit-log "$CIV5_M11_AUDIT"
```

The first validated state must have `schema_version: 8`. Keep the raw JSON
private. The watcher must not select a technology, open a popup, select or move
a unit, change production or research, or advance the turn.

Keep the initial bridge-session identity private for the duration of the
controlled sequence. Record only whether it remained the same. A replacement
identity after framing recovery is valid for later independent reads but does
not establish continuity for this sequence.

In terminal 2, read a small summary from the watcher without contacting
FireTuner independently:

```bash
PYTHONPATH=src python3 - <<'PY'
import json

from civ5_agent.api import WatcherBridgeClient

_, state = WatcherBridgeClient().read_state()
facts = state.research_runtime_facts
current = facts["current"] if facts else None
print(json.dumps({
    "schema_version": state.schema_version,
    "turn": state.turn,
    "research_type": state.research["type"] if state.research else None,
    "status": facts["status"] if facts else None,
    "reason": facts["reason"] if facts else None,
    "phase": facts["phase"] if facts else None,
    "science_per_turn_times100": (
        facts["science_per_turn_times100"] if facts else None
    ),
    "overflow_research": facts["overflow_research"] if facts else None,
    "current": current,
    "candidate_count": len(facts["candidates"]) if facts else None,
    "runtime_context": state.runtime_context,
}, allow_nan=False, sort_keys=True))
PY
```

Require `status: supported`, no reason, and phase
`action_window_after_interturn_research_resolution`. Run the summary twice in
the same action window. Confirm in the game that repeated reads cause no visible
side effect and do not change the turn, current research, exact facts, or
runtime context.

## 3. Check units and UI agreement

Compare the supported summary with the stock UI in the same action window:

- `current.type` agrees with the selected ordinary technology;
- `current.cost` agrees with its effective whole-point cost;
- `current.progress_times100 / 100` agrees with displayed progress, allowing
  only a UI display-rounding difference rather than a core-value substitution;
- `science_per_turn_times100 / 100` agrees with displayed science per turn;
- `current.turns_left_with_overflow` agrees with the stock turns-left value;
- `overflow_research` is recorded as whole research points, not times-100;
- available runtime-context identifiers agree with the current game setup;
- unavailable or unsupported context dimensions remain explicit and null.

Stop on an unexplained mismatch. Do not alter the value in evidence to make it
agree with the UI.

## 4. Controlled overflow sequence

This section is required for complete C4 evidence but may remain pending when no
natural save or turn satisfies the precondition.

Use an action window where the exact pre-interturn values satisfy:

```text
remaining_times100 = current.cost * 100 - current.progress_times100
0 < remaining_times100
remaining_times100 + 100 <= science_per_turn_times100
```

The previously documented 20-remaining/22-produced case is one example, not a
required literal fixture. Requiring at least 100 times-100 units of surplus
ensures that the whole-point overflow observation is positive rather than
indistinguishable from zero. Record only the summarized exact values and compute
`surplus_times100 = science_per_turn_times100 - remaining_times100`. When the
surplus is not a whole research point, preserve the fractional remainder in the
evidence and compare it with the whole-point `GetOverflowResearch` result; do
not rewrite either observation to force agreement. Then:

1. manually end the turn in the stock UI;
2. wait for the next ordinary action-window snapshot;
   if the watcher rotates its bridge-session identity, stop this sequence and
   record the continuity row as failed rather than correlating mutable fields;
3. confirm the prior technology completed and `overflow_research` is the
   game's positive whole-point representation of the computed exact surplus,
   not the times-100 integer;
4. manually select the next ordinary technology in the stock UI;
5. confirm selection alone does not immediately apply or erase the overflow;
6. manually advance the following interturn and confirm the next snapshot
   reflects the game's application of that overflow.

No `civ5_agent.command`, TurnPlan, arbitrary Lua, debug write, or automatic
retry is allowed in this sequence. If the exact inequalities cannot be observed
immediately before completion, record the row as pending; do not infer overflow
units from a non-overflowing turn or from values captured in different action
windows.

## 5. Audit and shutdown

Before shutdown, verify that no command was written. In terminal 1, after the
watcher has stopped, use:

```bash
if test -e "$CIV5_M11_AUDIT"; then
  stat -f '%Lp' "$CIV5_M11_AUDIT"
  wc -l < "$CIV5_M11_AUDIT"
else
  echo "audit absent: no command record created"
fi
```

An existing audit must be mode `600` and contain zero records. Any command
record invalidates the read-only run.

Quit Civilization V. The watcher may close when FireTuner closes. Restore the
recorded host baseline:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session restore
```

Require `ok: true`, result `restored` or `already_restored`, FireTuner disabled,
the firewall and Civ V rule returned to their recorded baseline, no agent
socket, and no TCP 4318 listener. A failed restoration is an operational issue
and must be resolved before any further live work.

## 6. Sanitized evidence template

Add only a concise result to the governed evidence documents:

```text
Date and implementation commit:
Target game family/build label:
Preparation and live preflight: pass/fail
Schema 8 complete: pass/fail
Facts status and phase: supported/other; phase
Read purity and repeated-read stability: pass/fail
UI agreement (cost/progress/science/turns): pass/fail, with rounding note
Runtime-context available/unsupported dimensions: summarized
Controlled exact pre-completion overflow case: pass/fail/pending; summarized values
Bridge-session continuity across controlled sequence: preserved/rotated/pending
Selection-before-next-interturn behavior: pass/fail/pending
Audit records and permissions: zero/other; 600/not applicable/other
Host baseline restoration: pass/fail
Unresolved observations:
```

Do not include the temporary directory, bridge-session ID, player name, unit or
city IDs, complete snapshot, save filename, local IP address, or credentials.

## Stop conditions

Stop without claiming C4 completion if schema 8 is incomplete, facts are
unsupported or unavailable in an ordinary action window, exact units cannot be
reconciled, a read causes a gameplay side effect, a command appears in the
audit, FireTuner safety fails, or the original host baseline cannot be restored.
