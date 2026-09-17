# Worker-Build Verification Specification

Status: M10 D3 frozen; implementation and evidence pending

Owning semantic contract: [worker-build contract](../contracts/worker-build.md)

## Purpose

Freeze the evidence required before `worker_build` can enter the advertised
core profile. This specification separates deterministic offline coverage from
one finite operator-assisted target-machine gate. Passing offline tests does
not authorize a live write, and one live success does not replace any negative
or uncertainty test below.

## Offline matrix

Every row is required for C5. Tests use synthetic identifiers, units, plots,
states, command IDs, and sessions; no real snapshot or local game path belongs
in a fixture.

| ID | Boundary | Required cases |
|---|---|---|
| WB-S01 | Schema versions and parts | Accept valid legacy schemas 2–6 unchanged; require schema 7 header plus each existing part and exactly one `worker_context` and `worker_builds` part; reject missing, duplicate, unknown, out-of-order lifecycle, and turn/player-mismatched parts. |
| WB-S02 | Current plot shape | Accept the exact required keys and documented nulls; reject extra/missing keys, booleans disguised as integers, invalid owner, wrong scalar types, bad prefixes, empty identifiers, presentation text, and identifiers over 64 characters. |
| WB-S03 | Current build shape | Accept `null` or one bounded `BUILD_*`; reject every other type, prefix, empty value, and oversized value. |
| WB-S04 | Candidate shape | Accept zero to 32 exact `{build_type, improvement_type}` objects sorted by both fields; reject 33 entries, extra/missing fields, wrong prefixes/types, duplicate build IDs, unsorted values, and candidates attached to an unknown or duplicate unit. |
| WB-S05 | Candidate predicate | Emit the positive ordinary-improvement case; independently suppress inactive turn, message processing, not-ready/no-move, busy, automated, delayed-death, embarked, current-build, water, feature, existing-improvement, wrong subtype/mapping, no-improvement, route, repair, route-removal, water, unit-killing, and `CanBuild == false` cases. |
| WB-S06 | Read privacy and purity | Generated reads use active-team resource visibility, never AI recommendation/flavor/personality or opponent-private data, contain no selection/write calls, preserve candidate-neutral sorting, and fit the 1,000-byte limit at worst-case identifiers. |
| WB-C01 | Public arguments | Accept exactly non-boolean non-negative `unit_id`, bounded non-boolean `x`/`y`, and bounded `BUILD_*`; reject missing/extra keys, booleans, negatives, coordinate overflow, malformed/injection strings, wrong prefixes, and oversized values before write generation. |
| WB-C02 | Fresh admission | Require schema 7, unchanged bridge session, exactly one owned unit, exact source coordinates, no current build, and exactly one matching candidate; reject legacy/malformed state, missing/duplicate unit, source drift, absent/duplicate candidate, and changed paired improvement without sending write Lua. |
| WB-C03 | Game-side guards | Generated Lua re-resolves active player, unit, plot, build, and action; repeats every critical turn/unit/plot/build/mapping/legality guard; verifies exact head selection; requires `Game.CanHandleAction`; invokes `Game.HandleAction` at most once; contains no `PushMission`, popup acceptance, movement, retry, arbitrary caller Lua, or alternative selection. |
| WB-C04 | Submission markers | Parse every bounded terminal rejection and accepted marker; reject malformed, missing, duplicate, mismatched-unit/build, lifecycle-only, and oversized output. No marker alone is success. |
| WB-V01 | Active-build success | Accept only the same session/turn/player/active turn and same unit/type/coordinates with strictly lower movement, unchanged non-improvement plot facts, `current_build_type` equal to the request, and no improvement. |
| WB-V02 | Immediate-completion success | Accept only the same common facts with strictly lower movement, no current build, and improvement equal to the candidate's captured paired improvement. |
| WB-V03 | Wrong outcomes | Reject unchanged/increased movement, coordinate/unit/type drift, disappearance, turn/player/activity drift, changed terrain/feature/resource/route/owner/hills/water/fresh-water, wrong build, wrong improvement, active build plus improvement, neither branch, and malformed schema 7 read-back. |
| WB-V04 | Polling and uncertainty | Retry only documented transient invalid reads within the bound; accept a later exact postcondition; reject explicit game refusal without polling; fail unchanged/partial state at timeout; classify transport loss or malformed post-submit output as unknown; never resubmit automatically. |
| WB-W01 | Watcher and audit | Forward all four arguments and verification timeout exactly; require matching session and terminal result; audit factual rejection/success/unknown outcomes; keep audit failure from changing or retrying the game result. |
| WB-W02 | UUID behavior | Replay an identical completed UUID without a second write; reject reuse with different coordinates/build; cache submitted unknown outcome and never retry it during the watcher lifetime. |
| WB-E01 | Plan admission | Keep TurnPlan schema 1; admit `worker_build` only when the action is implemented; preserve all four exact arguments through validation, watcher adaptation, events, reports, journal composition, and cached-result lookup; older packages reject it. |
| WB-E02 | Requirement coverage | Cover `unit_orders` only for the exact unit; reject uncovered other units; allow an explicit prior `move_unit` to establish coordinates; pause when the built unit remains ready without a later explicit move/build/skip. |
| WB-E03 | Continuity and recovery | Enforce before/after digest continuity around ordered actions; stop on rejection/failure/unknown outcome; reconcile a cached result only when exact command plus fresh state independently satisfy the postcondition; pause after recovered non-final work rather than continuing automatically. |
| WB-A01 | Compatibility surface | Export schema/limit/action values only in the compatible release; preserve `CommandResult`, execution event/report, journal, and stable `civ5-turn` envelope schemas; cover provisional CLI exit/error behavior without stabilizing its spelling. |
| WB-A02 | Release and privacy | Pass Python 3.11/3.13, documentation links, artifact inspection and clean install, generated-program bounds, and tracked/artifact sensitive-content scans; reject real snapshots, IDs, coordinates, UUIDs, audit files, local paths, and generated game data from commits. |

## Live/offline allocation

The target-machine gate proves only facts that deterministic fixtures cannot:

- schema 7 can be collected without changing UI selection;
- one conservative candidate agrees with the stock UI on the target build;
- stale source coordinates are rejected without submitting a build;
- exactly one separately authorized build reaches one accepted postcondition;
- an independent watcher update, private audit permissions, and exact host
  restoration agree with the command result.

All malformed shapes, exclusions, alternate result branch, marker failures,
timeouts, transport ambiguity, duplicate UUID behavior, executor sequences,
recovery, and compatibility cases remain offline-only. The live procedure must
not deliberately cause an unknown outcome, reuse a UUID, alter a plot to
manufacture exclusions, or submit a second build merely to exercise the other
success branch.

## Target-machine pass rule

Section 8 of the [live-test checklist](../LIVE_TEST_CHECKLIST.md) is the only
authorized procedure. It is eligible only after C1–C5 pass and the exact
implementation commit is recorded locally. The live gate passes only when its
read-only proof, safe pre-send rejection, one confirmed write, independent
read-back, audit-permission check, and restoration all pass in the same bounded
session.

The single write may prove either the active-build or immediate-completion
branch. The observed branch is recorded; the unobserved branch retains offline
evidence only. Any unexpected or unknown outcome fails C6, ends the write
portion, and leaves `worker_build` absent from the stable capability profile.
