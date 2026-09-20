from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from .audit import CommandAuditLog, default_audit_path
from .actions import CommandValidationError
from .command import (
    execute_choose_research,
    execute_city_production,
    execute_end_turn,
    execute_move_unit,
    execute_skip_unit,
    execute_worker_build,
)
from .identity import (
    SessionIdentityError,
    new_bridge_session_id,
    validate_bridge_session_id,
    validate_command_id,
)
from .ipc import LocalControlServer, default_socket_path
from .journal import JournalCapture, JournalError
from .models import Command, GameState, model_to_dict as asdict
from .preflight import UnsafeSessionError, require_safe_tuner_session
from .storage import UserDataStateReader, default_state_database
from .tuner import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    FireTunerClient,
    SnapshotStreamDesynchronizedError,
    _find_state,
)
from .validation import validate_live_state


def make_control_handler(
    client: FireTunerClient,
    state_id: int,
    connection_lock: threading.Lock,
    audit_log: CommandAuditLog | None = None,
    safety_check: Callable[[], None] | None = None,
    bridge_session_id: str | None = None,
    journal_capture: JournalCapture | None = None,
    read_only: bool = False,
):
    session_id = validate_bridge_session_id(
        bridge_session_id if bridge_session_id is not None else new_bridge_session_id()
    )
    completed_commands: dict[
        str,
        tuple[str, dict[str, object], dict[str, object]],
    ] = {}
    uncertain_commands: dict[
        str,
        tuple[str, dict[str, object], dict[str, object]],
    ] = {}

    def handle_request(request: dict[str, object]) -> dict[str, object]:
        operation = request.get("op")
        if operation == "ping":
            return {
                "ok": True,
                "bridge_session_id": session_id,
                "read_only": read_only,
            }
        if operation == "read_state":
            with connection_lock:
                state = validate_live_state(client.read_game_state(state_id))
            return {
                "ok": True,
                "bridge_session_id": session_id,
                "state": asdict(state),
            }
        if read_only:
            return {
                "ok": False,
                "error": "watcher is read-only; operation is not permitted",
            }
        if operation == "command_status":
            try:
                requested_session_id = validate_bridge_session_id(
                    request.get("bridge_session_id")
                )
                command_id = validate_command_id(request.get("command_id"))
            except SessionIdentityError as error:
                return {"ok": False, "error": str(error)}
            if requested_session_id != session_id:
                return {
                    "ok": False,
                    "error": "bridge session changed; command outcome is unavailable",
                }
            with connection_lock:
                completed = completed_commands.get(command_id)
                if completed is None:
                    return {
                        "ok": True,
                        "bridge_session_id": session_id,
                        "found": False,
                    }
                previous_operation, previous_arguments, previous_response = completed
                return {
                    "ok": True,
                    "bridge_session_id": session_id,
                    "found": True,
                    "action": previous_operation,
                    "arguments": dict(previous_arguments),
                    "result": previous_response["result"],
                }
        if operation in {
            "end_turn",
            "choose_research",
            "set_city_production",
            "skip_unit",
            "move_unit",
            "worker_build",
        }:
            try:
                requested_session_id = validate_bridge_session_id(
                    request.get("bridge_session_id")
                )
            except SessionIdentityError as error:
                return {"ok": False, "error": str(error)}
            if requested_session_id != session_id:
                return {
                    "ok": False,
                    "error": "bridge session changed; read fresh state before writing",
                }
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
                        "unit_id": request.get("unit_id"),
                        "x": request.get("x"),
                        "y": request.get("y"),
                    }
                    if operation == "move_unit"
                    else {
                        "unit_id": request.get("unit_id"),
                        "x": request.get("x"),
                        "y": request.get("y"),
                        "build_type": request.get("build_type"),
                    }
                    if operation == "worker_build"
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
                completed = completed_commands.get(command.id)
                if completed is not None:
                    previous_operation, previous_arguments, previous_response = completed
                    if (
                        previous_operation != command.action
                        or previous_arguments != command.args
                    ):
                        return {
                            "ok": False,
                            "error": (
                                "command id was already used with different arguments"
                            ),
                        }
                    return {**previous_response, "replayed": True}
                uncertain = uncertain_commands.get(command.id)
                if uncertain is not None:
                    previous_operation, previous_arguments, previous_response = uncertain
                    if (
                        previous_operation != command.action
                        or previous_arguments != command.args
                    ):
                        return {
                            "ok": False,
                            "error": (
                                "command id was already used with different arguments"
                            ),
                        }
                    return {**previous_response, "replayed": True}
                journal_errors: list[str] = []
                submission_turn: int | None = None
                if journal_capture is not None:
                    try:
                        submission_state = validate_live_state(
                            client.read_game_state(state_id)
                        )
                        submission_turn = submission_state.turn
                        journal_capture.record_command_submitted(
                            str(operation),
                            command.args,
                            command.id,
                            submission_state.turn,
                        )
                    except (JournalError, OSError, ValueError) as error:
                        journal_errors.append(str(error))
                        print(
                            f"Turn journal warning: {error}",
                            file=sys.stderr,
                            flush=True,
                        )
                try:
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
                    elif operation == "skip_unit":
                        result = execute_skip_unit(
                            client,
                            state_id,
                            command,
                            verify_timeout=verify_timeout,
                        )
                    elif operation == "move_unit":
                        result = execute_move_unit(
                            client,
                            state_id,
                            command,
                            verify_timeout=verify_timeout,
                        )
                    else:
                        result = execute_worker_build(
                            client,
                            state_id,
                            command,
                            verify_timeout=verify_timeout,
                        )
                except CommandValidationError as error:
                    return {
                        "ok": False,
                        "bridge_session_id": session_id,
                        "error": str(error),
                    }
                except (ConnectionError, OSError, TimeoutError, ValueError) as error:
                    if journal_capture is not None and submission_turn is not None:
                        try:
                            journal_capture.record_command_outcome_unknown(
                                str(operation),
                                command.id,
                                submission_turn,
                                str(error),
                            )
                        except (JournalError, OSError, ValueError) as journal_error:
                            journal_errors.append(str(journal_error))
                            print(
                                f"Turn journal warning: {journal_error}",
                                file=sys.stderr,
                                flush=True,
                            )
                    response = {
                        "ok": False,
                        "bridge_session_id": session_id,
                        "outcome_unknown": True,
                        "error": str(error),
                    }
                    if journal_errors:
                        response["journal_error"] = "; ".join(journal_errors)
                    uncertain_commands[command.id] = (
                        command.action,
                        dict(command.args),
                        dict(response),
                    )
                    return response
                result_data = asdict(result)
                response: dict[str, object] = {
                    "ok": True,
                    "bridge_session_id": session_id,
                    "result": result_data,
                }
                if audit_log is not None:
                    try:
                        audit_log.append(
                            str(operation),
                            result_data,
                            command.args,
                            bridge_session_id=session_id,
                        )
                    except OSError as error:
                        response["audit_error"] = str(error)
                        print(
                            f"Command audit warning: {error}",
                            file=sys.stderr,
                            flush=True,
                        )
                if journal_capture is not None:
                    try:
                        journal_capture.record_command_result(
                            str(operation),
                            command.args,
                            result_data,
                        )
                    except (JournalError, OSError, ValueError) as error:
                        journal_errors.append(str(error))
                        print(
                            f"Turn journal warning: {error}",
                            file=sys.stderr,
                            flush=True,
                        )
                if journal_errors:
                    response["journal_error"] = "; ".join(journal_errors)
                completed_commands[command.id] = (
                    command.action,
                    dict(command.args),
                    dict(response),
                )
                return response
        return {"ok": False, "error": f"unsupported operation: {operation!r}"}

    return handle_request


def _watch_database(args: argparse.Namespace) -> int:
    reader = UserDataStateReader(args.database)
    bridge_session_id = new_bridge_session_id()
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
            _print_state(state, bridge_session_id)
            previous = state
        if args.once:
            return 0
        time.sleep(args.interval)


def _watch_tuner(args: argparse.Namespace) -> int:
    previous = None
    waiting_reported = False
    audit_log = CommandAuditLog(args.audit_log)
    journal_capture: JournalCapture | None = None
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
                bridge_session_id = new_bridge_session_id()
                if journal_capture is not None:
                    print(
                        "Turn journal requires explicit --journal-mode resume after reconnect",
                        file=sys.stderr,
                    )
                    return 1
                journal_capture = _start_journal(args, bridge_session_id)
                if args.journal is not None and journal_capture is None:
                    return 1
                previous = None
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
                    bridge_session_id=bridge_session_id,
                    journal_capture=journal_capture,
                    read_only=args.read_only,
                )

                with LocalControlServer(handler, args.socket):
                    while True:
                        try:
                            with connection_lock:
                                state = validate_live_state(client.read_game_state(state_id))
                        except SnapshotStreamDesynchronizedError:
                            # This connection can no longer attribute split
                            # snapshot output to the command that produced it.
                            # Reconnect and issue a new bridge-session identity
                            # instead of reusing corrupted response framing.
                            raise
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
                            if journal_capture is not None:
                                try:
                                    journal_capture.record_snapshot(
                                        state,
                                        previous_turn=(
                                            previous.turn if previous is not None else None
                                        ),
                                    )
                                except (JournalError, OSError, ValueError) as error:
                                    print(
                                        f"Turn journal unavailable: {error}",
                                        file=sys.stderr,
                                        flush=True,
                                    )
                                    return 1
                            _print_state(state, bridge_session_id)
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


def _print_state(state: GameState, bridge_session_id: str) -> None:
    print(
        json.dumps(
            {"bridge_session_id": bridge_session_id, "state": asdict(state)},
            sort_keys=True,
        ),
        flush=True,
    )


def _start_journal(
    args: argparse.Namespace,
    bridge_session_id: str,
) -> JournalCapture | None:
    if args.journal is None:
        return None
    try:
        return JournalCapture.start(
            args.journal,
            bridge_session_id,
            args.journal_mode,
        )
    except (JournalError, OSError, ValueError) as error:
        print(f"Turn journal unavailable: {error}", file=sys.stderr, flush=True)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch live state from Civilization V")
    parser.add_argument("--transport", choices=["tuner", "database"], default="tuner")
    parser.add_argument("--database", type=Path, default=default_state_database())
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--socket", type=Path, default=default_socket_path())
    parser.add_argument("--audit-log", type=Path, default=default_audit_path())
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--journal-mode", choices=["new", "resume"])
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="server-enforced mode admitting only ping and state reads",
    )
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    if (args.journal is None) != (args.journal_mode is None):
        parser.error("--journal and --journal-mode must be provided together")

    if args.transport == "database" and args.journal is not None:
        parser.error("--journal requires --transport tuner")

    if args.transport == "database" and args.read_only:
        parser.error("--read-only requires --transport tuner")

    if args.read_only and args.journal is not None:
        parser.error("--read-only cannot capture a journal")

    try:
        if args.transport == "database":
            return _watch_database(args)
        return _watch_tuner(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
