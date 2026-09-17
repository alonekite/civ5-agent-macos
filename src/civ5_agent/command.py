from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
import sys

from .actions import CommandValidationError, validate_command
from .audit import CommandAuditLog, default_audit_path
from .identity import new_bridge_session_id, validate_bridge_session_id
from .ipc import default_socket_path, request
from .models import Command, CommandResult
from .preflight import UnsafeSessionError, require_safe_tuner_session
from .tuner import DEFAULT_HOST, DEFAULT_PORT, FireTunerClient, _find_state
from .validation import MAX_MAP_COORDINATE, validate_live_state


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
    before_ready = before_unit.get("ready_to_move")
    if not isinstance(before_ready, bool):
        return CommandResult(
            command.id,
            "error",
            f"unit {unit_id} state does not expose ready_to_move",
            before,
            before,
        )
    if not before_ready:
        return CommandResult(
            command.id,
            "success",
            f"verified unit {unit_id} already does not need orders",
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
            and after_unit.get("ready_to_move") is False
            and after_unit.get("x") == before_unit.get("x")
            and after_unit.get("y") == before_unit.get("y")
            and after_unit.get("moves") == before_unit.get("moves")
        ):
            return CommandResult(
                command.id,
                "success",
                f"verified unit {unit_id} skipped without moving or spending movement",
                before,
                asdict(after_state),
            )
    return CommandResult(
        command.id,
        "error",
        f"skip request was accepted but unit {unit_id} was not observed out of the "
        f"ready-unit cycle in place with unchanged movement "
        f"within {verify_timeout}s",
        before,
        asdict(after_state),
    )


def execute_move_unit(
    client: FireTunerClient,
    state_id: int,
    command: Command,
    *,
    verify_timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> CommandResult:
    unit_id = command.args.get("unit_id")
    target_x = command.args.get("x")
    target_y = command.args.get("y")
    if isinstance(unit_id, bool) or not isinstance(unit_id, int) or unit_id < 0:
        return CommandResult(command.id, "error", "move_unit requires unit_id")
    for name, value in (("x", target_x), ("y", target_y)):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= MAX_MAP_COORDINATE
        ):
            return CommandResult(
                command.id,
                "error",
                f"move_unit {name} must be an integer from 0 to {MAX_MAP_COORDINATE}",
            )

    before_state = validate_live_state(client.read_game_state(state_id))
    before = asdict(before_state)
    if before_state.schema_version < 6:
        return CommandResult(
            command.id,
            "error",
            "move_unit requires a fresh schema 6+ state",
            before,
            before,
        )
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
    if {"x": target_x, "y": target_y} not in before_unit["ordinary_move_targets"]:
        return CommandResult(
            command.id,
            "error",
            f"destination ({target_x}, {target_y}) is not an admitted ordinary move target for unit {unit_id}",
            before,
            before,
        )

    source_x = before_unit["x"]
    source_y = before_unit["y"]
    before_moves = before_unit["moves"]
    before_type = before_unit["type"]
    status, returned_unit_id, returned_x, returned_y = client.request_move_unit(
        state_id,
        unit_id,
        source_x,
        source_y,
        target_x,
        target_y,
    )
    if (
        status != "accepted"
        or returned_unit_id != unit_id
        or returned_x != target_x
        or returned_y != target_y
    ):
        return CommandResult(
            command.id,
            "error",
            f"Civ V rejected move for unit {unit_id} to ({target_x}, {target_y}) ({status})",
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
        after = asdict(after_state)
        if after_state.schema_version != before_state.schema_version:
            return CommandResult(
                command.id,
                "error",
                "move_unit read-back changed live-state schema",
                before,
                after,
            )
        if (
            after_state.turn != before_state.turn
            or after_state.active_player != before_state.active_player
            or after_state.turn_active is not True
        ):
            return CommandResult(
                command.id,
                "error",
                "move_unit read-back changed turn, active player, or active-turn state",
                before,
                after,
            )
        after_unit = next(
            (unit for unit in after_state.units if unit.get("id") == unit_id), None
        )
        if after_unit is None or after_unit.get("type") != before_type:
            return CommandResult(
                command.id,
                "error",
                f"move_unit read-back lost or transformed unit {unit_id}",
                before,
                after,
            )
        after_position = (after_unit.get("x"), after_unit.get("y"))
        after_moves = after_unit.get("moves")
        if after_position == (target_x, target_y):
            if isinstance(after_moves, int) and after_moves < before_moves:
                return CommandResult(
                    command.id,
                    "success",
                    f"verified unit {unit_id} moved ({source_x}, {source_y}) -> ({target_x}, {target_y})",
                    before,
                    after,
                )
            return CommandResult(
                command.id,
                "error",
                f"unit {unit_id} reached the destination without lower movement points",
                before,
                after,
            )
        if after_position != (source_x, source_y) or after_moves != before_moves:
            return CommandResult(
                command.id,
                "error",
                f"unit {unit_id} changed unexpectedly while verifying move_unit",
                before,
                after,
            )
    return CommandResult(
        command.id,
        "error",
        f"move request was accepted but unit {unit_id} did not reach ({target_x}, {target_y}) within {verify_timeout}s",
        before,
        asdict(after_state),
    )


def execute_worker_build(
    client: FireTunerClient,
    state_id: int,
    command: Command,
    *,
    verify_timeout: float = 10.0,
    poll_interval: float = 0.1,
) -> CommandResult:
    try:
        normalized = validate_command(command)
    except CommandValidationError as error:
        return CommandResult(command.id, "error", str(error))
    if normalized.action != "worker_build":
        return CommandResult(command.id, "error", "worker_build command required")
    unit_id = normalized.args["unit_id"]
    source_x = normalized.args["x"]
    source_y = normalized.args["y"]
    build_type = normalized.args["build_type"]

    try:
        before_state = validate_live_state(client.read_game_state(state_id))
    except ValueError as error:
        raise CommandValidationError(
            f"worker_build rejected malformed live state: {error}"
        ) from error
    before = asdict(before_state)
    if before_state.schema_version != 7:
        return CommandResult(
            command.id,
            "error",
            "worker_build requires a fresh schema 7 state",
            before,
            before,
        )
    matching_units = [
        unit for unit in before_state.units if unit.get("id") == unit_id
    ]
    if len(matching_units) != 1:
        return CommandResult(
            command.id,
            "error",
            f"worker_build requires exactly one owned unit {unit_id}",
            before,
            before,
        )
    before_unit = matching_units[0]
    if (before_unit["x"], before_unit["y"]) != (source_x, source_y):
        return CommandResult(
            command.id,
            "error",
            f"worker_build source ({source_x}, {source_y}) is stale for unit {unit_id}",
            before,
            before,
        )
    if before_unit["current_build_type"] is not None:
        return CommandResult(
            command.id,
            "error",
            f"unit {unit_id} is already executing a build",
            before,
            before,
        )
    before_plot = before_unit["current_plot"]
    if (
        before_plot["is_water"]
        or before_plot["feature_type"] is not None
        or before_plot["improvement_type"] is not None
        or not before_unit["ready_to_move"]
        or before_unit["moves"] <= 0
    ):
        return CommandResult(
            command.id,
            "error",
            f"unit {unit_id} is not in the admitted ordinary-build state",
            before,
            before,
        )
    candidates = [
        candidate
        for candidate in before_unit["ordinary_build_actions"]
        if candidate.get("build_type") == build_type
    ]
    if len(candidates) != 1:
        return CommandResult(
            command.id,
            "error",
            f"{build_type} is not one exact admitted ordinary build for unit {unit_id}",
            before,
            before,
        )
    expected_improvement = candidates[0]["improvement_type"]
    before_moves = before_unit["moves"]
    before_type = before_unit["type"]

    status, returned_unit_id, returned_build_type = client.request_worker_build(
        state_id, unit_id, source_x, source_y, build_type
    )
    if (
        status != "accepted"
        or returned_unit_id != unit_id
        or returned_build_type != build_type
    ):
        return CommandResult(
            command.id,
            "error",
            f"Civ V rejected worker build for unit {unit_id} ({status})",
            before,
            before,
        )

    unchanged_plot_fields = set(before_plot) - {"improvement_type"}
    deadline = time.monotonic() + verify_timeout
    after_state = before_state
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            after_state = validate_live_state(client.read_game_state(state_id))
        except ValueError:
            continue
        after = asdict(after_state)
        if (
            after_state.schema_version != 7
            or after_state.turn != before_state.turn
            or after_state.active_player != before_state.active_player
            or after_state.turn_active is not True
        ):
            return CommandResult(
                command.id,
                "error",
                "worker_build read-back changed schema, turn, player, or active-turn state",
                before,
                after,
            )
        units = [unit for unit in after_state.units if unit.get("id") == unit_id]
        if len(units) != 1 or units[0].get("type") != before_type:
            return CommandResult(
                command.id,
                "error",
                f"worker_build read-back lost or transformed unit {unit_id}",
                before,
                after,
            )
        after_unit = units[0]
        if (after_unit["x"], after_unit["y"]) != (source_x, source_y):
            return CommandResult(
                command.id,
                "error",
                f"unit {unit_id} moved while verifying worker_build",
                before,
                after,
            )
        after_plot = after_unit["current_plot"]
        if any(
            after_plot[field] != before_plot[field]
            for field in unchanged_plot_fields
        ):
            return CommandResult(
                command.id,
                "error",
                "worker_build changed an unsupported plot fact",
                before,
                after,
            )
        after_moves = after_unit["moves"]
        active = (
            after_unit["current_build_type"] == build_type
            and after_plot["improvement_type"] is None
        )
        completed = (
            after_unit["current_build_type"] is None
            and after_plot["improvement_type"] == expected_improvement
        )
        if after_moves < before_moves and active != completed:
            branch = "active" if active else "completed"
            return CommandResult(
                command.id,
                "success",
                f"verified {branch} {build_type} for unit {unit_id} at ({source_x}, {source_y})",
                before,
                after,
            )
        if after_moves > before_moves or (
            after_moves < before_moves and not (active or completed)
        ):
            return CommandResult(
                command.id,
                "error",
                f"worker_build produced an unexpected result for unit {unit_id}",
                before,
                after,
            )
    return CommandResult(
        command.id,
        "error",
        f"worker build was accepted but no exact result was observed within {verify_timeout}s",
        before,
        asdict(after_state),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit a verified, allowlisted Civ V action")
    parser.add_argument(
        "action",
        choices=[
            "end_turn",
            "choose_research",
            "set_city_production",
            "skip_unit",
            "move_unit",
            "worker_build",
        ],
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
    if args.action == "move_unit" and len(args.values) != 3:
        parser.error("move_unit requires UNIT_ID X Y")
    if args.action == "worker_build" and len(args.values) != 4:
        parser.error("worker_build requires UNIT_ID X Y BUILD_TYPE")

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
    elif args.action == "move_unit":
        try:
            unit_id, target_x, target_y = (int(value) for value in args.values)
        except ValueError:
            parser.error("UNIT_ID, X, and Y must be integers")
        command_args = {"unit_id": unit_id, "x": target_x, "y": target_y}
    elif args.action == "worker_build":
        try:
            unit_id, source_x, source_y = (int(value) for value in args.values[:3])
        except ValueError:
            parser.error("UNIT_ID, X, and Y must be integers")
        command_args = {
            "unit_id": unit_id,
            "x": source_x,
            "y": source_y,
            "build_type": args.values[3],
        }

    command = Command(
        action=args.action,
        args=command_args,
    )
    if not args.direct and args.socket.exists():
        bridge_session_id: str | None = None
        try:
            session_response = request(
                {"op": "ping"},
                socket_path=args.socket,
                timeout=args.timeout,
            )
            if not session_response.get("ok"):
                raise ValueError(
                    str(session_response.get("error", "local bridge ping failed"))
                )
            bridge_session_id = validate_bridge_session_id(
                session_response.get("bridge_session_id")
            )
            response = request(
                {
                    "op": args.action,
                    "id": command.id,
                    "bridge_session_id": bridge_session_id,
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
            if (
                validate_bridge_session_id(response.get("bridge_session_id"))
                != bridge_session_id
            ):
                raise ValueError("local bridge session changed during command")
            if response.get("audit_error"):
                print(f"Command audit warning: {response['audit_error']}", file=sys.stderr)
            print(
                json.dumps(
                    {**result_data, "bridge_session_id": bridge_session_id},
                    sort_keys=True,
                )
            )
            return 0 if result_data.get("status") == "success" else 1
        except (ConnectionError, OSError, TimeoutError, ValueError) as error:
            result = CommandResult(id=command.id, status="error", message=str(error))
            output = asdict(result)
            if bridge_session_id is not None:
                output["bridge_session_id"] = bridge_session_id
            print(json.dumps(output, sort_keys=True))
            return 1

    bridge_session_id: str | None = None
    try:
        require_safe_tuner_session(args.host, args.port, socket_path=args.socket)
        with FireTunerClient(args.host, args.port, args.timeout) as client:
            handshake = client.handshake()
            state_id = _find_state(handshake.lua_states, "InGame")
            bridge_session_id = new_bridge_session_id()
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
            elif args.action == "skip_unit":
                result = execute_skip_unit(
                    client, state_id, command, verify_timeout=args.verify_timeout
                )
            elif args.action == "move_unit":
                result = execute_move_unit(
                    client, state_id, command, verify_timeout=args.verify_timeout
                )
            else:
                result = execute_worker_build(
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
        CommandAuditLog(args.audit_log).append(
            args.action,
            asdict(result),
            command.args,
            bridge_session_id=bridge_session_id,
        )
    except OSError as error:
        print(f"Command audit warning: {error}", file=sys.stderr)

    output = asdict(result)
    if bridge_session_id is not None:
        output["bridge_session_id"] = bridge_session_id
    print(json.dumps(output, sort_keys=True))
    return 0 if result.status == "success" else 1

if __name__ == "__main__":
    raise SystemExit(main())
