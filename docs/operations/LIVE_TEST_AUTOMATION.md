# Live-test automation operations

The provisional live-test supervisor automates process and evidence plumbing;
it does not automate Civilization V menus or gameplay.

## Start

Quit Civ V and any watcher, then use a host terminal:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_testing start \
  --profile m11-research-runtime-c4
```

Keep this foreground process running. Enter an administrator password yourself
if `sudo` requests it for the firewall guard. The tool never accepts a password
argument. After Civ V opens, load the intended save manually and reach an
ordinary active-player action window.

Use other terminals for control commands:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_testing status
PYTHONPATH=src python3 -m civ5_agent.live_testing checkpoint live_state
PYTHONPATH=src python3 -m civ5_agent.live_testing checkpoint repeated_read
```

For UI-only comparison, Codex may inspect the screen and record its result; if
that is unavailable or ambiguous, the user records the decision:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_testing confirm ui_agreement \
  --result pass --source user --note "stock UI values agree"
```

Notes are length-bounded, are not echoed or persisted, and must remain generic.
Do not enter save names, player names, paths, credentials, or complete snapshot
content. Only the confirmation source and whether a note was supplied are kept.

## M11 sequence

Run `live_state`, `repeated_read`, and `ui_agreement` in one ordinary action
window. For the overflow branch, wait naturally for a state satisfying:

```text
remaining_times100 = cost * 100 - progress_times100
0 < remaining_times100
remaining_times100 + 100 <= science_per_turn_times100
```

Then run `overflow_precondition`. End the turn manually, run
`overflow_completion`, select the next ordinary technology manually, run
`selection_stability`, advance the following interturn manually, and run
`overflow_application`. The profile preserves fractional surplus in its bounded
summary and never substitutes the old illustrative 20/22 values. Finish with
`audit_clean`.

## Finish and recovery

Request orderly completion with:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_testing finish
```

The supervisor asks Civ V to quit normally, stops its watcher, restores the
recorded baseline, and removes runtime state. It never force-kills Civ V.

If the supervisor crashes, run `recover` in the same kind of host terminal:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_testing recover
```

If Civ V and the read-only watcher are intact, recovery resumes foreground
supervision. If Civ V is already closed, recovery restores the host baseline and
exits. If the session is paused for data inconsistency, do not discard the scene;
inspect `status` and resolve the observation before deciding whether to finish.

Runtime state belongs under the current user's Application Support directory,
is private, and is not target evidence. Only the governed sanitized template in
the M11 procedure may be committed.
