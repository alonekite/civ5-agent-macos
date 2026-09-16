from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .ipc import default_socket_path
from .turn_executor_adapter import WatcherTurnExecutor
from .turn_plan import TurnPlan, TurnPlanError, turn_plan_from_dict, validate_turn_plan

MAX_TURN_PLAN_FILE_BYTES = 64 * 1024


def load_turn_plan(path: Path) -> TurnPlan:
    with path.open("rb") as source:
        encoded = source.read(MAX_TURN_PLAN_FILE_BYTES + 1)
    if len(encoded) > MAX_TURN_PLAN_FILE_BYTES:
        raise TurnPlanError(
            f"TurnPlan file exceeds {MAX_TURN_PLAN_FILE_BYTES} bytes"
        )
    try:
        values = json.loads(encoded, parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise TurnPlanError(f"invalid TurnPlan JSON: {error}") from error
    return turn_plan_from_dict(values)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate or execute an explicit Civilization V TurnPlan"
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("validate", "execute"):
        command = subparsers.add_parser(operation)
        command.add_argument("plan", type=Path)
        command.add_argument("--socket", type=Path, default=default_socket_path())
        command.add_argument("--timeout", type=float, default=3.0)
        command.add_argument("--verify-timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if not 0 < args.verify_timeout <= 120:
        parser.error("--verify-timeout must be greater than zero and at most 120")

    try:
        plan = load_turn_plan(args.plan)
        executor = WatcherTurnExecutor(
            socket_path=args.socket,
            timeout=args.timeout,
            verify_timeout=args.verify_timeout,
        )
        if args.operation == "validate":
            session_id, state = executor.read_state()
            validate_turn_plan(plan, state, session_id)
            output: dict[str, Any] = {
                "ok": True,
                "operation": "validate",
                "plan_id": plan.plan_id,
                "bridge_session_id": plan.bridge_session_id,
                "action_count": len(plan.actions),
            }
            exit_status = 0
        else:
            report = executor.execute(plan)
            output = {
                "ok": report.status == "completed",
                "operation": "execute",
                "report": asdict(report),
            }
            exit_status = 0 if report.status == "completed" else 2
    except (
        ConnectionError,
        OSError,
        TimeoutError,
        TypeError,
        ValueError,
    ) as error:
        output = {"ok": False, "error": str(error)}
        exit_status = 1

    print(json.dumps(output, allow_nan=False, sort_keys=True))
    return exit_status


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
