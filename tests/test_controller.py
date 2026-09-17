import copy
import unittest

from civ5_agent.controller import Decision, decide
from civ5_agent.models import GameState
from civ5_agent.validation import StateValidationError, validate_live_state


def ready_state(**changes):
    values = {
        "schema_version": 2,
        "turn": 4,
        "active_player": 0,
        "gold": 12,
        "turn_active": True,
        "can_end_turn": True,
        "end_turn_blocking_type": -1,
        "research": {"id": 1, "type": "TECH_POTTERY", "progress": 8, "cost": 40},
        "cities": [
            {"id": 4, "name": "Madrid", "x": 10, "y": 11, "population": 2, "production": "SCOUT"}
        ],
        "units": [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 0,
            }
        ],
    }
    values.update(changes)
    return GameState(**values)


def schema_five_state(**changes):
    state = ready_state(
        schema_version=5,
        score=10,
        current_era=0,
        researched_technologies=["TECH_AGRICULTURE"],
        researchable_technologies=["TECH_POTTERY"],
        research_choice={"required": False, "mode": "normal"},
    )
    state.cities[0].update(
        {
            "food_times100": 0,
            "growth_threshold": 15,
            "food_per_turn_times100": 300,
            "production_times100": 0,
            "production_needed": 40,
            "production_per_turn_times100": 500,
        }
    )
    state.units[0].update(
        {
            "damage": 0,
            "max_hit_points": 100,
            "combat_strength": 8,
            "ranged_strength": 0,
            "range": 0,
            "ready_to_move": False,
        }
    )
    state.victory = {
        "science_enabled": True,
        "apollo": 0,
        "booster": 0,
        "cockpit": 0,
        "stasis_chamber": 0,
        "engine": 0,
    }
    for key, value in changes.items():
        setattr(state, key, value)
    return state


def schema_six_state(**changes):
    state = schema_five_state(schema_version=6)
    state.units[0]["ordinary_move_targets"] = [
        {"x": 8, "y": 12},
        {"x": 10, "y": 12},
    ]
    for key, value in changes.items():
        setattr(state, key, value)
    return state


def schema_seven_state(**changes):
    state = schema_six_state(schema_version=7)
    state.units[0].update(
        {
            "current_plot": {
                "terrain_type": "TERRAIN_GRASS",
                "feature_type": None,
                "resource_type": None,
                "improvement_type": None,
                "route_type": "ROUTE_ROAD",
                "owner_id": 0,
                "is_hills": False,
                "is_water": False,
                "is_fresh_water": True,
            },
            "current_build_type": None,
            "ordinary_build_actions": [
                {
                    "build_type": "BUILD_FARM",
                    "improvement_type": "IMPROVEMENT_FARM",
                },
                {
                    "build_type": "BUILD_TRADING_POST",
                    "improvement_type": "IMPROVEMENT_TRADING_POST",
                },
            ],
        }
    )
    for key, value in changes.items():
        setattr(state, key, value)
    return state


class StateValidationTest(unittest.TestCase):
    def test_accepts_consistent_live_state(self):
        state = ready_state()
        self.assertIs(validate_live_state(state), state)

    def test_rejects_duplicate_unit_ids(self):
        unit = {
            "id": 8,
            "name": "Warrior",
            "type": "UNIT_WARRIOR",
            "x": 9,
            "y": 12,
            "moves": 0,
        }
        with self.assertRaisesRegex(StateValidationError, "duplicate unit id"):
            validate_live_state(ready_state(units=[unit, dict(unit)]))

    def test_rejects_boolean_disguised_as_integer(self):
        with self.assertRaisesRegex(StateValidationError, "turn must be an integer"):
            validate_live_state(ready_state(turn=True))

    def test_rejects_malformed_record_instead_of_attribute_error(self):
        with self.assertRaisesRegex(StateValidationError, "unit record must be an object"):
            validate_live_state(ready_state(units=["not-a-unit"]))

    def test_rejects_invalid_optional_economy_type(self):
        with self.assertRaisesRegex(StateValidationError, "gold_per_turn"):
            validate_live_state(ready_state(gold_per_turn="3"))

    def test_validates_diplomacy_records(self):
        relation = {
            "player_id": 1,
            "team_id": 1,
            "name": "Harun al-Rashid",
            "civilization": "Arabia",
            "score": 24,
            "at_war": False,
            "approach": 4,
        }
        state = ready_state(diplomacy=[relation])
        self.assertIs(validate_live_state(state), state)
        with self.assertRaisesRegex(StateValidationError, "invalid at_war"):
            validate_live_state(
                ready_state(diplomacy=[{**relation, "at_war": "false"}])
            )

    def test_schema_three_requires_score_and_era(self):
        with self.assertRaisesRegex(StateValidationError, "score and current_era"):
            validate_live_state(ready_state(schema_version=3))
        city = dict(ready_state().cities[0])
        city.update(
            {
                "food_times100": 525,
                "growth_threshold": 24,
                "food_per_turn_times100": 300,
                "production_times100": 800,
                "production_needed": 40,
                "production_per_turn_times100": 500,
            }
        )
        unit = dict(ready_state().units[0])
        unit.update(
            {
                "damage": 15,
                "max_hit_points": 100,
                "combat_strength": 8,
                "ranged_strength": 0,
                "range": 1,
                "ready_to_move": False,
            }
        )
        state = ready_state(
            schema_version=3,
            score=33,
            current_era=0,
            cities=[city],
            units=[unit],
            victory={
                "science_enabled": True,
                "apollo": 0,
                "booster": 0,
                "cockpit": 0,
                "stasis_chamber": 0,
                "engine": 0,
            },
        )
        self.assertIs(validate_live_state(state), state)
        state.victory["science_enabled"] = "true"
        with self.assertRaisesRegex(StateValidationError, "science_enabled"):
            validate_live_state(state)

    def test_schema_three_requires_city_economy_fields(self):
        with self.assertRaisesRegex(StateValidationError, "food_times100"):
            validate_live_state(
                ready_state(schema_version=3, score=33, current_era=0)
            )

    def test_schema_three_rejects_impossible_unit_damage(self):
        state = ready_state()
        state.schema_version = 4
        state.score = 33
        state.current_era = 0
        state.cities[0].update(
            {
                "food_times100": 525,
                "growth_threshold": 24,
                "food_per_turn_times100": 300,
                "production_times100": 800,
                "production_needed": 40,
                "production_per_turn_times100": 500,
            }
        )
        state.units[0].update(
            {
                "damage": 101,
                "max_hit_points": 100,
                "combat_strength": 8,
                "ranged_strength": 0,
                "range": 1,
                "ready_to_move": False,
            }
        )
        with self.assertRaisesRegex(StateValidationError, "damage exceeds"):
            validate_live_state(state)

    def test_schema_four_requires_unit_readiness(self):
        state = ready_state()
        state.schema_version = 4
        state.score = 33
        state.current_era = 0
        state.cities[0].update(
            {
                "food_times100": 525,
                "growth_threshold": 24,
                "food_per_turn_times100": 300,
                "production_times100": 800,
                "production_needed": 40,
                "production_per_turn_times100": 500,
            }
        )
        state.units[0].update(
            {
                "damage": 0,
                "max_hit_points": 100,
                "combat_strength": 8,
                "ranged_strength": 0,
                "range": 1,
            }
        )
        state.victory = {
            "science_enabled": True,
            "apollo": 0,
            "booster": 0,
            "cockpit": 0,
            "stasis_chamber": 0,
            "engine": 0,
        }

        with self.assertRaisesRegex(StateValidationError, "ready_to_move"):
            validate_live_state(state)

    def test_schema_five_validates_technology_sets_and_choice(self):
        state = schema_five_state()
        self.assertIs(validate_live_state(state), state)
        state.researchable_technologies = ["TECH_POTTERY", "TECH_AGRICULTURE"]
        with self.assertRaisesRegex(StateValidationError, "stable sorted order"):
            validate_live_state(state)

    def test_schema_five_rejects_overlap_and_invalid_choice(self):
        with self.assertRaisesRegex(StateValidationError, "both researched"):
            validate_live_state(
                schema_five_state(
                    researchable_technologies=["TECH_AGRICULTURE"]
                )
            )
        with self.assertRaisesRegex(StateValidationError, "must use normal mode"):
            validate_live_state(
                schema_five_state(
                    research_choice={
                        "required": False,
                        "mode": "free_technology",
                    }
                )
            )
        with self.assertRaisesRegex(
            StateValidationError, "ordinary research availability"
        ):
            validate_live_state(
                schema_five_state(
                    research=None,
                    research_choice={"required": False, "mode": "normal"},
                )
            )
        with self.assertRaisesRegex(
            StateValidationError, "ordinary research availability"
        ):
            validate_live_state(
                schema_five_state(
                    research_choice={"required": True, "mode": "normal"},
                )
            )
        self.assertIsInstance(
            validate_live_state(
                schema_five_state(
                    research=None,
                    researchable_technologies=[],
                    research_choice={"required": False, "mode": "normal"},
                )
            ),
            GameState,
        )

    def test_schema_six_validates_bounded_sorted_move_targets(self):
        state = schema_six_state()
        self.assertIs(validate_live_state(state), state)

        invalid_targets = (
            None,
            [{"x": 10, "y": 12}, {"x": 8, "y": 12}],
            [{"x": 8, "y": 12}, {"x": 8, "y": 12}],
            [{"x": -1, "y": 12}],
            [{"x": 65_536, "y": 12}],
            [{"x": 8, "y": 12, "score": 1}],
            [{"x": value, "y": 12} for value in range(7)],
        )
        for targets in invalid_targets:
            with self.subTest(targets=targets):
                candidate = schema_six_state()
                if targets is None:
                    candidate.units[0].pop("ordinary_move_targets")
                else:
                    candidate.units[0]["ordinary_move_targets"] = targets
                with self.assertRaises(StateValidationError):
                    validate_live_state(candidate)

    def test_schema_seven_validates_current_plot_and_current_build(self):
        state = schema_seven_state()
        self.assertIs(validate_live_state(state), state)

        invalid_changes = (
            ("terrain_type", "GRASS"),
            ("feature_type", "FEATURE_"),
            ("resource_type", "RESOURCE_" + "X" * 65),
            ("improvement_type", 4),
            ("route_type", "BUILD_ROAD"),
            ("owner_id", True),
            ("owner_id", -1),
            ("is_hills", 0),
            ("is_water", "false"),
            ("is_fresh_water", None),
        )
        for field, value in invalid_changes:
            with self.subTest(field=field, value=value):
                candidate = copy.deepcopy(schema_seven_state())
                candidate.units[0]["current_plot"][field] = value
                with self.assertRaises(StateValidationError):
                    validate_live_state(candidate)

        for current_build in ("BUILD_", "IMPROVEMENT_FARM", 3, "BUILD_" + "X" * 65):
            with self.subTest(current_build=current_build):
                candidate = copy.deepcopy(schema_seven_state())
                candidate.units[0]["current_build_type"] = current_build
                with self.assertRaises(StateValidationError):
                    validate_live_state(candidate)

        missing = copy.deepcopy(schema_seven_state())
        missing.units[0]["current_plot"].pop("route_type")
        with self.assertRaisesRegex(StateValidationError, "malformed current_plot"):
            validate_live_state(missing)

        extra = copy.deepcopy(schema_seven_state())
        extra.units[0]["current_plot"]["score"] = 1
        with self.assertRaisesRegex(StateValidationError, "malformed current_plot"):
            validate_live_state(extra)

    def test_schema_seven_validates_bounded_sorted_worker_actions(self):
        invalid_actions = (
            None,
            [
                {
                    "build_type": "BUILD_TRADING_POST",
                    "improvement_type": "IMPROVEMENT_TRADING_POST",
                },
                {
                    "build_type": "BUILD_FARM",
                    "improvement_type": "IMPROVEMENT_FARM",
                },
            ],
            [
                {
                    "build_type": "BUILD_FARM",
                    "improvement_type": "IMPROVEMENT_FARM",
                },
                {
                    "build_type": "BUILD_FARM",
                    "improvement_type": "IMPROVEMENT_TRADING_POST",
                },
            ],
            [{"build_type": "BUILD_FARM"}],
            [
                {
                    "build_type": "IMPROVEMENT_FARM",
                    "improvement_type": "IMPROVEMENT_FARM",
                }
            ],
            [
                {
                    "build_type": f"BUILD_{index:02d}",
                    "improvement_type": f"IMPROVEMENT_{index:02d}",
                }
                for index in range(33)
            ],
        )
        for actions in invalid_actions:
            with self.subTest(actions=actions):
                candidate = copy.deepcopy(schema_seven_state())
                if actions is None:
                    candidate.units[0].pop("ordinary_build_actions")
                else:
                    candidate.units[0]["ordinary_build_actions"] = actions
                with self.assertRaises(StateValidationError):
                    validate_live_state(candidate)


class DeterministicPolicyTest(unittest.TestCase):
    def test_requests_research_before_turn_end(self):
        self.assertEqual(
            decide(ready_state(research=None)),
            Decision("manual_required", "choose research"),
        )

    def test_schema_five_rejects_masked_ordinary_research_choice(self):
        with self.assertRaisesRegex(
            StateValidationError, "ordinary research availability"
        ):
            decide(
                schema_five_state(
                    research=None,
                    research_choice={"required": False, "mode": "normal"},
                )
            )
        self.assertEqual(
            decide(
                schema_five_state(
                    research=None,
                    research_choice={"required": True, "mode": "normal"}
                )
            ).reason,
            "choose research",
        )

    def test_schema_five_special_research_choices_fail_closed(self):
        self.assertEqual(
            decide(
                schema_five_state(
                    research_choice={
                        "required": True,
                        "mode": "free_technology",
                    }
                )
            ).reason,
            "choose free technology",
        )
        self.assertEqual(
            decide(
                schema_five_state(
                    research_choice={"required": True, "mode": "unsupported"}
                )
            ).reason,
            "unsupported research choice",
        )

    def test_requests_production_before_unit_orders(self):
        state = ready_state()
        state.cities[0]["production"] = ""
        self.assertEqual(decide(state).reason, "choose city production")

    def test_requests_unit_orders(self):
        state = ready_state()
        state.units[0]["moves"] = 120
        self.assertEqual(decide(state).reason, "issue unit orders")

    def test_schema_three_uses_ready_state_not_remaining_movement(self):
        state = ready_state()
        state.schema_version = 4
        state.score = 10
        state.current_era = 0
        state.cities[0].update(
            {
                "food_times100": 0,
                "growth_threshold": 15,
                "food_per_turn_times100": 300,
                "production_times100": 0,
                "production_needed": 40,
                "production_per_turn_times100": 500,
            }
        )
        state.units[0].update(
            {
                "moves": 120,
                "damage": 0,
                "max_hit_points": 100,
                "combat_strength": 8,
                "ranged_strength": 0,
                "range": 0,
                "ready_to_move": False,
            }
        )
        state.victory = {
            "science_enabled": True,
            "apollo": 0,
            "booster": 0,
            "cockpit": 0,
            "stasis_chamber": 0,
            "engine": 0,
        }
        self.assertEqual(decide(state).action, "end_turn")

    def test_ends_turn_only_when_observed_state_is_ready(self):
        self.assertEqual(decide(ready_state()).action, "end_turn")


if __name__ == "__main__":
    unittest.main()
