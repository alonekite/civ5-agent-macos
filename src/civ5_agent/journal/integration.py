from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

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

    def record_snapshot(self, state: GameState) -> None:
        validated = validate_live_state(state)
        self.store.append(
            "snapshot",
            {"state": asdict(validated)},
            bridge_session_id=self.bridge_session_id,
            turn=validated.turn,
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
        return True


def _result_turn(result: dict[str, Any]) -> int | None:
    for field in ("before", "after"):
        state = result.get(field)
        if not isinstance(state, dict):
            continue
        turn = state.get("turn")
        if isinstance(turn, int) and not isinstance(turn, bool) and turn >= 0:
            return turn
    return None
