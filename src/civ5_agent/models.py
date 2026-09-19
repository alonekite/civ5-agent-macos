from dataclasses import asdict, dataclass, field
from typing import Any, Literal
from uuid import uuid4

@dataclass
class GameState:
    schema_version: int | None = None
    turn: int | None = None
    active_player: int | None = None
    gold: int | None = None
    gold_per_turn: int | None = None
    science_per_turn: int | None = None
    happiness: int | None = None
    culture: int | None = None
    culture_per_turn: int | None = None
    score: int | None = None
    current_era: int | None = None
    player_name: str | None = None
    civilization: str | None = None
    turn_active: bool | None = None
    can_end_turn: bool | None = None
    end_turn_blocking_type: int | None = None
    cities: list[dict[str, Any]] = field(default_factory=list)
    units: list[dict[str, Any]] = field(default_factory=list)
    diplomacy: list[dict[str, Any]] = field(default_factory=list)
    victory: dict[str, Any] | None = None
    research: dict[str, Any] | None = None
    researched_technologies: list[str] = field(default_factory=list)
    researchable_technologies: list[str] = field(default_factory=list)
    research_choice: dict[str, Any] | None = None
    research_forecast: dict[str, Any] | None = None
    runtime_context: dict[str, Any] | None = None

@dataclass
class Command:
    action: str
    args: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))

@dataclass
class CommandResult:
    id: str
    status: Literal["pending", "success", "error"]
    message: str = ""
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


def game_state_to_dict(state: GameState) -> dict[str, Any]:
    """Serialize one state without adding schema-8 fields to legacy payloads."""
    value = asdict(state)
    if state.schema_version is None or state.schema_version < 8:
        value.pop("research_forecast")
        value.pop("runtime_context")
    return value


def model_to_dict(value: Any) -> dict[str, Any]:
    """Serialize a dataclass while preserving legacy GameState wire shapes."""
    return game_state_to_dict(value) if isinstance(value, GameState) else asdict(value)
