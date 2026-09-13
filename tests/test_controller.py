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
        "end_turn_blocking_type": 0,
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
        state.schema_version = 3
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
            }
        )
        with self.assertRaisesRegex(StateValidationError, "damage exceeds"):
            validate_live_state(state)


class DeterministicPolicyTest(unittest.TestCase):
    def test_requests_research_before_turn_end(self):
        self.assertEqual(
            decide(ready_state(research=None)),
            Decision("manual_required", "choose research"),
        )

    def test_requests_production_before_unit_orders(self):
        state = ready_state()
        state.cities[0]["production"] = ""
        self.assertEqual(decide(state).reason, "choose city production")

    def test_requests_unit_orders(self):
        state = ready_state()
        state.units[0]["moves"] = 120
        self.assertEqual(decide(state).reason, "issue unit orders")

    def test_ends_turn_only_when_observed_state_is_ready(self):
        self.assertEqual(decide(ready_state()).action, "end_turn")


if __name__ == "__main__":
    unittest.main()
