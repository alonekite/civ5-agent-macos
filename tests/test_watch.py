import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from civ5_agent.audit import CommandAuditLog
from civ5_agent.models import CommandResult, GameState
from civ5_agent.preflight import UnsafeSessionError
from civ5_agent.watch import make_control_handler

END_TURN_ID = "123e4567-e89b-42d3-a456-426614174000"
SKIP_ID = "123e4567-e89b-42d3-a456-426614174001"
AUDIT_ID = "123e4567-e89b-42d3-a456-426614174002"


class _FakeClient:
    def read_game_state(self, state_id):
        return GameState(
            schema_version=2,
            turn=3,
            active_player=0,
            gold=9,
            turn_active=True,
            can_end_turn=True,
            end_turn_blocking_type=0,
        )


class WatchControlHandlerTest(unittest.TestCase):
    def setUp(self):
        self.client = _FakeClient()
        self.handler = make_control_handler(self.client, 172, threading.Lock())

    def test_reads_validated_state(self):
        response = self.handler({"op": "read_state"})
        self.assertTrue(response["ok"])
        self.assertEqual(response["state"]["turn"], 3)

    def test_rejects_invalid_verification_timeout(self):
        response = self.handler({"op": "end_turn", "verify_timeout": 121})
        self.assertFalse(response["ok"])
        response = self.handler({"op": "end_turn", "verify_timeout": True})
        self.assertFalse(response["ok"])

    def test_forwards_verification_timeout(self):
        result = CommandResult(id=END_TURN_ID, status="success")
        with patch("civ5_agent.watch.execute_end_turn", return_value=result) as execute:
            response = self.handler(
                {"op": "end_turn", "id": END_TURN_ID, "verify_timeout": 47}
            )
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["id"], END_TURN_ID)
        self.assertEqual(execute.call_args.kwargs["verify_timeout"], 47.0)

    def test_refuses_write_when_live_safety_check_fails(self):
        def reject_unsafe_session():
            raise UnsafeSessionError("firewall disabled")

        handler = make_control_handler(
            self.client,
            172,
            threading.Lock(),
            safety_check=reject_unsafe_session,
        )
        with patch("civ5_agent.watch.execute_end_turn") as execute:
            response = handler({"op": "end_turn", "id": "unsafe-id"})
        self.assertFalse(response["ok"])
        self.assertIn("firewall disabled", response["error"])
        execute.assert_not_called()

    def test_forwards_skip_unit_identifier(self):
        result = CommandResult(id=SKIP_ID, status="success")
        with patch("civ5_agent.watch.execute_skip_unit", return_value=result) as execute:
            response = self.handler(
                {"op": "skip_unit", "id": SKIP_ID, "unit_id": 8}
            )
        self.assertTrue(response["ok"])
        command = execute.call_args.args[2]
        self.assertEqual(command.action, "skip_unit")
        self.assertEqual(command.args, {"unit_id": 8})

    def test_audits_command_result(self):
        result = CommandResult(id=AUDIT_ID, status="success")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "commands.jsonl"
            handler = make_control_handler(
                self.client,
                172,
                threading.Lock(),
                CommandAuditLog(path),
            )
            with patch("civ5_agent.watch.execute_end_turn", return_value=result):
                response = handler({"op": "end_turn", "id": AUDIT_ID})
            record = json.loads(path.read_text())
        self.assertTrue(response["ok"])
        self.assertEqual(record["operation"], "end_turn")
        self.assertEqual(record["result"]["id"], AUDIT_ID)
        self.assertEqual(record["arguments"], {})

    def test_rejects_non_uuid_command_id_before_execution(self):
        with patch("civ5_agent.watch.execute_end_turn") as execute:
            response = self.handler({"op": "end_turn", "id": "not-a-uuid"})
        self.assertFalse(response["ok"])
        self.assertIn("UUIDv4", response["error"])
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
