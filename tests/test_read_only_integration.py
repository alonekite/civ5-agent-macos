import contextlib
import io
import json
import os
import stat
import tomllib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from civ5_agent.checkpoint_authorization import (
    CHECKPOINT_AUTHORIZATION_VERSION,
    authorize_checkpoint_challenge,
    create_checkpoint_challenge,
)
from civ5_agent.models import GameState
from civ5_agent.read_only_integration import (
    AUTOMATION_FRAMEWORK_RELEASE_TAG,
    AUTOMATION_FRAMEWORK_SESSION_SPEC_VERSION,
    AUTOMATION_FRAMEWORK_TAG_COMMIT,
    AUTOMATION_FRAMEWORK_WHEEL_NAME,
    AUTOMATION_FRAMEWORK_WHEEL_SHA256,
    AUTOMATION_FRAMEWORK_V2_CANDIDATE_COMMIT,
    AUTOMATION_FRAMEWORK_V2_CANDIDATE_SESSION_SPEC_VERSION,
    AUTOMATION_FRAMEWORK_V2_CANDIDATE_WHEEL_NAME,
    AUTOMATION_FRAMEWORK_V2_CANDIDATE_WHEEL_SHA256,
    CIV5_APP_BUNDLE_ID,
    CIV5_APP_BUNDLE_PATH,
    CIV5_GAME_EXECUTABLE_PATH,
    CIV5_LAUNCHER_BUTTON_ROLE,
    CIV5_LAUNCHER_BUTTON_TITLE,
    CIV5_WINDOW_TITLE,
    ReadOnlyIntegrationError,
    build_session_spec,
    build_ui_session_spec,
    main,
    read_sanitized_summary,
)


SESSION_ID = "123e4567-e89b-42d3-a456-426614174070"
CHECKPOINT_ID = "123e4567-e89b-42d3-a456-426614174071"
TASK_ID = "123e4567-e89b-42d3-a456-426614174072"


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
    def test_checkpoint_challenge_is_private_exact_and_one_time(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "challenge.json"
            challenge = create_checkpoint_challenge(
                path,
                checkpoint_id=CHECKPOINT_ID,
                step_id="press_launcher_play",
                task_id=TASK_ID,
                requested_at_unix=99.0,
                now=100.0,
                nonce="0123abcd",
            )

            self.assertEqual(challenge["schema_version"], CHECKPOINT_AUTHORIZATION_VERSION)
            self.assertEqual(
                challenge["prompt"],
                "I am at the Mac; authorize press_launcher_play 0123abcd",
            )
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaisesRegex(ValueError, "could not be created"):
                create_checkpoint_challenge(
                    path,
                    checkpoint_id=CHECKPOINT_ID,
                    step_id="press_launcher_play",
                    task_id=TASK_ID,
                    requested_at_unix=99.0,
                    now=100.0,
                    nonce="89abcdef",
                )
            authorized = authorize_checkpoint_challenge(
                path,
                checkpoint_id=CHECKPOINT_ID,
                step_id="press_launcher_play",
                task_id=TASK_ID,
                response=challenge["prompt"],
                now=101.0,
            )
            self.assertTrue(authorized["authorized"])
            self.assertFalse(path.exists())
            with self.assertRaisesRegex(ValueError, "unavailable"):
                authorize_checkpoint_challenge(
                    path,
                    checkpoint_id=CHECKPOINT_ID,
                    step_id="press_launcher_play",
                    task_id=TASK_ID,
                    response=challenge["prompt"],
                    now=102.0,
                )

    def test_checkpoint_challenge_rejects_predating_or_mismatched_authority(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "challenge.json"
            with self.assertRaisesRegex(ValueError, "after checkpoint.requested"):
                create_checkpoint_challenge(
                    path,
                    checkpoint_id=CHECKPOINT_ID,
                    step_id="press_launcher_play",
                    task_id=TASK_ID,
                    requested_at_unix=101.0,
                    now=100.0,
                    nonce="0123abcd",
                )
            challenge = create_checkpoint_challenge(
                path,
                checkpoint_id=CHECKPOINT_ID,
                step_id="press_launcher_play",
                task_id=TASK_ID,
                requested_at_unix=99.0,
                now=100.0,
                nonce="0123abcd",
            )
            for changed in (
                {"checkpoint_id": SESSION_ID},
                {"step_id": "click_game_continue"},
                {"task_id": "123e4567-e89b-42d3-a456-426614174073"},
                {"response": "确认 PLAY"},
            ):
                arguments = {
                    "checkpoint_id": CHECKPOINT_ID,
                    "step_id": "press_launcher_play",
                    "task_id": TASK_ID,
                    "response": challenge["prompt"],
                } | changed
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    authorize_checkpoint_challenge(path, **arguments, now=101.0)
                self.assertTrue(path.exists())

    def test_checkpoint_challenge_rejects_stale_insecure_and_replayed_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            stale = root / "stale.json"
            challenge = create_checkpoint_challenge(
                stale,
                checkpoint_id=CHECKPOINT_ID,
                step_id="press_launcher_play",
                task_id=TASK_ID,
                requested_at_unix=99.0,
                now=100.0,
                nonce="0123abcd",
            )
            with self.assertRaisesRegex(ValueError, "not fresh"):
                authorize_checkpoint_challenge(
                    stale,
                    checkpoint_id=CHECKPOINT_ID,
                    step_id="press_launcher_play",
                    task_id=TASK_ID,
                    response=challenge["prompt"],
                    max_age_seconds=10,
                    now=111.0,
                )
            os.chmod(stale, 0o644)
            with self.assertRaisesRegex(ValueError, "0600"):
                authorize_checkpoint_challenge(
                    stale,
                    checkpoint_id=CHECKPOINT_ID,
                    step_id="press_launcher_play",
                    task_id=TASK_ID,
                    response=challenge["prompt"],
                    now=101.0,
                )
            os.chmod(stale, 0o600)
            link = root / "link.json"
            link.symlink_to(stale)
            with self.assertRaisesRegex(ValueError, "unavailable"):
                authorize_checkpoint_challenge(
                    link,
                    checkpoint_id=CHECKPOINT_ID,
                    step_id="press_launcher_play",
                    task_id=TASK_ID,
                    response=challenge["prompt"],
                    now=101.0,
                )

    def test_checkpoint_challenge_cli_requires_post_request_exact_response(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "challenge.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "checkpoint-challenge",
                        "--file",
                        str(path),
                        "--checkpoint-id",
                        CHECKPOINT_ID,
                        "--step-id",
                        "press_launcher_play",
                        "--task-id",
                        TASK_ID,
                        "--checkpoint-requested-at",
                        "2020-01-01T00:00:00Z",
                    ]
                )
            self.assertEqual(status, 0)
            challenge = json.loads(output.getvalue())

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "checkpoint-authorize",
                        "--file",
                        str(path),
                        "--checkpoint-id",
                        CHECKPOINT_ID,
                        "--step-id",
                        "press_launcher_play",
                        "--task-id",
                        TASK_ID,
                        "--response",
                        challenge["prompt"],
                    ]
                )
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(output.getvalue())["authorized"])
            self.assertFalse(path.exists())

    def test_framework_remains_outside_python_dependency_and_import_graph(self):
        root = Path(__file__).resolve().parents[1]
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = project["project"].get("dependencies", [])
        self.assertFalse(
            any("local-app-test-automation" in item.lower() for item in dependencies)
        )

        for source in (root / "src" / "civ5_agent").rglob("*.py"):
            content = source.read_text(encoding="utf-8")
            self.assertNotIn("import local_app_test_automation", content, source)
            self.assertNotIn("from local_app_test_automation", content, source)

    def test_pins_the_adopted_framework_release_without_importing_it(self):
        self.assertEqual(AUTOMATION_FRAMEWORK_RELEASE_TAG, "v0.1.0")
        self.assertEqual(
            AUTOMATION_FRAMEWORK_TAG_COMMIT,
            "bf71fb072d9111d8cc4bbab24c50fc670fc2239c",
        )
        self.assertEqual(
            AUTOMATION_FRAMEWORK_WHEEL_NAME,
            "local_app_test_automation-0.1.0-py3-none-any.whl",
        )
        self.assertRegex(AUTOMATION_FRAMEWORK_WHEEL_SHA256, r"^[0-9a-f]{64}$")
        self.assertEqual(
            AUTOMATION_FRAMEWORK_WHEEL_SHA256,
            "6c0040ec2e4911c80b318687ad0fd53511972b517ca21dfbb5d0a3cd4af34eb3",
        )
        self.assertEqual(AUTOMATION_FRAMEWORK_SESSION_SPEC_VERSION, 1)
        self.assertEqual(
            AUTOMATION_FRAMEWORK_V2_CANDIDATE_COMMIT,
            "b1f99ef988d376b61269e1cdc377e2033d6d736e",
        )
        self.assertEqual(
            AUTOMATION_FRAMEWORK_V2_CANDIDATE_WHEEL_NAME,
            "local_app_test_automation-0.2.0.dev0-py3-none-any.whl",
        )
        self.assertEqual(
            AUTOMATION_FRAMEWORK_V2_CANDIDATE_WHEEL_SHA256,
            "cc57a78719507ac65795169d7f87a7c8c58de7d793680f8360bb1de4d2175685",
        )
        self.assertEqual(AUTOMATION_FRAMEWORK_V2_CANDIDATE_SESSION_SPEC_VERSION, 2)

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

        self.assertEqual(
            spec["spec_version"], AUTOMATION_FRAMEWORK_SESSION_SPEC_VERSION
        )
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

    def test_ui_session_spec_preserves_v1_process_and_orders_two_ui_gates(self):
        spec = build_ui_session_spec(
            label="core-read-only-ui",
            app_bundle_id=CIV5_APP_BUNDLE_ID,
            app_bundle_path=None,
            existing_instance_policy="reject",
            leave_open_on_success=True,
            watcher_executable=Path("/opt/core/bin/civ5-watch"),
            cwd=Path("/opt/core"),
            socket_path=Path("/private/tmp/core.sock"),
            audit_log=Path("/private/tmp/audit.jsonl"),
            session_timeout_ms=60_000,
            continue_x_ratio=0.5,
            continue_y_ratio=0.64,
            expected_game_executable_path=CIV5_GAME_EXECUTABLE_PATH,
        )

        self.assertEqual(spec["spec_version"], 2)
        self.assertEqual(len(spec["processes"]), 1)
        self.assertIn("--read-only", spec["processes"][0]["argv"])
        self.assertFalse(spec["processes"][0]["retain_raw_output"])
        self.assertEqual(
            [step["step_id"] for step in spec["ui_steps"]],
            ["press_launcher_play", "click_game_continue"],
        )
        launcher, game = spec["ui_steps"]
        self.assertEqual(
            launcher,
            {
                "step_id": "press_launcher_play",
                "target": {
                    "bundle_id": CIV5_APP_BUNDLE_ID,
                    "window_title": CIV5_WINDOW_TITLE,
                },
                "action": {
                    "kind": "accessibility_press",
                    "role": CIV5_LAUNCHER_BUTTON_ROLE,
                    "title": CIV5_LAUNCHER_BUTTON_TITLE,
                },
                "timeout_ms": 300_000,
                "authorization_timeout_ms": 300_000,
                "identity_handoff": {
                    "kind": "same_process_executable",
                    "expected_executable_path": str(CIV5_GAME_EXECUTABLE_PATH),
                    "timeout_ms": 300_000,
                },
            },
        )
        self.assertEqual(game["action"]["kind"], "window_relative_click")
        self.assertEqual(game["action"]["x_ratio"], 0.5)
        self.assertEqual(game["action"]["y_ratio"], 0.64)
        self.assertNotIn("identity_handoff", game)

    def test_ui_session_spec_fails_closed_for_unverified_identity_and_coordinates(self):
        arguments = dict(
            label="core-read-only-ui",
            app_bundle_id=CIV5_APP_BUNDLE_ID,
            app_bundle_path=None,
            existing_instance_policy="reject",
            leave_open_on_success=True,
            watcher_executable=Path("/opt/core/bin/civ5-watch"),
            cwd=Path("/opt/core"),
            socket_path=Path("/private/tmp/core.sock"),
            audit_log=Path("/private/tmp/audit.jsonl"),
            session_timeout_ms=60_000,
            continue_x_ratio=0.5,
            continue_y_ratio=0.64,
            expected_game_executable_path=CIV5_GAME_EXECUTABLE_PATH,
        )
        with self.assertRaisesRegex(ValueError, "verified Civ V bundle"):
            build_ui_session_spec(**(arguments | {"app_bundle_id": "com.example.Other"}))
        with self.assertRaisesRegex(ValueError, "verified Civ V bundle"):
            build_ui_session_spec(
                **(
                    arguments
                    | {
                        "app_bundle_id": None,
                        "app_bundle_path": Path("/Applications/Other.app"),
                    }
                )
            )
        with self.assertRaisesRegex(ValueError, "verified Civ V game executable"):
            build_ui_session_spec(
                **(
                    arguments
                    | {"expected_game_executable_path": Path("/Applications/Other.app")}
                )
            )
        path_spec = build_ui_session_spec(
            **(
                arguments
                | {
                    "app_bundle_id": None,
                    "app_bundle_path": CIV5_APP_BUNDLE_PATH,
                }
            )
        )
        self.assertEqual(path_spec["app"]["bundle_path"], str(CIV5_APP_BUNDLE_PATH))
        for value in (0, 1, float("nan"), float("inf"), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_ui_session_spec(**(arguments | {"continue_x_ratio": value}))
        for value in (0, 300_001, True, 1.5):
            with self.subTest(identity_handoff_timeout_ms=value), self.assertRaises(
                ValueError
            ):
                build_ui_session_spec(
                    **(arguments | {"identity_handoff_timeout_ms": value})
                )

    def test_ui_session_spec_keeps_private_selectors_out_of_watcher_fields(self):
        spec = build_ui_session_spec(
            label="core-read-only-ui",
            app_bundle_id=CIV5_APP_BUNDLE_ID,
            app_bundle_path=None,
            existing_instance_policy="reject",
            leave_open_on_success=True,
            watcher_executable=Path("/opt/core/bin/civ5-watch"),
            cwd=Path("/opt/core"),
            socket_path=Path("/private/tmp/core.sock"),
            audit_log=Path("/private/tmp/audit.jsonl"),
            session_timeout_ms=60_000,
            continue_x_ratio=0.5,
            continue_y_ratio=0.64,
            expected_game_executable_path=CIV5_GAME_EXECUTABLE_PATH,
        )
        process_json = json.dumps(spec["processes"], sort_keys=True)
        for private in (
            CIV5_WINDOW_TITLE,
            "PLAY",
            "x_ratio",
            "y_ratio",
            str(CIV5_GAME_EXECUTABLE_PATH),
        ):
            self.assertNotIn(private, process_json)
        self.assertEqual(spec["app"]["bundle_id"], CIV5_APP_BUNDLE_ID)
        self.assertNotIn("bundle_path", spec["app"])
        self.assertEqual(
            json.dumps(spec, sort_keys=True).count(str(CIV5_GAME_EXECUTABLE_PATH)),
            1,
        )

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

    def test_cli_emits_candidate_v2_without_changing_v1_default(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                [
                    "ui-session-spec",
                    "--app-bundle-id",
                    CIV5_APP_BUNDLE_ID,
                    "--watcher-executable",
                    "/opt/core/bin/civ5-watch",
                    "--cwd",
                    "/opt/core",
                    "--socket",
                    "/private/tmp/core.sock",
                    "--audit-log",
                    "/private/tmp/audit.jsonl",
                    "--continue-x-ratio",
                    "0.5",
                    "--continue-y-ratio",
                    "0.64",
                    "--expected-game-executable",
                    str(CIV5_GAME_EXECUTABLE_PATH),
                ]
            )
        self.assertEqual(status, 0)
        spec = json.loads(output.getvalue())
        self.assertEqual(spec["spec_version"], 2)
        self.assertEqual(len(spec["ui_steps"]), 2)

    def test_cli_requires_explicit_successor_executable_for_candidate_v2(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(
            SystemExit, "2"
        ):
            main(
                [
                    "ui-session-spec",
                    "--app-bundle-id",
                    CIV5_APP_BUNDLE_ID,
                    "--watcher-executable",
                    "/opt/core/bin/civ5-watch",
                    "--cwd",
                    "/opt/core",
                    "--socket",
                    "/private/tmp/core.sock",
                    "--audit-log",
                    "/private/tmp/audit.jsonl",
                    "--continue-x-ratio",
                    "0.5",
                    "--continue-y-ratio",
                    "0.64",
                ]
            )


if __name__ == "__main__":
    unittest.main()
