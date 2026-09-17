from __future__ import annotations

import re
from typing import Any

from .errors import ValidationError
from .identity import validate_command_id
from .models import Command
from .validation import MAX_MAP_COORDINATE

_TECH_PATTERN = re.compile(r"TECH_[A-Z0-9_]+\Z")
_PRODUCTION_PATTERNS = {
    "unit": re.compile(r"UNIT_[A-Z0-9_]+\Z"),
    "building": re.compile(r"BUILDING_[A-Z0-9_]+\Z"),
    "project": re.compile(r"PROJECT_[A-Z0-9_]+\Z"),
}
ALLOWED_ACTIONS = frozenset(
    {"end_turn", "choose_research", "set_city_production", "skip_unit", "move_unit"}
)
MAX_COMMAND_MESSAGE_LENGTH = 1024


class CommandValidationError(ValidationError):
    pass


def validate_command(command: Command) -> Command:
    if not isinstance(command, Command):
        raise CommandValidationError("command must be a Command")
    try:
        command_id = validate_command_id(command.id)
    except ValueError as error:
        raise CommandValidationError(str(error)) from error
    if command.action not in ALLOWED_ACTIONS:
        raise CommandValidationError(f"unsupported action: {command.action!r}")
    if not isinstance(command.args, dict):
        raise CommandValidationError("command args must be an object")
    arguments = dict(command.args)
    if command.action == "end_turn":
        _require_fields(arguments, set(), command.action)
    elif command.action == "choose_research":
        _require_fields(arguments, {"tech_type"}, command.action)
        tech_type = arguments["tech_type"]
        if not isinstance(tech_type, str) or not _TECH_PATTERN.fullmatch(tech_type):
            raise CommandValidationError("tech_type must match TECH_[A-Z0-9_]+")
    elif command.action == "set_city_production":
        _require_fields(
            arguments,
            {"city_id", "kind", "item_type"},
            command.action,
        )
        city_id = arguments["city_id"]
        if isinstance(city_id, bool) or not isinstance(city_id, int) or city_id < 0:
            raise CommandValidationError("city_id must be a non-negative integer")
        kind = arguments["kind"]
        pattern = _PRODUCTION_PATTERNS.get(kind) if isinstance(kind, str) else None
        if pattern is None:
            raise CommandValidationError(
                "production kind must be unit, building, or project"
            )
        item_type = arguments["item_type"]
        if not isinstance(item_type, str) or not pattern.fullmatch(item_type):
            raise CommandValidationError(f"{kind} item_type has an invalid format")
    elif command.action == "skip_unit":
        _require_fields(arguments, {"unit_id"}, command.action)
        unit_id = arguments["unit_id"]
        if isinstance(unit_id, bool) or not isinstance(unit_id, int) or unit_id < 0:
            raise CommandValidationError("unit_id must be a non-negative integer")
    else:
        _require_fields(arguments, {"unit_id", "x", "y"}, command.action)
        unit_id = arguments["unit_id"]
        if isinstance(unit_id, bool) or not isinstance(unit_id, int) or unit_id < 0:
            raise CommandValidationError("unit_id must be a non-negative integer")
        for field in ("x", "y"):
            value = arguments[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= MAX_MAP_COORDINATE
            ):
                raise CommandValidationError(
                    f"{field} must be an integer from 0 to {MAX_MAP_COORDINATE}"
                )
    return Command(action=command.action, args=arguments, id=command_id)


def _require_fields(arguments: dict[str, Any], expected: set[str], action: str) -> None:
    if set(arguments) != expected:
        raise CommandValidationError(
            f"{action} argument fields must be exactly {sorted(expected)}"
        )
