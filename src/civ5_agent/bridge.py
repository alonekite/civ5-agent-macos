from __future__ import annotations

from typing import Protocol, runtime_checkable

from .actions import ALLOWED_ACTIONS, CommandValidationError, validate_command
from .models import Command, CommandResult, GameState
from .watcher_client import WatcherBridgeClient


@runtime_checkable
class Bridge(Protocol):
    def read_state(self) -> tuple[str, GameState]: ...

    def execute_command(
        self,
        command: Command,
        bridge_session_id: str,
    ) -> CommandResult: ...

    def lookup_command_result(
        self,
        command: Command,
        bridge_session_id: str,
    ) -> CommandResult | None: ...


__all__ = [
    "ALLOWED_ACTIONS",
    "Bridge",
    "Command",
    "CommandResult",
    "CommandValidationError",
    "GameState",
    "WatcherBridgeClient",
    "validate_command",
]
