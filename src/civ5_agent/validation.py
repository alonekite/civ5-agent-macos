from __future__ import annotations

import re

from .errors import ValidationError
from .models import GameState


TECH_TYPE_PATTERN = re.compile(r"TECH_[A-Z0-9_]+\Z")
TERRAIN_TYPE_PATTERN = re.compile(r"TERRAIN_[A-Z0-9_]+\Z")
FEATURE_TYPE_PATTERN = re.compile(r"FEATURE_[A-Z0-9_]+\Z")
RESOURCE_TYPE_PATTERN = re.compile(r"RESOURCE_[A-Z0-9_]+\Z")
IMPROVEMENT_TYPE_PATTERN = re.compile(r"IMPROVEMENT_[A-Z0-9_]+\Z")
ROUTE_TYPE_PATTERN = re.compile(r"ROUTE_[A-Z0-9_]+\Z")
BUILD_TYPE_PATTERN = re.compile(r"BUILD_[A-Z0-9_]+\Z")
GAME_SPEED_TYPE_PATTERN = re.compile(r"GAMESPEED_[A-Z0-9_]+\Z")
HANDICAP_TYPE_PATTERN = re.compile(r"HANDICAP_[A-Z0-9_]+\Z")
WORLD_SIZE_TYPE_PATTERN = re.compile(r"WORLDSIZE_[A-Z0-9_]+\Z")
CIVILIZATION_TYPE_PATTERN = re.compile(r"CIVILIZATION_[A-Z0-9_]+\Z")
SUPPORTED_LIVE_STATE_SCHEMA_VERSIONS = frozenset({2, 3, 4, 5, 6, 7, 8})
RESEARCH_FORECAST_CAPABILITY_VERSION = 1
RUNTIME_CONTEXT_VERSION = 1
MAX_MAP_COORDINATE = 65_535
MAX_BUILD_IDENTIFIER_LENGTH = 64
MAX_ORDINARY_WORKER_BUILDS_PER_UNIT = 32
NO_END_TURN_BLOCKING_TYPE = -1


class StateValidationError(ValidationError):
    pass


def validate_live_state(state: GameState) -> GameState:
    required = {
        "schema_version": state.schema_version,
        "turn": state.turn,
        "active_player": state.active_player,
        "gold": state.gold,
        "turn_active": state.turn_active,
        "can_end_turn": state.can_end_turn,
        "end_turn_blocking_type": state.end_turn_blocking_type,
    }
    missing = sorted(name for name, value in required.items() if value is None)
    if missing:
        raise StateValidationError(f"live state is missing: {', '.join(missing)}")
    for field in (
        "schema_version",
        "turn",
        "active_player",
        "gold",
        "end_turn_blocking_type",
    ):
        value = getattr(state, field)
        if not isinstance(value, int) or isinstance(value, bool):
            raise StateValidationError(f"{field} must be an integer")
    for field in (
        "gold_per_turn",
        "science_per_turn",
        "happiness",
        "culture",
        "culture_per_turn",
        "score",
        "current_era",
    ):
        value = getattr(state, field)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise StateValidationError(f"{field} must be an integer when present")
    for field in ("turn_active", "can_end_turn"):
        if not isinstance(getattr(state, field), bool):
            raise StateValidationError(f"{field} must be a boolean")
    if state.schema_version not in SUPPORTED_LIVE_STATE_SCHEMA_VERSIONS:
        raise StateValidationError(f"unsupported schema_version: {state.schema_version}")
    if state.turn is not None and state.turn < 0:
        raise StateValidationError("turn must be non-negative")
    if state.active_player is not None and state.active_player < 0:
        raise StateValidationError("active_player must be non-negative")
    if state.score is not None and state.score < 0:
        raise StateValidationError("score must be non-negative")
    if state.current_era is not None and state.current_era < 0:
        raise StateValidationError("current_era must be non-negative")
    if state.schema_version >= 3 and (
        state.score is None or state.current_era is None
    ):
        raise StateValidationError("schema 3+ requires score and current_era")

    if (
        not isinstance(state.cities, list)
        or not isinstance(state.units, list)
        or not isinstance(state.diplomacy, list)
    ):
        raise StateValidationError("cities, units, and diplomacy must be lists")
    _validate_records(state.cities, "city")
    _validate_records(state.units, "unit")
    for city in state.cities:
        population = city.get("population")
        if (
            not isinstance(population, int)
            or isinstance(population, bool)
            or population < 1
        ):
            raise StateValidationError(f"city {city.get('id')} has invalid population")
        for field in ("name", "production"):
            if not isinstance(city.get(field), str):
                raise StateValidationError(f"city {city.get('id')} has invalid {field}")
        if state.schema_version >= 3:
            for field in (
                "food_times100",
                "growth_threshold",
                "production_times100",
                "production_needed",
            ):
                value = city.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise StateValidationError(
                        f"city {city.get('id')} has invalid {field}"
                    )
            for field in (
                "food_per_turn_times100",
                "production_per_turn_times100",
            ):
                value = city.get(field)
                if not isinstance(value, int) or isinstance(value, bool):
                    raise StateValidationError(
                        f"city {city.get('id')} has invalid {field}"
                    )
    for unit in state.units:
        moves = unit.get("moves")
        if not isinstance(moves, int) or isinstance(moves, bool) or moves < 0:
            raise StateValidationError(f"unit {unit.get('id')} has invalid moves")
        for field in ("name", "type"):
            if not isinstance(unit.get(field), str):
                raise StateValidationError(f"unit {unit.get('id')} has invalid {field}")
        if state.schema_version >= 3:
            for field in (
                "damage",
                "combat_strength",
                "ranged_strength",
                "range",
            ):
                value = unit.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise StateValidationError(
                        f"unit {unit.get('id')} has invalid {field}"
                    )
            max_hit_points = unit.get("max_hit_points")
            if (
                not isinstance(max_hit_points, int)
                or isinstance(max_hit_points, bool)
                or max_hit_points <= 0
            ):
                raise StateValidationError(
                    f"unit {unit.get('id')} has invalid max_hit_points"
                )
            if unit["damage"] > max_hit_points:
                raise StateValidationError(
                    f"unit {unit.get('id')} damage exceeds max_hit_points"
                )
            if state.schema_version >= 4 and not isinstance(
                unit.get("ready_to_move"), bool
            ):
                raise StateValidationError(
                    f"unit {unit.get('id')} has invalid ready_to_move"
                )
            if state.schema_version >= 6:
                _validate_ordinary_move_targets(unit)
            if state.schema_version >= 7:
                _validate_worker_state(unit)

    diplomacy_players: set[int] = set()
    for relation in state.diplomacy:
        if not isinstance(relation, dict):
            raise StateValidationError("diplomacy record must be an object")
        player_id = relation.get("player_id")
        if (
            not isinstance(player_id, int)
            or isinstance(player_id, bool)
            or player_id < 0
        ):
            raise StateValidationError("diplomacy record has invalid player_id")
        if player_id == state.active_player or player_id in diplomacy_players:
            raise StateValidationError(f"invalid diplomacy player id: {player_id}")
        diplomacy_players.add(player_id)
        for field in ("team_id", "score"):
            value = relation.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise StateValidationError(
                    f"diplomacy player {player_id} has invalid {field}"
                )
        approach = relation.get("approach")
        if not isinstance(approach, int) or isinstance(approach, bool) or approach < -1:
            raise StateValidationError(
                f"diplomacy player {player_id} has invalid approach"
            )
        if not isinstance(relation.get("at_war"), bool):
            raise StateValidationError(
                f"diplomacy player {player_id} has invalid at_war"
            )
        for field in ("name", "civilization"):
            if not isinstance(relation.get(field), str):
                raise StateValidationError(
                    f"diplomacy player {player_id} has invalid {field}"
                )

    if state.schema_version >= 3:
        if not isinstance(state.victory, dict):
            raise StateValidationError("schema 3+ requires a victory record")
        if not isinstance(state.victory.get("science_enabled"), bool):
            raise StateValidationError("victory has invalid science_enabled")
        for field in (
            "apollo",
            "booster",
            "cockpit",
            "stasis_chamber",
            "engine",
        ):
            value = state.victory.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < -1:
                raise StateValidationError(f"victory has invalid {field}")

    if state.research is not None:
        if not isinstance(state.research, dict):
            raise StateValidationError("research must be an object when present")
        for field in ("id", "progress", "cost"):
            value = state.research.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise StateValidationError(f"research has invalid {field}")
        if not isinstance(state.research.get("type"), str) or not state.research["type"]:
            raise StateValidationError("research has invalid type")
        if state.schema_version >= 5 and not TECH_TYPE_PATTERN.fullmatch(
            state.research["type"]
        ):
            raise StateValidationError("research has invalid technology identifier")
    if state.schema_version >= 5:
        _validate_technology_ids(
            state.researched_technologies,
            "researched_technologies",
        )
        _validate_technology_ids(
            state.researchable_technologies,
            "researchable_technologies",
        )
        overlap = set(state.researched_technologies) & set(
            state.researchable_technologies
        )
        if overlap:
            raise StateValidationError(
                "technology cannot be both researched and researchable: "
                + ", ".join(sorted(overlap))
            )
        if state.research and state.research["type"] in state.researched_technologies:
            raise StateValidationError("current research is already researched")
        if not isinstance(state.research_choice, dict):
            raise StateValidationError("schema 5 requires research_choice")
        required = state.research_choice.get("required")
        mode = state.research_choice.get("mode")
        if not isinstance(required, bool):
            raise StateValidationError("research_choice has invalid required")
        if mode not in {"normal", "free_technology", "unsupported"}:
            raise StateValidationError("research_choice has invalid mode")
        if not required and mode != "normal":
            raise StateValidationError(
                "non-required research_choice must use normal mode"
            )
        ordinary_required = state.research is None and bool(
            state.researchable_technologies
        )
        if mode == "normal" and required != ordinary_required:
            raise StateValidationError(
                "normal research_choice must match ordinary research availability"
            )
    if state.schema_version >= 8:
        _validate_research_forecast(state)
        _validate_runtime_context(state.runtime_context)
    return state


def _validate_research_forecast(state: GameState) -> None:
    forecast = state.research_forecast
    expected = {
        "capability_version",
        "status",
        "reason",
        "phase",
        "science_per_turn_times100",
        "overflow_research",
        "current",
        "candidates",
        "field_provenance",
    }
    if not isinstance(forecast, dict) or set(forecast) != expected:
        raise StateValidationError("schema 8 requires exact research_forecast")
    if forecast["capability_version"] != RESEARCH_FORECAST_CAPABILITY_VERSION:
        raise StateValidationError("research_forecast has invalid capability_version")
    provenance = forecast["field_provenance"]
    expected_provenance = {
        "cost": "CvPlayer.GetResearchCost",
        "progress_times100": "CvPlayer.GetResearchProgressTimes100",
        "science_per_turn_times100": "CvPlayer.GetScienceTimes100",
        "overflow_research": "CvPlayer.GetOverflowResearch",
        "turns_left_with_overflow": "CvPlayer.GetResearchTurnsLeft(include_overflow=true)",
        "phase": "CvPlayer.IsTurnActive+Game.IsProcessingMessages",
    }
    if provenance != expected_provenance:
        raise StateValidationError("research_forecast has invalid field_provenance")
    status = forecast["status"]
    reason = forecast["reason"]
    if status == "supported":
        if reason is not None:
            raise StateValidationError("supported research_forecast cannot have reason")
        if forecast["phase"] != "action_window_after_interturn_research_resolution":
            raise StateValidationError("supported research_forecast has invalid phase")
        if state.research_choice.get("mode") != "normal" or not state.turn_active:
            raise StateValidationError("supported research_forecast is outside ordinary active mode")
        for field in ("science_per_turn_times100", "overflow_research"):
            value = forecast[field]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise StateValidationError(f"research_forecast has invalid {field}")
        candidates = forecast["candidates"]
        if not isinstance(candidates, list):
            raise StateValidationError("research_forecast candidates must be a list")
        normalized: list[str] = []
        for candidate in candidates:
            _validate_research_candidate(candidate)
            normalized.append(candidate["type"])
        if normalized != sorted(normalized) or len(set(normalized)) != len(normalized):
            raise StateValidationError("research_forecast candidates must be sorted and unique")
        expected_types = sorted(
            set(state.researchable_technologies)
            | ({state.research["type"]} if state.research is not None else set())
        )
        if normalized != expected_types:
            raise StateValidationError("research_forecast candidates disagree with researchable technologies")
        current = forecast["current"]
        if state.research is None:
            if current is not None:
                raise StateValidationError("research_forecast current must be null")
        else:
            if not isinstance(current, dict):
                raise StateValidationError("research_forecast current is missing")
            match = next(
                (item for item in candidates if item["type"] == state.research["type"]),
                None,
            )
            if current != match:
                raise StateValidationError("research_forecast current must match its candidate")
            if current["cost"] != state.research["cost"]:
                raise StateValidationError("research_forecast current cost disagrees with research")
    elif status in {"unsupported", "unavailable"}:
        if reason not in {
            "free_technology_mode",
            "technology_steal_mode",
            "outside_action_window",
            "runtime_api_binding_unavailable",
        }:
            raise StateValidationError("research_forecast has invalid unsupported reason")
        if forecast["phase"] != "outside_action_window":
            raise StateValidationError("unsupported research_forecast has invalid phase")
        if any(
            forecast[field] is not None
            for field in ("science_per_turn_times100", "overflow_research", "current")
        ) or forecast["candidates"] != []:
            raise StateValidationError("unsupported research_forecast contains partial facts")
        expected_status = (
            "unavailable"
            if reason == "runtime_api_binding_unavailable"
            else "unsupported"
        )
        if status != expected_status:
            raise StateValidationError("research_forecast status disagrees with reason")
        mode = state.research_choice.get("mode")
        if reason == "free_technology_mode" and mode != "free_technology":
            raise StateValidationError("research_forecast free mode disagrees with research_choice")
        if reason == "technology_steal_mode" and mode != "unsupported":
            raise StateValidationError("research_forecast steal mode disagrees with research_choice")
    else:
        raise StateValidationError("research_forecast has invalid status")


def _validate_research_candidate(candidate: object) -> None:
    expected = {"type", "cost", "progress_times100", "turns_left_with_overflow"}
    if not isinstance(candidate, dict) or set(candidate) != expected:
        raise StateValidationError("research_forecast has malformed candidate")
    if not isinstance(candidate["type"], str) or not TECH_TYPE_PATTERN.fullmatch(
        candidate["type"]
    ):
        raise StateValidationError("research_forecast has invalid candidate type")
    for field in ("cost", "progress_times100", "turns_left_with_overflow"):
        value = candidate[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise StateValidationError(f"research_forecast candidate has invalid {field}")


def _validate_runtime_context(context: object) -> None:
    dimensions = {
        "game_speed",
        "difficulty",
        "world_size",
        "map_script",
        "civilization",
        "game_family",
        "game_build",
        "active_content",
        "ruleset_fingerprint",
    }
    if not isinstance(context, dict) or set(context) != {"context_version", *dimensions}:
        raise StateValidationError("schema 8 requires exact runtime_context")
    if context["context_version"] != RUNTIME_CONTEXT_VERSION:
        raise StateValidationError("runtime_context has invalid context_version")
    for name in dimensions:
        item = context[name]
        if not isinstance(item, dict) or set(item) != {"status", "value", "source"}:
            raise StateValidationError(f"runtime_context has malformed {name}")
        if item["status"] == "available":
            if not isinstance(item["value"], str) or not item["value"]:
                raise StateValidationError(f"runtime_context has invalid {name} value")
            if not isinstance(item["source"], str) or not item["source"]:
                raise StateValidationError(f"runtime_context has invalid {name} source")
        elif item["status"] in {"unavailable", "unsupported"}:
            if item["value"] is not None or item["source"] is not None:
                raise StateValidationError(f"runtime_context {name} must be null")
        else:
            raise StateValidationError(f"runtime_context has invalid {name} status")
    if context["ruleset_fingerprint"]["status"] != "unsupported":
        raise StateValidationError("runtime_context cannot claim a ruleset fingerprint")
    if context["game_family"]["status"] != "unavailable" or context["game_build"]["status"] != "unavailable":
        raise StateValidationError("runtime_context cannot invent game family or build")
    if context["active_content"]["status"] != "unsupported":
        raise StateValidationError("runtime_context cannot claim active content")
    identifier_patterns = {
        "game_speed": GAME_SPEED_TYPE_PATTERN,
        "difficulty": HANDICAP_TYPE_PATTERN,
        "world_size": WORLD_SIZE_TYPE_PATTERN,
        "civilization": CIVILIZATION_TYPE_PATTERN,
    }
    for name, pattern in identifier_patterns.items():
        item = context[name]
        if item["status"] == "available" and not pattern.fullmatch(item["value"]):
            raise StateValidationError(f"runtime_context has invalid {name} identifier")
    map_script = context["map_script"]
    if map_script["status"] == "available":
        value = map_script["value"]
        if (
            len(value) > 512
            or value.startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:", value)
            or ".." in value.replace("\\", "/").split("/")
            or "\x00" in value
        ):
            raise StateValidationError("runtime_context has unsafe map_script")


def _validate_technology_ids(values: object, field: str) -> None:
    if not isinstance(values, list):
        raise StateValidationError(f"{field} must be a list")
    if values != sorted(values):
        raise StateValidationError(f"{field} must use stable sorted order")
    if len(set(values)) != len(values):
        raise StateValidationError(f"{field} contains duplicates")
    if any(
        not isinstance(value, str) or not TECH_TYPE_PATTERN.fullmatch(value)
        for value in values
    ):
        raise StateValidationError(
            f"{field} contains an invalid technology identifier"
        )


def _validate_ordinary_move_targets(unit: dict[str, object]) -> None:
    targets = unit.get("ordinary_move_targets")
    if not isinstance(targets, list):
        raise StateValidationError(
            f"unit {unit.get('id')} has invalid ordinary_move_targets"
        )
    if len(targets) > 6:
        raise StateValidationError(
            f"unit {unit.get('id')} has too many ordinary_move_targets"
        )
    normalized: list[tuple[int, int]] = []
    for target in targets:
        if not isinstance(target, dict) or set(target) != {"x", "y"}:
            raise StateValidationError(
                f"unit {unit.get('id')} has malformed ordinary move target"
            )
        values: list[int] = []
        for coordinate in ("x", "y"):
            value = target[coordinate]
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 0 <= value <= MAX_MAP_COORDINATE
            ):
                raise StateValidationError(
                    f"unit {unit.get('id')} has invalid move target {coordinate}"
                )
            values.append(value)
        normalized.append((values[0], values[1]))
    if normalized != sorted(normalized):
        raise StateValidationError(
            f"unit {unit.get('id')} ordinary_move_targets are not sorted"
        )
    if len(set(normalized)) != len(normalized):
        raise StateValidationError(
            f"unit {unit.get('id')} ordinary_move_targets contain duplicates"
        )


def _validate_worker_state(unit: dict[str, object]) -> None:
    unit_id = unit.get("id")
    plot = unit.get("current_plot")
    expected_plot_fields = {
        "terrain_type",
        "feature_type",
        "resource_type",
        "improvement_type",
        "route_type",
        "owner_id",
        "is_hills",
        "is_water",
        "is_fresh_water",
    }
    if not isinstance(plot, dict) or set(plot) != expected_plot_fields:
        raise StateValidationError(f"unit {unit_id} has malformed current_plot")
    _validate_worker_identifier(
        plot["terrain_type"], TERRAIN_TYPE_PATTERN, "terrain_type", unit_id
    )
    for field, pattern in (
        ("feature_type", FEATURE_TYPE_PATTERN),
        ("resource_type", RESOURCE_TYPE_PATTERN),
        ("improvement_type", IMPROVEMENT_TYPE_PATTERN),
        ("route_type", ROUTE_TYPE_PATTERN),
    ):
        value = plot[field]
        if value is not None:
            _validate_worker_identifier(value, pattern, field, unit_id)
    owner_id = plot["owner_id"]
    if owner_id is not None and (
        not isinstance(owner_id, int)
        or isinstance(owner_id, bool)
        or owner_id < 0
    ):
        raise StateValidationError(f"unit {unit_id} has invalid plot owner_id")
    for field in ("is_hills", "is_water", "is_fresh_water"):
        if not isinstance(plot[field], bool):
            raise StateValidationError(f"unit {unit_id} has invalid plot {field}")

    current_build = unit.get("current_build_type")
    if current_build is not None:
        _validate_worker_identifier(
            current_build, BUILD_TYPE_PATTERN, "current_build_type", unit_id
        )

    actions = unit.get("ordinary_build_actions")
    if not isinstance(actions, list):
        raise StateValidationError(
            f"unit {unit_id} has invalid ordinary_build_actions"
        )
    if len(actions) > MAX_ORDINARY_WORKER_BUILDS_PER_UNIT:
        raise StateValidationError(
            f"unit {unit_id} has too many ordinary_build_actions"
        )
    normalized: list[tuple[str, str]] = []
    for action in actions:
        if not isinstance(action, dict) or set(action) != {
            "build_type",
            "improvement_type",
        }:
            raise StateValidationError(
                f"unit {unit_id} has malformed ordinary build action"
            )
        build_type = action["build_type"]
        improvement_type = action["improvement_type"]
        _validate_worker_identifier(
            build_type, BUILD_TYPE_PATTERN, "build_type", unit_id
        )
        _validate_worker_identifier(
            improvement_type,
            IMPROVEMENT_TYPE_PATTERN,
            "improvement_type",
            unit_id,
        )
        normalized.append((build_type, improvement_type))
    if normalized != sorted(normalized):
        raise StateValidationError(
            f"unit {unit_id} ordinary_build_actions are not sorted"
        )
    if len({build_type for build_type, _ in normalized}) != len(normalized):
        raise StateValidationError(
            f"unit {unit_id} ordinary_build_actions contain duplicate builds"
        )


def _validate_worker_identifier(
    value: object,
    pattern: re.Pattern[str],
    field: str,
    unit_id: object,
) -> None:
    if (
        not isinstance(value, str)
        or len(value) > MAX_BUILD_IDENTIFIER_LENGTH
        or not pattern.fullmatch(value)
    ):
        raise StateValidationError(f"unit {unit_id} has invalid {field}")


def _validate_records(records: list[dict[str, object]], kind: str) -> None:
    identifiers: set[int] = set()
    for record in records:
        if not isinstance(record, dict):
            raise StateValidationError(f"{kind} record must be an object")
        identifier = record.get("id")
        if (
            not isinstance(identifier, int)
            or isinstance(identifier, bool)
            or identifier < 0
        ):
            raise StateValidationError(f"{kind} has invalid id")
        if identifier in identifiers:
            raise StateValidationError(f"duplicate {kind} id: {identifier}")
        identifiers.add(identifier)
        for coordinate in ("x", "y"):
            value = record.get(coordinate)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise StateValidationError(f"{kind} {identifier} has invalid {coordinate}")
