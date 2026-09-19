import copy
import json
import unittest

from civ5_agent.models import GameState, game_state_to_dict
from civ5_agent.turn_plan import live_state_digest
from civ5_agent.validation import StateValidationError, validate_live_state


PROVENANCE = {
    "cost": "CvPlayer.GetResearchCost",
    "progress_times100": "CvTeamTechs.GetResearchProgressTimes100",
    "science_per_turn_times100": "CvPlayer.GetScienceTimes100",
    "overflow_research": "CvPlayer.GetOverflowResearch",
    "turns_left_with_overflow": "CvPlayer.GetResearchTurnsLeft(include_overflow=true)",
    "phase": "CvPlayer.IsTurnActive+Game.IsProcessingMessages",
}


def available(value, source):
    return {"status": "available", "value": value, "source": source}


def schema_eight_state():
    candidate = {
        "type": "TECH_POTTERY",
        "cost": 35,
        "progress_times100": 600,
        "turns_left_with_overflow": 6,
    }
    return GameState(
        schema_version=8,
        turn=2,
        active_player=0,
        gold=7,
        gold_per_turn=4,
        science_per_turn=5,
        happiness=9,
        culture=0,
        culture_per_turn=1,
        score=33,
        current_era=0,
        player_name="Test",
        civilization="Test",
        turn_active=True,
        can_end_turn=False,
        end_turn_blocking_type=8,
        cities=[],
        units=[],
        diplomacy=[],
        victory={
            "science_enabled": True,
            "apollo": 0,
            "booster": 0,
            "cockpit": 0,
            "stasis_chamber": 0,
            "engine": 0,
        },
        research={"id": 1, "type": "TECH_POTTERY", "progress": 6, "cost": 35},
        researched_technologies=["TECH_AGRICULTURE"],
        researchable_technologies=["TECH_POTTERY"],
        research_choice={"required": False, "mode": "normal"},
        research_runtime_facts={
            "capability_version": 1,
            "status": "supported",
            "reason": None,
            "phase": "action_window_after_interturn_research_resolution",
            "science_per_turn_times100": 500,
            "overflow_research": 0,
            "current": candidate.copy(),
            "candidates": [candidate],
            "field_provenance": PROVENANCE.copy(),
        },
        runtime_context={
            "context_version": 1,
            "game_speed": available(
                "GAMESPEED_STANDARD", "PreGame.GetGameSpeed+GameInfo.GameSpeeds"
            ),
            "difficulty": available(
                "HANDICAP_PRINCE", "CvPlayer.GetHandicapType+GameInfo.HandicapInfos"
            ),
            "world_size": available(
                "WORLDSIZE_STANDARD", "Map.GetWorldSize+GameInfo.Worlds"
            ),
            "map_script": available("Assets/Maps/Continents.lua", "PreGame.GetMapScript"),
            "civilization": available(
                "CIVILIZATION_SPAIN",
                "CvPlayer.GetCivilizationType+GameInfo.Civilizations",
            ),
            "game_family": {"status": "unavailable", "value": None, "source": None},
            "game_build": {"status": "unavailable", "value": None, "source": None},
            "active_content": {"status": "unsupported", "value": None, "source": None},
            "ruleset_fingerprint": {
                "status": "unsupported",
                "value": None,
                "source": None,
            },
        },
    )


class ResearchRuntimeFactsValidationTest(unittest.TestCase):
    def test_accepts_supported_zero_and_positive_overflow(self):
        state = schema_eight_state()
        self.assertIs(validate_live_state(state), state)
        state.research_runtime_facts["overflow_research"] = 2
        self.assertIs(validate_live_state(state), state)

    def test_accepts_no_current_research_with_sorted_candidates(self):
        state = schema_eight_state()
        state.research = None
        state.research_choice = {"required": True, "mode": "normal"}
        state.research_runtime_facts["current"] = None
        self.assertIs(validate_live_state(state), state)

    def test_rejects_malformed_duplicate_or_mismatched_candidates(self):
        mutations = []
        duplicate = schema_eight_state()
        duplicate.research_runtime_facts["candidates"].append(
            duplicate.research_runtime_facts["candidates"][0].copy()
        )
        mutations.append(duplicate)
        wrong = schema_eight_state()
        wrong.research_runtime_facts["candidates"][0]["type"] = "TECH_WRITING"
        mutations.append(wrong)
        negative = schema_eight_state()
        negative.research_runtime_facts["candidates"][0]["progress_times100"] = -1
        mutations.append(negative)
        malformed = schema_eight_state()
        malformed.research_runtime_facts["candidates"][0]["extra"] = 1
        mutations.append(malformed)
        for state in mutations:
            with self.subTest(state=state), self.assertRaises(StateValidationError):
                validate_live_state(state)

    def test_accepts_fail_closed_unsupported_modes_and_unavailable_binding(self):
        for status, reason in (
            ("unsupported", "free_technology_mode"),
            ("unsupported", "technology_steal_mode"),
            ("unsupported", "outside_action_window"),
            ("unavailable", "runtime_api_binding_unavailable"),
        ):
            with self.subTest(reason=reason):
                state = schema_eight_state()
                state.research_runtime_facts.update(
                    {
                        "status": status,
                        "reason": reason,
                        "phase": "outside_action_window",
                        "science_per_turn_times100": None,
                        "overflow_research": None,
                        "current": None,
                        "candidates": [],
                    }
                )
                if reason == "free_technology_mode":
                    state.research_choice = {"required": True, "mode": "free_technology"}
                elif reason == "technology_steal_mode":
                    state.research_choice = {"required": True, "mode": "unsupported"}
                self.assertIs(validate_live_state(state), state)

    def test_rejects_partial_unsupported_runtime_facts(self):
        state = schema_eight_state()
        state.research_runtime_facts.update(
            {
                "status": "unsupported",
                "reason": "outside_action_window",
                "phase": "outside_action_window",
                "overflow_research": None,
                "current": None,
                "candidates": [],
            }
        )
        with self.assertRaisesRegex(StateValidationError, "partial facts"):
            validate_live_state(state)

    def test_rejects_claimed_fingerprint_and_unsafe_map_path(self):
        fingerprint = schema_eight_state()
        fingerprint.runtime_context["ruleset_fingerprint"] = available(
            "fake", "fixed string"
        )
        unsafe_path = schema_eight_state()
        unsafe_path.runtime_context["map_script"] = available(
            "/absolute/private.lua", "PreGame.GetMapScript"
        )
        for state in (fingerprint, unsafe_path):
            with self.assertRaises(StateValidationError):
                validate_live_state(state)

    def test_rejects_mutated_provenance_and_context_shape(self):
        provenance = schema_eight_state()
        provenance.research_runtime_facts["field_provenance"]["cost"] = "guessed"
        context = schema_eight_state()
        del context.runtime_context["game_build"]
        for state in (provenance, context):
            with self.assertRaises(StateValidationError):
                validate_live_state(state)

    def test_validation_does_not_require_a_knowledge_bundle(self):
        state = copy.deepcopy(schema_eight_state())
        self.assertIs(validate_live_state(state), state)

    def test_legacy_serialization_omits_schema_eight_fields(self):
        state = schema_eight_state()
        state.schema_version = 7
        value = game_state_to_dict(state)
        self.assertNotIn("research_runtime_facts", value)
        self.assertNotIn("research_forecast", value)
        self.assertNotIn("runtime_context", value)
        state.schema_version = 8
        value = game_state_to_dict(state)
        self.assertIn("research_runtime_facts", value)
        self.assertNotIn("research_forecast", value)
        self.assertIn("runtime_context", value)

    def test_schema_two_through_seven_canonical_bytes_and_digests_are_stable(self):
        expected_digests = {
            2: "4ff169e7d62c5b9f6c4124d702f555ec38b4d45abbb6600a47f9b7a6b6cbb57f",
            3: "f228df013d43a7f5df0df90291f546c9ffd483b6ce07894d9d5ebe4f11309eb4",
            4: "d02e5876b7f551abd4d93102b39cf453098934151a478088084844cef9a604f3",
            5: "974b1b1fad3ff54e76f92a7f8e7d5296398c78e4f0e42fb55efce34047003471",
            6: "76d7af9d9c4b12f5bf7f3cdbd889954901b30857ed2850f4d995e15e8e671502",
            7: "a0ad3a792de592774e03aa28d7916832d0c3f5c805495f961bcdc1baefb1df3d",
        }
        expected_template = (
            '{{"active_player":0,"can_end_turn":false,"cities":[],"civilization":"Test",'
            '"culture":0,"culture_per_turn":1,"current_era":0,"diplomacy":[],'
            '"end_turn_blocking_type":8,"gold":7,"gold_per_turn":4,"happiness":9,'
            '"player_name":"Test","research":{{"cost":35,"id":1,"progress":6,'
            '"type":"TECH_POTTERY"}},"research_choice":{{"mode":"normal",'
            '"required":false}},"researchable_technologies":["TECH_POTTERY"],'
            '"researched_technologies":["TECH_AGRICULTURE"],"schema_version":{},'
            '"science_per_turn":5,"score":33,"turn":2,"turn_active":true,"units":[],'
            '"victory":{{"apollo":0,"booster":0,"cockpit":0,"engine":0,'
            '"science_enabled":true,"stasis_chamber":0}}}}'
        )
        for version, expected_digest in expected_digests.items():
            with self.subTest(schema_version=version):
                state = schema_eight_state()
                state.schema_version = version
                encoded = json.dumps(
                    game_state_to_dict(state),
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
                self.assertEqual(encoded, expected_template.format(version).encode())
                self.assertEqual(live_state_digest(state), expected_digest)


if __name__ == "__main__":
    unittest.main()
