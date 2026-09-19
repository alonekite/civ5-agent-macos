import copy
import unittest

from civ5_agent.models import GameState, game_state_to_dict
from civ5_agent.validation import StateValidationError, validate_live_state


PROVENANCE = {
    "cost": "CvPlayer.GetResearchCost",
    "progress_times100": "CvPlayer.GetResearchProgressTimes100",
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
        research_forecast={
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


class ResearchForecastValidationTest(unittest.TestCase):
    def test_accepts_supported_zero_and_positive_overflow(self):
        state = schema_eight_state()
        self.assertIs(validate_live_state(state), state)
        state.research_forecast["overflow_research"] = 2
        self.assertIs(validate_live_state(state), state)

    def test_accepts_no_current_research_with_sorted_candidates(self):
        state = schema_eight_state()
        state.research = None
        state.research_choice = {"required": True, "mode": "normal"}
        state.research_forecast["current"] = None
        self.assertIs(validate_live_state(state), state)

    def test_rejects_malformed_duplicate_or_mismatched_candidates(self):
        mutations = []
        duplicate = schema_eight_state()
        duplicate.research_forecast["candidates"].append(
            duplicate.research_forecast["candidates"][0].copy()
        )
        mutations.append(duplicate)
        wrong = schema_eight_state()
        wrong.research_forecast["candidates"][0]["type"] = "TECH_WRITING"
        mutations.append(wrong)
        negative = schema_eight_state()
        negative.research_forecast["candidates"][0]["progress_times100"] = -1
        mutations.append(negative)
        malformed = schema_eight_state()
        malformed.research_forecast["candidates"][0]["extra"] = 1
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
                state.research_forecast.update(
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

    def test_rejects_partial_unsupported_forecast(self):
        state = schema_eight_state()
        state.research_forecast.update(
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
        provenance.research_forecast["field_provenance"]["cost"] = "guessed"
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
        self.assertNotIn("research_forecast", value)
        self.assertNotIn("runtime_context", value)
        state.schema_version = 8
        value = game_state_to_dict(state)
        self.assertIn("research_forecast", value)
        self.assertIn("runtime_context", value)


if __name__ == "__main__":
    unittest.main()
