from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .ipc import default_socket_path, request
from .models import Command, GameState
from .validation import validate_live_state


@dataclass(frozen=True)
class Decision:
    action: Literal["wait", "manual_required", "end_turn"]
    reason: str


def decide(state: GameState) -> Decision:
    validate_live_state(state)
    if not state.turn_active:
        return Decision("wait", "active player's turn is not active")
    if state.research is None:
        return Decision("manual_required", "choose research")
    without_production = [city for city in state.cities if not city.get("production")]
    if without_production:
        return Decision("manual_required", "choose city production")
    ready_units = [unit for unit in state.units if int(unit.get("moves", 0)) > 0]
    if ready_units:
        return Decision("manual_required", "issue unit orders")
    if not state.can_end_turn:
        return Decision(
            "manual_required",
            f"Civ V end-turn blocker {state.end_turn_blocking_type}",
        )
    return Decision("end_turn", "all observed mandatory choices are complete")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the deterministic Civ V policy")
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
        decision = decide(state)
        output: dict[str, object] = {
            "state": asdict(state),
            "decision": asdict(decision),
        }
        if args.execute:
            if decision.action != "end_turn":
                output["result"] = {
                    "status": "error",
                    "message": f"policy refused execution: {decision.reason}",
                }
            else:
                command = Command("end_turn")
                command_response = request(
                    {
                        "op": "end_turn",
                        "id": command.id,
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
