import contextlib
import io
import json
import os
import stat
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from civ5_agent.play_session_grant import (
    PLAY_INITIATION_TEXT,
    consume_play_session_grant,
    create_play_session_grant,
)
from civ5_agent.read_only_integration import main

SESSION = "123e4567-e89b-42d3-a456-426614174070"
CHECKPOINT = "123e4567-e89b-42d3-a456-426614174071"
TASK = "123e4567-e89b-42d3-a456-426614174072"
DIGEST = "a" * 64


def grant_arguments() -> dict[str, object]:
    return {
        "framework_session_id": SESSION,
        "checkpoint_id": CHECKPOINT,
        "spec_sha256": DIGEST,
        "task_id": TASK,
        "initiation_text": PLAY_INITIATION_TEXT,
        "initiated_at_unix": 100.0,
        "checkpoint_requested_at_unix": 110.0,
        "checkpoint_expires_at_unix": 410.0,
        "now": 111.0,
    }


class PlaySessionGrantTest(unittest.TestCase):
    def test_cli_create_and_consume_bind_the_active_checkpoint(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "play-grant.json"
            now = datetime.now(UTC)
            encoded = lambda value: value.isoformat()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "play-grant-create",
                        "--file",
                        str(path),
                        "--framework-session-id",
                        SESSION,
                        "--checkpoint-id",
                        CHECKPOINT,
                        "--spec-sha256",
                        DIGEST,
                        "--task-id",
                        TASK,
                        "--initiation-text",
                        PLAY_INITIATION_TEXT,
                        "--initiated-at",
                        encoded(now - timedelta(seconds=10)),
                        "--checkpoint-requested-at",
                        encoded(now - timedelta(seconds=5)),
                        "--checkpoint-expires-at",
                        encoded(now + timedelta(seconds=295)),
                    ]
                )
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(output.getvalue())["ok"])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "play-grant-consume",
                        "--file",
                        str(path),
                        "--framework-session-id",
                        SESSION,
                        "--checkpoint-id",
                        CHECKPOINT,
                        "--spec-sha256",
                        DIGEST,
                        "--task-id",
                        TASK,
                    ]
                )
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(output.getvalue())["authorized"])

    def test_one_exact_private_grant_is_consumed_once(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "play-grant.json"
            created = create_play_session_grant(path, **grant_arguments())
            self.assertTrue(created["ok"])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            record = json.loads(path.read_text())
            self.assertEqual(record["framework_session_id"], SESSION)
            self.assertEqual(record["step_id"], "press_launcher_play")
            self.assertNotIn("initiation_text", record)
            self.assertNotIn("nonce", record)
            consumed = consume_play_session_grant(
                path,
                framework_session_id=SESSION,
                checkpoint_id=CHECKPOINT,
                spec_sha256=DIGEST,
                task_id=TASK,
                now=112.0,
            )
            self.assertTrue(consumed["authorized"])
            self.assertFalse(path.exists())
            with self.assertRaisesRegex(ValueError, "unavailable"):
                consume_play_session_grant(
                    path,
                    framework_session_id=SESSION,
                    checkpoint_id=CHECKPOINT,
                    spec_sha256=DIGEST,
                    task_id=TASK,
                    now=113.0,
                )

    def test_no_generic_or_stale_session_initiation(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "play-grant.json"
            for change in (
                {"initiation_text": "start"},
                {
                    "initiation_text": "I am at the Mac; authorize press_launcher_play deadbeef"
                },
                {"initiated_at_unix": 111.0},
                {"initiated_at_unix": -500.0},
                {"checkpoint_requested_at_unix": 90.0},
                {"checkpoint_expires_at_unix": 110.0},
                {"spec_sha256": "A" * 64},
                {"task_id": "not-a-task"},
                {"now": 411.0},
            ):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    create_play_session_grant(path, **(grant_arguments() | change))
                self.assertFalse(path.exists())

    def test_exact_session_checkpoint_spec_and_task_are_required(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "play-grant.json"
            create_play_session_grant(path, **grant_arguments())
            arguments = {
                "framework_session_id": SESSION,
                "checkpoint_id": CHECKPOINT,
                "spec_sha256": DIGEST,
                "task_id": TASK,
                "now": 112.0,
            }
            for change in (
                {"framework_session_id": "123e4567-e89b-42d3-a456-426614174073"},
                {"checkpoint_id": "123e4567-e89b-42d3-a456-426614174074"},
                {"spec_sha256": "b" * 64},
                {"task_id": "123e4567-e89b-42d3-a456-426614174075"},
                {"now": 411.0},
            ):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    consume_play_session_grant(path, **(arguments | change))
                self.assertTrue(path.exists())

    def test_existing_insecure_or_modified_grant_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "play-grant.json"
            create_play_session_grant(path, **grant_arguments())
            with self.assertRaisesRegex(ValueError, "could not be created"):
                create_play_session_grant(path, **grant_arguments())
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "mode or size"):
                consume_play_session_grant(
                    path,
                    framework_session_id=SESSION,
                    checkpoint_id=CHECKPOINT,
                    spec_sha256=DIGEST,
                    task_id=TASK,
                    now=112.0,
                )
            path.unlink()
            target = Path(directory) / "target"
            target.write_text("private")
            os.symlink(target, path)
            with self.assertRaisesRegex(ValueError, "unavailable"):
                consume_play_session_grant(
                    path,
                    framework_session_id=SESSION,
                    checkpoint_id=CHECKPOINT,
                    spec_sha256=DIGEST,
                    task_id=TASK,
                    now=112.0,
                )


if __name__ == "__main__":
    unittest.main()
