import socket
import unittest
from unittest.mock import patch

from civ5_agent.preflight import UnsafeSessionError
from civ5_agent.tuner import (
    HEADER,
    TAG_COMMAND,
    TAG_HANDSHAKE,
    FireTunerClient,
    LuaState,
    TunerMessage,
    decode_states,
    encode_message,
    choose_research_lua,
    city_production_lua,
    end_turn_lua,
    parse_lua_states,
    parse_game_state,
    parse_end_turn_response,
    parse_choose_research_response,
    parse_city_production_response,
    parse_skip_unit_response,
    parse_snapshot,
    skip_unit_lua,
    snapshot_lua,
)


class TunerProtocolTest(unittest.TestCase):
    def test_connect_requires_safe_session_before_opening_socket(self):
        client = FireTunerClient()
        with patch(
            "civ5_agent.tuner.require_safe_tuner_session",
            side_effect=UnsafeSessionError("firewall disabled"),
        ), patch("civ5_agent.tuner.socket.create_connection") as connect:
            with self.assertRaisesRegex(UnsafeSessionError, "firewall disabled"):
                client.connect()
        connect.assert_not_called()

    def test_encodes_firaxis_frame(self):
        frame = encode_message(TAG_HANDSHAKE, "APP:")
        length, tag = HEADER.unpack(frame[: HEADER.size])
        self.assertEqual(length, 5)
        self.assertEqual(tag, TAG_HANDSHAKE)
        self.assertEqual(frame[HEADER.size :], b"APP:\x00")

    def test_rejects_non_positive_frame_length(self):
        client = FireTunerClient()
        client._socket = _FakeSocket([HEADER.pack(0, TAG_COMMAND)])
        with self.assertRaisesRegex(ValueError, "invalid tuner message length"):
            client.receive()

    def test_decodes_null_separated_states(self):
        self.assertEqual(decode_states("GameCore\x00InGame"), ("GameCore", "InGame"))

    def test_decodes_newline_separated_states(self):
        self.assertEqual(decode_states("GameCore\nInGame\n"), ("GameCore", "InGame"))

    def test_parses_civ5_id_name_pairs(self):
        self.assertEqual(
            parse_lua_states("0\x00Main State\x00172\x00InGame"),
            (LuaState(0, "Main State"), LuaState(172, "InGame")),
        )

    def test_handshake_skips_unsolicited_lifecycle_update(self):
        fake_socket = _FakeSocket(
            [
                encode_message(-1, "L\x000\x00Main State"),
                encode_message(TAG_HANDSHAKE, "Civ5\x00Civilization V"),
                encode_message(TAG_HANDSHAKE, "0\x00Main State\x00172\x00InGame"),
            ]
        )
        client = FireTunerClient()
        client._socket = fake_socket

        handshake = client.handshake()

        self.assertEqual(handshake.application, "Civ5\x00Civilization V")
        self.assertEqual(handshake.lua_states[-1], LuaState(172, "InGame"))

    def test_collect_treats_idle_as_end_of_asynchronous_response(self):
        fake_socket = _FakeSocket([encode_message(9, "first"), socket.timeout()])
        client = FireTunerClient()
        client._socket = fake_socket

        with patch("civ5_agent.tuner.time.monotonic", side_effect=[0.0, 0.1, 0.2]):
            responses = client.execute_collect(172, 'print("probe")')

        self.assertEqual(tuple(message.payload for message in responses), ("first",))
        self.assertEqual(fake_socket.sent, encode_message(TAG_COMMAND, 'CMD:172:print("probe")'))

    def test_collect_ignores_lua_state_lifecycle_frames(self):
        fake_socket = _FakeSocket(
            [
                encode_message(-1, "L\x000\x00Main State\x00172\x00InGame"),
                encode_message(-1, "CIV5_AGENT_STATE:4:0:12"),
                encode_message(TAG_COMMAND, ""),
            ]
        )
        client = FireTunerClient()
        client._socket = fake_socket

        with patch("civ5_agent.tuner.time.monotonic", side_effect=[0.0, 0.1, 0.2, 0.3]):
            responses = client.execute_collect(172, 'print("probe")')

        self.assertEqual([message.payload for message in responses], ["CIV5_AGENT_STATE:4:0:12", ""])

    def test_collect_reports_game_shutdown_concisely(self):
        fake_socket = _FakeSocket([encode_message(-1, "Closing")])
        client = FireTunerClient()
        client._socket = fake_socket

        with patch("civ5_agent.tuner.time.monotonic", side_effect=[0.0, 0.1]):
            with self.assertRaisesRegex(ConnectionError, "FireTuner is closing"):
                client.execute_collect(172, 'print("probe")')

    def test_parses_game_state_from_prefixed_tuner_output(self):
        messages = (
            TunerMessage(-1, "O\x00InGame: CIV5_AGENT_STATE:1:0:3"),
            TunerMessage(3, ""),
        )
        self.assertEqual(parse_game_state(messages), (1, 0, 3))

    def test_rejects_response_without_game_state_marker(self):
        with self.assertRaisesRegex(ValueError, "did not return"):
            parse_game_state((TunerMessage(-1, "Lua error"),))

    def test_parses_rich_snapshot_records(self):
        messages = (
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_SNAPSHOT|3|2|0|7|4|5|9|0|1|33|0|Isabella|Spain|3|TECH_POTTERY|6|35|true|false|8",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_CITY|4|Mad%7Crid|10|11|2|"
                "TXT_KEY_UNIT_WARRIOR|525|24|300|800|40|500",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_UNIT|8|Warrior|UNIT_WARRIOR|"
                "9|12|120|15|100|8|0|1",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_DIPLOMACY|1|1|Harun%7Cal-Rashid|Arabia|24|false|4",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_VICTORY|science|true|1|2|1|0|1",
            ),
            TunerMessage(3, ""),
        )

        state = parse_snapshot(messages)

        self.assertEqual(state.schema_version, 3)
        self.assertEqual(state.turn, 2)
        self.assertEqual(state.player_name, "Isabella")
        self.assertEqual(state.score, 33)
        self.assertEqual(state.current_era, 0)
        self.assertTrue(state.turn_active)
        self.assertFalse(state.can_end_turn)
        self.assertEqual(state.end_turn_blocking_type, 8)
        self.assertEqual(
            state.research,
            {"id": 3, "type": "TECH_POTTERY", "progress": 6, "cost": 35},
        )
        self.assertEqual(state.cities[0]["name"], "Mad|rid")
        self.assertEqual(state.cities[0]["food_times100"], 525)
        self.assertEqual(state.cities[0]["production_per_turn_times100"], 500)
        self.assertEqual(state.units[0]["moves"], 120)
        self.assertEqual(state.units[0]["damage"], 15)
        self.assertEqual(state.units[0]["combat_strength"], 8)
        self.assertEqual(
            state.diplomacy[0],
            {
                "player_id": 1,
                "team_id": 1,
                "name": "Harun|al-Rashid",
                "civilization": "Arabia",
                "score": 24,
                "at_war": False,
                "approach": 4,
            },
        )
        self.assertEqual(
            state.victory,
            {
                "science_enabled": True,
                "apollo": 1,
                "booster": 2,
                "cockpit": 1,
                "stasis_chamber": 0,
                "engine": 1,
            },
        )

    def test_parses_legacy_schema_two_snapshot(self):
        state = parse_snapshot(
            (
                TunerMessage(
                    -1,
                    "CIV5_AGENT_SNAPSHOT|2|2|0|7|4|5|9|0|1|Isabella|Spain|-1||-1|-1|true|true|-1",
                ),
            )
        )
        self.assertEqual(state.schema_version, 2)
        self.assertIsNone(state.score)
        self.assertIsNone(state.current_era)
        self.assertIsNone(state.research)

    def test_rejects_records_before_header_and_duplicate_headers(self):
        with self.assertRaisesRegex(ValueError, "before snapshot header"):
            parse_snapshot(
                (TunerMessage(-1, "CIV5_AGENT_UNIT|8|W|UNIT_W|1|2|0"),)
            )
        header = (
            "CIV5_AGENT_SNAPSHOT|3|2|0|7|4|5|9|0|1|33|0|Isabella|Spain|"
            "-1||-1|-1|true|true|-1"
        )
        with self.assertRaisesRegex(ValueError, "multiple snapshot headers"):
            parse_snapshot((TunerMessage(-1, header), TunerMessage(-1, header)))
        victory = "CIV5_AGENT_VICTORY|science|true|0|0|0|0|0"
        with self.assertRaisesRegex(ValueError, "multiple victory records"):
            parse_snapshot(
                (
                    TunerMessage(-1, header),
                    TunerMessage(-1, victory),
                    TunerMessage(-1, victory),
                )
            )

    def test_parses_end_turn_precondition_result(self):
        self.assertEqual(
            parse_end_turn_response(
                (TunerMessage(-1, "InGame: CIV5_AGENT_COMMAND|end_turn|blocked|8"),)
            ),
            (False, 8),
        )

    def test_snapshot_lua_contains_no_game_write_calls(self):
        lua = snapshot_lua()
        for forbidden in (
            "Game.DoControl",
            ":SetGold",
            ":ChangeGold",
            ":PushResearch",
            "SelectionListGameNetMessage",
        ):
            self.assertNotIn(forbidden, lua)

    def test_snapshot_lua_only_emits_met_major_civilizations(self):
        lua = snapshot_lua()
        self.assertIn("GameDefines.MAX_MAJOR_CIVS", lua)
        self.assertIn("myTeam:IsHasMet(o:GetTeam())", lua)
        self.assertIn("myTeam:IsAtWar(o:GetTeam())", lua)

    def test_snapshot_lua_reads_active_team_science_victory_projects(self):
        lua = snapshot_lua()
        self.assertIn('GameInfo.Victories["VICTORY_SPACE_RACE"]', lua)
        self.assertIn('projectCount("PROJECT_APOLLO_PROGRAM")', lua)
        self.assertIn('projectCount("PROJECT_SS_ENGINE")', lua)

    def test_end_turn_is_narrow_and_preconditioned(self):
        lua = end_turn_lua()
        self.assertIn("UI.CanEndTurn()", lua)
        self.assertIn("Game.IsProcessingMessages()", lua)
        self.assertIn("ENDTURN_BLOCKING_UNIT_NEEDS_ORDERS", lua)
        self.assertIn("ENDTURN_BLOCKING_FOUND_RELIGION", lua)
        self.assertIn("ENDTURN_BLOCKING_LEAGUE_CALL_FOR_VOTES", lua)
        self.assertIn("Network.HasSentNetTurnComplete()", lua)
        self.assertIn("not blocked", lua)
        self.assertEqual(lua.count("Game.DoControl"), 1)

    def test_choose_research_rejects_lua_injection(self):
        with self.assertRaisesRegex(ValueError, "must match"):
            choose_research_lua('TECH_POTTERY; Game.DoControl(1)')

    def test_choose_research_uses_stock_network_api_and_checks_availability(self):
        lua = choose_research_lua("TECH_POTTERY")
        self.assertIn("p:CanResearch(tech)", lua)
        self.assertIn("Network.SendResearch(tech,0,-1,false)", lua)

    def test_parses_choose_research_response(self):
        messages = (
            TunerMessage(
                -1,
                "InGame: CIV5_AGENT_COMMAND|choose_research|accepted|1",
            ),
        )
        self.assertEqual(parse_choose_research_response(messages), ("accepted", 1))

    def test_city_production_rejects_untrusted_identifiers(self):
        with self.assertRaisesRegex(ValueError, "invalid format"):
            city_production_lua(4, "unit", "UNIT_SCOUT; os.execute('bad')")
        with self.assertRaisesRegex(ValueError, "kind"):
            city_production_lua(4, "purchase", "UNIT_SCOUT")

    def test_city_production_uses_stock_api_and_capability_check(self):
        lua = city_production_lua(8192, "unit", "UNIT_SCOUT")
        self.assertIn("p:GetCityByID(8192)", lua)
        self.assertIn("city:CanTrain(item)", lua)
        self.assertIn("Game.CityPushOrder(city,OrderTypes.ORDER_TRAIN", lua)

    def test_parses_city_production_response(self):
        messages = (
            TunerMessage(
                -1,
                "InGame: CIV5_AGENT_COMMAND|set_city_production|accepted|3|TXT_KEY_UNIT_SCOUT",
            ),
        )
        self.assertEqual(
            parse_city_production_response(messages),
            ("accepted", 3, "TXT_KEY_UNIT_SCOUT"),
        )

    def test_skip_unit_rejects_invalid_identifier(self):
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            skip_unit_lua(True)
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            skip_unit_lua(-1)

    def test_skip_unit_selects_and_rechecks_exact_owned_unit(self):
        lua = skip_unit_lua(16385)
        self.assertIn("p:GetUnitByID(16385)", lua)
        self.assertIn("UI.ClearSelectionList()", lua)
        self.assertIn("UI.SelectUnit(unit)", lua)
        self.assertIn("selected:GetID()~=16385", lua)
        self.assertIn("Game.CanHandleAction(action)", lua)
        self.assertEqual(lua.count("Game.SelectionListGameNetMessage"), 1)

    def test_parses_skip_unit_response(self):
        messages = (
            TunerMessage(-1, "InGame: CIV5_AGENT_COMMAND|skip_unit|accepted|16385"),
        )
        self.assertEqual(parse_skip_unit_response(messages), ("accepted", 16385))


class _FakeSocket:
    def __init__(self, events):
        self.events = list(events)
        self.sent = b""
        self.timeout = 3.0

    def sendall(self, data):
        self.sent += data

    def recv(self, length):
        event = self.events[0]
        if isinstance(event, BaseException):
            self.events.pop(0)
            raise event
        chunk = event[:length]
        self.events[0] = event[length:]
        if not self.events[0]:
            self.events.pop(0)
        return chunk

    def gettimeout(self):
        return self.timeout

    def settimeout(self, value):
        self.timeout = value


if __name__ == "__main__":
    unittest.main()
