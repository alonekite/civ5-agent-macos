import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from civ5_agent.models import GameState
from civ5_agent.read_only_integration import (
    ReadOnlyIntegrationError,
    build_session_spec,
    main,
    read_sanitized_summary,
)


SESSION_ID = "123e4567-e89b-42d3-a456-426614174070"


def private_state() -> GameState:
    return GameState(
        schema_version=8,
        turn=87,
        active_player=0,
        gold=123,
        turn_active=True,
        can_end_turn=False,
        player_name="PRIVATE PLAYER",
        civilization="PRIVATE CIVILIZATION",
        research={"id": 6, "type": "TECH_PRIVATE", "progress": 10, "cost": 20},
        cities=[{"id": 1, "name": "PRIVATE CITY", "x": 4, "y": 5}],
        units=[{"id": 2, "name": "PRIVATE UNIT", "x": 6, "y": 7}],
        runtime_context={},
        research_runtime_facts={},
    )


class ReadOnlyIntegrationTest(unittest.TestCase):
    def test_probe_requires_read_only_and_redacts_private_state(self):
        client = Mock()
        client.read_state.return_value = (SESSION_ID, private_state())
        with patch(
            "civ5_agent.read_only_integration.request",
            return_value={
                "ok": True,
                "bridge_session_id": SESSION_ID,
                "read_only": True,
            },
        ), patch(
            "civ5_agent.read_only_integration.WatcherBridgeClient",
            return_value=client,
        ):
            summary = read_sanitized_summary(Path("/private/tmp/watcher.sock"))

        self.assertEqual(summary["turn"], 87)
        self.assertEqual(summary["city_count"], 1)
        self.assertEqual(summary["unit_count"], 1)
        self.assertTrue(summary["research_selected"])
        encoded = json.dumps(summary)
        for private in ("PRIVATE", "TECH_", SESSION_ID, '"x"', '"y"'):
            self.assertNotIn(private, encoded)

    def test_probe_rejects_write_capable_watcher_before_state_read(self):
        with patch(
            "civ5_agent.read_only_integration.request",
            return_value={
                "ok": True,
                "bridge_session_id": SESSION_ID,
                "read_only": False,
            },
        ) as send, patch(
            "civ5_agent.read_only_integration.WatcherBridgeClient"
        ) as client, self.assertRaisesRegex(
            ReadOnlyIntegrationError, "not in server-enforced"
        ):
            read_sanitized_summary(Path("/private/tmp/watcher.sock"))

        self.assertEqual(send.call_args.args[0], {"op": "ping"})
        client.assert_not_called()

    def test_probe_timeout_has_bounded_non_path_error(self):
        socket_path = Path("/private/tmp/private-name.sock")
        with patch(
            "civ5_agent.read_only_integration.request",
            side_effect=FileNotFoundError("private-name.sock"),
        ), self.assertRaises(ReadOnlyIntegrationError) as raised:
                read_sanitized_summary(
                    socket_path,
                    request_timeout=0.01,
                    wait_timeout=0.01,
                    poll_interval=0.001,
                )
        self.assertEqual(raised.exception.code, "watcher_unavailable")
        self.assertNotIn("private-name", str(raised.exception))

    def test_session_spec_is_framework_v1_and_contains_no_domain_profile(self):
        spec = build_session_spec(
            label="core-read-only",
            app_bundle_id="com.example.CivFixture",
            app_bundle_path=None,
            existing_instance_policy="observe_verified",
            leave_open_on_success=True,
            watcher_executable=Path("/opt/core/bin/civ5-watch"),
            cwd=Path("/opt/core"),
            socket_path=Path("/private/tmp/core.sock"),
            audit_log=Path("/private/tmp/audit.jsonl"),
            session_timeout_ms=60_000,
        )

        self.assertEqual(spec["spec_version"], 1)
        self.assertEqual(len(spec["processes"]), 1)
        process = spec["processes"][0]
        self.assertEqual(process["argv"][0], "/opt/core/bin/civ5-watch")
        self.assertIn("--read-only", process["argv"])
        self.assertFalse(process["retain_raw_output"])
        self.assertEqual(process["environment"]["inherit"], "none")
        encoded = json.dumps(spec).lower()
        self.assertNotIn("m11", encoded)
        self.assertNotIn("research", encoded)
        self.assertNotIn("c4", encoded)

    def test_cli_emits_one_json_object_and_stable_exit_classes(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                [
                    "session-spec",
                    "--app-bundle-id",
                    "com.example.CivFixture",
                    "--watcher-executable",
                    "/opt/core/bin/civ5-watch",
                    "--cwd",
                    "/opt/core",
                    "--socket",
                    "/private/tmp/core.sock",
                    "--audit-log",
                    "/private/tmp/audit.jsonl",
                ]
            )
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["spec_version"], 1)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                [
                    "session-spec",
                    "--app-bundle-id",
                    "com.example.CivFixture",
                    "--watcher-executable",
                    "relative",
                    "--cwd",
                    "/opt/core",
                    "--socket",
                    "/private/tmp/core.sock",
                    "--audit-log",
                    "/private/tmp/audit.jsonl",
                ]
            )
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
