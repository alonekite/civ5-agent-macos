from __future__ import annotations

import re

from .models import GameState


TECH_TYPE_PATTERN = re.compile(r"TECH_[A-Z0-9_]+\Z")


class StateValidationError(ValueError):
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
    if state.schema_version not in {2, 3, 4, 5}:
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
    return state


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
