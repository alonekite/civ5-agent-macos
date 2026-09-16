from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .ipc import default_socket_path, request
from .identity import validate_bridge_session_id
from .models import Command, GameState
from .turn_requirements import inspect_turn_requirements
from .validation import validate_live_state


@dataclass(frozen=True)
class Decision:
    action: Literal["wait", "manual_required", "end_turn"]
    reason: str


def decide(state: GameState) -> Decision:
    validate_live_state(state)
    requirements = inspect_turn_requirements(state)
    if not requirements:
        return Decision("end_turn", "all observed mandatory choices are complete")
    requirement = requirements[0]
    if requirement.kind == "turn_inactive":
        return Decision("wait", "active player's turn is not active")
    if requirement.kind == "research_choice":
        if requirement.mode == "free_technology":
            return Decision("manual_required", "choose free technology")
        if requirement.mode == "unsupported":
            return Decision("manual_required", "unsupported research choice")
        return Decision("manual_required", "choose research")
    if requirement.kind == "city_production":
        return Decision("manual_required", "choose city production")
    if requirement.kind == "unit_orders":
        return Decision("manual_required", "issue unit orders")
    if requirement.kind == "end_turn_blocked":
        return Decision(
            "manual_required",
            f"Civ V end-turn blocker {requirement.blocking_type}",
        )
    raise AssertionError(f"unsupported turn requirement: {requirement.kind}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the legacy Civ V readiness/end-turn proof"
    )
    parser.add_argument("--socket", type=Path, default=default_socket_path())
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify-timeout", type=float, default=30.0)
    args = parser.parse_args()

    if not 0 < args.verify_timeout <= 120:
        parser.error("--verify-timeout must be greater than zero and at most 120")

    try:
        response = request({"op": "read_state"}, socket_path=args.socket)
        if not response.get("ok") or not isinstance(response.get("state"), dict):
            raise ValueError(str(response.get("error", "watcher omitted state")))
        state = GameState(**response["state"])
        bridge_session_id = validate_bridge_session_id(
            response.get("bridge_session_id")
        )
        decision = decide(state)
        output: dict[str, object] = {
            "state": asdict(state),
            "decision": asdict(decision),
            "bridge_session_id": bridge_session_id,
        }
        if args.execute:
            if decision.action != "end_turn":
                output["result"] = {
                    "status": "error",
                    "message": f"readiness check refused execution: {decision.reason}",
                }
            else:
                command = Command("end_turn")
                command_response = request(
                    {
                        "op": "end_turn",
                        "id": command.id,
                        "bridge_session_id": bridge_session_id,
                        "verify_timeout": args.verify_timeout,
                    },
                    socket_path=args.socket,
                    timeout=args.verify_timeout + 5,
                )
                if not command_response.get("ok"):
                    raise ValueError(str(command_response.get("error", "command failed")))
                output["result"] = command_response.get("result")
        print(json.dumps(output, sort_keys=True))
        result = output.get("result")
        return 1 if isinstance(result, dict) and result.get("status") == "error" else 0
    except (ConnectionError, OSError, TimeoutError, TypeError, ValueError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
