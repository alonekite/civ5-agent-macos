from __future__ import annotations

from typing import Protocol, runtime_checkable

from .actions import (
    ALLOWED_ACTIONS,
    MAX_COMMAND_MESSAGE_LENGTH,
    CommandValidationError,
    validate_command,
)
from .ipc import MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES
from .models import Command, CommandResult, GameState
from .validation import (
    NO_END_TURN_BLOCKING_TYPE,
    SUPPORTED_LIVE_STATE_SCHEMA_VERSIONS,
    validate_live_state,
)
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
    "MAX_REQUEST_BYTES",
    "MAX_RESPONSE_BYTES",
    "MAX_COMMAND_MESSAGE_LENGTH",
    "NO_END_TURN_BLOCKING_TYPE",
    "SUPPORTED_LIVE_STATE_SCHEMA_VERSIONS",
    "WatcherBridgeClient",
    "validate_command",
    "validate_live_state",
]
