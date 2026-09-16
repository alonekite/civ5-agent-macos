import unittest
from dataclasses import asdict, replace

from civ5_agent.models import CommandResult, GameState
from civ5_agent.turn_executor import execute_turn_plan
from civ5_agent.turn_plan import PlannedAction, make_turn_plan

SESSION_ID = "123e4567-e89b-42d3-a456-426614174040"
PLAN_ID = "123e4567-e89b-42d3-a456-426614174041"
COMMAND_IDS = tuple(
    f"123e4567-e89b-42d3-a456-426614174{index:03d}" for index in range(42, 50)
)


def state(**changes):
    values = {
        "schema_version": 2,
        "turn": 4,
        "active_player": 0,
        "gold": 12,
        "turn_active": True,
        "can_end_turn": True,
        "end_turn_blocking_type": 0,
        "research": {"id": 1, "type": "TECH_POTTERY", "progress": 0, "cost": 40},
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


class FakeBridge:
    def __init__(self, states):
        self.states = states
        self.index = 0
        self.executed = []

    def read_state(self):
        return SESSION_ID, self.states[self.index]

    def execute(self, action, session_id):
        self.assert_session(session_id)
        before = self.states[self.index]
        after = self.states[self.index + 1]
        self.executed.append(action.action)
        self.index += 1
        return CommandResult(
            id=action.command_id,
            status="success",
            message="verified",
            before=asdict(before),
            after=asdict(after),
        )

    def assert_session(self, session_id):
        if session_id != SESSION_ID:
            raise AssertionError("wrong session")


class TurnExecutorTest(unittest.TestCase):
    def test_invalid_plan_fails_before_write(self):
        initial = state()
        valid = make_turn_plan(
            initial,
            SESSION_ID,
            (PlannedAction(COMMAND_IDS[0], "end_turn", {}),),
            plan_id=PLAN_ID,
        )
        reads = []

        def read():
            reads.append(True)
            return SESSION_ID, initial

        report = execute_turn_plan(replace(valid, actions=()), read, lambda *_: None)

        self.assertEqual(report.status, "failed")
        self.assertEqual(report.reason_code, "invalid_plan")
        self.assertEqual(len(reads), 1)

    def test_executes_ordered_actions_and_completes_only_after_end_turn(self):
        initial = state(
            research=None,
            cities=[{**state().cities[0], "production": ""}],
            units=[{**state().units[0], "moves": 60}],
            can_end_turn=False,
            end_turn_blocking_type=1,
        )
        after_research = state(
            cities=[{**state().cities[0], "production": ""}],
            units=[{**state().units[0], "moves": 60}],
            can_end_turn=False,
            end_turn_blocking_type=2,
        )
        after_production = state(
            units=[{**state().units[0], "moves": 60}],
            can_end_turn=False,
            end_turn_blocking_type=3,
        )
        ready = state()
        advanced = state(turn=5)
        actions = (
            PlannedAction(
                COMMAND_IDS[0],
                "choose_research",
                {"tech_type": "TECH_POTTERY"},
            ),
            PlannedAction(
                COMMAND_IDS[1],
                "set_city_production",
                {"city_id": 4, "kind": "unit", "item_type": "UNIT_SCOUT"},
            ),
            PlannedAction(COMMAND_IDS[2], "skip_unit", {"unit_id": 8}),
            PlannedAction(COMMAND_IDS[3], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge(
            [initial, after_research, after_production, ready, advanced]
        )

        report = execute_turn_plan(plan, bridge.read_state, bridge.execute)

        self.assertEqual(report.status, "completed")
        self.assertEqual(report.next_action_index, 4)
        self.assertEqual(
            bridge.executed,
            ["choose_research", "set_city_production", "skip_unit", "end_turn"],
        )
        self.assertTrue(all(step.status == "success" for step in report.steps))

    def test_pauses_before_writing_when_requirement_is_uncovered(self):
        initial = state(research=None, can_end_turn=False, end_turn_blocking_type=1)
        plan = make_turn_plan(
            initial,
            SESSION_ID,
            (PlannedAction(COMMAND_IDS[0], "end_turn", {}),),
            plan_id=PLAN_ID,
        )
        bridge = FakeBridge([initial])

        report = execute_turn_plan(plan, bridge.read_state, bridge.execute)

        self.assertEqual(report.status, "paused")
        self.assertEqual(report.reason_code, "unresolved_requirement")
        self.assertEqual(bridge.executed, [])

    def test_detects_drift_from_last_verified_action_state(self):
        initial = state(units=[{**state().units[0], "moves": 60}])
        after_skip = state()
        drifted = state(gold=99)
        actions = (
            PlannedAction(COMMAND_IDS[0], "skip_unit", {"unit_id": 8}),
            PlannedAction(COMMAND_IDS[1], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge([initial, after_skip])

        def read_with_drift():
            if bridge.index == 1:
                return SESSION_ID, drifted
            return bridge.read_state()

        report = execute_turn_plan(plan, read_with_drift, bridge.execute)

        self.assertEqual(report.status, "stale")
        self.assertEqual(report.next_action_index, 1)
        self.assertEqual(len(report.steps), 1)

    def test_unknown_action_outcome_requires_recovery_without_retry(self):
        initial = state()
        plan = make_turn_plan(
            initial,
            SESSION_ID,
            (PlannedAction(COMMAND_IDS[0], "end_turn", {}),),
            plan_id=PLAN_ID,
        )
        attempts = []

        def timeout(action, session_id):
            attempts.append(action.command_id)
            raise TimeoutError("connection lost after submission")

        report = execute_turn_plan(
            plan,
            lambda: (SESSION_ID, initial),
            timeout,
        )

        self.assertEqual(report.status, "recovery_required")
        self.assertEqual(report.next_action_index, 0)
        self.assertEqual(attempts, [COMMAND_IDS[0]])

    def test_bridge_error_result_is_failed_and_not_retried(self):
        initial = state()
        action = PlannedAction(COMMAND_IDS[0], "end_turn", {})
        plan = make_turn_plan(initial, SESSION_ID, (action,), plan_id=PLAN_ID)
        attempts = []

        def fail(candidate, session_id):
            attempts.append(candidate.command_id)
            return CommandResult(
                id=candidate.command_id,
                status="error",
                message="blocked",
                before=asdict(initial),
                after=asdict(initial),
            )

        report = execute_turn_plan(plan, lambda: (SESSION_ID, initial), fail)

        self.assertEqual(report.status, "failed")
        self.assertEqual(report.next_action_index, 0)
        self.assertEqual(report.steps[-1].status, "error")
        self.assertEqual(attempts, [COMMAND_IDS[0]])

    def test_bridge_rejection_exception_is_failed_without_retry(self):
        initial = state()
        action = PlannedAction(COMMAND_IDS[0], "end_turn", {})
        plan = make_turn_plan(initial, SESSION_ID, (action,), plan_id=PLAN_ID)
        attempts = []

        def reject(candidate, session_id):
            attempts.append(candidate.command_id)
            raise ValueError("bridge rejected arguments")

        report = execute_turn_plan(plan, lambda: (SESSION_ID, initial), reject)

        self.assertEqual(report.status, "failed")
        self.assertEqual(report.reason_code, "action_rejected")
        self.assertEqual(attempts, [COMMAND_IDS[0]])

    def test_emits_bounded_factual_lifecycle_events(self):
        initial = state()
        advanced = state(turn=5)
        action = PlannedAction(COMMAND_IDS[0], "end_turn", {})
        plan = make_turn_plan(initial, SESSION_ID, (action,), plan_id=PLAN_ID)
        bridge = FakeBridge([initial, advanced])
        events = []

        report = execute_turn_plan(
            plan,
            bridge.read_state,
            bridge.execute,
            events.append,
        )

        self.assertEqual(report.status, "completed")
        self.assertEqual(
            [event.kind for event in events],
            [
                "plan_received",
                "action_started",
                "action_result_received",
                "completed",
            ],
        )
        self.assertEqual(events[1].command_id, COMMAND_IDS[0])

    def test_event_sink_failure_does_not_change_or_retry_execution(self):
        initial = state()
        advanced = state(turn=5)
        action = PlannedAction(COMMAND_IDS[0], "end_turn", {})
        plan = make_turn_plan(initial, SESSION_ID, (action,), plan_id=PLAN_ID)
        bridge = FakeBridge([initial, advanced])

        def broken_sink(event):
            raise OSError("event sink unavailable")

        report = execute_turn_plan(
            plan,
            bridge.read_state,
            bridge.execute,
            broken_sink,
        )

        self.assertEqual(report.status, "completed")
        self.assertEqual(bridge.executed, ["end_turn"])
        self.assertTrue(report.event_sink_errors)


if __name__ == "__main__":
    unittest.main()
