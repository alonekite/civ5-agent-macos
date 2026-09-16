import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from civ5_agent.models import GameState
from civ5_agent.turn_executor_adapter import WatcherTurnExecutor
from civ5_agent.turn_plan import PlannedAction, make_turn_plan

SESSION_ID = "123e4567-e89b-42d3-a456-426614174050"
PLAN_ID = "123e4567-e89b-42d3-a456-426614174051"
COMMAND_ID = "123e4567-e89b-42d3-a456-426614174052"


def state(turn=4):
    return GameState(
        schema_version=2,
        turn=turn,
        active_player=0,
        gold=12,
        turn_active=True,
        can_end_turn=True,
        end_turn_blocking_type=0,
        research={"id": 1, "type": "TECH_POTTERY", "progress": 0, "cost": 40},
        cities=[
            {
                "id": 4,
                "name": "City",
                "x": 10,
                "y": 11,
                "population": 2,
                "production": "SCOUT",
            }
        ],
        units=[
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 0,
            }
        ],
    )


class WatcherTurnExecutorTest(unittest.TestCase):
    def test_executes_complete_plan_through_watcher_protocol(self):
        before = state()
        after = state(turn=5)
        action = PlannedAction(COMMAND_ID, "end_turn", {})
        plan = make_turn_plan(before, SESSION_ID, (action,), plan_id=PLAN_ID)
        responses = (
            {
                "ok": True,
                "bridge_session_id": SESSION_ID,
                "state": asdict(before),
            },
            {
                "ok": True,
                "bridge_session_id": SESSION_ID,
                "result": {
                    "id": COMMAND_ID,
                    "status": "success",
                    "message": "verified",
                    "before": asdict(before),
                    "after": asdict(after),
                },
            },
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "civ5_agent.turn_executor_adapter.request",
            side_effect=responses,
        ) as send:
            adapter = WatcherTurnExecutor(Path(directory) / "agent.sock")
            report = adapter.execute(plan)

        self.assertEqual(report.status, "completed")
        self.assertEqual(send.call_count, 2)
        action_request = send.call_args_list[1].args[0]
        self.assertEqual(action_request["id"], COMMAND_ID)
        self.assertEqual(action_request["bridge_session_id"], SESSION_ID)

    def test_rejects_changed_session_in_action_response(self):
        action = PlannedAction(COMMAND_ID, "end_turn", {})
        adapter = WatcherTurnExecutor()
        response = {
            "ok": True,
            "bridge_session_id": "123e4567-e89b-42d3-a456-426614174099",
            "result": {},
        }
        with patch(
            "civ5_agent.turn_executor_adapter.request",
            return_value=response,
        ), self.assertRaisesRegex(ValueError, "session changed"):
            adapter.execute_action(action, SESSION_ID)

    def test_validates_timeouts_before_contacting_watcher(self):
        with self.assertRaisesRegex(ValueError, "timeout"):
            WatcherTurnExecutor(timeout=0)
        with self.assertRaisesRegex(ValueError, "verify_timeout"):
            WatcherTurnExecutor(verify_timeout=121)

    def test_looks_up_cached_result_without_resubmitting_action(self):
        action = PlannedAction(COMMAND_ID, "skip_unit", {"unit_id": 8})
        response = {
            "ok": True,
            "bridge_session_id": SESSION_ID,
            "found": True,
            "action": "skip_unit",
            "arguments": {"unit_id": 8},
            "result": {
                "id": COMMAND_ID,
                "status": "success",
                "message": "verified",
                "before": asdict(state()),
                "after": asdict(state()),
            },
        }
        with patch(
            "civ5_agent.turn_executor_adapter.request",
            return_value=response,
        ) as send:
            result = WatcherTurnExecutor().lookup_action_result(action, SESSION_ID)

        self.assertEqual(result.id, COMMAND_ID)
        self.assertEqual(send.call_args.args[0]["op"], "command_status")
        self.assertNotIn("unit_id", send.call_args.args[0])

    def test_cached_result_lookup_distinguishes_missing_and_mismatch(self):
        action = PlannedAction(COMMAND_ID, "skip_unit", {"unit_id": 8})
        missing = {
            "ok": True,
            "bridge_session_id": SESSION_ID,
            "found": False,
        }
        with patch(
            "civ5_agent.turn_executor_adapter.request",
            return_value=missing,
        ):
            self.assertIsNone(
                WatcherTurnExecutor().lookup_action_result(action, SESSION_ID)
            )

        mismatched = {
            **missing,
            "found": True,
            "action": "end_turn",
            "arguments": {},
            "result": {},
        }
        with patch(
            "civ5_agent.turn_executor_adapter.request",
            return_value=mismatched,
        ), self.assertRaisesRegex(ValueError, "action does not match"):
            WatcherTurnExecutor().lookup_action_result(action, SESSION_ID)


if __name__ == "__main__":
    unittest.main()
