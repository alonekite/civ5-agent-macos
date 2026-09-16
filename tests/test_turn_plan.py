import unittest
from dataclasses import replace

from civ5_agent.models import GameState
from civ5_agent.turn_plan import (
    ExecutionReport,
    ExecutionStepReport,
    MAX_PLAN_ACTIONS,
    PlannedAction,
    StaleTurnPlanError,
    TurnPlanError,
    live_state_digest,
    make_turn_plan,
    validate_turn_plan,
    validate_execution_report,
)

SESSION_ID = "123e4567-e89b-42d3-a456-426614174030"
PLAN_ID = "123e4567-e89b-42d3-a456-426614174031"
COMMAND_ONE = "123e4567-e89b-42d3-a456-426614174032"
COMMAND_TWO = "123e4567-e89b-42d3-a456-426614174033"


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
            {
                "id": 4,
                "name": "City",
                "x": 10,
                "y": 11,
                "population": 2,
                "production": "SCOUT",
            }
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


class TurnPlanTest(unittest.TestCase):
    def end_turn(self, command_id=COMMAND_TWO):
        return PlannedAction(command_id, "end_turn", {})

    def test_builds_and_validates_complete_turn_plan(self):
        state = ready_state()
        arguments = {"unit_id": 8}
        plan = make_turn_plan(
            state,
            SESSION_ID,
            (
                PlannedAction(COMMAND_ONE, "skip_unit", arguments),
                self.end_turn(),
            ),
            plan_id=PLAN_ID,
        )

        self.assertEqual(plan.schema_version, 1)
        self.assertEqual(plan.plan_id, PLAN_ID)
        self.assertEqual(plan.state_basis_digest, live_state_digest(state))
        self.assertIsNot(plan.actions[0].arguments, arguments)
        arguments["unit_id"] = 99
        self.assertEqual(plan.actions[0].arguments["unit_id"], 8)
        self.assertEqual(validate_turn_plan(plan, state, SESSION_ID), plan)

    def test_rejects_stale_session_turn_player_and_state_basis(self):
        state = ready_state()
        plan = make_turn_plan(
            state,
            SESSION_ID,
            (self.end_turn(),),
            plan_id=PLAN_ID,
        )
        cases = (
            (plan, state, "123e4567-e89b-42d3-a456-426614174099"),
            (plan, ready_state(turn=5), SESSION_ID),
            (plan, ready_state(active_player=1), SESSION_ID),
            (plan, ready_state(gold=13), SESSION_ID),
        )
        for candidate, live_state, session_id in cases:
            with self.subTest(live_state=live_state, session_id=session_id):
                with self.assertRaises(StaleTurnPlanError):
                    validate_turn_plan(candidate, live_state, session_id)

    def test_requires_unique_bounded_allowlisted_actions_and_final_end_turn(self):
        state = ready_state()
        valid = make_turn_plan(
            state,
            SESSION_ID,
            (self.end_turn(),),
            plan_id=PLAN_ID,
        )
        invalid_actions = (
            (),
            (PlannedAction(COMMAND_ONE, "skip_unit", {"unit_id": 8}),),
            (self.end_turn(COMMAND_ONE), self.end_turn(COMMAND_TWO)),
            (
                PlannedAction(COMMAND_ONE, "skip_unit", {"unit_id": 8}),
                self.end_turn(COMMAND_ONE),
            ),
            tuple(self.end_turn(f"123e4567-e89b-42d3-a456-{index:012d}") for index in range(MAX_PLAN_ACTIONS + 1)),
        )
        for actions in invalid_actions:
            with self.subTest(action_count=len(actions)):
                with self.assertRaises(TurnPlanError):
                    validate_turn_plan(replace(valid, actions=actions), state, SESSION_ID)

    def test_rejects_unknown_extra_or_malformed_action_arguments(self):
        state = ready_state()
        valid = make_turn_plan(
            state,
            SESSION_ID,
            (self.end_turn(),),
            plan_id=PLAN_ID,
        )
        bad = (
            PlannedAction(COMMAND_ONE, "arbitrary_lua", {}),
            PlannedAction(COMMAND_ONE, "end_turn", {"extra": True}),
            PlannedAction(COMMAND_ONE, "choose_research", {"tech_type": "Pottery"}),
            PlannedAction(
                COMMAND_ONE,
                "set_city_production",
                {"city_id": True, "kind": "unit", "item_type": "UNIT_SCOUT"},
            ),
            PlannedAction(COMMAND_ONE, "skip_unit", {"unit_id": -1}),
        )
        for action in bad:
            with self.subTest(action=action.action):
                with self.assertRaises(TurnPlanError):
                    validate_turn_plan(
                        replace(valid, actions=(action, self.end_turn())),
                        state,
                        SESSION_ID,
                    )

    def test_state_digest_is_deterministic_and_changes_with_valid_state(self):
        first = ready_state()
        second = ready_state()
        self.assertEqual(live_state_digest(first), live_state_digest(second))
        second.gold = 13
        self.assertNotEqual(live_state_digest(first), live_state_digest(second))

    def test_validates_completed_and_failed_execution_reports(self):
        state = ready_state()
        plan = make_turn_plan(
            state,
            SESSION_ID,
            (self.end_turn(),),
            plan_id=PLAN_ID,
        )
        digest = live_state_digest(state)
        successful_step = ExecutionStepReport(
            index=0,
            command_id=COMMAND_TWO,
            action="end_turn",
            status="success",
            message="verified",
            before_state_digest=digest,
            after_state_digest=digest,
        )
        completed = ExecutionReport(
            schema_version=1,
            plan_id=PLAN_ID,
            bridge_session_id=SESSION_ID,
            status="completed",
            next_action_index=1,
            steps=(successful_step,),
            reason_code="turn_ended",
            message="complete",
        )
        self.assertIs(validate_execution_report(completed, plan), completed)

        failed_step = replace(successful_step, status="error", message="blocked")
        failed = replace(
            completed,
            status="failed",
            next_action_index=0,
            steps=(failed_step,),
            reason_code="action_failed",
        )
        self.assertIs(validate_execution_report(failed, plan), failed)

    def test_rejects_inconsistent_execution_report_state(self):
        state = ready_state()
        plan = make_turn_plan(
            state,
            SESSION_ID,
            (self.end_turn(),),
            plan_id=PLAN_ID,
        )
        report = ExecutionReport(
            schema_version=1,
            plan_id=PLAN_ID,
            bridge_session_id=SESSION_ID,
            status="completed",
            next_action_index=0,
            steps=(),
            reason_code="turn_ended",
            message="not actually complete",
        )
        with self.assertRaisesRegex(TurnPlanError, "every action"):
            validate_execution_report(report, plan)


if __name__ == "__main__":
    unittest.main()
