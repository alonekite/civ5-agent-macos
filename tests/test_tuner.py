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
    parse_move_unit_response,
    parse_game_state,
    parse_end_turn_response,
    parse_choose_research_response,
    parse_city_production_response,
    parse_skip_unit_response,
    parse_snapshot,
    skip_unit_lua,
    move_unit_lua,
    snapshot_lua,
    snapshot_lua_programs,
    MAX_LUA_PROGRAM_BYTES,
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
                "O\x00InGame: CIV5_AGENT_SNAPSHOT|4|2|0|7|4|5|9|0|1|33|0|Isabella|Spain|3|TECH_POTTERY|6|35|true|false|8",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_PART|cities|2|0",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_CITY|4|Mad%7Crid|10|11|2|"
                "TXT_KEY_UNIT_WARRIOR|525|24|300|800|40|500",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_PART|units|2|0",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_UNIT|8|Warrior|UNIT_WARRIOR|"
                "9|12|120|15|100|8|0|1|true",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_PART|diplomacy|2|0",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_DIPLOMACY|1|1|Harun%7Cal-Rashid|Arabia|24|false|4",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_PART|victory|2|0",
            ),
            TunerMessage(
                -1,
                "O\x00InGame: CIV5_AGENT_VICTORY|science|true|1|2|1|0|1",
            ),
            TunerMessage(3, ""),
        )

        state = parse_snapshot(messages)

        self.assertEqual(state.schema_version, 4)
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
        self.assertTrue(state.units[0]["ready_to_move"])
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

    def test_parses_legacy_schema_three_unit_without_readiness(self):
        state = parse_snapshot(
            (
                TunerMessage(
                    -1,
                    "CIV5_AGENT_SNAPSHOT|3|2|0|7|4|5|9|0|1|33|0|Test|Test|"
                    "-1||-1|-1|true|true|-1",
                ),
                TunerMessage(
                    -1,
                    "CIV5_AGENT_UNIT|8|Warrior|UNIT_WARRIOR|9|12|120|0|100|8|0|0",
                ),
                TunerMessage(
                    -1,
                    "CIV5_AGENT_VICTORY|science|true|0|0|0|0|0",
                ),
            )
        )
        self.assertEqual(state.schema_version, 3)
        self.assertNotIn("ready_to_move", state.units[0])

    def test_parses_schema_five_technology_state_in_stable_order(self):
        header = (
            "CIV5_AGENT_SNAPSHOT|5|2|0|7|4|5|9|0|1|33|0|Test|Test|"
            "-1||-1|-1|true|false|8"
        )
        messages = [TunerMessage(-1, header)]
        for part in ("cities", "units", "diplomacy", "victory"):
            payload = f"CIV5_AGENT_PART|{part}|2|0"
            if part == "victory":
                payload += "\nCIV5_AGENT_VICTORY|science|true|0|0|0|0|0"
            messages.append(TunerMessage(-1, payload))
        messages.append(
            TunerMessage(
                -1,
                "CIV5_AGENT_PART|technologies|2|0\n"
                "CIV5_AGENT_RESEARCH_CHOICE|true|normal\n"
                "CIV5_AGENT_TECHNOLOGY|researched|TECH_POTTERY\n"
                "CIV5_AGENT_TECHNOLOGY|researched|TECH_AGRICULTURE\n"
                "CIV5_AGENT_TECHNOLOGY|researchable|TECH_WRITING\n"
                "CIV5_AGENT_TECHNOLOGY|researchable|TECH_CALENDAR",
            )
        )

        state = parse_snapshot(tuple(messages))

        self.assertEqual(
            state.researched_technologies,
            ["TECH_AGRICULTURE", "TECH_POTTERY"],
        )
        self.assertEqual(
            state.researchable_technologies,
            ["TECH_CALENDAR", "TECH_WRITING"],
        )
        self.assertEqual(
            state.research_choice,
            {"required": True, "mode": "normal"},
        )

    def test_rejects_duplicate_or_malformed_technology_records(self):
        header = (
            "CIV5_AGENT_SNAPSHOT|5|2|0|7|4|5|9|0|1|33|0|Test|Test|"
            "-1||-1|-1|true|false|8"
        )
        duplicate = (
            TunerMessage(-1, header),
            TunerMessage(-1, "CIV5_AGENT_TECHNOLOGY|researched|TECH_POTTERY"),
            TunerMessage(-1, "CIV5_AGENT_TECHNOLOGY|researched|TECH_POTTERY"),
        )
        with self.assertRaisesRegex(ValueError, "duplicate researched technology"):
            parse_snapshot(duplicate)
        with self.assertRaisesRegex(ValueError, "malformed technology record"):
            parse_snapshot(
                (
                    TunerMessage(-1, header),
                    TunerMessage(-1, "CIV5_AGENT_TECHNOLOGY|researched|POTTERY"),
                )
            )

    def test_parses_schema_six_sorted_ordinary_move_targets(self):
        header = (
            "CIV5_AGENT_SNAPSHOT|6|2|0|7|4|5|9|0|1|33|0|Test|Test|"
            "1|TECH_POTTERY|6|35|true|false|8"
        )
        messages = [TunerMessage(-1, header)]
        for part in ("cities", "units", "diplomacy", "victory", "technologies"):
            payload = f"CIV5_AGENT_PART|{part}|2|0"
            if part == "units":
                payload += (
                    "\nCIV5_AGENT_UNIT|8|Warrior|UNIT_WARRIOR|"
                    "9|12|120|0|100|8|0|0|true"
                )
            elif part == "victory":
                payload += "\nCIV5_AGENT_VICTORY|science|true|0|0|0|0|0"
            elif part == "technologies":
                payload += (
                    "\nCIV5_AGENT_RESEARCH_CHOICE|false|normal"
                    "\nCIV5_AGENT_TECHNOLOGY|researched|TECH_AGRICULTURE"
                    "\nCIV5_AGENT_TECHNOLOGY|researchable|TECH_WRITING"
                )
            messages.append(TunerMessage(-1, payload))
        messages.append(
            TunerMessage(
                -1,
                "CIV5_AGENT_PART|move_targets|2|0\n"
                "CIV5_AGENT_MOVE_TARGET|8|10|12\n"
                "CIV5_AGENT_MOVE_TARGET|8|8|12",
            )
        )

        state = parse_snapshot(tuple(messages))

        self.assertEqual(state.schema_version, 6)
        self.assertEqual(
            state.units[0]["ordinary_move_targets"],
            [{"x": 8, "y": 12}, {"x": 10, "y": 12}],
        )

    def test_rejects_invalid_schema_six_move_target_records(self):
        header = (
            "CIV5_AGENT_SNAPSHOT|6|2|0|7|4|5|9|0|1|33|0|Test|Test|"
            "1|TECH_POTTERY|6|35|true|false|8"
        )
        invalid_records = (
            "CIV5_AGENT_MOVE_TARGET|8|1",
            "CIV5_AGENT_MOVE_TARGET|8|-1|2",
            "CIV5_AGENT_MOVE_TARGET|8|65536|2",
        )
        for record in invalid_records:
            with self.subTest(record=record), self.assertRaises(ValueError):
                parse_snapshot((TunerMessage(-1, header), TunerMessage(-1, record)))

        duplicate = "CIV5_AGENT_MOVE_TARGET|8|1|2"
        with self.assertRaisesRegex(ValueError, "duplicate move target"):
            parse_snapshot(
                (
                    TunerMessage(-1, header),
                    TunerMessage(-1, duplicate),
                    TunerMessage(-1, duplicate),
                )
            )

    def test_rejects_schema_six_target_for_unknown_unit(self):
        header = (
            "CIV5_AGENT_SNAPSHOT|6|2|0|7|4|5|9|0|1|33|0|Test|Test|"
            "1|TECH_POTTERY|6|35|true|false|8"
        )
        parts = [
            TunerMessage(-1, f"CIV5_AGENT_PART|{part}|2|0")
            for part in ("cities", "units", "diplomacy")
        ]
        parts.extend(
            (
                TunerMessage(
                    -1,
                    "CIV5_AGENT_PART|victory|2|0\n"
                    "CIV5_AGENT_VICTORY|science|true|0|0|0|0|0",
                ),
                TunerMessage(
                    -1,
                    "CIV5_AGENT_PART|technologies|2|0\n"
                    "CIV5_AGENT_RESEARCH_CHOICE|false|normal",
                ),
                TunerMessage(
                    -1,
                    "CIV5_AGENT_PART|move_targets|2|0\n"
                    "CIV5_AGENT_MOVE_TARGET|99|1|2",
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "unknown unit"):
            parse_snapshot((TunerMessage(-1, header), *parts))

    def test_schema_six_requires_move_targets_part(self):
        header = (
            "CIV5_AGENT_SNAPSHOT|6|2|0|7|4|5|9|0|1|33|0|Test|Test|"
            "1|TECH_POTTERY|6|35|true|false|8"
        )
        parts = [
            TunerMessage(-1, f"CIV5_AGENT_PART|{part}|2|0")
            for part in ("cities", "units", "diplomacy")
        ]
        parts.extend(
            (
                TunerMessage(
                    -1,
                    "CIV5_AGENT_PART|victory|2|0\n"
                    "CIV5_AGENT_VICTORY|science|true|0|0|0|0|0",
                ),
                TunerMessage(
                    -1,
                    "CIV5_AGENT_PART|technologies|2|0\n"
                    "CIV5_AGENT_RESEARCH_CHOICE|false|normal",
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "incomplete.*move_targets"):
            parse_snapshot((TunerMessage(-1, header), *parts))

    def test_rejects_records_before_header_and_duplicate_headers(self):
        with self.assertRaisesRegex(ValueError, "before snapshot header"):
            parse_snapshot(
                (TunerMessage(-1, "CIV5_AGENT_UNIT|8|W|UNIT_W|1|2|0"),)
            )
        header = (
            "CIV5_AGENT_SNAPSHOT|4|2|0|7|4|5|9|0|1|33|0|Isabella|Spain|"
            "-1||-1|-1|true|true|-1"
        )
        with self.assertRaisesRegex(ValueError, "multiple snapshot headers"):
            parse_snapshot((TunerMessage(-1, header), TunerMessage(-1, header)))
        parts = tuple(
            TunerMessage(-1, f"CIV5_AGENT_PART|{part}|2|0")
            for part in ("cities", "units", "diplomacy", "victory")
        )
        victory = "CIV5_AGENT_VICTORY|science|true|0|0|0|0|0"
        with self.assertRaisesRegex(ValueError, "multiple victory records"):
            parse_snapshot(
                (
                    TunerMessage(-1, header),
                    *parts,
                    TunerMessage(-1, victory),
                    TunerMessage(-1, victory),
                )
            )

    def test_rejects_split_snapshot_from_different_turn(self):
        header = (
            "CIV5_AGENT_SNAPSHOT|4|2|0|7|4|5|9|0|1|33|0|Isabella|Spain|"
            "-1||-1|-1|true|true|-1"
        )
        with self.assertRaisesRegex(ValueError, "does not match header turn/player"):
            parse_snapshot(
                (
                    TunerMessage(-1, header),
                    TunerMessage(-1, "CIV5_AGENT_PART|cities|3|0"),
                )
            )

    def test_parses_end_turn_precondition_result(self):
        self.assertEqual(
            parse_end_turn_response(
                (TunerMessage(-1, "InGame: CIV5_AGENT_COMMAND|end_turn|blocked|8"),)
            ),
            (False, 8),
        )

    def test_parses_move_unit_submission_result(self):
        self.assertEqual(
            parse_move_unit_response(
                (
                    TunerMessage(
                        -1,
                        "InGame: CIV5_AGENT_COMMAND|move_unit|accepted|8|10|12",
                    ),
                )
            ),
            ("accepted", 8, 10, 12),
        )
        with self.assertRaisesRegex(ValueError, "did not return"):
            parse_move_unit_response((TunerMessage(-1, "Lua error"),))

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

    def test_snapshot_programs_fit_verified_firetuner_command_limit(self):
        programs = snapshot_lua_programs()
        self.assertEqual(len(programs), 7)
        self.assertTrue(all(len(program.encode("utf-8")) < 900 for program in programs))

    def test_read_game_state_collects_every_snapshot_program(self):
        header = TunerMessage(
            -1,
            "CIV5_AGENT_SNAPSHOT|6|2|0|7|4|5|9|0|1|33|0|Test|Test|"
            "-1||-1|-1|true|true|-1",
        )
        part_names = (
            "cities",
            "units",
            "diplomacy",
            "victory",
            "technologies",
            "move_targets",
        )
        part_messages = [
            TunerMessage(-1, f"CIV5_AGENT_PART|{name}|2|0")
            for name in part_names
        ]
        part_messages[3] = TunerMessage(
            -1,
            "CIV5_AGENT_PART|victory|2|0\n"
            "CIV5_AGENT_VICTORY|science|true|0|0|0|0|0",
        )
        part_messages[4] = TunerMessage(
            -1,
            "CIV5_AGENT_PART|technologies|2|0\n"
            "CIV5_AGENT_RESEARCH_CHOICE|false|normal",
        )
        client = FireTunerClient()
        with patch.object(
            client,
            "execute_collect",
            side_effect=[(header,), *((message,) for message in part_messages)],
        ) as execute:
            state = client.read_game_state(172)

        self.assertEqual(state.turn, 2)
        self.assertEqual(execute.call_count, 7)
        self.assertEqual(
            [call.args for call in execute.call_args_list],
            [(172, program) for program in snapshot_lua_programs()],
        )

    def test_snapshot_lua_only_emits_met_major_civilizations(self):
        lua = snapshot_lua()
        self.assertIn("GameDefines.MAX_MAJOR_CIVS", lua)
        self.assertIn("myTeam:IsHasMet(o:GetTeam())", lua)
        self.assertIn("myTeam:IsAtWar(o:GetTeam())", lua)

    def test_snapshot_lua_reads_active_team_science_victory_projects(self):
        lua = snapshot_lua()
        self.assertIn('GameInfo.Victories["VICTORY_SPACE_RACE"]', lua)

    def test_snapshot_lua_reads_technology_facts_from_game_capabilities(self):
        lua = snapshot_lua()
        self.assertIn("team:IsHasTech(tech.ID)", lua)
        self.assertIn("p:CanResearch(tech.ID)", lua)
        self.assertIn("p:CanResearchForFree(tech.ID)", lua)
        self.assertIn("p:GetCurrentResearch()", lua)
        self.assertIn("ENDTURN_BLOCKING_FREE_TECH", lua)
        self.assertIn("ENDTURN_BLOCKING_STEAL_TECH", lua)
        self.assertIn('projectCount("PROJECT_APOLLO_PROGRAM")', lua)
        self.assertIn('projectCount("PROJECT_SS_ENGINE")', lua)

    def test_snapshot_lua_emits_only_conservative_ordinary_move_targets(self):
        lua = snapshot_lua_programs()[-1]
        for required in (
            "u:IsReadyToMove()",
            "u:MovesLeft()>0",
            "not u:IsBusy()",
            "not u:IsAutomated()",
            "not u:IsDelayedDeath()",
            "u:GetDomainType()~=DomainTypes.DOMAIN_AIR",
            "not u:IsEmbarked()",
            "q:IsVisible(team,false)",
            "not q:IsCity()",
            "q:GetNumUnits()==0",
            "s:IsWater()==q:IsWater()",
            "u:CanMoveThrough(q)",
        ):
            self.assertIn(required, lua)
        self.assertNotIn("CanMoveOrAttackInto", lua)
        self.assertNotIn("PushMission", lua)
        self.assertNotIn("SelectionListMove", lua)

    def test_end_turn_is_narrow_and_preconditioned(self):
        lua = end_turn_lua()
        self.assertIn("UI.CanEndTurn()", lua)
        self.assertIn("Game.IsProcessingMessages()", lua)
        self.assertIn("b==EndTurnBlockingTypes.NO_ENDTURN_BLOCKING_TYPE", lua)
        self.assertIn("Network.HasSentNetTurnComplete()", lua)
        self.assertEqual(lua.count("Game.DoControl"), 1)
        self.assertLessEqual(len(lua.encode("utf-8")), MAX_LUA_PROGRAM_BYTES)

    def test_all_generated_lua_programs_fit_firetuner_limit(self):
        programs = (
            *snapshot_lua_programs(),
            end_turn_lua(),
            choose_research_lua("TECH_" + "X" * 128),
            city_production_lua(
                2_147_483_647,
                "building",
                "BUILDING_" + "X" * 128,
            ),
            skip_unit_lua(2_147_483_647),
            move_unit_lua(2_147_483_647, 65_535, 65_535, 65_535, 65_535),
        )
        self.assertTrue(programs)
        for program in programs:
            with self.subTest(size=len(program.encode("utf-8"))):
                self.assertLessEqual(
                    len(program.encode("utf-8")),
                    MAX_LUA_PROGRAM_BYTES,
                )

    def test_firetuner_rejects_oversized_lua_before_send(self):
        client = FireTunerClient()
        with self.assertRaisesRegex(ValueError, "exceeds"):
            client.execute_collect(172, "x" * (MAX_LUA_PROGRAM_BYTES + 1))

    def test_choose_research_rejects_lua_injection(self):
        with self.assertRaisesRegex(ValueError, "must match"):
            choose_research_lua('TECH_POTTERY; Game.DoControl(1)')

    def test_move_unit_repeats_guards_and_uses_stock_selected_path_once(self):
        lua = move_unit_lua(8, 9, 12, 10, 12)
        for required in (
            "p:GetUnitByID(8)",
            "Map.GetPlot(10,12)",
            "u:GetX()~=9",
            "u:GetY()~=12",
            "Map.PlotDistance(9,12,10,12)~=1",
            "u:IsReadyToMove()",
            "u:MovesLeft()<=0",
            "u:IsBusy()",
            "u:IsAutomated()",
            "u:IsDelayedDeath()",
            "DomainTypes.DOMAIN_AIR",
            "u:IsEmbarked()",
            "q:IsVisible(t,false)",
            "q:IsCity()",
            "q:GetNumUnits()~=0",
            "s:IsWater()~=q:IsWater()",
            "u:CanMoveThrough(q)",
            "UI.ClearSelectionList()",
            "UI.SelectUnit(u)",
            "UI.GetHeadSelectedUnit()",
        ):
            self.assertIn(required, lua)
        self.assertEqual(lua.count("Game.SelectionListMove"), 1)
        self.assertNotIn("PushMission", lua)
        self.assertLessEqual(len(lua.encode("utf-8")), MAX_LUA_PROGRAM_BYTES)

    def test_move_unit_rejects_invalid_numeric_inputs(self):
        for arguments in (
            (True, 1, 1, 2, 2),
            (8, -1, 1, 2, 2),
            (8, 1, 1, 65_536, 2),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                move_unit_lua(*arguments)

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
