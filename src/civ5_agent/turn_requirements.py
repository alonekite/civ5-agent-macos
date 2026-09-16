from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import GameState
from .validation import validate_live_state


@dataclass(frozen=True)
class TurnRequirement:
    kind: Literal[
        "turn_inactive",
        "research_choice",
        "city_production",
        "unit_orders",
        "end_turn_blocked",
    ]
    subject_id: int | None = None
    mode: str | None = None
    candidates: tuple[str, ...] = ()
    blocking_type: int | None = None


def inspect_turn_requirements(state: GameState) -> tuple[TurnRequirement, ...]:
    validated = validate_live_state(state)
    if not validated.turn_active:
        return (TurnRequirement("turn_inactive"),)

    requirements: list[TurnRequirement] = []
    if validated.schema_version >= 5 and validated.research_choice["required"]:
        mode = validated.research_choice["mode"]
        candidates = (
            tuple(validated.researchable_technologies) if mode == "normal" else ()
        )
        requirements.append(
            TurnRequirement(
                "research_choice",
                mode=mode,
                candidates=candidates,
            )
        )
    elif validated.schema_version < 5 and validated.research is None:
        requirements.append(TurnRequirement("research_choice", mode="legacy_unknown"))

    for city in sorted(validated.cities, key=lambda value: value["id"]):
        if not city.get("production"):
            requirements.append(
                TurnRequirement("city_production", subject_id=city["id"])
            )

    for unit in sorted(validated.units, key=lambda value: value["id"]):
        needs_orders = (
            unit["ready_to_move"] is True
            if validated.schema_version >= 4
            else unit["moves"] > 0
        )
        if needs_orders:
            requirements.append(TurnRequirement("unit_orders", subject_id=unit["id"]))

    if not validated.can_end_turn:
        requirements.append(
            TurnRequirement(
                "end_turn_blocked",
                blocking_type=validated.end_turn_blocking_type,
            )
        )
    return tuple(requirements)
