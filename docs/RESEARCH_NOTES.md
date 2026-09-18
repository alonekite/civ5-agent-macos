# Research Notes

Current working conclusions:
- Civ V Lua can access internal game state.
- Windows projects demonstrate external read/write, but some depend on Windows-only DLLs.
- [`corytodd/civ5-mcp`](https://github.com/corytodd/civ5-mcp)
  demonstrates a Lua-to-database bridge and MCP server; its README says it has
  only been tested on Brave New World for Windows.
- [`vox-deorum/vox-deorum`](https://github.com/vox-deorum/vox-deorum)
  demonstrates richer LLM integration but relies on a modified Windows
  GameCore DLL / Vox Populi stack.
- The installed App Store Campaign Edition hides its Mods browser, so discovered
  custom mods remain disabled on the stock build.
- FireTuner/TCP 4318 is exposed after reversibly setting `EnableTuner = 1` in
  user-owned `config.ini`.
- Python completed a real bidirectional FireTuner round trip against Lua state
  ID 172 (`InGame`) and read turn 1, player 0, and 3 gold from a live match.
- The old server behaves as a single-client endpoint and can retain a closed
  connection in `CLOSE_WAIT`; prefer one persistent client connection.

Open questions:
1. Which additional victory-progress fields are stable enough to add?

Resolved since the initial notes:

- The watcher now owns the sole persistent FireTuner connection and exposes a
  per-user mode-0600 Unix socket for serialized read/write requests.
- `end_turn` has been verified live with before/after state.
- `choose_research` and `set_city_production` use the same stock APIs as the
  bundled UI and have been live-verified with strict identifiers, capability
  checks, and read-back verification.
- Snapshot schema 2 and the legacy controller readiness/end-turn proof have
  been live-verified.
- Snapshot schema 4 has live-verified early-game score, era, city, unit,
  pre-contact diplomacy, and science-victory values. Non-empty diplomacy and
  non-zero science projects remain optional enhancement evidence.
- Unit skip is live-verified using `IsReadyToMove()` rather than spent movement.

## 2026-09-17 — Unit-movement source reconnaissance

Evidence level: source inspection only. Nothing in this section is a live
movement verification.

The installed Brave New World UI uses the selected-unit path for ordinary
right-click movement. `DLC/Expansion2/UI/InGame/WorldView/WorldView.lua` calls
`Game.SelectionListMove(plot, bAlt, bShift, bCtrl)`, and other bundled UI code
uses `UI.SelectUnit(unit)` plus `UI.GetHeadSelectedUnit()` to establish and read
the selected unit. Bundled uses of `Map.PlotDirection(x, y, direction)` and
`Map.PlotDistance(x1, y1, x2, y2)` also confirm stock adjacent-plot primitives.

Strings in the installed target executable and expansion library corroborate
the presence of `SelectionListMove`, `SelectUnit`, `GetHeadSelectedUnit`, and
movement predicates. They also include a protocol-error diagnostic for calling
`PushMission` on a human-controlled unit outside network-message dispatch.

For implementation detail only, the public
[`Gedemon/Civ5-DLL`](https://github.com/Gedemon/Civ5-DLL) mirror was inspected
at commit `aa29e80751f541ae04858b6d2a2c7dcca454201e`. No source or data was copied
into this repository. The released source shows that:

- `CvGame::selectionListMove` resolves the head-selected active-player unit and
  sends a network mission (or a swap when the destination permits one);
- direct `CvLuaUnit::lPushMission` reaches the path that warns when a human
  unit mission is invoked outside network-message dispatch;
- `CvLuaUnit::lGeneratePath` raises `NYI`;
- `CvLuaUnit::lCanMoveOrAttackInto` fails to assign its native result before
  returning the initialized false value in that source revision;
- `CvLuaUnit::lCanMoveThrough` does return its native predicate result, but it
  is not by itself a complete destination/stacking contract.

These findings select the stock network-backed `SelectionListMove` route for
the first experiment and reject direct `PushMission`. They also justify a
conservative first slice: one caller-chosen adjacent, currently visible, empty,
non-city plot; no attack, swap, air movement, embark/disembark, automation, or
multi-step path. The command must select the exact active-player unit, verify
the head selection, submit one non-queued move, and prove from a fresh read that
the same unit reached the exact destination. ADR-0032 owns the decision. The
method remains unsupported until its contracts, offline tests, and bounded
target-machine evidence pass.

## 2026-09-17 — Worker-build source reconnaissance

Evidence level: bundled-source and supporting released-SDK inspection plus
offline byte prototypes. Nothing in this section is a live worker-build
verification.

The installed BNW
`DLC/Expansion2/UI/InGame/WorldView/UnitPanel.lua` enumerates
`GameInfoActions` and identifies build buttons through
`ActionSubTypes.ACTIONSUBTYPE_BUILD`. It stores `action.MissionData` as the
numeric build identifier, uses `Game.CanHandleAction(action_index, 0, 1)` for
visibility and `Game.CanHandleAction(action_index)` for current executability,
then sends the selected button through `Game.HandleAction(action_index)`.

The same file reads ongoing work with `unit:GetBuildType()` and obtains timing
through `plot:GetBuildTurnsLeft` and `plot:GetBuildTurnsTotal`. Its recommended
action branch calls `unit:IsActionRecommended`; M10 explicitly excludes that
recommendation signal because selection belongs downstream.

The same public `Gedemon/Civ5-DLL` Expansion 2 source and commit recorded above
shows that the Lua `unit:CanBuild(plot, build, 0, 1)` binding reaches
unit-specific legality without consulting UI selection. In contrast,
`CvGame::canHandleAction` and `CvGame::handleAction` resolve the head-selected
unit, and `handleAction` sends a build mission through the game network-message
path. It may instead open an overwrite-confirmation popup when the current plot
already contains an improvement.

ADR-0033 therefore separates selection-free candidate reads from exact
selected-unit submission. The first slice requires blank featureless land and
only a build that creates an improvement without route, repair, route-removal,
water, or unit-killing semantics. This excludes the popup and gives two exact
verification branches: the requested `BUILD_*` remains active, or its paired
`IMPROVEMENT_*` is complete. Both also require the same unit and plot plus
lower movement.

The 2026-09-19 target read retry confirmed why integer flags matter: this
Campaign Edition binding rejects Lua booleans because `CvLuaUnit::lCanBuild`
reads both options with `luaL_optint`. ADR-0034 records the correction without
changing ADR-0033's candidate or submission semantics.

Offline string prototypes place the two read-only segments at 688 and 895
UTF-8 bytes. A compact write prototype using a 64-character build identifier,
maximum unit ID, and maximum supported coordinates is 994 bytes. Final
generated strings, parser behavior, and all bounds still require executable
tests. The target runtime still requires bounded evidence before the capability
can be advertised, but no unresolved source-design question blocks D2.
