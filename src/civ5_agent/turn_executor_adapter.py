from __future__ import annotations

from .models import Command, CommandResult
from .turn_executor import EventSink, execute_turn_plan, reconcile_turn_plan
from .turn_plan import ExecutionReport, PlannedAction, TurnPlan
from .watcher_client import WatcherBridgeClient


class WatcherTurnExecutor(WatcherBridgeClient):
    def execute_action(
        self,
        action: PlannedAction,
        bridge_session_id: str,
    ) -> CommandResult:
        return self.execute_command(
            Command(
                action=action.action,
                args=action.arguments,
                id=action.command_id,
            ),
            bridge_session_id,
        )

    def lookup_action_result(
        self,
        action: PlannedAction,
        bridge_session_id: str,
    ) -> CommandResult | None:
        return self.lookup_command_result(
            Command(
                action=action.action,
                args=action.arguments,
                id=action.command_id,
            ),
            bridge_session_id,
        )

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

    def reconcile(
        self,
        plan: TurnPlan,
        report: ExecutionReport,
    ) -> ExecutionReport:
        return reconcile_turn_plan(
            plan,
            report,
            self.read_state,
            self.lookup_action_result,
        )
