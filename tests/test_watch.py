import threading
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from civ5_agent.audit import CommandAuditLog
from civ5_agent.models import CommandResult, GameState
from civ5_agent.watch import make_control_handler


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
        result = CommandResult(id="test-id", status="success")
        with patch("civ5_agent.watch.execute_end_turn", return_value=result) as execute:
            response = self.handler(
                {"op": "end_turn", "id": "test-id", "verify_timeout": 47}
            )
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["id"], "test-id")
        self.assertEqual(execute.call_args.kwargs["verify_timeout"], 47.0)

    def test_forwards_skip_unit_identifier(self):
        result = CommandResult(id="skip-id", status="success")
        with patch("civ5_agent.watch.execute_skip_unit", return_value=result) as execute:
            response = self.handler(
                {"op": "skip_unit", "id": "skip-id", "unit_id": 8}
            )
        self.assertTrue(response["ok"])
        command = execute.call_args.args[2]
        self.assertEqual(command.action, "skip_unit")
        self.assertEqual(command.args, {"unit_id": 8})

    def test_audits_command_result(self):
        result = CommandResult(id="audit-id", status="success")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "commands.jsonl"
            handler = make_control_handler(
                self.client,
                172,
                threading.Lock(),
                CommandAuditLog(path),
            )
            with patch("civ5_agent.watch.execute_end_turn", return_value=result):
                response = handler({"op": "end_turn", "id": "audit-id"})
            record = json.loads(path.read_text())
        self.assertTrue(response["ok"])
        self.assertEqual(record["operation"], "end_turn")
        self.assertEqual(record["result"]["id"], "audit-id")


if __name__ == "__main__":
    unittest.main()
