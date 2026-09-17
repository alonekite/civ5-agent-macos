import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from civ5_agent.command import (
    execute_choose_research,
    execute_city_production,
    execute_end_turn,
    execute_move_unit,
    execute_skip_unit,
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
    ):
        self.states = iter(states)
        self.end_turn_result = end_turn_result
        self.research_result = research_result
        self.production_result = production_result
        self.skip_result = skip_result
        self.move_result = move_result

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


def movement_state(*, x=9, y=12, moves=120, unit_type="UNIT_WARRIOR", turn=3):
    state = GameState(
        schema_version=6,
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
        self.assertIn("schema 6", result.message)

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


if __name__ == "__main__":
    unittest.main()
