# Ordinary Research Forecast Facts Contract

Status: Frozen design for M11; implementation and target evidence pending

Compatible release: 1.3.0

Live-state schema: 8

Capability version: 1

## Purpose and boundary

Schema 8 provides exact, read-only runtime facts that a downstream adapter can
use to forecast ordinary technology completion. The core does not recommend a
technology, compare candidates, simulate a route, bind a knowledge bundle, or
change research. The existing `choose_research` command and every write/result
contract remain unchanged.

## `research_forecast`

Every schema 8 state has exactly one object with this shape:

```json
{
  "capability_version": 1,
  "status": "supported",
  "reason": null,
  "phase": "action_window_after_interturn_research_resolution",
  "science_per_turn_times100": 2200,
  "overflow_research": 2,
  "current": {
    "type": "TECH_WRITING",
    "cost": 55,
    "progress_times100": 3500,
    "turns_left_with_overflow": 1
  },
  "candidates": [],
  "field_provenance": {
    "cost": "CvPlayer.GetResearchCost",
    "progress_times100": "CvPlayer.GetResearchProgressTimes100",
    "science_per_turn_times100": "CvPlayer.GetScienceTimes100",
    "overflow_research": "CvPlayer.GetOverflowResearch",
    "turns_left_with_overflow": "CvPlayer.GetResearchTurnsLeft(include_overflow=true)",
    "phase": "CvPlayer.IsTurnActive+Game.IsProcessingMessages"
  }
}
```

`status` is `supported` only when all capability fields are available, the
active player is in an ordinary research mode, the turn is active, and the game
is not processing interturn messages. `reason` is then `null`. Otherwise
`status` is `unsupported` or `unavailable`, all scalar/current/candidate facts
are `null` or empty as defined below, and `reason` is one of:

- `free_technology_mode`;
- `technology_steal_mode`;
- `outside_action_window`;
- `runtime_api_binding_unavailable`.

Malformed values invalidate the whole state rather than producing an
unsupported object.

### Units and semantics

- `science_per_turn_times100` is the integer returned directly by
  `GetScienceTimes100`. One research point is 100 units.
- `overflow_research` is the integer returned directly by
  `GetOverflowResearch`. Its unit is whole research points. Schema 8 does not
  multiply it by 100 and does not claim fractional overflow precision.
- `cost` is the effective whole-point cost returned by `GetResearchCost` for
  that player and candidate in the current game.
- `progress_times100` is the exact integer returned by
  `GetResearchProgressTimes100`. One research point is 100 units.
- `turns_left_with_overflow` is the non-negative integer returned by
  `GetResearchTurnsLeft(tech_id, true)`. It is a runtime fact, not a core
  recomputation.

`current` is `null` when no ordinary current research exists. Otherwise its
technology must be present in `candidates`, and the four values must equal the
candidate record. `candidates` contains exactly the schema 5
`researchable_technologies`, sorted by `type`, with no duplicates. The maximum
candidate count remains bounded by the number of valid technology records in
the active ruleset and by the existing response-size limit.

When `status` is not `supported`, `phase` is `outside_action_window`, scalar
facts and `current` are `null`, and `candidates` is empty. This fail-closed
shape prevents a consumer from mixing partial exact facts with an unsupported
mode.

The optional recent-completed-technology fact requested by the consumer is not
included in capability version 1 because no reliable runtime binding has been
identified. Absence must not be inferred from the researched set.

## `runtime_context`

Every schema 8 state also has:

```json
{
  "context_version": 1,
  "game_speed": {"status": "available", "value": "GAMESPEED_STANDARD", "source": "PreGame.GetGameSpeed+GameInfo.GameSpeeds"},
  "difficulty": {"status": "available", "value": "HANDICAP_PRINCE", "source": "CvPlayer.GetHandicapType+GameInfo.HandicapInfos"},
  "world_size": {"status": "available", "value": "WORLDSIZE_STANDARD", "source": "Map.GetWorldSize+GameInfo.Worlds"},
  "map_script": {"status": "available", "value": "Assets/Maps/Continents.lua", "source": "PreGame.GetMapScript"},
  "civilization": {"status": "available", "value": "CIVILIZATION_SPAIN", "source": "PreGame.GetCivilization+GameInfo.Civilizations"},
  "game_family": {"status": "unavailable", "value": null, "source": null},
  "game_build": {"status": "unavailable", "value": null, "source": null},
  "active_content": {"status": "unsupported", "value": null, "source": null},
  "ruleset_fingerprint": {"status": "unsupported", "value": null, "source": null}
}
```

Each dimension has exactly `status`, `value`, and `source`. `available` requires
non-empty runtime-derived values and source; the other statuses require both to
be `null`. Paths are game-relative values returned by the runtime, never local
absolute paths. Schema 8 never substitutes a constant or inferred value for an
unavailable dimension.

This object is runtime context identity and provenance. It is not a complete
ruleset manifest or cryptographic proof. A consumer that requires a complete
ruleset identity must bind the available dimensions to a selected
`KnowledgeBundle`, verify its source hashes, and fail closed on gaps or
conflicts for exact-supported forecasting and forecast-dependent automation.
That downstream binding result does not change the core object's `status` and
must not erase its authoritative runtime values.

## Compatibility and missing behavior

- Core 1.3.0 adds schema 8 and capability version 1 as a backward-compatible
  minor feature. Schemas 2–7 remain accepted and retain their exact shapes.
- Consumers must negotiate schema 8 explicitly. A package version alone does
  not prove field presence.
- On schemas 2–7, the forecast and runtime-context capabilities are absent, not
  zero, empty-supported, or inferable from whole-unit legacy fields.
- A schema 8 consumer must require `status == "supported"`, the exact phase,
  and a sufficient external context/knowledge binding before claiming an
  exact-supported forecast or admitting forecast-dependent automatic intent.
- KnowledgeBundle binding is not required to expose authoritative live research
  facts. It is also not, by itself, a reason to prohibit a separately approved
  core-only/manual-review `choose_research` intent that uses current candidates
  and makes no exact-forecast claim.
- Free/steal research stays unsupported and produces no candidates.

## Required evidence

Before release, offline tests must cover exact costs, exact progress with and
without current research, zero/positive overflow, unavailable binding,
ordinary/free/steal modes, action-window phase, malformed records, duplicate or
misordered candidates, ruleset-context conflicts at the consumer boundary,
deterministic serialization, response/program bounds, and schemas 2–7.

Target verification must separately prove read purity and the runtime units.
The preferred controlled case has 20 whole research points remaining and 22
whole points produced: completion occurs during interturn, the next action
window reports overflow `2`, choosing the next technology does not immediately
apply it, and the following interturn does. If that exact save is unavailable,
the experiment must remain pending rather than substitute inference.
