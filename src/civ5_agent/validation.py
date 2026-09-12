from __future__ import annotations

from .models import GameState


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
    ):
        value = getattr(state, field)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise StateValidationError(f"{field} must be an integer when present")
    for field in ("turn_active", "can_end_turn"):
        if not isinstance(getattr(state, field), bool):
            raise StateValidationError(f"{field} must be a boolean")
    if state.schema_version != 2:
        raise StateValidationError(f"unsupported schema_version: {state.schema_version}")
    if state.turn is not None and state.turn < 0:
        raise StateValidationError("turn must be non-negative")
    if state.active_player is not None and state.active_player < 0:
        raise StateValidationError("active_player must be non-negative")

    if not isinstance(state.cities, list) or not isinstance(state.units, list):
        raise StateValidationError("cities and units must be lists")
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
    for unit in state.units:
        moves = unit.get("moves")
        if not isinstance(moves, int) or isinstance(moves, bool) or moves < 0:
            raise StateValidationError(f"unit {unit.get('id')} has invalid moves")
        for field in ("name", "type"):
            if not isinstance(unit.get(field), str):
                raise StateValidationError(f"unit {unit.get('id')} has invalid {field}")

    if state.research is not None:
        if not isinstance(state.research, dict):
            raise StateValidationError("research must be an object when present")
        for field in ("id", "progress", "cost"):
            value = state.research.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise StateValidationError(f"research has invalid {field}")
        if not isinstance(state.research.get("type"), str) or not state.research["type"]:
            raise StateValidationError("research has invalid type")
    return state


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
