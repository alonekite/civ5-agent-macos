from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from .audit import CommandAuditLog, default_audit_path
from .command import (
    execute_choose_research,
    execute_city_production,
    execute_end_turn,
    execute_skip_unit,
)
from .ipc import LocalControlServer, default_socket_path
from .models import Command, GameState
from .preflight import UnsafeSessionError, require_safe_tuner_session
from .storage import UserDataStateReader, default_state_database
from .tuner import DEFAULT_HOST, DEFAULT_PORT, FireTunerClient, _find_state
from .validation import validate_live_state


def make_control_handler(
    client: FireTunerClient,
    state_id: int,
    connection_lock: threading.Lock,
    audit_log: CommandAuditLog | None = None,
    safety_check: Callable[[], None] | None = None,
):
    def handle_request(request: dict[str, object]) -> dict[str, object]:
        operation = request.get("op")
        if operation == "ping":
            return {"ok": True}
        if operation == "read_state":
            with connection_lock:
                state = validate_live_state(client.read_game_state(state_id))
            return {"ok": True, "state": asdict(state)}
        if operation in {
            "end_turn",
            "choose_research",
            "set_city_production",
            "skip_unit",
        }:
            if safety_check is not None:
                try:
                    safety_check()
                except UnsafeSessionError as error:
                    return {"ok": False, "error": f"unsafe FireTuner session: {error}"}
            command_id = request.get("id")
            if command_id is None:
                normalized_command_id = Command(str(operation)).id
            else:
                try:
                    parsed_command_id = UUID(str(command_id))
                except (ValueError, AttributeError):
                    return {"ok": False, "error": "command id must be a UUIDv4"}
                if (
                    not isinstance(command_id, str)
                    or parsed_command_id.version != 4
                    or str(parsed_command_id) != command_id
                ):
                    return {"ok": False, "error": "command id must be a UUIDv4"}
                normalized_command_id = command_id
            command = Command(
                action=str(operation),
                args=(
                    {"tech_type": request.get("tech_type")}
                    if operation == "choose_research"
                    else {"unit_id": request.get("unit_id")}
                    if operation == "skip_unit"
                    else {
                        "city_id": request.get("city_id"),
                        "kind": request.get("kind"),
                        "item_type": request.get("item_type"),
                    }
                    if operation == "set_city_production"
                    else {}
                ),
                id=normalized_command_id,
            )
            raw_verify_timeout = request.get("verify_timeout", 30.0)
            if isinstance(raw_verify_timeout, bool) or not isinstance(
                raw_verify_timeout, (int, float)
            ):
                return {"ok": False, "error": "verify_timeout must be numeric"}
            verify_timeout = float(raw_verify_timeout)
            if not 0 < verify_timeout <= 120:
                return {
                    "ok": False,
                    "error": "verify_timeout must be greater than 0 and at most 120",
                }
            with connection_lock:
                if operation == "end_turn":
                    result = execute_end_turn(
                        client,
                        state_id,
                        command,
                        verify_timeout=verify_timeout,
                    )
                elif operation == "choose_research":
                    result = execute_choose_research(
                        client,
                        state_id,
                        command,
                        verify_timeout=verify_timeout,
                    )
                elif operation == "set_city_production":
                    result = execute_city_production(
                        client,
                        state_id,
                        command,
                        verify_timeout=verify_timeout,
                    )
                else:
                    result = execute_skip_unit(
                        client,
                        state_id,
                        command,
                        verify_timeout=verify_timeout,
                    )
            result_data = asdict(result)
            response: dict[str, object] = {"ok": True, "result": result_data}
            if audit_log is not None:
                try:
                    audit_log.append(str(operation), result_data, command.args)
                except OSError as error:
                    response["audit_error"] = str(error)
                    print(f"Command audit warning: {error}", file=sys.stderr, flush=True)
            return response
        return {"ok": False, "error": f"unsupported operation: {operation!r}"}

    return handle_request


def _watch_database(args: argparse.Namespace) -> int:
    reader = UserDataStateReader(args.database)
    previous = None
    waiting_reported = False

    while True:
        try:
            state = reader.read_state()
        except (FileNotFoundError, sqlite3.Error) as error:
            if args.once:
                print(f"State unavailable: {error}", file=sys.stderr)
                return 1
            if not waiting_reported:
                print(f"Waiting for Civ V state database: {args.database}", file=sys.stderr)
                waiting_reported = True
            time.sleep(args.interval)
            continue

        waiting_reported = False
        if state != previous:
            _print_state(state)
            previous = state
        if args.once:
            return 0
        time.sleep(args.interval)


def _watch_tuner(args: argparse.Namespace) -> int:
    previous = None
    waiting_reported = False
    audit_log = CommandAuditLog(args.audit_log)
    try:
        audit_log.ensure_ready()
    except OSError as error:
        print(f"Command audit unavailable: {error}", file=sys.stderr)
        return 1

    while True:
        try:
            require_safe_tuner_session(args.host, args.port, socket_path=args.socket)
            with FireTunerClient(args.host, args.port, args.timeout) as client:
                handshake = client.handshake()
                state_id = _find_state(handshake.lua_states, "InGame")
                waiting_reported = False
                connection_lock = threading.Lock()
                handler = make_control_handler(
                    client,
                    state_id,
                    connection_lock,
                    audit_log,
                    safety_check=lambda: require_safe_tuner_session(
                        args.host,
                        args.port,
                        socket_path=args.socket,
                    ),
                )

                with LocalControlServer(handler, args.socket):
                    while True:
                        try:
                            with connection_lock:
                                state = validate_live_state(client.read_game_state(state_id))
                        except ValueError as error:
                            if args.once:
                                print(f"State unavailable: {error}", file=sys.stderr)
                                return 1
                            if not waiting_reported:
                                print(
                                    f"Waiting for an active Civ V match: {error}",
                                    file=sys.stderr,
                                    flush=True,
                                )
                                waiting_reported = True
                            time.sleep(args.interval)
                            continue
                        waiting_reported = False
                        if state != previous:
                            _print_state(state)
                            previous = state
                        if args.once:
                            return 0
                        time.sleep(args.interval)
        except UnsafeSessionError as error:
            print(f"Unsafe FireTuner session: {error}", file=sys.stderr, flush=True)
            return 1
        except (ConnectionError, OSError, RuntimeError, TimeoutError, ValueError) as error:
            if args.once:
                print(f"State unavailable: {error}", file=sys.stderr)
                return 1
            if not waiting_reported:
                print(f"Waiting for Civ V FireTuner: {error}", file=sys.stderr, flush=True)
                waiting_reported = True
            time.sleep(args.interval)


def _print_state(state: GameState) -> None:
    print(json.dumps(asdict(state), sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch live state from Civilization V")
    parser.add_argument("--transport", choices=["tuner", "database"], default="tuner")
    parser.add_argument("--database", type=Path, default=default_state_database())
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--socket", type=Path, default=default_socket_path())
    parser.add_argument("--audit-log", type=Path, default=default_audit_path())
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    try:
        if args.transport == "database":
            return _watch_database(args)
        return _watch_tuner(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
