# Worker-Build Contract

Status: Frozen M10 contract; C1–C5 offline gate complete; two bounded live read
attempts failed safely and are repaired offline; fresh live evidence pending

Expected compatibility release: 1.2.0, only after the offline and bounded live
gates pass

## Purpose

Define the first strategy-neutral worker construction capability. A caller
chooses one active-player unit, its exact current plot, and one exact ordinary
`BUILD_*` candidate from fresh state. The bridge validates, submits through the
stock selected-unit action path, and proves one of two exact factual outcomes.

This contract applies ADR-0033. Development head reports `1.2.0.dev0` and
implements schema 7 plus the bridge command, while tagged core 1.1.0 does not.
The capability must not be treated as stable until the compatible release
advertises schema 7 and the action after all remaining gates.

## Schema 7 live-state input

Schema 7 retains every schema 6 field and adds two mandatory read-only snapshot
parts, `worker_context` and `worker_builds`. Every part identifies the same turn
and active player as the header. A missing, duplicate, malformed, or mismatched
part invalidates the whole snapshot.

Every owned-unit record gains these required fields:

```json
{
  "current_plot": {
    "terrain_type": "TERRAIN_GRASS",
    "feature_type": null,
    "resource_type": null,
    "improvement_type": null,
    "route_type": "ROUTE_ROAD",
    "owner_id": 0,
    "is_hills": false,
    "is_water": false,
    "is_fresh_water": true
  },
  "current_build_type": null,
  "ordinary_build_actions": [
    {
      "build_type": "BUILD_FARM",
      "improvement_type": "IMPROVEMENT_FARM"
    }
  ]
}
```

`current_plot` is the plot at the unit's already-recorded `x`, `y`. It is not a
map, path, destination list, or claim about plots without active-player units.
Its fields have these meanings:

- `terrain_type` is one stable `TERRAIN_*` identifier;
- `feature_type`, `improvement_type`, and `route_type` are their stable
  `FEATURE_*`, `IMPROVEMENT_*`, and `ROUTE_*` identifiers or `null`;
- `resource_type` is a stable `RESOURCE_*` identifier only when the stock
  active-team lookup reveals it, otherwise `null`;
- `owner_id` is a non-negative player ID or `null` for an unowned plot;
- `is_hills`, `is_water`, and `is_fresh_water` are exact booleans.

`current_build_type` is the stable `BUILD_*` returned for the unit's active
build mission, or `null`. It may describe a build outside this contract and
does not itself make that build executable.

Stable identifiers in the new fields must match their prefixes plus
`[A-Z0-9_]+` and contain at most 64 characters. Empty strings, presentation
text, numeric database IDs, unknown prefixes, and values above the bound are
invalid.

`ordinary_build_actions` contains zero to 32 objects, sorted by
`(build_type, improvement_type)`. Every object has exactly the two shown
fields. Build identifiers are unique per unit. Every record must refer to the
same unit as its containing list; candidates for an unknown or duplicate unit
are invalid.

An empty list means only that no action in this deliberately narrow subset is
currently exposed. It does not mean the unit has no legal Civ V command.

## Candidate meaning and privacy

A candidate is emitted only when the same read observes all of the following:

- the active player's turn is active and game messages are not processing;
- the unit is ready, has movement remaining, and is not busy, automated,
  delayed-death, embarked, or already executing a build;
- the unit's current plot is land, has no feature, and has no improvement;
- the action is `ACTIONSUBTYPE_BUILD`, and its type and mission data match the
  referenced build row;
- the build creates the paired improvement and is not a route, repair,
  route-removal, water, or unit-killing build; and
- `unit:CanBuild(current_plot, build_id, 0, 1)` succeeds. ADR-0034 requires
  numeric option flags because the Campaign Edition binding reads them through
  `luaL_optint`; the values retain false/true semantics.

The list excludes feature clearing, improvement replacement, repair, routes,
water construction, automation, and great-person or other consuming builds.
It must not read `IsActionRecommended`, AI flavor/personality fields, hidden
resources, or opponent-private state. Candidate order carries no preference.

Schema 2–6 readers retain their existing meanings. They do not gain optional
worker fields and cannot admit `worker_build`.

## Command

The planned allowlisted command is:

```json
{
  "action": "worker_build",
  "args": {
    "unit_id": 7,
    "x": 12,
    "y": 8,
    "build_type": "BUILD_FARM"
  }
}
```

The argument object has exactly these four fields:

- `unit_id` is a non-negative integer and not a boolean;
- `x` and `y` are integers, not booleans, from 0 through 65,535;
- `build_type` matches `BUILD_[A-Z0-9_]+` and is at most 64 characters.

The coordinates are caller intent, not redundant decoration: they identify the
plot on which the caller authorized construction. A unit found elsewhere is a
stale request and must not build there.

Before generating or sending Lua, the Python bridge requires a fresh validated
schema 7 state, finds exactly one unit with `unit_id`, requires its coordinates
to equal `(x, y)`, and requires exactly one matching `build_type` in that
unit's `ordinary_build_actions`. The candidate's paired `improvement_type` is
captured as the expected completed result. Legacy, malformed, missing,
duplicate, stale, or unlisted state is rejection without game contact.

The single bounded Lua program re-resolves the active player, unit, build,
action, and current plot; repeats the source coordinates, active-turn,
message-processing, current-build, blank-plot, action-mapping, and exact
`CanBuild` guards; then clears selection, selects that unit, and verifies its
head-selected ID. It calls `Game.HandleAction(action_index)` exactly once only
after `Game.CanHandleAction(action_index)` succeeds.

The command never moves a unit, chooses a build or alternative, accepts a
popup, restores prior selection, calls direct `PushMission`, submits caller
Lua, or retries. UI selection is the only accepted visible side effect before
verified work.

Private command markers distinguish factual rejection, stale state, selection
failure, and accepted submission. Their encoding is not a public API and no
marker proves the build result.

## Success postcondition

The bridge polls fresh validated schema 7 state within the existing
caller-supplied verification timeout. One after-state is success only when all
common conditions hold:

- bridge session, turn, active player, and active-turn status are unchanged;
- exactly one owned unit retains the requested ID and before-state unit type;
- the unit remains exactly at `(x, y)`;
- its movement points are strictly lower than before submission;
- terrain, feature, active-team-visible resource, route, ownership, hills,
  water, and fresh-water values equal the before-state `current_plot`; and
- the complete after-state passes schema 7 validation.

It must then satisfy exactly one result branch:

1. **active:** `current_build_type` equals the requested `build_type` and
   `current_plot.improvement_type` remains `null`; or
2. **completed:** `current_build_type` is `null` and
   `current_plot.improvement_type` equals the candidate's exact paired
   `improvement_type`.

The result message may describe which branch succeeded, but `CommandResult`
schema and `status = "success"` retain their existing meanings.

A different or simultaneous build/improvement state, unchanged or increased
movement, changed plot fact, changed coordinates, disappearance,
transformation, turn/player drift, popup without work, unchanged state,
malformed read-back, timeout, or explicit game-side rejection is not success.
A loss of transport or malformed result after submission is an unknown outcome
under ADR-0028 and ADR-0023 and is never retried automatically.

## TurnPlan behavior

TurnPlan schema 1 may contain `worker_build` after the compatible action
addition. The schema number does not change because `action` remains an
extensible allowlist field; core 1.1 packages reject it. Consumers must check
package version, schema 7 support, and `ALLOWED_ACTIONS` rather than infer
availability from TurnPlan schema 1.

A `worker_build` action covers a factual `unit_orders` requirement only for its
exact `unit_id`. Its four arguments are preserved exactly through validation,
watcher forwarding, events, journal composition, cached-result lookup, and
reports. Fresh bridge admission occurs at its execution step, so a prior
explicit `move_unit` may establish the requested `(x, y)` before the build.

If the verified build leaves the unit ready and no later explicit
`move_unit`, `worker_build`, or `skip_unit` covers that exact unit, execution
pauses. The executor never chooses another build, changes coordinates, or
assumes that an accepted marker satisfied the unit requirement.

Recovery uses the existing conservative rule. A cached result must match the
exact command and independently satisfy this postcondition against the last
verified basis and fresh state. Recovery of a non-final worker action pauses
before the next action instead of automatically continuing the old plan.

## Ownership and privacy

The tactical layer owns worker, plot, build, sequence, purpose, scoring,
expected yield, threat, alternatives, and replanning. The core owns only the
visible current-plot facts, conservative candidates, argument validation,
stock dispatch, and factual result classification. Knowledge and journal are
not executor dependencies.

Real snapshots, unit IDs, coordinates, plans, UUIDs, and match facts remain
private and must not be committed. Tests use synthetic values.

## Compatibility and evidence gate

The planned backward-compatible additions are:

- live-state schema 7 and two required snapshot parts;
- `worker_build` in `ALLOWED_ACTIONS`;
- public limits `MAX_BUILD_IDENTIFIER_LENGTH = 64` and
  `MAX_ORDINARY_WORKER_BUILDS_PER_UNIT = 32`;
- schema 1 TurnPlan support for the exact four-field action; and
- unchanged `CommandResult`, execution-report/event, journal, and stable
  `civ5-turn` envelope schemas.

These changes require at least package version 1.2.0. Development head is
`1.2.0.dev0`: C1 implements the read/schema surface, C2–C3 implement exact
admission, one stock submission, marker handling, polling, and both factual
success branches, and C4 integrates schema 1 TurnPlans with independent result
validation, exact-unit coverage, continuity, pause, and recovery behavior.
The complete capability remains absent from the stable downstream profile until
C5 offline reconciliation and C6 bounded target-machine evidence pass. A
failed live gate leaves core 1.1.0 as the latest advertised capability.
