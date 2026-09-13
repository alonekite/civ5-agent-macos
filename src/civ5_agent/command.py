from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
import sys

from .audit import CommandAuditLog, default_audit_path
from .ipc import default_socket_path, request
from .models import Command, CommandResult
from .preflight import UnsafeSessionError, require_safe_tuner_session
from .tuner import DEFAULT_HOST, DEFAULT_PORT, FireTunerClient, _find_state
from .validation import validate_live_state


def execute_end_turn(
    client: FireTunerClient,
    state_id: int,
    command: Command,
    *,
    verify_timeout: float = 30.0,
    poll_interval: float = 0.25,
) -> CommandResult:
    before_state = validate_live_state(client.read_game_state(state_id))
    before = asdict(before_state)
    accepted, blocking_type = client.request_end_turn(state_id)
    if not accepted:
        return CommandResult(
            id=command.id,
            status="error",
            message=f"Civ V blocked end_turn (blocking_type={blocking_type})",
            before=before,
            after=before,
        )

    deadline = time.monotonic() + verify_timeout
    after_state = before_state
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            after_state = validate_live_state(client.read_game_state(state_id))
        except ValueError:
            # Civ V can briefly report no active game state while advancing the
            # turn. Keep the last validated snapshot and retry until deadline.
            continue
        if after_state.turn is not None and before_state.turn is not None:
            if after_state.turn > before_state.turn:
                return CommandResult(
                    id=command.id,
                    status="success",
                    message=f"verified turn {before_state.turn} -> {after_state.turn}",
                    before=before,
                    after=asdict(after_state),
                )

    return CommandResult(
        id=command.id,
        status="error",
        message=f"end_turn was accepted but turn did not advance within {verify_timeout}s",
        before=before,
        after=asdict(after_state),
    )


def execute_choose_research(
    client: FireTunerClient,
    state_id: int,
    command: Command,
    *,
    verify_timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> CommandResult:
    tech_type = command.args.get("tech_type")
    if not isinstance(tech_type, str):
        return CommandResult(command.id, "error", "choose_research requires tech_type")
    before_state = validate_live_state(client.read_game_state(state_id))
    before = asdict(before_state)
    if before_state.research and before_state.research.get("type") == tech_type:
        return CommandResult(
            command.id,
            "success",
            f"verified research already selected: {tech_type}",
            before,
            before,
        )

    status, tech_id = client.request_choose_research(state_id, tech_type)
    if status not in {"accepted", "already"}:
        return CommandResult(
            command.id,
            "error",
            f"Civ V rejected {tech_type} ({status}, tech_id={tech_id})",
            before,
            before,
        )

    deadline = time.monotonic() + verify_timeout
    after_state = before_state
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            after_state = validate_live_state(client.read_game_state(state_id))
        except ValueError:
            continue
        if after_state.research and after_state.research.get("type") == tech_type:
            return CommandResult(
                command.id,
                "success",
                f"verified research selection: {tech_type}",
                before,
                asdict(after_state),
            )
    return CommandResult(
        command.id,
        "error",
        f"research request was accepted but {tech_type} was not observed within {verify_timeout}s",
        before,
        asdict(after_state),
    )


def execute_city_production(
    client: FireTunerClient,
    state_id: int,
    command: Command,
    *,
    verify_timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> CommandResult:
    city_id = command.args.get("city_id")
    kind = command.args.get("kind")
    item_type = command.args.get("item_type")
    if not isinstance(city_id, int) or isinstance(city_id, bool) or city_id < 0:
        return CommandResult(command.id, "error", "set_city_production requires city_id")
    if not isinstance(kind, str) or not isinstance(item_type, str):
        return CommandResult(
            command.id, "error", "set_city_production requires kind and item_type"
        )

    before_state = validate_live_state(client.read_game_state(state_id))
    before = asdict(before_state)
    if not any(city.get("id") == city_id for city in before_state.cities):
        return CommandResult(
            command.id,
            "error",
            f"city {city_id} is not owned by the active player",
            before,
            before,
        )
    status, item_id, expected = client.request_city_production(
        state_id, city_id, kind, item_type
    )
    if status not in {"accepted", "already"}:
        return CommandResult(
            command.id,
            "error",
            f"Civ V rejected {item_type} ({status}, item_id={item_id})",
            before,
            before,
        )

    deadline = time.monotonic() + verify_timeout
    after_state = before_state
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            after_state = validate_live_state(client.read_game_state(state_id))
        except ValueError:
            continue
        city = next(
            (candidate for candidate in after_state.cities if candidate.get("id") == city_id),
            None,
        )
        if city is not None and city.get("production") == expected:
            return CommandResult(
                command.id,
                "success",
                f"verified city {city_id} production: {item_type}",
                before,
                asdict(after_state),
            )
    return CommandResult(
        command.id,
        "error",
        f"production request was accepted but {item_type} was not observed within {verify_timeout}s",
        before,
        asdict(after_state),
    )


def execute_skip_unit(
    client: FireTunerClient,
    state_id: int,
    command: Command,
    *,
    verify_timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> CommandResult:
    unit_id = command.args.get("unit_id")
    if not isinstance(unit_id, int) or isinstance(unit_id, bool) or unit_id < 0:
        return CommandResult(command.id, "error", "skip_unit requires unit_id")

    before_state = validate_live_state(client.read_game_state(state_id))
    before = asdict(before_state)
    before_unit = next(
        (unit for unit in before_state.units if unit.get("id") == unit_id), None
    )
    if before_unit is None:
        return CommandResult(
            command.id,
            "error",
            f"unit {unit_id} is not owned by the active player",
            before,
            before,
        )
    if before_unit.get("moves") == 0:
        return CommandResult(
            command.id,
            "success",
            f"verified unit {unit_id} already has no moves",
            before,
            before,
        )

    status, returned_unit_id = client.request_skip_unit(state_id, unit_id)
    if status != "accepted" or returned_unit_id != unit_id:
        return CommandResult(
            command.id,
            "error",
            f"Civ V rejected skip for unit {unit_id} ({status}, unit_id={returned_unit_id})",
            before,
            before,
        )

    deadline = time.monotonic() + verify_timeout
    after_state = before_state
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            after_state = validate_live_state(client.read_game_state(state_id))
        except ValueError:
            continue
        after_unit = next(
            (unit for unit in after_state.units if unit.get("id") == unit_id), None
        )
        if (
            after_unit is not None
            and after_unit.get("moves") == 0
            and after_unit.get("x") == before_unit.get("x")
            and after_unit.get("y") == before_unit.get("y")
        ):
            return CommandResult(
                command.id,
                "success",
                f"verified unit {unit_id} skipped without moving",
                before,
                asdict(after_state),
            )
    return CommandResult(
        command.id,
        "error",
        f"skip request was accepted but unit {unit_id} was not observed idle in place "
        f"within {verify_timeout}s",
        before,
        asdict(after_state),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit a verified, allowlisted Civ V action")
    parser.add_argument(
        "action",
        choices=["end_turn", "choose_research", "set_city_production", "skip_unit"],
    )
    parser.add_argument("values", nargs="*")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--verify-timeout", type=float, default=30.0)
    parser.add_argument("--socket", type=Path, default=default_socket_path())
    parser.add_argument("--audit-log", type=Path, default=default_audit_path())
    parser.add_argument("--direct", action="store_true", help="connect directly to FireTuner")
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if not 0 < args.verify_timeout <= 120:
        parser.error("--verify-timeout must be greater than zero and at most 120")

    if args.action == "end_turn" and args.values:
        parser.error("end_turn does not accept values")
    if args.action == "choose_research" and len(args.values) != 1:
        parser.error("choose_research requires exactly one TECH_* value")
    if args.action == "set_city_production" and len(args.values) != 3:
        parser.error("set_city_production requires CITY_ID KIND ITEM_TYPE")
    if args.action == "skip_unit" and len(args.values) != 1:
        parser.error("skip_unit requires UNIT_ID")

    command_args: dict[str, object] = {}
    if args.action == "choose_research":
        command_args = {"tech_type": args.values[0]}
    elif args.action == "set_city_production":
        try:
            city_id = int(args.values[0])
        except ValueError:
            parser.error("CITY_ID must be an integer")
        command_args = {
            "city_id": city_id,
            "kind": args.values[1],
            "item_type": args.values[2],
        }
    elif args.action == "skip_unit":
        try:
            unit_id = int(args.values[0])
        except ValueError:
            parser.error("UNIT_ID must be an integer")
        command_args = {"unit_id": unit_id}

    command = Command(
        action=args.action,
        args=command_args,
    )
    if not args.direct and args.socket.exists():
        try:
            response = request(
                {
                    "op": args.action,
                    "id": command.id,
                    **command.args,
                    "verify_timeout": args.verify_timeout,
                },
                socket_path=args.socket,
                timeout=args.verify_timeout + args.timeout + 5,
            )
            if not response.get("ok"):
                raise ValueError(str(response.get("error", "local bridge request failed")))
            result_data = response.get("result")
            if not isinstance(result_data, dict):
                raise ValueError("local bridge omitted command result")
            if response.get("audit_error"):
                print(f"Command audit warning: {response['audit_error']}", file=sys.stderr)
            print(json.dumps(result_data, sort_keys=True))
            return 0 if result_data.get("status") == "success" else 1
        except (ConnectionError, OSError, TimeoutError, ValueError) as error:
            result = CommandResult(id=command.id, status="error", message=str(error))
            print(json.dumps(asdict(result), sort_keys=True))
            return 1

    try:
        require_safe_tuner_session(args.host, args.port, socket_path=args.socket)
        with FireTunerClient(args.host, args.port, args.timeout) as client:
            handshake = client.handshake()
            state_id = _find_state(handshake.lua_states, "InGame")
            if args.action == "end_turn":
                result = execute_end_turn(
                    client, state_id, command, verify_timeout=args.verify_timeout
                )
            elif args.action == "choose_research":
                result = execute_choose_research(
                    client, state_id, command, verify_timeout=args.verify_timeout
                )
            elif args.action == "set_city_production":
                result = execute_city_production(
                    client, state_id, command, verify_timeout=args.verify_timeout
                )
            else:
                result = execute_skip_unit(
                    client, state_id, command, verify_timeout=args.verify_timeout
                )
    except (
        ConnectionError,
        OSError,
        TimeoutError,
        UnsafeSessionError,
        ValueError,
    ) as error:
        result = CommandResult(id=command.id, status="error", message=str(error))

    try:
        CommandAuditLog(args.audit_log).append(args.action, asdict(result))
    except OSError as error:
        print(f"Command audit warning: {error}", file=sys.stderr)

    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.status == "success" else 1

if __name__ == "__main__":
    raise SystemExit(main())
