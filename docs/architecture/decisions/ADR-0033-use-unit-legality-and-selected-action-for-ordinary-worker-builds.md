# ADR-0033: Use unit legality and the selected-unit stock action for ordinary worker builds

Status: Accepted

Date: 2026-09-17

## Context

The downstream tactical layer needs to choose an improvement for an explicit
worker, but core 1.1.0 neither exposes current-plot build candidates nor admits
a construction action. This core must expose reusable visible facts and execute
one exact mechanic without choosing a worker, plot, improvement, purpose, or
alternative.

Worker actions combine two different game contexts. Released Expansion 2 SDK
source shows that `CvUnit::canBuild` evaluates the exact unit, plot, build,
player prerequisites, domain, cost, and conflicting workers without consulting
the UI selection. The Lua binding exposes that predicate as
`unit:CanBuild(plot, build_id, bTestVisible, bTestGold)`. Conversely,
`CvGame::canHandleAction` and `CvGame::handleAction` resolve the head-selected
unit. `handleAction` submits a `MISSION_BUILD` through the game's network
message path, but may open a confirmation popup instead when an existing
improvement would be replaced.

The installed BNW `UnitPanel.lua` corroborates the public source: build buttons
are `ACTIONSUBTYPE_BUILD` entries; `action.MissionData` is the build ID;
`Game.CanHandleAction(action_index)` controls current executability; and a
click calls `Game.HandleAction(action_index)`. It reads ongoing work through
`unit:GetBuildType()` and plot build-turn methods. Bundled UI also uses
`unit:IsActionRecommended`, but that value is a recommendation rather than a
legality fact.

Completion has two observable forms. A multi-turn action remains in the unit's
mission queue and `GetBuildType()` returns the requested build. A sufficiently
advanced or one-turn action may complete immediately, remove the mission, and
leave only the resulting plot improvement. Treating only the active mission as
success would produce false failure; treating any plot change as success would
produce false success.

The existing FireTuner path rejects programs above 1,000 UTF-8 bytes. Design
prototypes put the two new read-only segments at 688 and 895 bytes. A compact
write program with a 64-character build identifier, maximum supported unit ID,
and maximum supported coordinates is 994 bytes. These measurements show
feasibility only; the implementation must generate and test the final strings.

The supporting public source was inspected from `Gedemon/Civ5-DLL` commit
`aa29e80751f541ae04858b6d2a2c7dcca454201e`. No source was copied into this
repository, and that inspection is not target-macOS runtime evidence.

## Decision

M10's first slice will expose and execute only an **ordinary current-plot
improvement build**. The caller supplies the exact active-player unit and one
stable `BUILD_*` identifier. The worker must already stand on the intended
plot. The core will not move it or choose an action.

### Read model

Schema 7 will add two read-only, selection-free parts:

- per-unit current-plot context sufficient to identify terrain, feature,
  active-team-visible resource, improvement, route, ownership, land/water and
  hill/fresh-water state, plus the stable current `BUILD_*` or no build;
- a bounded per-unit list of currently admissible ordinary builds, pairing the
  stable `BUILD_*` with its exact resulting `IMPROVEMENT_*`.

Resource lookup must pass the active team to the stock plot API. The read path
must never use raw resource access, change selection, expose recommendation
values, or infer a preferred build.

Candidate enumeration will inspect build actions and require all of the
following:

- the action is exactly `ACTIONSUBTYPE_BUILD`, its type matches the referenced
  `GameInfo.Builds` row, and its mission data matches that build ID;
- the build has an `ImprovementType` and has no route, repair, route-removal,
  water, or unit-killing semantics;
- the unit is owned by the active player, ready with movement remaining, not
  busy, automated, delayed-death, embarked, or already executing a build;
- the current plot is land with no feature and no existing improvement; and
- `unit:CanBuild(plot, build_id, false, true)` succeeds.

Requiring no feature prevents the first slice from silently clearing terrain
features. Requiring no improvement prevents the stock overwrite-confirmation
popup and makes the completed result exact. Existing routes may coexist with
an ordinary improvement but route construction and removal are not candidates.

### Command path

The provisional public action remains `worker_build(unit_id, build)`. Contract
D2 may rename it only before it enters the stable allowlist.

Admission must bind the exact bridge session, active player, turn, full state
basis, unit identity and coordinates, candidate membership, and expected
improvement. The compact game-side program must independently re-resolve the
active-player unit and stable build, locate the matching build action, repeat
the coordinates and critical current-plot/`CanBuild` guards, clear selection,
select the exact unit, and immediately verify the head-selected unit ID. Only
then may it require `Game.CanHandleAction(action_index)` and call
`Game.HandleAction(action_index)` once.

The core will not call `unit:PushMission`, construct a second game-message
path, accept a popup, restore a former selection through another command, or
retry after an uncertain submission. UI selection is an accepted visible side
effect of using the stock human action path.

### Verification

A command marker proves only that one submission was attempted. Success
requires bounded fresh-state polling and all common conditions:

- the bridge session, active player, and active turn remain the expected ones;
- the same unit identity and type remain at the exact source coordinates;
- the unit's movement is lower than before submission; and
- no unsupported schema or malformed evidence is used.

The verifier then accepts exactly one of two branches:

1. **active build:** the unit's current stable build is the requested
   `BUILD_*`, while the plot still has no improvement; or
2. **completed build:** the unit has no active build and the same plot's stable
   improvement is the exact `IMPROVEMENT_*` paired with the admitted candidate.

A different build or improvement, unchanged movement, changed coordinates,
unit disappearance/transformation, turn or player drift, popup/no mission,
unchanged state, timeout, malformed response, or transport ambiguity is not
success. Unknown outcomes follow ADR-0028 and ADR-0023 and are never retried
automatically.

### Layer boundary

The bridge owns visible facts, stable identifiers, conservative legality,
stock dispatch, and verification. M6 may execute only the exact plan-listed
action and cover only that unit's factual order requirement. Knowledge remains
outside executor dependencies; the live candidate pairs carry the exact
ruleset mapping needed for verification.

The tactical layer owns worker, plot, build, sequence, scoring, expected yield,
threat, purpose, alternatives, and replanning. `IsActionRecommended` and all AI
flavor/personality information remain prohibited. The capability stays absent
from the stable downstream profile until offline and bounded target-machine
evidence pass.

## Consequences

- Per-unit candidate reads no longer depend on or mutate UI selection.
- Submission uses the same selected-unit action path as the stock BNW UI.
- The first slice rejects otherwise legal feature clearing, improvement
  replacement, repair, routes, water builds, automation, and great-person or
  other consuming builds.
- Pairing each candidate with its resulting improvement makes immediate
  completion verifiable without querying the knowledge module.
- Requiring lower movement distinguishes an actual work step from a coincidental
  pre-existing mission or plot value.
- The narrow blank land plot scope is not a complete worker system. Later
  mechanics require separate capability requests and, if they change this
  boundary, a superseding ADR.
- Final generated Lua remains blocked on executable byte-bound tests, and the
  capability remains unverified until the target Mac proves schema 7,
  selection, dispatch, both applicable result states, and restoration.

## Alternatives considered

- Select each unit and call `Game.CanHandleAction` while reading candidates:
  rejected because reads would mutate UI state and selection could drift.
- Use only `plot:CanBuild`: rejected because it omits exact unit capability and
  conflicting-worker semantics enforced by `unit:CanBuild`.
- Call `unit:PushMission(MISSION_BUILD, ...)`: rejected because human missions
  use the stock network-message path and direct mission calls create a second,
  less-supported write mechanism.
- Accept all `BUILD_*` values for which `CanBuild` succeeds: rejected because it
  would combine improvements, routes, repair, feature removal, water work, and
  consuming special units under one ambiguous postcondition.
- Allow existing improvements and handle the confirmation popup: rejected
  because popup control is a separate UI mechanic and an accepted popup is not
  a verified build submission.
- Verify only `GetBuildType()`: rejected because an immediate completion has no
  remaining active build.
- Verify only the resulting improvement: rejected because most builds are
  multi-turn and an accepted first work step does not yet create it.
- Query the knowledge module from M6 for build-to-improvement mapping: rejected
  under ADR-0018; the live schema binds the admitted candidate to its exact
  expected result.

## Supersedes

None. This applies ADR-0003, ADR-0018, ADR-0023, ADR-0028, ADR-0031, and the
selected-unit safety pattern established by ADR-0032.
