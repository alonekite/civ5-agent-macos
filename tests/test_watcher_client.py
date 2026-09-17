import unittest
from dataclasses import asdict
from unittest.mock import patch

from civ5_agent.actions import CommandValidationError, validate_command
from civ5_agent.bridge import Bridge
from civ5_agent.errors import ProtocolError, TransportError
from civ5_agent.models import Command, GameState
from civ5_agent.watcher_client import WatcherBridgeClient

SESSION_ID = "123e4567-e89b-42d3-a456-426614174070"
COMMAND_ID = "123e4567-e89b-42d3-a456-426614174071"


def state(turn=4):
    return GameState(
        schema_version=2,
        turn=turn,
        active_player=0,
        gold=12,
        turn_active=True,
        can_end_turn=True,
        end_turn_blocking_type=-1,
        research={"id": 1, "type": "TECH_POTTERY", "progress": 0, "cost": 40},
        cities=[],
        units=[],
    )


class WatcherBridgeClientTest(unittest.TestCase):
    def test_watcher_client_implements_public_bridge_protocol(self):
        self.assertIsInstance(WatcherBridgeClient(), Bridge)

    def test_reads_validated_session_and_state(self):
        response = {
            "ok": True,
            "bridge_session_id": SESSION_ID,
            "state": asdict(state()),
        }
        with patch("civ5_agent.watcher_client.request", return_value=response):
            session_id, observed = WatcherBridgeClient().read_state()

        self.assertEqual(session_id, SESSION_ID)
        self.assertEqual(observed, state())

        malformed = {**response, "bridge_session_id": "not-a-session"}
        with patch(
            "civ5_agent.watcher_client.request",
            return_value=malformed,
        ), self.assertRaisesRegex(ProtocolError, "UUID"):
            WatcherBridgeClient().read_state()

    def test_executes_validated_command_and_requires_terminal_matching_result(self):
        command = Command("skip_unit", {"unit_id": 8}, id=COMMAND_ID)
        response = {
            "ok": True,
            "bridge_session_id": SESSION_ID,
            "result": {
                "id": COMMAND_ID,
                "status": "success",
                "message": "verified",
                "before": asdict(state()),
                "after": asdict(state()),
            },
        }
        with patch(
            "civ5_agent.watcher_client.request",
            return_value=response,
        ) as send:
            result = WatcherBridgeClient().execute_command(command, SESSION_ID)

        self.assertEqual(result.id, COMMAND_ID)
        self.assertEqual(send.call_args.args[0]["op"], "skip_unit")
        self.assertEqual(send.call_args.args[0]["unit_id"], 8)

        pending = {**response, "result": {**response["result"], "status": "pending"}}
        with patch(
            "civ5_agent.watcher_client.request",
            return_value=pending,
        ), self.assertRaisesRegex(TransportError, "terminal"):
            WatcherBridgeClient().execute_command(command, SESSION_ID)

        malformed = {**response, "result": {**response["result"], "after": {}}}
        with patch(
            "civ5_agent.watcher_client.request",
            return_value=malformed,
        ), self.assertRaisesRegex(TransportError, "live state is missing"):
            WatcherBridgeClient().execute_command(command, SESSION_ID)

        with patch(
            "civ5_agent.watcher_client.request",
            side_effect=TimeoutError("timed out"),
        ), self.assertRaisesRegex(TransportError, "timed out"):
            WatcherBridgeClient().execute_command(command, SESSION_ID)

    def test_rejects_invalid_command_before_watcher_contact(self):
        invalid = Command("skip_unit", {"unit_id": True}, id=COMMAND_ID)
        with patch("civ5_agent.watcher_client.request") as send, self.assertRaises(
            CommandValidationError
        ):
            WatcherBridgeClient().execute_command(invalid, SESSION_ID)

        send.assert_not_called()

    def test_preserves_submitted_unknown_outcome_as_transport_error(self):
        command = Command("end_turn", {}, id=COMMAND_ID)
        response = {
            "ok": False,
            "bridge_session_id": SESSION_ID,
            "outcome_unknown": True,
            "error": "FireTuner response was incomplete",
        }
        with patch(
            "civ5_agent.watcher_client.request",
            return_value=response,
        ), self.assertRaisesRegex(TransportError, "incomplete"):
            WatcherBridgeClient().execute_command(command, SESSION_ID)

    def test_public_command_validation_normalizes_and_rejects_extra_fields(self):
        command = Command("choose_research", {"tech_type": "TECH_POTTERY"}, COMMAND_ID)
        self.assertEqual(validate_command(command), command)
        with self.assertRaisesRegex(CommandValidationError, "exactly"):
            validate_command(
                Command(
                    "choose_research",
                    {"tech_type": "TECH_POTTERY", "extra": True},
                    COMMAND_ID,
                )
            )

    def test_public_move_command_validation_is_exact_and_bounded(self):
        command = Command(
            "move_unit",
            {"unit_id": 8, "x": 65_535, "y": 0},
            COMMAND_ID,
        )
        self.assertEqual(validate_command(command), command)
        invalid_arguments = (
            {"unit_id": 8, "x": 1},
            {"unit_id": True, "x": 1, "y": 2},
            {"unit_id": 8, "x": -1, "y": 2},
            {"unit_id": 8, "x": 1, "y": 65_536},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments), self.assertRaises(
                CommandValidationError
            ):
                validate_command(Command("move_unit", arguments, COMMAND_ID))

    def test_public_worker_build_validation_is_exact_and_bounded(self):
        command = Command(
            "worker_build",
            {"unit_id": 8, "x": 65_535, "y": 0, "build_type": "BUILD_FARM"},
            COMMAND_ID,
        )
        self.assertEqual(validate_command(command), command)
        invalid_arguments = (
            {"unit_id": 8, "x": 1, "y": 2},
            {"unit_id": True, "x": 1, "y": 2, "build_type": "BUILD_FARM"},
            {"unit_id": 8, "x": -1, "y": 2, "build_type": "BUILD_FARM"},
            {"unit_id": 8, "x": 1, "y": 65_536, "build_type": "BUILD_FARM"},
            {"unit_id": 8, "x": 1, "y": 2, "build_type": "IMPROVEMENT_FARM"},
            {"unit_id": 8, "x": 1, "y": 2, "build_type": "BUILD_" + "X" * 59},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments), self.assertRaises(
                CommandValidationError
            ):
                validate_command(Command("worker_build", arguments, COMMAND_ID))


if __name__ == "__main__":
    unittest.main()
