from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .actions import validate_command
from .identity import validate_bridge_session_id
from .ipc import default_socket_path, request
from .models import Command, CommandResult, GameState
from .validation import validate_live_state


@dataclass(frozen=True)
class WatcherBridgeClient:
    socket_path: Path = field(default_factory=default_socket_path)
    timeout: float = 3.0
    verify_timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if not 0 < self.verify_timeout <= 120:
            raise ValueError("verify_timeout must be greater than zero and at most 120")

    def read_state(self) -> tuple[str, GameState]:
        response = request(
            {"op": "read_state"},
            socket_path=self.socket_path,
            timeout=self.timeout,
        )
        if not response.get("ok") or not isinstance(response.get("state"), dict):
            raise ValueError(str(response.get("error", "watcher omitted state")))
        session_id = validate_bridge_session_id(response.get("bridge_session_id"))
        state = validate_live_state(GameState(**response["state"]))
        return session_id, state

    def execute_command(
        self,
        command: Command,
        bridge_session_id: str,
    ) -> CommandResult:
        normalized = validate_command(command)
        session_id = validate_bridge_session_id(bridge_session_id)
        response = request(
            {
                "op": normalized.action,
                "id": normalized.id,
                "bridge_session_id": session_id,
                **normalized.args,
                "verify_timeout": self.verify_timeout,
            },
            socket_path=self.socket_path,
            timeout=self.timeout + self.verify_timeout + 5,
        )
        return self._command_result(response, normalized, session_id)

    def lookup_command_result(
        self,
        command: Command,
        bridge_session_id: str,
    ) -> CommandResult | None:
        normalized = validate_command(command)
        session_id = validate_bridge_session_id(bridge_session_id)
        response = request(
            {
                "op": "command_status",
                "command_id": normalized.id,
                "bridge_session_id": session_id,
            },
            socket_path=self.socket_path,
            timeout=self.timeout + self.verify_timeout + 5,
        )
        if not response.get("ok"):
            raise ValueError(str(response.get("error", "watcher rejected lookup")))
        if validate_bridge_session_id(response.get("bridge_session_id")) != session_id:
            raise ValueError("watcher bridge session changed during lookup")
        found = response.get("found")
        if found is False:
            return None
        if found is not True:
            raise ValueError("watcher returned malformed command status")
        if response.get("action") != normalized.action:
            raise ValueError("cached command action does not match request")
        if response.get("arguments") != normalized.args:
            raise ValueError("cached command arguments do not match request")
        return self._command_result(response, normalized, session_id, cached=True)

    @staticmethod
    def _command_result(
        response: dict[str, object],
        command: Command,
        session_id: str,
        *,
        cached: bool = False,
    ) -> CommandResult:
        if not response.get("ok"):
            label = "lookup" if cached else "action"
            raise ValueError(str(response.get("error", f"watcher rejected {label}")))
        if validate_bridge_session_id(response.get("bridge_session_id")) != session_id:
            label = "lookup" if cached else "action"
            raise ValueError(f"watcher bridge session changed during {label}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise ValueError("watcher omitted command result")
        try:
            command_result = CommandResult(**result)
        except TypeError as error:
            raise ValueError("watcher returned malformed command result") from error
        if command_result.id != command.id:
            raise ValueError("command result id does not match request")
        if command_result.status not in {"success", "error"}:
            raise ValueError("watcher command result must be terminal")
        if (
            not isinstance(command_result.message, str)
            or len(command_result.message) > 1024
        ):
            raise ValueError("watcher command result message is invalid or too long")
        if not isinstance(command_result.before, dict) or not isinstance(
            command_result.after, dict
        ):
            raise ValueError("watcher command result requires before and after states")
        validate_live_state(GameState(**command_result.before))
        validate_live_state(GameState(**command_result.after))
        return command_result
