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
