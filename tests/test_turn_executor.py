import unittest
from dataclasses import asdict, replace

from civ5_agent.models import CommandResult, GameState
from civ5_agent.turn_executor import execute_turn_plan, reconcile_turn_plan
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
        "end_turn_blocking_type": -1,
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


def movement_state(
    *,
    x=9,
    y=12,
    moves=120,
    ready=True,
    targets=({"x": 10, "y": 12},),
    turn=4,
    blocker=3,
):
    return GameState(
        schema_version=6,
        turn=turn,
        active_player=0,
        gold=12,
        score=10,
        current_era=0,
        turn_active=True,
        can_end_turn=blocker == -1,
        end_turn_blocking_type=blocker,
        research={"id": 1, "type": "TECH_POTTERY", "progress": 0, "cost": 40},
        research_choice={"required": False, "mode": "normal"},
        victory={
            "science_enabled": True,
            "apollo": 0,
            "booster": 0,
            "cockpit": 0,
            "stasis_chamber": 0,
            "engine": 0,
        },
        units=[
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": x,
                "y": y,
                "moves": moves,
                "damage": 0,
                "max_hit_points": 100,
                "combat_strength": 8,
                "ranged_strength": 0,
                "range": 1,
                "ready_to_move": ready,
                "ordinary_move_targets": list(targets),
            }
        ],
    )


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
    def test_executes_explicit_move_then_end_turn_with_factual_events(self):
        initial = movement_state()
        moved = movement_state(
            x=10,
            y=12,
            moves=60,
            ready=False,
            targets=(),
            blocker=-1,
        )
        advanced = movement_state(
            x=10,
            y=12,
            moves=60,
            ready=False,
            targets=(),
            turn=5,
            blocker=-1,
        )
        actions = (
            PlannedAction(
                COMMAND_IDS[0],
                "move_unit",
                {"unit_id": 8, "x": 10, "y": 12},
            ),
            PlannedAction(COMMAND_IDS[1], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge([initial, moved, advanced])
        events = []

        report = execute_turn_plan(
            plan,
            bridge.read_state,
            bridge.execute,
            events.append,
        )

        self.assertEqual(report.status, "completed")
        self.assertEqual(bridge.executed, ["move_unit", "end_turn"])
        self.assertEqual(
            [event.command_id for event in events if event.command_id is not None],
            [COMMAND_IDS[0], COMMAND_IDS[0], COMMAND_IDS[1], COMMAND_IDS[1]],
        )

    def test_move_covers_only_its_exact_unit_requirement(self):
        initial = movement_state()
        actions = (
            PlannedAction(
                COMMAND_IDS[0],
                "move_unit",
                {"unit_id": 9, "x": 10, "y": 12},
            ),
            PlannedAction(COMMAND_IDS[1], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge([initial])

        report = execute_turn_plan(plan, bridge.read_state, bridge.execute)

        self.assertEqual(report.status, "paused")
        self.assertEqual(report.reason_code, "unresolved_requirement")
        self.assertEqual(bridge.executed, [])

    def test_pauses_when_moved_unit_still_needs_uncovered_orders(self):
        initial = movement_state()
        still_ready = movement_state(
            x=10,
            y=12,
            moves=60,
            ready=True,
            targets=({"x": 11, "y": 12},),
        )
        actions = (
            PlannedAction(
                COMMAND_IDS[0],
                "move_unit",
                {"unit_id": 8, "x": 10, "y": 12},
            ),
            PlannedAction(COMMAND_IDS[1], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge([initial, still_ready])

        report = execute_turn_plan(plan, bridge.read_state, bridge.execute)

        self.assertEqual(report.status, "paused")
        self.assertEqual(report.next_action_index, 1)
        self.assertEqual(bridge.executed, ["move_unit"])

    def test_executes_multiple_explicit_moves_for_same_unit(self):
        initial = movement_state()
        first = movement_state(
            x=10,
            y=12,
            moves=60,
            ready=True,
            targets=({"x": 11, "y": 12},),
        )
        second = movement_state(
            x=11,
            y=12,
            moves=0,
            ready=False,
            targets=(),
            blocker=-1,
        )
        advanced = movement_state(
            x=11,
            y=12,
            moves=0,
            ready=False,
            targets=(),
            turn=5,
            blocker=-1,
        )
        actions = (
            PlannedAction(
                COMMAND_IDS[0],
                "move_unit",
                {"unit_id": 8, "x": 10, "y": 12},
            ),
            PlannedAction(
                COMMAND_IDS[1],
                "move_unit",
                {"unit_id": 8, "x": 11, "y": 12},
            ),
            PlannedAction(COMMAND_IDS[2], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge([initial, first, second, advanced])

        report = execute_turn_plan(plan, bridge.read_state, bridge.execute)

        self.assertEqual(report.status, "completed")
        self.assertEqual(bridge.executed, ["move_unit", "move_unit", "end_turn"])

    def test_rejects_invalid_move_result_even_when_bridge_calls_it_success(self):
        initial = movement_state()
        unexpected = movement_state(
            x=11,
            y=12,
            moves=60,
            ready=False,
            targets=(),
            blocker=-1,
        )
        actions = (
            PlannedAction(
                COMMAND_IDS[0],
                "move_unit",
                {"unit_id": 8, "x": 10, "y": 12},
            ),
            PlannedAction(COMMAND_IDS[1], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge([initial, unexpected])

        report = execute_turn_plan(plan, bridge.read_state, bridge.execute)

        self.assertEqual(report.status, "failed")
        self.assertEqual(report.reason_code, "invalid_action_result")
        self.assertEqual(bridge.executed, ["move_unit"])

    def test_rejects_move_result_that_never_changes_coordinates(self):
        initial = movement_state(targets=({"x": 9, "y": 12},))
        spent = movement_state(
            moves=60,
            ready=False,
            targets=(),
            blocker=-1,
        )
        actions = (
            PlannedAction(
                COMMAND_IDS[0],
                "move_unit",
                {"unit_id": 8, "x": 9, "y": 12},
            ),
            PlannedAction(COMMAND_IDS[1], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        bridge = FakeBridge([initial, spent])

        report = execute_turn_plan(plan, bridge.read_state, bridge.execute)

        self.assertEqual(report.status, "failed")
        self.assertEqual(report.reason_code, "invalid_action_result")

    def test_reconciles_verified_move_then_pauses_without_resubmission(self):
        initial = movement_state()
        moved = movement_state(
            x=10,
            y=12,
            moves=60,
            ready=False,
            targets=(),
            blocker=-1,
        )
        action = PlannedAction(
            COMMAND_IDS[0],
            "move_unit",
            {"unit_id": 8, "x": 10, "y": 12},
        )
        plan = make_turn_plan(
            initial,
            SESSION_ID,
            (action, PlannedAction(COMMAND_IDS[1], "end_turn", {})),
            plan_id=PLAN_ID,
        )
        recovery = execute_turn_plan(
            plan,
            lambda: (SESSION_ID, initial),
            lambda *_: (_ for _ in ()).throw(TimeoutError("outcome unknown")),
        )
        cached = CommandResult(
            id=COMMAND_IDS[0],
            status="success",
            message="verified",
            before=asdict(initial),
            after=asdict(moved),
        )

        report = reconcile_turn_plan(
            plan,
            recovery,
            lambda: (SESSION_ID, moved),
            lambda *_: cached,
        )

        self.assertEqual(report.status, "paused")
        self.assertEqual(report.reason_code, "action_reconciled")
        self.assertEqual(report.next_action_index, 1)

    def test_rejects_cached_move_with_unexpected_destination(self):
        initial = movement_state()
        unexpected = movement_state(
            x=11,
            y=12,
            moves=60,
            ready=False,
            targets=(),
            blocker=-1,
        )
        action = PlannedAction(
            COMMAND_IDS[0],
            "move_unit",
            {"unit_id": 8, "x": 10, "y": 12},
        )
        plan = make_turn_plan(
            initial,
            SESSION_ID,
            (action, PlannedAction(COMMAND_IDS[1], "end_turn", {})),
            plan_id=PLAN_ID,
        )
        recovery = execute_turn_plan(
            plan,
            lambda: (SESSION_ID, initial),
            lambda *_: (_ for _ in ()).throw(TimeoutError("outcome unknown")),
        )
        cached = CommandResult(
            id=COMMAND_IDS[0],
            status="success",
            message="verified",
            before=asdict(initial),
            after=asdict(unexpected),
        )

        report = reconcile_turn_plan(
            plan,
            recovery,
            lambda: (SESSION_ID, unexpected),
            lambda *_: cached,
        )

        self.assertEqual(report.status, "recovery_required")
        self.assertEqual(report.reason_code, "invalid_recovery_evidence")

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

    def test_reconciles_cached_final_end_turn_without_resubmission(self):
        initial = state()
        advanced = state(turn=5)
        action = PlannedAction(COMMAND_IDS[0], "end_turn", {})
        plan = make_turn_plan(initial, SESSION_ID, (action,), plan_id=PLAN_ID)
        recovery = execute_turn_plan(
            plan,
            lambda: (SESSION_ID, initial),
            lambda *_: (_ for _ in ()).throw(TimeoutError("outcome unknown")),
        )
        lookups = []

        def lookup(candidate, session_id):
            lookups.append((candidate.command_id, session_id))
            return CommandResult(
                id=candidate.command_id,
                status="success",
                message="verified",
                before=asdict(initial),
                after=asdict(advanced),
            )

        report = reconcile_turn_plan(
            plan,
            recovery,
            lambda: (SESSION_ID, advanced),
            lookup,
        )

        self.assertEqual(report.status, "completed")
        self.assertEqual(report.next_action_index, 1)
        self.assertEqual(lookups, [(COMMAND_IDS[0], SESSION_ID)])

    def test_recovery_cache_miss_remains_unknown_without_write(self):
        initial = state()
        action = PlannedAction(COMMAND_IDS[0], "end_turn", {})
        plan = make_turn_plan(initial, SESSION_ID, (action,), plan_id=PLAN_ID)
        recovery = execute_turn_plan(
            plan,
            lambda: (SESSION_ID, initial),
            lambda *_: (_ for _ in ()).throw(TimeoutError("outcome unknown")),
        )
        reads = []

        report = reconcile_turn_plan(
            plan,
            recovery,
            lambda: reads.append(True),
            lambda *_: None,
        )

        self.assertEqual(report.status, "recovery_required")
        self.assertEqual(report.reason_code, "command_result_unavailable")
        self.assertEqual(reads, [])

    def test_reconciles_nonfinal_action_then_pauses_at_next_action(self):
        initial = state(units=[{**state().units[0], "moves": 60}])
        ready = state()
        actions = (
            PlannedAction(COMMAND_IDS[0], "skip_unit", {"unit_id": 8}),
            PlannedAction(COMMAND_IDS[1], "end_turn", {}),
        )
        plan = make_turn_plan(initial, SESSION_ID, actions, plan_id=PLAN_ID)
        recovery = execute_turn_plan(
            plan,
            lambda: (SESSION_ID, initial),
            lambda *_: (_ for _ in ()).throw(TimeoutError("outcome unknown")),
        )
        cached = CommandResult(
            id=COMMAND_IDS[0],
            status="success",
            message="verified",
            before=asdict(initial),
            after=asdict(ready),
        )

        report = reconcile_turn_plan(
            plan,
            recovery,
            lambda: (SESSION_ID, ready),
            lambda *_: cached,
        )

        self.assertEqual(report.status, "paused")
        self.assertEqual(report.reason_code, "action_reconciled")
        self.assertEqual(report.next_action_index, 1)
        self.assertEqual(len(report.steps), 1)

    def test_invalid_cached_result_keeps_recovery_required(self):
        initial = state()
        action = PlannedAction(COMMAND_IDS[0], "end_turn", {})
        plan = make_turn_plan(initial, SESSION_ID, (action,), plan_id=PLAN_ID)
        recovery = execute_turn_plan(
            plan,
            lambda: (SESSION_ID, initial),
            lambda *_: (_ for _ in ()).throw(TimeoutError("outcome unknown")),
        )
        invalid = CommandResult(
            id=COMMAND_IDS[1],
            status="success",
            before=asdict(initial),
            after=asdict(state(turn=5)),
        )

        report = reconcile_turn_plan(
            plan,
            recovery,
            lambda: (SESSION_ID, state(turn=5)),
            lambda *_: invalid,
        )

        self.assertEqual(report.status, "recovery_required")
        self.assertEqual(report.reason_code, "invalid_recovery_evidence")

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
