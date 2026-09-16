import unittest

from civ5_agent.models import GameState
from civ5_agent.turn_requirements import inspect_turn_requirements


def schema_five_state(**changes):
    values = {
        "schema_version": 5,
        "turn": 4,
        "active_player": 0,
        "gold": 12,
        "score": 10,
        "current_era": 0,
        "turn_active": True,
        "can_end_turn": True,
        "end_turn_blocking_type": 0,
        "research": {"id": 1, "type": "TECH_POTTERY", "progress": 8, "cost": 40},
        "researched_technologies": ["TECH_AGRICULTURE"],
        "researchable_technologies": ["TECH_MINING", "TECH_POTTERY"],
        "research_choice": {"required": False, "mode": "normal"},
        "cities": [
            {
                "id": 4,
                "name": "City",
                "x": 10,
                "y": 11,
                "population": 2,
                "production": "SCOUT",
                "food_times100": 0,
                "growth_threshold": 15,
                "food_per_turn_times100": 300,
                "production_times100": 0,
                "production_needed": 40,
                "production_per_turn_times100": 500,
            }
        ],
        "units": [
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 60,
                "damage": 0,
                "max_hit_points": 100,
                "combat_strength": 8,
                "ranged_strength": 0,
                "range": 0,
                "ready_to_move": False,
            }
        ],
        "victory": {
            "science_enabled": True,
            "apollo": 0,
            "booster": 0,
            "cockpit": 0,
            "stasis_chamber": 0,
            "engine": 0,
        },
    }
    values.update(changes)
    return GameState(**values)


class TurnRequirementTest(unittest.TestCase):
    def test_reports_nothing_when_turn_is_ready(self):
        self.assertEqual(inspect_turn_requirements(schema_five_state()), ())

    def test_inactive_turn_short_circuits_other_requirements(self):
        state = schema_five_state(
            turn_active=False,
            can_end_turn=False,
            research=None,
            research_choice={"required": True, "mode": "normal"},
        )
        requirements = inspect_turn_requirements(state)
        self.assertEqual([item.kind for item in requirements], ["turn_inactive"])

    def test_reports_ordered_facts_without_selecting_actions(self):
        state = schema_five_state(
            research=None,
            research_choice={"required": True, "mode": "normal"},
            can_end_turn=False,
            end_turn_blocking_type=1,
        )
        city = dict(state.cities[0])
        city["production"] = ""
        city_two = {**city, "id": 2, "name": "Second"}
        state.cities = [city, city_two]
        unit = dict(state.units[0])
        unit["ready_to_move"] = True
        unit_two = {**unit, "id": 3, "name": "Scout"}
        state.units = [unit, unit_two]

        requirements = inspect_turn_requirements(state)

        self.assertEqual(
            [item.kind for item in requirements],
            [
                "research_choice",
                "city_production",
                "city_production",
                "unit_orders",
                "unit_orders",
                "end_turn_blocked",
            ],
        )
        self.assertEqual(requirements[0].candidates, ("TECH_MINING", "TECH_POTTERY"))
        self.assertEqual(
            [item.subject_id for item in requirements[1:5]],
            [2, 4, 3, 8],
        )
        self.assertEqual(requirements[-1].blocking_type, 1)

    def test_special_research_mode_does_not_reuse_ordinary_candidates(self):
        state = schema_five_state(
            research=None,
            research_choice={"required": True, "mode": "free_technology"},
        )
        requirement = inspect_turn_requirements(state)[0]
        self.assertEqual(requirement.mode, "free_technology")
        self.assertEqual(requirement.candidates, ())


if __name__ == "__main__":
    unittest.main()
