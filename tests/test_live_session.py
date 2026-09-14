import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from civ5_agent.live_session import (
    LiveSessionError,
    _run_firewall_command,
    prepare,
    restore,
)
from civ5_agent.preflight import SafetyStatus


def status(**overrides):
    values = {
        "phase": "status",
        "firetuner_enabled": False,
        "firewall_enabled": False,
        "civ_rule_present": False,
        "civ_incoming_blocked": False,
        "port_4318_listening": False,
        "agent_socket_present": False,
    }
    values.update(overrides)
    return SafetyStatus(**values)


class LiveSessionTest(unittest.TestCase):
    @patch("civ5_agent.live_session.subprocess.run")
    @patch("civ5_agent.live_session.os.geteuid", return_value=501)
    def test_firewall_mutations_use_sudo_without_elevating_python(
        self, _geteuid, run
    ):
        run.return_value.stdout = ""
        _run_firewall_command(Path("/firewall"), "--setglobalstate", "on")
        self.assertEqual(
            run.call_args.args[0],
            ["/usr/bin/sudo", "/firewall", "--setglobalstate", "on"],
        )

    def test_prepare_records_baseline_and_verifies_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.ini"
            config.write_text("EnableTuner = 0\nLoggingEnabled = 0\n")
            commands = []

            with patch(
                "civ5_agent.live_session.inspect_safety",
                side_effect=[
                    status(),
                    status(civ_rule_present=True, civ_incoming_blocked=True),
                    status(
                        phase="ready",
                        firetuner_enabled=True,
                        firewall_enabled=True,
                        civ_rule_present=True,
                        civ_incoming_blocked=True,
                    ),
                ],
            ):
                result = prepare(
                    config_path=config,
                    session_dir=root / "session",
                    command_runner=lambda *args: commands.append(args) or "",
                )

            self.assertEqual(result["result"], "prepared")
            self.assertIn("EnableTuner = 1", config.read_text())
            self.assertEqual([command[1] for command in commands], [
                "--add",
                "--blockapp",
                "--setglobalstate",
            ])
            state_path = root / "session/live-session.json"
            self.assertEqual(json.loads(state_path.read_text())["phase"], "prepared")
            self.assertEqual(state_path.stat().st_mode & 0o777, 0o600)

    def test_prepare_is_idempotent_when_recorded_session_is_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session"
            session.mkdir()
            (session / "live-session-config.backup").write_text("EnableTuner = 0\n")
            (session / "live-session.json").write_text(json.dumps({
                "schema_version": 1,
                "phase": "prepared",
                "firewall_enabled": False,
                "civ_rule_present": False,
                "civ_incoming_blocked": False,
            }))
            ready = status(
                phase="ready",
                firetuner_enabled=True,
                firewall_enabled=True,
                civ_rule_present=True,
                civ_incoming_blocked=True,
            )
            with patch("civ5_agent.live_session.inspect_safety", return_value=ready):
                result = prepare(
                    config_path=root / "unused.ini",
                    session_dir=session,
                    command_runner=lambda *args: self.fail("unexpected mutation"),
                )
            self.assertEqual(result["result"], "already_prepared")

    def test_prepare_rejects_recorded_session_without_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session"
            session.mkdir()
            (session / "live-session.json").write_text(json.dumps({
                "schema_version": 1,
                "phase": "prepared",
                "firewall_enabled": False,
                "civ_rule_present": False,
                "civ_incoming_blocked": False,
            }))
            with self.assertRaisesRegex(LiveSessionError, "missing its config backup"):
                prepare(config_path=root / "unused.ini", session_dir=session)

    def test_prepare_rolls_back_every_changed_boundary_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.ini"
            config.write_text("EnableTuner = 0\n")
            commands = []
            unsafe = status(
                phase="ready",
                firetuner_enabled=True,
                firewall_enabled=True,
                civ_rule_present=True,
                civ_incoming_blocked=True,
                issues=["verification failed"],
            )
            with patch(
                "civ5_agent.live_session.inspect_safety",
                side_effect=[
                    status(),
                    status(civ_rule_present=True, civ_incoming_blocked=True),
                    unsafe,
                    unsafe,
                ],
            ):
                with self.assertRaisesRegex(LiveSessionError, "rolled back"):
                    prepare(
                        config_path=config,
                        session_dir=root / "session",
                        command_runner=lambda *args: commands.append(args) or "",
                    )
            self.assertEqual(config.read_text(), "EnableTuner = 0\n")
            self.assertEqual([command[1] for command in commands], [
                "--add",
                "--blockapp",
                "--setglobalstate",
                "--remove",
                "--setglobalstate",
            ])
            self.assertFalse((root / "session/live-session.json").exists())

    def test_prepare_cleans_recovery_state_when_first_mutation_is_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.ini"
            config.write_text("EnableTuner = 0\n")
            commands = []

            def deny_first(*args):
                commands.append(args)
                raise PermissionError("administrator authentication required")

            with patch(
                "civ5_agent.live_session.inspect_safety",
                side_effect=[status(), status()],
            ):
                with self.assertRaisesRegex(LiveSessionError, "rolled back"):
                    prepare(
                        config_path=config,
                        session_dir=root / "session",
                        command_runner=deny_first,
                    )
            self.assertEqual(len(commands), 1)
            self.assertFalse((root / "session/live-session.json").exists())

    def test_restore_returns_all_boundaries_to_recorded_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session"
            session.mkdir()
            config = root / "config.ini"
            config.write_text("EnableTuner = 1\n")
            (session / "live-session-config.backup").write_text("EnableTuner = 0\n")
            (session / "live-session.json").write_text(json.dumps({
                "schema_version": 1,
                "phase": "prepared",
                "firewall_enabled": False,
                "civ_rule_present": False,
                "civ_incoming_blocked": False,
            }))
            commands = []
            with patch(
                "civ5_agent.live_session.inspect_safety",
                side_effect=[
                    status(
                        firetuner_enabled=True,
                        firewall_enabled=True,
                        civ_rule_present=True,
                        civ_incoming_blocked=True,
                    ),
                    status(phase="shutdown"),
                ],
            ):
                result = restore(
                    config_path=config,
                    session_dir=session,
                    command_runner=lambda *args: commands.append(args) or "",
                )
            self.assertEqual(result["result"], "restored")
            self.assertEqual(config.read_text(), "EnableTuner = 0\n")
            self.assertEqual([command[1] for command in commands], [
                "--remove",
                "--setglobalstate",
            ])
            self.assertFalse((session / "live-session.json").exists())
            self.assertFalse((session / "live-session-config.backup").exists())

    def test_restore_refuses_while_game_is_listening(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session"
            session.mkdir()
            (session / "live-session.json").write_text(json.dumps({
                "schema_version": 1,
                "phase": "prepared",
                "firewall_enabled": False,
                "civ_rule_present": False,
                "civ_incoming_blocked": False,
            }))
            with patch(
                "civ5_agent.live_session.inspect_safety",
                return_value=status(port_4318_listening=True),
            ):
                with self.assertRaisesRegex(LiveSessionError, "quit Civilization"):
                    restore(
                        config_path=root / "config.ini",
                        session_dir=session,
                    )


if __name__ == "__main__":
    unittest.main()
