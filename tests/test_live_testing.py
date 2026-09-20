import copy
import json
import stat
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from civ5_agent.live_testing import (
    PROFILE_M11,
    DataInconsistencyError,
    LiveTestingError,
    M11ResearchRuntimeProfile,
    RuntimePaths,
    SessionLock,
    Supervisor,
    _new_state,
    _read_state,
    _sanitize_message,
    _stop_orphan_watcher,
    _stop_watcher,
    _write_state,
    run_recover,
    run_start,
)
from civ5_agent.models import GameState
from civ5_agent.watch import make_control_handler


def research_state(
    *,
    turn=10,
    technology="TECH_WRITING",
    cost=100,
    progress=9850,
    science=275,
    overflow=0,
):
    current = None
    research = None
    candidates = []
    if technology is not None:
        current = {
            "type": technology,
            "cost": cost,
            "progress_times100": progress,
            "turns_left_with_overflow": 1,
        }
        research = {"type": technology}
        candidates = [current.copy()]
    return GameState(
        schema_version=8,
        turn=turn,
        research=research,
        research_runtime_facts={
            "status": "supported",
            "reason": None,
            "phase": "action_window_after_interturn_research_resolution",
            "science_per_turn_times100": science,
            "overflow_research": overflow,
            "current": current,
            "candidates": candidates,
        },
        runtime_context={
            "context_version": 1,
            "game_speed": {"status": "available"},
            "game_build": {"status": "unavailable"},
        },
    )


class FakeWatcherClient:
    def __init__(self, *states):
        self.states = list(states)

    def read_state(self):
        if len(self.states) > 1:
            return "session", self.states.pop(0)
        return "session", self.states[0]


class ReadOnlyWatcherTest(unittest.TestCase):
    def test_server_enforced_mode_rejects_every_non_read_operation(self):
        client = Mock()
        client.read_game_state.return_value = GameState(
            schema_version=2,
            turn=1,
            active_player=0,
            gold=0,
            turn_active=True,
            can_end_turn=True,
            end_turn_blocking_type=-1,
        )
        handler = make_control_handler(
            client,
            7,
            threading.Lock(),
            read_only=True,
        )
        self.assertTrue(handler({"op": "ping"})["read_only"])
        self.assertTrue(handler({"op": "read_state"})["ok"])
        for operation in ("end_turn", "command_status", "choose_research"):
            with self.subTest(operation=operation):
                response = handler({"op": operation})
                self.assertFalse(response["ok"])
                self.assertIn("read-only", response["error"])


class LiveTestingStateTest(unittest.TestCase):
    def test_recovery_state_is_private_and_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private/session.json"
            state = _new_state(PROFILE_M11)
            _write_state(path, state)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            self.assertEqual(_read_state(path), state)
            payload = json.loads(path.read_text())
            payload["snapshot"] = {"player_name": "private"}
            path.write_text(json.dumps(payload))
            path.chmod(0o600)
            with self.assertRaisesRegex(LiveTestingError, "unsupported fields"):
                _read_state(path)

    def test_single_session_lock_refuses_second_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.lock"
            with SessionLock(path):
                with self.assertRaisesRegex(LiveTestingError, "another live-test"):
                    with SessionLock(path):
                        self.fail("second lock unexpectedly acquired")

    def test_diagnostics_redact_the_home_directory(self):
        self.assertEqual(
            _sanitize_message(str(Path.home()) + "/private/file"),
            "<home>/private/file",
        )

    def test_recovery_state_rejects_snapshot_fields_inside_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            state = _new_state(PROFILE_M11)
            state["checkpoints"]["live_state"] = {
                "status": "pass",
                "evidence": {"player_name": "private"},
            }
            with self.assertRaisesRegex(LiveTestingError, "snapshot fields"):
                _write_state(path, state)


class M11ProfileTest(unittest.TestCase):
    def setUp(self):
        self.profile = M11ResearchRuntimeProfile()
        self.state = _new_state(PROFILE_M11)

    def paths(self, root):
        return RuntimePaths.under(Path(root))

    def test_generalized_overflow_precondition_preserves_fraction(self):
        game = research_state(progress=9850, science=275)
        with tempfile.TemporaryDirectory() as directory:
            result = self.profile.run(
                "overflow_precondition",
                self.state,
                FakeWatcherClient(game),
                self.paths(directory),
            )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["evidence"]["remaining_times100"], 150)
        self.assertEqual(result["evidence"]["surplus_times100"], 125)
        self.assertEqual(result["evidence"]["expected_whole_overflow"], 1)
        self.assertEqual(result["evidence"]["fractional_surplus_times100"], 25)

    def test_absent_overflow_window_is_pending_not_inconsistent(self):
        game = research_state(progress=9000, science=500)
        with tempfile.TemporaryDirectory() as directory:
            result = self.profile.run(
                "overflow_precondition",
                self.state,
                FakeWatcherClient(game),
                self.paths(directory),
            )
        self.assertEqual(result["status"], "pending")

    def test_repeated_read_detects_changed_bounded_facts(self):
        first = research_state()
        second = copy.deepcopy(first)
        second.research_runtime_facts["science_per_turn_times100"] = 276
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(DataInconsistencyError, "repeated reads"):
                self.profile.run(
                    "repeated_read",
                    self.state,
                    FakeWatcherClient(first, second),
                    self.paths(directory),
                )

    def test_complete_overflow_sequence_uses_prior_exact_summary(self):
        pre = research_state(progress=9850, science=275)
        with tempfile.TemporaryDirectory() as directory:
            paths = self.paths(directory)
            self.state["checkpoints"]["overflow_precondition"] = self.profile.run(
                "overflow_precondition", self.state, FakeWatcherClient(pre), paths
            )
            after = research_state(
                turn=11,
                technology=None,
                cost=0,
                progress=0,
                science=275,
                overflow=1,
            )
            completion = self.profile.run(
                "overflow_completion", self.state, FakeWatcherClient(after), paths
            )
            self.state["checkpoints"]["overflow_completion"] = completion
            selected = research_state(
                turn=11,
                technology="TECH_PHILOSOPHY",
                cost=120,
                progress=0,
                science=275,
                overflow=1,
            )
            selection = self.profile.run(
                "selection_stability", self.state, FakeWatcherClient(selected), paths
            )
            self.state["checkpoints"]["selection_stability"] = selection
            applied = research_state(
                turn=12,
                technology="TECH_PHILOSOPHY",
                cost=120,
                progress=375,
                science=275,
                overflow=0,
            )
            application = self.profile.run(
                "overflow_application", self.state, FakeWatcherClient(applied), paths
            )
        self.assertEqual(completion["status"], "pass")
        self.assertEqual(selection["status"], "pass")
        self.assertEqual(application["status"], "pass")

    def test_audit_checkpoint_requires_zero_records_and_mode_600(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.paths(directory)
            paths.audit.write_text("")
            paths.audit.chmod(0o600)
            result = self.profile.run(
                "audit_clean", self.state, FakeWatcherClient(), paths
            )
            self.assertEqual(result["evidence"], {"records": 0, "permissions": "600"})
            paths.audit.write_text("{}\n")
            with self.assertRaises(DataInconsistencyError):
                self.profile.run("audit_clean", self.state, FakeWatcherClient(), paths)


class SupervisorTest(unittest.TestCase):
    def test_data_inconsistency_pauses_and_preserves_state(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = RuntimePaths.under(Path(directory))
            state = _new_state(PROFILE_M11)
            _write_state(paths.state, state)
            profile = Mock()
            profile.checkpoints = ("live_state",)
            profile.run.side_effect = DataInconsistencyError("facts disagree")
            supervisor = Supervisor(paths, state, profile=profile)
            with patch("civ5_agent.live_testing.WatcherBridgeClient"):
                response = supervisor.handle({"op": "checkpoint", "name": "live_state"})
            self.assertFalse(response["ok"])
            self.assertEqual(state["phase"], "paused_data_inconsistency")
            self.assertTrue(paths.state.exists())

    def test_visual_confirmation_records_only_bounded_source_and_note(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = RuntimePaths.under(Path(directory))
            state = _new_state(PROFILE_M11)
            _write_state(paths.state, state)
            response = Supervisor(paths, state).handle(
                {
                    "op": "confirm",
                    "name": "ui_agreement",
                    "result": "pass",
                    "source": "codex",
                    "note": "visible values agree",
                }
            )
            self.assertTrue(response["ok"])
            persisted = _read_state(paths.state)
            self.assertEqual(
                persisted["checkpoints"]["ui_agreement"]["confirmation"]["source"],
                "codex",
            )
            self.assertNotIn(
                "note",
                persisted["checkpoints"]["ui_agreement"]["confirmation"],
            )

    def test_visual_confirmation_cannot_override_data_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = RuntimePaths.under(Path(directory))
            state = _new_state(PROFILE_M11)
            _write_state(paths.state, state)
            response = Supervisor(paths, state).handle(
                {
                    "op": "confirm",
                    "name": "overflow_completion",
                    "result": "pass",
                    "source": "user",
                }
            )
            self.assertFalse(response["ok"])
            self.assertNotIn("overflow_completion", state["checkpoints"])

    def test_status_and_finish_are_controlled_without_game_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = RuntimePaths.under(Path(directory))
            state = _new_state(PROFILE_M11)
            _write_state(paths.state, state)
            supervisor = Supervisor(paths, state)
            status = supervisor.handle({"op": "status"})
            finished = supervisor.handle({"op": "finish"})
        self.assertEqual(status["profile"], PROFILE_M11)
        self.assertEqual(finished["result"], "finish_requested")
        self.assertTrue(supervisor.stop_event.is_set())


class LifecycleTest(unittest.TestCase):
    def test_start_composes_guard_launch_read_only_watcher_and_cleanup(self):
        process = Mock(pid=2468)
        with tempfile.TemporaryDirectory() as directory, patch(
            "civ5_agent.live_testing.prepare"
        ) as prepare, patch(
            "civ5_agent.live_testing._launch_game"
        ) as launch, patch(
            "civ5_agent.live_testing._wait_for_live"
        ) as wait_live, patch(
            "civ5_agent.live_testing._launch_watcher", return_value=process
        ) as launch_watcher, patch(
            "civ5_agent.live_testing._install_signal_handlers"
        ), patch.object(
            Supervisor, "serve", return_value=0
        ) as serve, patch(
            "civ5_agent.live_testing._cleanup"
        ) as cleanup:
            result = run_start(PROFILE_M11, runtime_dir=Path(directory))
        self.assertEqual(result, 0)
        prepare.assert_called_once_with()
        launch.assert_called_once_with()
        wait_live.assert_called_once()
        launch_watcher.assert_called_once()
        serve.assert_called_once_with()
        cleanup.assert_called_once()

    def test_recover_restores_when_game_is_already_closed(self):
        status = Mock(port_4318_listening=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = RuntimePaths.under(root)
            _write_state(paths.state, _new_state(PROFILE_M11))
            with patch(
                "civ5_agent.live_testing.inspect_safety", return_value=status
            ), patch(
                "civ5_agent.live_testing._stop_orphan_watcher"
            ) as stop, patch(
                "civ5_agent.live_testing.restore"
            ) as restore:
                result = run_recover(runtime_dir=root)
            self.assertEqual(result, 0)
            stop.assert_called_once()
            restore.assert_called_once_with()
            self.assertFalse(paths.state.exists())

    def test_stopping_watcher_may_kill_child_but_never_targets_game(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("watcher", 10), None]
        with tempfile.TemporaryDirectory() as directory:
            _stop_watcher(process, RuntimePaths.under(Path(directory)))
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()

    def test_recovery_refuses_ambiguous_reused_process_id(self):
        inspection = Mock(returncode=0, stdout="/Applications/Other.app/other")
        with tempfile.TemporaryDirectory() as directory, patch(
            "civ5_agent.live_testing.subprocess.run", return_value=inspection
        ), patch("civ5_agent.live_testing.os.kill") as kill:
            with self.assertRaisesRegex(LiveTestingError, "ambiguous"):
                _stop_orphan_watcher(
                    4321,
                    RuntimePaths.under(Path(directory)),
                )
        kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
