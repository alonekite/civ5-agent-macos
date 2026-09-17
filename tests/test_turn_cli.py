import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from civ5_agent.models import GameState
from civ5_agent.turn_cli import (
    EXIT_ERROR,
    EXIT_INCOMPLETE,
    EXIT_SUCCESS,
    MAX_TURN_PLAN_FILE_BYTES,
    load_turn_plan,
    main,
)
from civ5_agent.turn_executor_adapter import WatcherTurnExecutor
from civ5_agent.turn_plan import (
    ExecutionReport,
    ExecutionStepReport,
    PlannedAction,
    TurnPlanError,
    live_state_digest,
    make_turn_plan,
)

SESSION_ID = "123e4567-e89b-42d3-a456-426614174060"
PLAN_ID = "123e4567-e89b-42d3-a456-426614174061"
COMMAND_ID = "123e4567-e89b-42d3-a456-426614174062"
MOVE_COMMAND_ID = "123e4567-e89b-42d3-a456-426614174063"


def state(turn=4):
    return GameState(
        schema_version=2,
        turn=turn,
        active_player=0,
        gold=12,
        turn_active=True,
        can_end_turn=True,
        end_turn_blocking_type=-1,
        research={"id": 1, "type": "TECH_POTTERY", "progress": 0, "cost": 40},
        cities=[
            {
                "id": 4,
                "name": "City",
                "x": 10,
                "y": 11,
                "population": 2,
                "production": "SCOUT",
            }
        ],
        units=[
            {
                "id": 8,
                "name": "Warrior",
                "type": "UNIT_WARRIOR",
                "x": 9,
                "y": 12,
                "moves": 0,
            }
        ],
    )


def plan():
    return make_turn_plan(
        state(),
        SESSION_ID,
        (PlannedAction(COMMAND_ID, "end_turn", {}),),
        plan_id=PLAN_ID,
    )


class TurnPlanCliTest(unittest.TestCase):
    def write_plan(self, directory, values=None):
        path = Path(directory) / "plan.json"
        path.write_text(json.dumps(values if values is not None else asdict(plan())))
        return path

    def test_loads_bounded_exact_turn_plan_json(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded = load_turn_plan(self.write_plan(directory))

        self.assertEqual(loaded, plan())

    def test_loads_schema_one_plan_with_explicit_move_action(self):
        movement_plan = make_turn_plan(
            state(),
            SESSION_ID,
            (
                PlannedAction(
                    MOVE_COMMAND_ID,
                    "move_unit",
                    {"unit_id": 8, "x": 10, "y": 12},
                ),
                PlannedAction(COMMAND_ID, "end_turn", {}),
            ),
            plan_id=PLAN_ID,
        )
        with tempfile.TemporaryDirectory() as directory:
            loaded = load_turn_plan(
                self.write_plan(directory, asdict(movement_plan))
            )
        self.assertEqual(loaded, movement_plan)

    def test_rejects_extra_fields_nonfinite_values_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            values = asdict(plan())
            values["unexpected"] = True
            with self.assertRaisesRegex(TurnPlanError, "fields must be exactly"):
                load_turn_plan(self.write_plan(directory, values))

            nested = asdict(plan())
            nested["actions"][0]["unexpected"] = True
            with self.assertRaisesRegex(TurnPlanError, "PlannedAction fields"):
                load_turn_plan(self.write_plan(directory, nested))

            nonfinite = self.write_plan(directory)
            nonfinite.write_text('{"schema_version":NaN}')
            with self.assertRaisesRegex(TurnPlanError, "invalid JSON constant"):
                load_turn_plan(nonfinite)

            oversized = self.write_plan(directory)
            oversized.write_bytes(b" " * (MAX_TURN_PLAN_FILE_BYTES + 1))
            with self.assertRaisesRegex(TurnPlanError, "exceeds"):
                load_turn_plan(oversized)

    def test_validate_reads_live_state_but_never_executes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            WatcherTurnExecutor,
            "read_state",
            return_value=(SESSION_ID, state()),
        ), patch.object(WatcherTurnExecutor, "execute") as execute, redirect_stdout(
            StringIO()
        ) as output:
            status = main(["validate", str(self.write_plan(directory))])

        self.assertEqual(status, EXIT_SUCCESS)
        self.assertEqual(
            set(json.loads(output.getvalue())),
            {"ok", "operation", "plan_id", "bridge_session_id", "action_count"},
        )
        self.assertTrue(json.loads(output.getvalue())["ok"])
        execute.assert_not_called()

    def test_execute_outputs_complete_report(self):
        before_digest = live_state_digest(state())
        after_digest = live_state_digest(state(turn=5))
        report = ExecutionReport(
            schema_version=1,
            plan_id=PLAN_ID,
            bridge_session_id=SESSION_ID,
            status="completed",
            next_action_index=1,
            steps=(
                ExecutionStepReport(
                    index=0,
                    command_id=COMMAND_ID,
                    action="end_turn",
                    status="success",
                    message="verified",
                    before_state_digest=before_digest,
                    after_state_digest=after_digest,
                ),
            ),
            reason_code="turn_ended",
            message="verified",
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            WatcherTurnExecutor,
            "execute",
            return_value=report,
        ) as execute, redirect_stdout(StringIO()) as output:
            status = main(["execute", str(self.write_plan(directory))])

        rendered = json.loads(output.getvalue())
        self.assertEqual(status, EXIT_SUCCESS)
        self.assertEqual(set(rendered), {"ok", "operation", "report"})
        self.assertTrue(rendered["ok"])
        self.assertEqual(rendered["report"]["status"], "completed")
        self.assertEqual(execute.call_args.args[0], plan())

    def test_noncompleted_report_has_distinct_exit_status(self):
        report = ExecutionReport(
            schema_version=1,
            plan_id=PLAN_ID,
            bridge_session_id=SESSION_ID,
            status="recovery_required",
            next_action_index=0,
            steps=(),
            reason_code="action_outcome_unknown",
            message="unknown",
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            WatcherTurnExecutor,
            "execute",
            return_value=report,
        ), redirect_stdout(StringIO()) as output:
            status = main(["execute", str(self.write_plan(directory))])

        self.assertEqual(status, EXIT_INCOMPLETE)
        rendered = json.loads(output.getvalue())
        self.assertEqual(set(rendered), {"ok", "operation", "report"})
        self.assertFalse(rendered["ok"])

    def test_invalid_file_fails_before_watcher_contact(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "civ5_agent.turn_cli.WatcherTurnExecutor"
        ) as executor, redirect_stdout(StringIO()) as output:
            path = Path(directory) / "invalid.json"
            path.write_text("[]")
            status = main(["execute", str(path)])

        self.assertEqual(status, EXIT_ERROR)
        rendered = json.loads(output.getvalue())
        self.assertEqual(set(rendered), {"ok", "error"})
        self.assertFalse(rendered["ok"])
        executor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
