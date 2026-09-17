import io
import json
import tempfile
import unittest
from copy import deepcopy
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from civ5_agent.actions import CommandValidationError
from civ5_agent.command import (
    execute_choose_research,
    execute_city_production,
    execute_end_turn,
    execute_move_unit,
    execute_skip_unit,
    execute_worker_build,
    main,
)
from civ5_agent.models import Command, GameState


class _FakeClient:
    def __init__(
        self,
        states,
        end_turn_result=(False, 0),
        research_result=("blocked", -1),
        production_result=("blocked", -1, ""),
        skip_result=("blocked", -1),
        move_result=("blocked", -1, -1, -1),
        worker_build_result=("blocked", -1, "BUILD_X"),
    ):
        self.states = iter(states)
        self.end_turn_result = end_turn_result
        self.research_result = research_result
        self.production_result = production_result
        self.skip_result = skip_result
        self.move_result = move_result
        self.worker_build_result = worker_build_result

    def read_game_state(self, state_id):
        state = next(self.states)
        if isinstance(state, Exception):
            raise state
        return state

    def request_end_turn(self, state_id):
        return self.end_turn_result

    def request_choose_research(self, state_id, tech_type):
        return self.research_result

    def request_city_production(self, state_id, city_id, kind, item_type):
        return self.production_result

    def request_skip_unit(self, state_id, unit_id):
        return self.skip_result

    def request_move_unit(
        self, state_id, unit_id, source_x, source_y, target_x, target_y
    ):
        return self.move_result

    def request_worker_build(self, state_id, unit_id, source_x, source_y, build_type):
        return self.worker_build_result


def game_state(turn, gold):
    return GameState(
        schema_version=2,
        turn=turn,
        active_player=0,
        gold=gold,
        turn_active=True,
        can_end_turn=True,
        end_turn_blocking_type=-1,
    )


def movement_state(
    *,
    x=9,
    y=12,
    moves=120,
    unit_type="UNIT_WARRIOR",
    turn=3,
    schema_version=6,
):
    state = GameState(
        schema_version=schema_version,
        turn=turn,
        active_player=0,
        gold=0,
        score=0,
        current_era=0,
        turn_active=True,
        can_end_turn=True,
        end_turn_blocking_type=-1,
        victory={
            "science_enabled": True,
            "apollo": 0,
            "booster": 0,
            "cockpit": 0,
            "stasis_chamber": 0,
            "engine": 0,
        },
        research_choice={"required": False, "mode": "normal"},
    )
    state.units = [
        {
            "id": 8,
            "name": "Warrior",
            "type": unit_type,
            "x": x,
            "y": y,
            "moves": moves,
            "damage": 0,
            "max_hit_points": 100,
            "combat_strength": 8,
            "ranged_strength": 0,
            "range": 1,
            "ready_to_move": moves > 0,
            "ordinary_move_targets": [{"x": 10, "y": 12}] if (x, y) == (9, 12) else [],
        }
    ]
    if schema_version >= 7:
        state.units[0].update(
            {
                "current_plot": {
                    "terrain_type": "TERRAIN_GRASS",
                    "feature_type": None,
                    "resource_type": None,
                    "improvement_type": None,
                    "route_type": None,
                    "owner_id": 0,
                    "is_hills": False,
                    "is_water": False,
                    "is_fresh_water": False,
                },
                "current_build_type": None,
                "ordinary_build_actions": [],
            }
        )
    return state


def worker_state(
    *,
    x=9,
    y=12,
    moves=120,
    current_build_type=None,
    improvement_type=None,
    build_actions=None,
    turn=3,
    unit_type="UNIT_WORKER",
    schema_version=7,
):
    state = movement_state(
        x=x,
        y=y,
        moves=moves,
        unit_type=unit_type,
        turn=turn,
        schema_version=schema_version,
    )
    if schema_version == 7:
        state.units[0]["current_build_type"] = current_build_type
        state.units[0]["current_plot"]["improvement_type"] = improvement_type
        state.units[0]["ordinary_build_actions"] = (
            [{"build_type": "BUILD_FARM", "improvement_type": "IMPROVEMENT_FARM"}]
            if build_actions is None
            else build_actions
        )
    return state


class EndTurnTest(unittest.TestCase):
    def test_does_not_write_when_game_reports_blocker(self):
        client = _FakeClient([game_state(1, 3)], (False, 8))
        result = execute_end_turn(client, 172, Command("end_turn"))
        self.assertEqual(result.status, "error")
        self.assertIn("blocking_type=8", result.message)
        self.assertEqual(result.before, result.after)

    def test_success_requires_turn_to_advance(self):
        client = _FakeClient(
            [game_state(1, 3), game_state(1, 3), game_state(2, 7)],
            (True, 0),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1, 0.2]
        ):
            result = execute_end_turn(client, 172, Command("end_turn"), verify_timeout=1.0)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.before["turn"], 1)
        self.assertEqual(result.after["turn"], 2)

    def test_retries_transient_invalid_state_during_verification(self):
        client = _FakeClient(
            [game_state(1, 3), ValueError("no active match"), game_state(2, 7)],
            (True, 0),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1, 0.2]
        ):
            result = execute_end_turn(client, 172, Command("end_turn"), verify_timeout=1.0)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.after["turn"], 2)


class ChooseResearchTest(unittest.TestCase):
    def test_rejects_unavailable_technology_without_waiting(self):
        client = _FakeClient([game_state(0, 0)], research_result=("blocked", 7))
        command = Command("choose_research", {"tech_type": "TECH_WRITING"})
        result = execute_choose_research(client, 172, command)
        self.assertEqual(result.status, "error")
        self.assertIn("blocked", result.message)

    def test_success_requires_selected_technology_to_be_read_back(self):
        before = game_state(0, 0)
        after = game_state(0, 0)
        after.research = {
            "id": 1,
            "type": "TECH_POTTERY",
            "progress": 0,
            "cost": 40,
        }
        client = _FakeClient(
            [before, after],
            research_result=("accepted", 1),
        )
        command = Command("choose_research", {"tech_type": "TECH_POTTERY"})
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_choose_research(client, 172, command, verify_timeout=1.0)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.after["research"]["type"], "TECH_POTTERY")


class CityProductionTest(unittest.TestCase):
    def test_rejects_city_not_present_in_before_state(self):
        client = _FakeClient([game_state(0, 0)])
        command = Command(
            "set_city_production",
            {"city_id": 9, "kind": "unit", "item_type": "UNIT_SCOUT"},
        )
        result = execute_city_production(client, 172, command)
        self.assertEqual(result.status, "error")
        self.assertIn("not owned", result.message)

    def test_success_requires_production_key_to_be_read_back(self):
        before = game_state(0, 0)
        before.cities = [
            {"id": 4, "name": "Madrid", "x": 10, "y": 11, "population": 1, "production": ""}
        ]
        after = game_state(0, 0)
        after.cities = [
            {
                "id": 4,
                "name": "Madrid",
                "x": 10,
                "y": 11,
                "population": 1,
                "production": "TXT_KEY_UNIT_SCOUT",
            }
        ]
        client = _FakeClient(
            [before, after],
            production_result=("accepted", 3, "TXT_KEY_UNIT_SCOUT"),
        )
        command = Command(
            "set_city_production",
            {"city_id": 4, "kind": "unit", "item_type": "UNIT_SCOUT"},
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_city_production(client, 172, command, verify_timeout=1.0)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.after["cities"][0]["production"], "TXT_KEY_UNIT_SCOUT")


class SkipUnitTest(unittest.TestCase):
    def test_rejects_unit_not_owned_by_active_player(self):
        client = _FakeClient([game_state(0, 0)])
        command = Command("skip_unit", {"unit_id": 99})
        result = execute_skip_unit(client, 172, command)
        self.assertEqual(result.status, "error")
        self.assertIn("not owned", result.message)

    def test_success_requires_unit_to_leave_ready_cycle_without_moving(self):
        before = game_state(0, 0)
        before.units = [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 120,
                "ready_to_move": True,
            }
        ]
        after = game_state(0, 0)
        after.units = [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 120,
                "ready_to_move": False,
            }
        ]
        client = _FakeClient([before, after], skip_result=("accepted", 8))
        command = Command("skip_unit", {"unit_id": 8})
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_skip_unit(client, 172, command, verify_timeout=1.0)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.after["units"][0]["moves"], 120)
        self.assertFalse(result.after["units"][0]["ready_to_move"])

    def test_already_skipped_unit_is_success_without_a_write(self):
        state = game_state(0, 0)
        state.units = [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 120,
                "ready_to_move": False,
            }
        ]
        client = _FakeClient([state], skip_result=("accepted", 8))
        with patch.object(client, "request_skip_unit", wraps=client.request_skip_unit) as write:
            result = execute_skip_unit(
                client, 172, Command("skip_unit", {"unit_id": 8})
            )

        self.assertEqual(result.status, "success")
        self.assertIn("already", result.message)
        write.assert_not_called()

    def test_rejects_snapshot_without_readiness_before_writing(self):
        state = game_state(0, 0)
        state.units = [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 120,
            }
        ]
        client = _FakeClient([state], skip_result=("accepted", 8))
        with patch.object(client, "request_skip_unit", wraps=client.request_skip_unit) as write:
            result = execute_skip_unit(
                client, 172, Command("skip_unit", {"unit_id": 8})
            )

        self.assertEqual(result.status, "error")
        self.assertIn("ready_to_move", result.message)
        write.assert_not_called()

    def test_rejects_postcondition_that_spends_movement(self):
        before = game_state(0, 0)
        before.units = [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 120,
                "ready_to_move": True,
            }
        ]
        after = game_state(0, 0)
        after.units = [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 0,
                "ready_to_move": False,
            }
        ]
        client = _FakeClient([before, after], skip_result=("accepted", 8))
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1, 1.1]
        ):
            result = execute_skip_unit(
                client,
                172,
                Command("skip_unit", {"unit_id": 8}),
                verify_timeout=1.0,
            )

        self.assertEqual(result.status, "error")
        self.assertIn("unchanged movement", result.message)


class MoveUnitTest(unittest.TestCase):
    def test_rejects_malformed_arguments_before_reading_or_writing(self):
        cases = (
            {"unit_id": True, "x": 10, "y": 12},
            {"unit_id": 8, "x": -1, "y": 12},
            {"unit_id": 8, "x": 10, "y": 65_536},
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                client = _FakeClient([])
                with patch.object(client, "read_game_state") as read, patch.object(
                    client, "request_move_unit"
                ) as write:
                    result = execute_move_unit(
                        client, 172, Command("move_unit", arguments)
                    )
                self.assertEqual(result.status, "error")
                read.assert_not_called()
                write.assert_not_called()

    def test_rejects_legacy_state_before_writing(self):
        client = _FakeClient([game_state(3, 0)])
        with patch.object(client, "request_move_unit") as write:
            result = execute_move_unit(
                client, 172, Command("move_unit", {"unit_id": 8, "x": 10, "y": 12})
            )
        self.assertEqual(result.status, "error")
        self.assertIn("schema 6", result.message)
        write.assert_not_called()

    def test_rejects_unknown_unit_or_unlisted_target_before_writing(self):
        cases = (
            ({"unit_id": 99, "x": 10, "y": 12}, "not owned"),
            ({"unit_id": 8, "x": 11, "y": 12}, "not an admitted"),
        )
        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                client = _FakeClient([movement_state()])
                with patch.object(client, "request_move_unit") as write:
                    result = execute_move_unit(
                        client, 172, Command("move_unit", arguments)
                    )
                self.assertEqual(result.status, "error")
                self.assertIn(message, result.message)
                write.assert_not_called()

    def test_success_requires_exact_destination_and_lower_movement(self):
        client = _FakeClient(
            [movement_state(), movement_state(x=10, y=12, moves=60)],
            move_result=("accepted", 8, 10, 12),
        )
        with patch.object(
            client, "request_move_unit", wraps=client.request_move_unit
        ) as write, patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_move_unit(
                client,
                172,
                Command("move_unit", {"unit_id": 8, "x": 10, "y": 12}),
                verify_timeout=1.0,
            )
        self.assertEqual(result.status, "success")
        self.assertEqual((result.after["units"][0]["x"], result.after["units"][0]["y"]), (10, 12))
        self.assertEqual(result.after["units"][0]["moves"], 60)
        write.assert_called_once_with(172, 8, 9, 12, 10, 12)

    def test_schema_seven_preserves_existing_move_unit_behavior(self):
        client = _FakeClient(
            [
                movement_state(schema_version=7),
                movement_state(x=10, y=12, moves=60, schema_version=7),
            ],
            move_result=("accepted", 8, 10, 12),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_move_unit(
                client,
                172,
                Command("move_unit", {"unit_id": 8, "x": 10, "y": 12}),
                verify_timeout=1.0,
            )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.after["schema_version"], 7)

    def test_rejects_game_marker_mismatch_without_polling(self):
        client = _FakeClient(
            [movement_state()], move_result=("accepted", 9, 10, 12)
        )
        result = execute_move_unit(
            client, 172, Command("move_unit", {"unit_id": 8, "x": 10, "y": 12})
        )
        self.assertEqual(result.status, "error")
        self.assertIn("rejected", result.message)

    def test_explicit_game_rejection_does_not_poll_or_retry(self):
        client = _FakeClient(
            [movement_state()], move_result=("blocked", 8, 10, 12)
        )
        with patch.object(
            client, "request_move_unit", wraps=client.request_move_unit
        ) as write:
            result = execute_move_unit(
                client, 172, Command("move_unit", {"unit_id": 8, "x": 10, "y": 12})
            )
        self.assertEqual(result.status, "error")
        self.assertIn("blocked", result.message)
        write.assert_called_once()

    def test_retries_transient_invalid_read_back_then_verifies(self):
        client = _FakeClient(
            [
                movement_state(),
                ValueError("transient snapshot"),
                movement_state(x=10, y=12, moves=60),
            ],
            move_result=("accepted", 8, 10, 12),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1, 0.2]
        ):
            result = execute_move_unit(
                client,
                172,
                Command("move_unit", {"unit_id": 8, "x": 10, "y": 12}),
                verify_timeout=1.0,
            )
        self.assertEqual(result.status, "success")

    def test_rejects_schema_drift_after_acceptance(self):
        client = _FakeClient(
            [movement_state(), game_state(3, 0)],
            move_result=("accepted", 8, 10, 12),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_move_unit(
                client,
                172,
                Command("move_unit", {"unit_id": 8, "x": 10, "y": 12}),
                verify_timeout=1.0,
            )
        self.assertEqual(result.status, "error")
        self.assertIn("live-state schema", result.message)

    def test_rejects_uncontracted_read_back_states(self):
        vanished = movement_state()
        vanished.units = []
        changed_player = movement_state(x=10, y=12, moves=60)
        changed_player.active_player = 1
        inactive = movement_state(x=10, y=12, moves=60)
        inactive.turn_active = False
        cases = (
            (movement_state(x=10, y=12, moves=120), "without lower"),
            (movement_state(x=11, y=12, moves=60), "unexpectedly"),
            (movement_state(x=9, y=12, moves=60), "unexpectedly"),
            (movement_state(x=10, y=12, moves=60, unit_type="UNIT_SPEARMAN"), "lost or transformed"),
            (vanished, "lost or transformed"),
            (movement_state(x=10, y=12, moves=60, turn=4), "changed turn"),
            (changed_player, "changed turn"),
            (inactive, "changed turn"),
        )
        for after, message in cases:
            with self.subTest(message=message):
                client = _FakeClient(
                    [movement_state(), after],
                    move_result=("accepted", 8, 10, 12),
                )
                with patch("civ5_agent.command.time.sleep"), patch(
                    "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
                ):
                    result = execute_move_unit(
                        client,
                        172,
                        Command("move_unit", {"unit_id": 8, "x": 10, "y": 12}),
                        verify_timeout=1.0,
                    )
                self.assertEqual(result.status, "error")
                self.assertIn(message, result.message)

    def test_accepted_but_unchanged_state_times_out(self):
        client = _FakeClient(
            [movement_state(), movement_state()],
            move_result=("accepted", 8, 10, 12),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1, 1.1]
        ):
            result = execute_move_unit(
                client,
                172,
                Command("move_unit", {"unit_id": 8, "x": 10, "y": 12}),
                verify_timeout=1.0,
            )
        self.assertEqual(result.status, "error")
        self.assertIn("did not reach", result.message)


class CommandCliSessionTest(unittest.TestCase):
    def test_brokered_command_echoes_and_verifies_bridge_session(self):
        session_id = "123e4567-e89b-42d3-a456-426614174000"
        command_result = {
            "id": "123e4567-e89b-42d3-a456-426614174001",
            "status": "success",
            "message": "verified",
            "before": {},
            "after": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "bridge.sock"
            socket_path.touch()
            with patch(
                "civ5_agent.command.request",
                side_effect=[
                    {"ok": True, "bridge_session_id": session_id},
                    {
                        "ok": True,
                        "bridge_session_id": session_id,
                        "result": command_result,
                    },
                ],
            ) as broker, patch(
                "sys.argv",
                ["civ5-command", "end_turn", "--socket", str(socket_path)],
            ), redirect_stdout(io.StringIO()) as output:
                status = main()

        self.assertEqual(status, 0)
        sent_command = broker.call_args_list[1].args[0]
        self.assertEqual(sent_command["bridge_session_id"], session_id)
        rendered = json.loads(output.getvalue())
        self.assertEqual(rendered["bridge_session_id"], session_id)
        self.assertEqual(rendered["status"], "success")

    def test_brokered_move_command_forwards_exact_coordinates(self):
        session_id = "123e4567-e89b-42d3-a456-426614174000"
        result = {
            "id": "123e4567-e89b-42d3-a456-426614174001",
            "status": "success",
            "message": "verified",
            "before": {},
            "after": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "bridge.sock"
            socket_path.touch()
            with patch(
                "civ5_agent.command.request",
                side_effect=[
                    {"ok": True, "bridge_session_id": session_id},
                    {
                        "ok": True,
                        "bridge_session_id": session_id,
                        "result": result,
                    },
                ],
            ) as broker, patch(
                "sys.argv",
                [
                    "civ5-command",
                    "move_unit",
                    "8",
                    "10",
                    "12",
                    "--socket",
                    str(socket_path),
                ],
            ), redirect_stdout(io.StringIO()):
                status = main()

        self.assertEqual(status, 0)
        sent = broker.call_args_list[1].args[0]
        self.assertEqual(
            {key: sent[key] for key in ("unit_id", "x", "y")},
            {"unit_id": 8, "x": 10, "y": 12},
        )

    def test_brokered_worker_build_forwards_exact_arguments(self):
        session_id = "123e4567-e89b-42d3-a456-426614174000"
        result = {
            "id": "123e4567-e89b-42d3-a456-426614174001",
            "status": "success",
            "message": "verified",
            "before": {},
            "after": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "bridge.sock"
            socket_path.touch()
            with patch(
                "civ5_agent.command.request",
                side_effect=[
                    {"ok": True, "bridge_session_id": session_id},
                    {
                        "ok": True,
                        "bridge_session_id": session_id,
                        "result": result,
                    },
                ],
            ) as broker, patch(
                "sys.argv",
                [
                    "civ5-command",
                    "worker_build",
                    "8",
                    "9",
                    "12",
                    "BUILD_FARM",
                    "--socket",
                    str(socket_path),
                ],
            ), redirect_stdout(io.StringIO()):
                status = main()

        self.assertEqual(status, 0)
        sent = broker.call_args_list[1].args[0]
        self.assertEqual(
            {key: sent[key] for key in ("unit_id", "x", "y", "build_type")},
            {"unit_id": 8, "x": 9, "y": 12, "build_type": "BUILD_FARM"},
        )


class WorkerBuildTest(unittest.TestCase):
    command = Command(
        "worker_build",
        {"unit_id": 8, "x": 9, "y": 12, "build_type": "BUILD_FARM"},
    )

    def test_rejects_malformed_or_unadmitted_request_without_write(self):
        cases = (
            (Command("worker_build", {"unit_id": 8}), [], "exactly"),
            (self.command, [movement_state(schema_version=6)], "schema 7"),
            (
                Command(
                    "worker_build",
                    {"unit_id": 8, "x": 10, "y": 12, "build_type": "BUILD_FARM"},
                ),
                [worker_state()],
                "stale",
            ),
            (
                self.command,
                [worker_state(build_actions=[])],
                "not one exact admitted",
            ),
            (
                self.command,
                [worker_state(current_build_type="BUILD_FARM")],
                "already executing",
            ),
        )
        for command, states, message in cases:
            with self.subTest(message=message):
                client = _FakeClient(states)
                with patch.object(client, "request_worker_build") as write:
                    result = execute_worker_build(client, 172, command)
                self.assertEqual(result.status, "error")
                self.assertIn(message, result.message)
                write.assert_not_called()

    def test_malformed_schema_seven_state_is_prewrite_rejection(self):
        malformed = worker_state()
        malformed.units.append(dict(malformed.units[0]))
        client = _FakeClient([malformed])
        with patch.object(client, "request_worker_build") as write, self.assertRaises(
            CommandValidationError
        ):
            execute_worker_build(client, 172, self.command)
        write.assert_not_called()

    def test_accepts_active_build_only_after_exact_read_back(self):
        client = _FakeClient(
            [
                worker_state(),
                worker_state(moves=60, current_build_type="BUILD_FARM", build_actions=[]),
            ],
            worker_build_result=("accepted", 8, "BUILD_FARM"),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_worker_build(
                client, 172, self.command, verify_timeout=1.0
            )
        self.assertEqual(result.status, "success")
        self.assertIn("active", result.message)

    def test_accepts_exact_immediate_completion(self):
        client = _FakeClient(
            [
                worker_state(),
                worker_state(
                    moves=60,
                    improvement_type="IMPROVEMENT_FARM",
                    build_actions=[],
                ),
            ],
            worker_build_result=("accepted", 8, "BUILD_FARM"),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_worker_build(
                client, 172, self.command, verify_timeout=1.0
            )
        self.assertEqual(result.status, "success")
        self.assertIn("completed", result.message)

    def test_marker_is_not_success_and_mismatch_does_not_poll(self):
        for marker in (
            ("blocked", 8, "BUILD_FARM"),
            ("accepted", 9, "BUILD_FARM"),
            ("accepted", 8, "BUILD_MINE"),
        ):
            with self.subTest(marker=marker):
                client = _FakeClient([worker_state()], worker_build_result=marker)
                result = execute_worker_build(client, 172, self.command)
                self.assertEqual(result.status, "error")
                self.assertIn("rejected", result.message)

    def test_rejects_wrong_postcondition_after_submission(self):
        client = _FakeClient(
            [worker_state(), worker_state(moves=60, current_build_type="BUILD_MINE", build_actions=[])],
            worker_build_result=("accepted", 8, "BUILD_FARM"),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
        ):
            result = execute_worker_build(client, 172, self.command, verify_timeout=1.0)
        self.assertEqual(result.status, "error")
        self.assertIn("unexpected", result.message)

    def test_rejects_identity_turn_coordinate_and_plot_drift(self):
        base = worker_state(
            moves=60,
            current_build_type="BUILD_FARM",
            build_actions=[],
        )
        cases = []

        vanished = deepcopy(base)
        vanished.units = []
        cases.append(vanished)
        transformed = deepcopy(base)
        transformed.units[0]["type"] = "UNIT_WARRIOR"
        cases.append(transformed)
        moved = deepcopy(base)
        moved.units[0]["x"] = 10
        cases.append(moved)
        changed_turn = deepcopy(base)
        changed_turn.turn = 4
        cases.append(changed_turn)
        changed_player = deepcopy(base)
        changed_player.active_player = 1
        cases.append(changed_player)
        inactive = deepcopy(base)
        inactive.turn_active = False
        cases.append(inactive)
        for field, value in (
            ("terrain_type", "TERRAIN_PLAINS"),
            ("feature_type", "FEATURE_FOREST"),
            ("resource_type", "RESOURCE_WHEAT"),
            ("route_type", "ROUTE_ROAD"),
            ("owner_id", 1),
            ("is_hills", True),
            ("is_water", True),
            ("is_fresh_water", True),
        ):
            changed = deepcopy(base)
            changed.units[0]["current_plot"][field] = value
            cases.append(changed)

        for after in cases:
            with self.subTest(after=after):
                client = _FakeClient(
                    [worker_state(), after],
                    worker_build_result=("accepted", 8, "BUILD_FARM"),
                )
                with patch("civ5_agent.command.time.sleep"), patch(
                    "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
                ):
                    result = execute_worker_build(
                        client, 172, self.command, verify_timeout=1.0
                    )
                self.assertEqual(result.status, "error")

    def test_rejects_ambiguous_or_wrong_build_outcomes(self):
        cases = (
            worker_state(
                moves=60,
                current_build_type="BUILD_FARM",
                improvement_type="IMPROVEMENT_FARM",
                build_actions=[],
            ),
            worker_state(
                moves=60,
                improvement_type="IMPROVEMENT_MINE",
                build_actions=[],
            ),
            worker_state(moves=60, build_actions=[]),
            worker_state(
                moves=60,
                current_build_type="BUILD_MINE",
                build_actions=[],
            ),
        )
        for after in cases:
            with self.subTest(after=after):
                client = _FakeClient(
                    [worker_state(), after],
                    worker_build_result=("accepted", 8, "BUILD_FARM"),
                )
                with patch("civ5_agent.command.time.sleep"), patch(
                    "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1]
                ):
                    result = execute_worker_build(
                        client, 172, self.command, verify_timeout=1.0
                    )
                self.assertEqual(result.status, "error")
                self.assertIn("unexpected", result.message)

    def test_retries_transient_invalid_snapshot_then_verifies(self):
        client = _FakeClient(
            [
                worker_state(),
                ValueError("transient snapshot"),
                worker_state(
                    moves=60,
                    current_build_type="BUILD_FARM",
                    build_actions=[],
                ),
            ],
            worker_build_result=("accepted", 8, "BUILD_FARM"),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1, 0.2]
        ):
            result = execute_worker_build(
                client, 172, self.command, verify_timeout=1.0
            )
        self.assertEqual(result.status, "success")

    def test_accepted_but_unchanged_state_times_out(self):
        client = _FakeClient(
            [worker_state(), worker_state()],
            worker_build_result=("accepted", 8, "BUILD_FARM"),
        )
        with patch("civ5_agent.command.time.sleep"), patch(
            "civ5_agent.command.time.monotonic", side_effect=[0.0, 0.1, 1.1]
        ):
            result = execute_worker_build(
                client, 172, self.command, verify_timeout=1.0
            )
        self.assertEqual(result.status, "error")
        self.assertIn("no exact result", result.message)


if __name__ == "__main__":
    unittest.main()
