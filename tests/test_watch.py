import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from civ5_agent.audit import CommandAuditLog
from civ5_agent.models import CommandResult, GameState
from civ5_agent.preflight import UnsafeSessionError
from civ5_agent.watch import main, make_control_handler

END_TURN_ID = "123e4567-e89b-42d3-a456-426614174000"
SKIP_ID = "123e4567-e89b-42d3-a456-426614174001"
AUDIT_ID = "123e4567-e89b-42d3-a456-426614174002"
MOVE_ID = "123e4567-e89b-42d3-a456-426614174003"
WORKER_BUILD_ID = "123e4567-e89b-42d3-a456-426614174004"


class _FakeClient:
    def read_game_state(self, state_id):
        return GameState(
            schema_version=2,
            turn=3,
            active_player=0,
            gold=9,
            turn_active=True,
            can_end_turn=True,
            end_turn_blocking_type=-1,
        )


class WatchControlHandlerTest(unittest.TestCase):
    def setUp(self):
        self.client = _FakeClient()
        self.handler = make_control_handler(self.client, 172, threading.Lock())
        self.session_id = self.handler({"op": "ping"})["bridge_session_id"]

    def write(self, request):
        return self.handler({**request, "bridge_session_id": self.session_id})

    def test_reads_validated_state(self):
        response = self.handler({"op": "read_state"})
        self.assertTrue(response["ok"])
        self.assertEqual(response["state"]["turn"], 3)
        self.assertEqual(response["bridge_session_id"], self.session_id)

    def test_rejects_missing_or_changed_session_before_write(self):
        missing = self.handler({"op": "end_turn", "id": END_TURN_ID})
        self.assertFalse(missing["ok"])
        self.assertIn("bridge_session_id", missing["error"])

        changed = self.handler(
            {
                "op": "end_turn",
                "id": END_TURN_ID,
                "bridge_session_id": "123e4567-e89b-42d3-a456-426614174099",
            }
        )
        self.assertFalse(changed["ok"])
        self.assertIn("session changed", changed["error"])

    def test_rejects_invalid_verification_timeout(self):
        response = self.write({"op": "end_turn", "verify_timeout": 121})
        self.assertFalse(response["ok"])
        response = self.write({"op": "end_turn", "verify_timeout": True})
        self.assertFalse(response["ok"])

    def test_forwards_verification_timeout(self):
        result = CommandResult(id=END_TURN_ID, status="success")
        with patch("civ5_agent.watch.execute_end_turn", return_value=result) as execute:
            response = self.write(
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
        session_id = handler({"op": "ping"})["bridge_session_id"]
        with patch("civ5_agent.watch.execute_end_turn") as execute:
            response = handler(
                {
                    "op": "end_turn",
                    "id": "unsafe-id",
                    "bridge_session_id": session_id,
                }
            )
        self.assertFalse(response["ok"])
        self.assertIn("firewall disabled", response["error"])
        execute.assert_not_called()

    def test_forwards_skip_unit_identifier(self):
        result = CommandResult(id=SKIP_ID, status="success")
        with patch("civ5_agent.watch.execute_skip_unit", return_value=result) as execute:
            response = self.write(
                {"op": "skip_unit", "id": SKIP_ID, "unit_id": 8}
            )
        self.assertTrue(response["ok"])
        command = execute.call_args.args[2]
        self.assertEqual(command.action, "skip_unit")
        self.assertEqual(command.args, {"unit_id": 8})

    def test_forwards_move_unit_identifier_and_coordinates(self):
        result = CommandResult(id=MOVE_ID, status="success")
        with patch("civ5_agent.watch.execute_move_unit", return_value=result) as execute:
            response = self.write(
                {"op": "move_unit", "id": MOVE_ID, "unit_id": 8, "x": 10, "y": 12}
            )
        self.assertTrue(response["ok"])
        command = execute.call_args.args[2]
        self.assertEqual(command.action, "move_unit")
        self.assertEqual(command.args, {"unit_id": 8, "x": 10, "y": 12})

    def test_forwards_exact_worker_build_arguments(self):
        result = CommandResult(id=WORKER_BUILD_ID, status="success")
        with patch(
            "civ5_agent.watch.execute_worker_build", return_value=result
        ) as execute:
            response = self.write(
                {
                    "op": "worker_build",
                    "id": WORKER_BUILD_ID,
                    "unit_id": 8,
                    "x": 9,
                    "y": 12,
                    "build_type": "BUILD_FARM",
                }
            )
        self.assertTrue(response["ok"])
        command = execute.call_args.args[2]
        self.assertEqual(command.action, "worker_build")
        self.assertEqual(
            command.args,
            {"unit_id": 8, "x": 9, "y": 12, "build_type": "BUILD_FARM"},
        )

    def test_worker_build_uuid_replay_is_exact_and_never_executes_twice(self):
        result = CommandResult(id=WORKER_BUILD_ID, status="success")
        request = {
            "op": "worker_build",
            "id": WORKER_BUILD_ID,
            "unit_id": 8,
            "x": 9,
            "y": 12,
            "build_type": "BUILD_FARM",
        }
        with patch(
            "civ5_agent.watch.execute_worker_build", return_value=result
        ) as execute:
            first = self.write(request)
            replay = self.write(request)
            mismatch = self.write({**request, "build_type": "BUILD_MINE"})
        self.assertTrue(first["ok"])
        self.assertTrue(replay["replayed"])
        self.assertFalse(mismatch["ok"])
        self.assertIn("different arguments", mismatch["error"])
        self.assertEqual(execute.call_count, 1)

    def test_worker_build_lifecycle_reaches_journal_and_private_audit(self):
        class RecordingJournal:
            def __init__(self):
                self.submitted = []
                self.results = []

            def record_command_submitted(self, operation, arguments, command_id, turn):
                self.submitted.append((operation, arguments, command_id, turn))

            def record_command_result(self, operation, arguments, result):
                self.results.append((operation, arguments, result))

        expected = {
            "unit_id": 8,
            "x": 9,
            "y": 12,
            "build_type": "BUILD_FARM",
        }
        journal = RecordingJournal()
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "commands.jsonl"
            handler = make_control_handler(
                self.client,
                172,
                threading.Lock(),
                CommandAuditLog(audit_path),
                bridge_session_id=self.session_id,
                journal_capture=journal,
            )
            result = CommandResult(id=WORKER_BUILD_ID, status="success")
            with patch(
                "civ5_agent.watch.execute_worker_build", return_value=result
            ):
                response = handler(
                    {
                        "op": "worker_build",
                        "id": WORKER_BUILD_ID,
                        "bridge_session_id": self.session_id,
                        **expected,
                    }
                )
            audit = json.loads(audit_path.read_text())
            permissions = audit_path.stat().st_mode & 0o777

        self.assertTrue(response["ok"])
        self.assertEqual(journal.submitted[0][0:3], ("worker_build", expected, WORKER_BUILD_ID))
        self.assertEqual(journal.results[0][0:2], ("worker_build", expected))
        self.assertEqual(audit["operation"], "worker_build")
        self.assertEqual(audit["arguments"], expected)
        self.assertEqual(permissions, 0o600)

    def test_worker_build_unknown_outcome_is_cached_and_never_retried(self):
        request = {
            "op": "worker_build",
            "id": WORKER_BUILD_ID,
            "unit_id": 8,
            "x": 9,
            "y": 12,
            "build_type": "BUILD_FARM",
        }
        with patch(
            "civ5_agent.watch.execute_worker_build",
            side_effect=ValueError("worker_build returned no valid marker"),
        ) as execute:
            first = self.write(request)
            replay = self.write(request)

        self.assertFalse(first["ok"])
        self.assertTrue(first["outcome_unknown"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(execute.call_count, 1)

    def test_replays_move_unit_uuid_without_executing_twice(self):
        result = CommandResult(id=MOVE_ID, status="success")
        request = {
            "op": "move_unit",
            "id": MOVE_ID,
            "unit_id": 8,
            "x": 10,
            "y": 12,
        }
        with patch(
            "civ5_agent.watch.execute_move_unit", return_value=result
        ) as execute:
            first = self.write(request)
            replay = self.write(request)
        self.assertTrue(first["ok"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(execute.call_count, 1)

    def test_move_unit_lifecycle_is_available_to_journal_composition(self):
        class RecordingJournal:
            def __init__(self):
                self.submitted = []
                self.results = []

            def record_command_submitted(self, operation, arguments, command_id, turn):
                self.submitted.append((operation, arguments, command_id, turn))

            def record_command_result(self, operation, arguments, result):
                self.results.append((operation, arguments, result))

        journal = RecordingJournal()
        handler = make_control_handler(
            self.client,
            172,
            threading.Lock(),
            bridge_session_id=self.session_id,
            journal_capture=journal,
        )
        result = CommandResult(id=MOVE_ID, status="success")
        with patch("civ5_agent.watch.execute_move_unit", return_value=result):
            response = handler(
                {
                    "op": "move_unit",
                    "id": MOVE_ID,
                    "unit_id": 8,
                    "x": 10,
                    "y": 12,
                    "bridge_session_id": self.session_id,
                }
            )

        self.assertTrue(response["ok"])
        expected = {"unit_id": 8, "x": 10, "y": 12}
        self.assertEqual(journal.submitted[0][0:3], ("move_unit", expected, MOVE_ID))
        self.assertEqual(journal.results[0][0:2], ("move_unit", expected))

    def test_move_unit_unknown_outcome_is_cached_and_never_retried(self):
        request = {
            "op": "move_unit",
            "id": MOVE_ID,
            "unit_id": 8,
            "x": 10,
            "y": 12,
        }
        with patch(
            "civ5_agent.watch.execute_move_unit",
            side_effect=ConnectionError("connection lost after submission"),
        ) as execute:
            first = self.write(request)
            replay = self.write(request)

        self.assertFalse(first["ok"])
        self.assertTrue(first["outcome_unknown"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(execute.call_count, 1)

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
            session_id = handler({"op": "ping"})["bridge_session_id"]
            with patch("civ5_agent.watch.execute_end_turn", return_value=result):
                response = handler(
                    {
                        "op": "end_turn",
                        "id": AUDIT_ID,
                        "bridge_session_id": session_id,
                    }
                )
            record = json.loads(path.read_text())
        self.assertTrue(response["ok"])
        self.assertEqual(record["operation"], "end_turn")
        self.assertEqual(record["result"]["id"], AUDIT_ID)
        self.assertEqual(record["arguments"], {})
        self.assertEqual(record["bridge_session_id"], session_id)

    def test_journal_failure_does_not_retry_or_change_verified_result(self):
        class FailingJournal:
            def record_command_submitted(self, operation, arguments, command_id, turn):
                raise ValueError("journal unavailable")

            def record_command_result(self, operation, arguments, result):
                raise ValueError("journal unavailable")

        result = CommandResult(id=END_TURN_ID, status="success")
        handler = make_control_handler(
            self.client,
            172,
            threading.Lock(),
            bridge_session_id=self.session_id,
            journal_capture=FailingJournal(),
        )
        with patch(
            "civ5_agent.watch.execute_end_turn", return_value=result
        ) as execute, patch("sys.stderr", new=io.StringIO()):
            response = handler(
                {
                    "op": "end_turn",
                    "id": END_TURN_ID,
                    "bridge_session_id": self.session_id,
                }
            )
            replay = handler(
                {
                    "op": "end_turn",
                    "id": END_TURN_ID,
                    "bridge_session_id": self.session_id,
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "success")
        self.assertIn("journal unavailable", response["journal_error"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(execute.call_count, 1)

    def test_records_and_caches_unknown_outcome_without_retry(self):
        class RecordingJournal:
            def __init__(self):
                self.unknown = []

            def record_command_submitted(self, operation, arguments, command_id, turn):
                pass

            def record_command_outcome_unknown(
                self, operation, command_id, turn, message
            ):
                self.unknown.append((operation, command_id, turn, message))

        journal = RecordingJournal()
        handler = make_control_handler(
            self.client,
            172,
            threading.Lock(),
            bridge_session_id=self.session_id,
            journal_capture=journal,
        )
        request = {
            "op": "end_turn",
            "id": END_TURN_ID,
            "bridge_session_id": self.session_id,
        }
        with patch(
            "civ5_agent.watch.execute_end_turn",
            side_effect=ValueError("FireTuner response was incomplete"),
        ) as execute:
            first = handler(request)
            second = handler(request)

        self.assertFalse(first["ok"])
        self.assertTrue(first["outcome_unknown"])
        self.assertTrue(second["replayed"])
        self.assertEqual(len(journal.unknown), 1)
        self.assertEqual(journal.unknown[0][0:3], ("end_turn", END_TURN_ID, 3))
        self.assertEqual(execute.call_count, 1)
        status = handler(
            {
                "op": "command_status",
                "command_id": END_TURN_ID,
                "bridge_session_id": self.session_id,
            }
        )
        self.assertTrue(status["ok"])
        self.assertFalse(status["found"])

    def test_rejects_non_uuid_command_id_before_execution(self):
        with patch("civ5_agent.watch.execute_end_turn") as execute:
            response = self.write({"op": "end_turn", "id": "not-a-uuid"})
        self.assertFalse(response["ok"])
        self.assertIn("UUIDv4", response["error"])
        execute.assert_not_called()

    def test_replays_completed_command_without_executing_twice(self):
        result = CommandResult(id=SKIP_ID, status="success")
        with patch(
            "civ5_agent.watch.execute_skip_unit",
            return_value=result,
        ) as execute:
            first = self.write({"op": "skip_unit", "id": SKIP_ID, "unit_id": 8})
            replay = self.write({"op": "skip_unit", "id": SKIP_ID, "unit_id": 8})
        self.assertTrue(first["ok"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(execute.call_count, 1)

    def test_rejects_command_id_reuse_with_different_arguments(self):
        result = CommandResult(id=SKIP_ID, status="success")
        with patch(
            "civ5_agent.watch.execute_skip_unit",
            return_value=result,
        ) as execute:
            self.write({"op": "skip_unit", "id": SKIP_ID, "unit_id": 8})
            collision = self.write(
                {"op": "skip_unit", "id": SKIP_ID, "unit_id": 9}
            )
        self.assertFalse(collision["ok"])
        self.assertIn("different arguments", collision["error"])
        self.assertEqual(execute.call_count, 1)

    def test_command_status_is_read_only_and_session_scoped(self):
        missing = self.write(
            {"op": "command_status", "command_id": SKIP_ID}
        )
        self.assertTrue(missing["ok"])
        self.assertFalse(missing["found"])

        result = CommandResult(id=SKIP_ID, status="success")
        with patch(
            "civ5_agent.watch.execute_skip_unit",
            return_value=result,
        ) as execute:
            self.write({"op": "skip_unit", "id": SKIP_ID, "unit_id": 8})
            status = self.write(
                {"op": "command_status", "command_id": SKIP_ID}
            )

        self.assertTrue(status["found"])
        self.assertEqual(status["action"], "skip_unit")
        self.assertEqual(status["arguments"], {"unit_id": 8})
        self.assertEqual(status["result"]["id"], SKIP_ID)
        self.assertEqual(execute.call_count, 1)

        changed = self.handler(
            {
                "op": "command_status",
                "command_id": SKIP_ID,
                "bridge_session_id": "123e4567-e89b-42d3-a456-426614174099",
            }
        )
        self.assertFalse(changed["ok"])
        self.assertIn("session changed", changed["error"])


class WatchArgumentsTest(unittest.TestCase):
    def test_database_transport_rejects_journal_capture(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "sys.argv",
            [
                "civ5_agent.watch",
                "--transport",
                "database",
                "--journal",
                str(Path(directory) / "match.jsonl"),
                "--journal-mode",
                "new",
            ],
        ), patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main()

        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
