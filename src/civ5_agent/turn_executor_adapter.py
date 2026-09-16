from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .identity import validate_bridge_session_id
from .ipc import default_socket_path, request
from .models import CommandResult, GameState
from .turn_executor import EventSink, execute_turn_plan
from .turn_plan import ExecutionReport, PlannedAction, TurnPlan
from .validation import validate_live_state


@dataclass(frozen=True)
class WatcherTurnExecutor:
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

    def execute_action(
        self,
        action: PlannedAction,
        bridge_session_id: str,
    ) -> CommandResult:
        session_id = validate_bridge_session_id(bridge_session_id)
        response = request(
            {
                "op": action.action,
                "id": action.command_id,
                "bridge_session_id": session_id,
                **action.arguments,
                "verify_timeout": self.verify_timeout,
            },
            socket_path=self.socket_path,
            timeout=self.timeout + self.verify_timeout + 5,
        )
        if not response.get("ok"):
            raise ValueError(str(response.get("error", "watcher rejected action")))
        if validate_bridge_session_id(response.get("bridge_session_id")) != session_id:
            raise ValueError("watcher bridge session changed during action")
        result = response.get("result")
        if not isinstance(result, dict):
            raise ValueError("watcher omitted command result")
        try:
            return CommandResult(**result)
        except TypeError as error:
            raise ValueError("watcher returned malformed command result") from error

    def lookup_action_result(
        self,
        action: PlannedAction,
        bridge_session_id: str,
    ) -> CommandResult | None:
        session_id = validate_bridge_session_id(bridge_session_id)
        response = request(
            {
                "op": "command_status",
                "command_id": action.command_id,
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
        if response.get("action") != action.action:
            raise ValueError("cached command action does not match TurnPlan")
        if response.get("arguments") != action.arguments:
            raise ValueError("cached command arguments do not match TurnPlan")
        result = response.get("result")
        if not isinstance(result, dict):
            raise ValueError("watcher omitted cached command result")
        try:
            command_result = CommandResult(**result)
        except TypeError as error:
            raise ValueError("watcher returned malformed cached command result") from error
        if command_result.id != action.command_id:
            raise ValueError("cached command result id does not match TurnPlan")
        return command_result

    def execute(
        self,
        plan: TurnPlan,
        event_sink: EventSink | None = None,
    ) -> ExecutionReport:
        return execute_turn_plan(
            plan,
            self.read_state,
            self.execute_action,
            event_sink,
        )
