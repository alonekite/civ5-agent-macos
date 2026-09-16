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
    ):
        self.states = iter(states)
        self.end_turn_result = end_turn_result
        self.research_result = research_result
        self.production_result = production_result
        self.skip_result = skip_result

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


if __name__ == "__main__":
    unittest.main()
