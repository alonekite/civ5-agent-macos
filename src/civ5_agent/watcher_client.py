from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .actions import MAX_COMMAND_MESSAGE_LENGTH, validate_command
from .errors import ProtocolError, TransportError
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
        response = self._request(
            {"op": "read_state"},
            timeout=self.timeout,
        )
        if not response.get("ok") or not isinstance(response.get("state"), dict):
            raise ProtocolError(str(response.get("error", "watcher omitted state")))
        try:
            session_id = validate_bridge_session_id(
                response.get("bridge_session_id")
            )
            state = validate_live_state(GameState(**response["state"]))
        except (TypeError, ValueError) as error:
            raise ProtocolError(str(error)) from error
        return session_id, state

    def execute_command(
        self,
        command: Command,
        bridge_session_id: str,
    ) -> CommandResult:
        normalized = validate_command(command)
        session_id = validate_bridge_session_id(bridge_session_id)
        response = self._request(
            {
                "op": normalized.action,
                "id": normalized.id,
                "bridge_session_id": session_id,
                **normalized.args,
                "verify_timeout": self.verify_timeout,
            },
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
        response = self._request(
            {
                "op": "command_status",
                "command_id": normalized.id,
                "bridge_session_id": session_id,
            },
            timeout=self.timeout + self.verify_timeout + 5,
        )
        if not response.get("ok"):
            raise ProtocolError(str(response.get("error", "watcher rejected lookup")))
        try:
            returned_session_id = validate_bridge_session_id(
                response.get("bridge_session_id")
            )
        except ValueError as error:
            raise ProtocolError("watcher returned invalid bridge session") from error
        if returned_session_id != session_id:
            raise ProtocolError("watcher bridge session changed during lookup")
        found = response.get("found")
        if found is False:
            return None
        if found is not True:
            raise ProtocolError("watcher returned malformed command status")
        if response.get("action") != normalized.action:
            raise ProtocolError("cached command action does not match request")
        if response.get("arguments") != normalized.args:
            raise ProtocolError("cached command arguments do not match request")
        return self._command_result(response, normalized, session_id, cached=True)

    def _request(
        self,
        payload: dict[str, Any],
        *,
        timeout: float,
    ) -> dict[str, Any]:
        try:
            return request(
                payload,
                socket_path=self.socket_path,
                timeout=timeout,
            )
        except (ConnectionError, OSError, TimeoutError, ValueError) as error:
            raise TransportError(str(error)) from error

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
            raise ProtocolError(
                str(response.get("error", f"watcher rejected {label}"))
            )
        try:
            returned_session_id = validate_bridge_session_id(
                response.get("bridge_session_id")
            )
        except ValueError as error:
            if cached:
                raise ProtocolError("watcher returned invalid bridge session") from error
            raise TransportError("watcher returned invalid bridge session") from error
        if returned_session_id != session_id:
            label = "lookup" if cached else "action"
            _invalid_result(
                cached,
                f"watcher bridge session changed during {label}",
            )
        result = response.get("result")
        if not isinstance(result, dict):
            _invalid_result(cached, "watcher omitted command result")
        try:
            command_result = CommandResult(**result)
        except TypeError as error:
            if cached:
                raise ProtocolError("watcher returned malformed command result") from error
            raise TransportError("watcher returned malformed command result") from error
        if command_result.id != command.id:
            _invalid_result(cached, "command result id does not match request")
        if command_result.status not in {"success", "error"}:
            _invalid_result(cached, "watcher command result must be terminal")
        if (
            not isinstance(command_result.message, str)
            or len(command_result.message) > MAX_COMMAND_MESSAGE_LENGTH
        ):
            _invalid_result(
                cached,
                "watcher command result message is invalid or too long",
            )
        if not isinstance(command_result.before, dict) or not isinstance(
            command_result.after, dict
        ):
            _invalid_result(
                cached,
                "watcher command result requires before and after states",
            )
        try:
            validate_live_state(GameState(**command_result.before))
            validate_live_state(GameState(**command_result.after))
        except (TypeError, ValueError) as error:
            if cached:
                raise ProtocolError(str(error)) from error
            raise TransportError(str(error)) from error
        return command_result


def _invalid_result(cached: bool, message: str) -> None:
    if cached:
        raise ProtocolError(message)
    raise TransportError(message)
