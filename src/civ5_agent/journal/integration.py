from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from ..identity import validate_command_id
from ..models import GameState
from ..validation import validate_live_state
from .store import JournalStore


class JournalCapture:
    def __init__(self, store: JournalStore, bridge_session_id: str):
        self.store = store
        self.bridge_session_id = bridge_session_id

    @classmethod
    def start(
        cls,
        path: Path,
        bridge_session_id: str,
        mode: Literal["new", "resume"],
    ) -> JournalCapture:
        if mode == "new":
            store = JournalStore.create(path, bridge_session_id)
        elif mode == "resume":
            store = JournalStore.open(path)
            store.bind_session(bridge_session_id)
        else:
            raise ValueError(f"unsupported journal mode: {mode!r}")
        return cls(store, bridge_session_id)

    def record_snapshot(
        self,
        state: GameState,
        *,
        previous_turn: int | None = None,
    ) -> None:
        validated = validate_live_state(state)
        if previous_turn is not None and (
            isinstance(previous_turn, bool)
            or not isinstance(previous_turn, int)
            or previous_turn < 0
        ):
            raise ValueError("previous_turn must be a non-negative integer")
        if previous_turn is not None and validated.turn < previous_turn:
            raise ValueError("observed turn cannot move backwards")
        if previous_turn is not None and validated.turn > previous_turn:
            self.store.append(
                "turn_transition",
                {
                    "from_turn": previous_turn,
                    "to_turn": validated.turn,
                    "cause": "observed_state",
                },
                bridge_session_id=self.bridge_session_id,
                turn=validated.turn,
            )
        self.store.append(
            "snapshot",
            {"state": asdict(validated)},
            bridge_session_id=self.bridge_session_id,
            turn=validated.turn,
        )

    def record_command_submitted(
        self,
        operation: str,
        arguments: dict[str, Any],
        command_id: str,
        turn: int,
    ) -> None:
        self.store.append(
            "command_submitted",
            {
                "id": command_id,
                "operation": operation,
                "arguments": arguments,
            },
            bridge_session_id=self.bridge_session_id,
            turn=turn,
        )

    def record_command_result(
        self,
        operation: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> bool:
        turn = _result_turn(result)
        if turn is None:
            return False
        self.store.append(
            "command_result",
            {
                "operation": operation,
                "arguments": arguments,
                "result": result,
            },
            bridge_session_id=self.bridge_session_id,
            turn=turn,
        )
        if result.get("status") == "error":
            self.store.append(
                "verification_error",
                {
                    "id": result.get("id"),
                    "operation": operation,
                    "stage": "execution_or_postcondition",
                    "message": result.get("message"),
                },
                bridge_session_id=self.bridge_session_id,
                turn=turn,
            )
        return True

    def record_command_outcome_unknown(
        self,
        operation: str,
        command_id: str,
        turn: int,
        message: str,
    ) -> None:
        if not isinstance(operation, str) or not operation:
            raise ValueError("operation must be a non-empty string")
        normalized_id = validate_command_id(command_id)
        if not isinstance(message, str) or not message:
            raise ValueError("message must be a non-empty string")
        self.store.append(
            "verification_error",
            {
                "id": normalized_id,
                "operation": operation,
                "stage": "execution_outcome_unknown",
                "message": message[:1024],
            },
            bridge_session_id=self.bridge_session_id,
            turn=turn,
        )


def _result_turn(result: dict[str, Any]) -> int | None:
    turns = []
    for field in ("before", "after"):
        state = result.get(field)
        if not isinstance(state, dict):
            continue
        turn = state.get("turn")
        if isinstance(turn, int) and not isinstance(turn, bool) and turn >= 0:
            turns.append(turn)
    return max(turns, default=None)
