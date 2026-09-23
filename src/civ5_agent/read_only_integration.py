"""Provisional process-boundary helpers for external read-only supervision."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Sequence

from .checkpoint_authorization import (
    CHECKPOINT_STEPS,
    authorize_checkpoint_challenge,
    create_checkpoint_challenge,
    parse_checkpoint_time,
)
from .play_session_grant import (
    create_play_session_grant,
    consume_play_session_grant,
)
from .errors import ProtocolError, TransportError
from .identity import validate_bridge_session_id
from .ipc import default_socket_path, request
from .watcher_client import WatcherBridgeClient

READ_ONLY_INTEGRATION_VERSION = 1
AUTOMATION_FRAMEWORK_RELEASE_TAG = "v0.1.0"
AUTOMATION_FRAMEWORK_TAG_COMMIT = "bf71fb072d9111d8cc4bbab24c50fc670fc2239c"
AUTOMATION_FRAMEWORK_WHEEL_NAME = "local_app_test_automation-0.1.0-py3-none-any.whl"
AUTOMATION_FRAMEWORK_WHEEL_SHA256 = (
    "6c0040ec2e4911c80b318687ad0fd53511972b517ca21dfbb5d0a3cd4af34eb3"
)
AUTOMATION_FRAMEWORK_SESSION_SPEC_VERSION = 1
AUTOMATION_FRAMEWORK_V2_CANDIDATE_COMMIT = (
    "3402862a43e9c29e056a42ecb75d90a04222684b"
)
AUTOMATION_FRAMEWORK_V2_CANDIDATE_WHEEL_NAME = (
    "local_app_test_automation-0.2.0.dev0-py3-none-any.whl"
)
AUTOMATION_FRAMEWORK_V2_CANDIDATE_WHEEL_SHA256 = (
    "285251f0cabbcd98bfbb8c0a709aab5ba630192ea1d86706e72de9e2a77ab9a6"
)
AUTOMATION_FRAMEWORK_V2_CANDIDATE_SESSION_SPEC_VERSION = 2
CIV5_APP_BUNDLE_ID = "com.aspyr.civ5campaign"
CIV5_APP_BUNDLE_PATH = Path("/Applications/Civilization V Campaign Edition.app")
CIV5_GAME_EXECUTABLE_PATH = Path(
    "/Applications/Civilization V Campaign Edition.app/Contents/MacOS/"
    "Civilization V Campaign Edition"
)
CIV5_WINDOW_TITLE = "Civilization V: Campaign Edition"
CIV5_LAUNCHER_BUTTON_ROLE = "AXButton"
CIV5_LAUNCHER_BUTTON_TITLE = "PLAY"
CIV5_MANUAL_GAME_ENTRY_GATE_ID = "manual_game_entry"
_BUNDLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,254}$")


class ReadOnlyIntegrationError(RuntimeError):
    """A bounded, safe failure at the external read-only boundary."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def read_sanitized_summary(
    socket_path: Path,
    *,
    request_timeout: float = 3.0,
    wait_timeout: float = 30.0,
    poll_interval: float = 0.1,
    require_active_match: bool = False,
) -> dict[str, object]:
    """Require a read-only watcher and return a non-identifying state summary."""
    if request_timeout <= 0:
        raise ValueError("request_timeout must be greater than zero")
    if wait_timeout <= 0:
        raise ValueError("wait_timeout must be greater than zero")
    if poll_interval <= 0:
        raise ValueError("poll_interval must be greater than zero")
    if not PurePosixPath(str(socket_path)).is_absolute():
        raise ValueError("socket path must be absolute")

    deadline = time.monotonic() + wait_timeout
    while True:
        try:
            ping = request(
                {"op": "ping"},
                socket_path=socket_path,
                timeout=request_timeout,
            )
            break
        except (ConnectionError, OSError, TimeoutError):
            if time.monotonic() >= deadline:
                raise ReadOnlyIntegrationError(
                    "watcher_unavailable",
                    "read-only watcher did not become available before the deadline",
                ) from None
            time.sleep(min(poll_interval, max(deadline - time.monotonic(), 0)))
        except ValueError as error:
            raise ReadOnlyIntegrationError(
                "protocol_error",
                "watcher returned an invalid capability response",
            ) from error

    if ping.get("ok") is not True:
        raise ReadOnlyIntegrationError("protocol_error", "watcher rejected the capability probe")
    if ping.get("read_only") is not True:
        raise ReadOnlyIntegrationError(
            "write_capability_exposed",
            "watcher is not in server-enforced read-only mode",
        )
    try:
        ping_session = validate_bridge_session_id(ping.get("bridge_session_id"))
        state_session, state = WatcherBridgeClient(
            socket_path=socket_path,
            timeout=request_timeout,
        ).read_state()
    except (ProtocolError, TransportError, ValueError) as error:
        raise ReadOnlyIntegrationError(
            "state_unavailable",
            "watcher did not return one valid state",
        ) from error
    if state_session != ping_session:
        raise ReadOnlyIntegrationError(
            "session_changed",
            "watcher session changed between capability and state reads",
        )
    if require_active_match and state.turn_active is not True:
        raise ReadOnlyIntegrationError(
            "active_match_unavailable",
            "watcher did not observe an active player turn",
        )

    return {
        "capability": "civ5-read-only-state-summary",
        "capability_version": READ_ONLY_INTEGRATION_VERSION,
        "can_end_turn": state.can_end_turn,
        "city_count": len(state.cities),
        "ok": True,
        "read_only": True,
        "research_selected": state.research is not None,
        "schema_version": state.schema_version,
        "turn": state.turn,
        "turn_active": state.turn_active,
        "unit_count": len(state.units),
    }


def build_session_spec(
    *,
    label: str,
    app_bundle_id: str | None,
    app_bundle_path: Path | None,
    existing_instance_policy: str,
    leave_open_on_success: bool,
    watcher_executable: Path,
    cwd: Path,
    socket_path: Path,
    audit_log: Path,
    session_timeout_ms: int,
) -> dict[str, object]:
    """Build framework SessionSpec v1 JSON without importing the framework."""
    if not label or len(label) > 128:
        raise ValueError("label must contain 1..128 characters")
    if (app_bundle_id is None) == (app_bundle_path is None):
        raise ValueError("exactly one app identity must be provided")
    if app_bundle_id is not None and not _BUNDLE_ID.fullmatch(app_bundle_id):
        raise ValueError("app bundle identifier is invalid")
    if app_bundle_path is not None and not PurePosixPath(
        str(app_bundle_path)
    ).is_absolute():
        raise ValueError("app bundle path must be absolute")
    if existing_instance_policy not in {"reject", "observe_verified"}:
        raise ValueError("existing instance policy is invalid")
    for name, path in (
        ("watcher executable", watcher_executable),
        ("working directory", cwd),
        ("socket", socket_path),
        ("audit log", audit_log),
    ):
        if not PurePosixPath(str(path)).is_absolute():
            raise ValueError(f"{name} must be absolute")
    if not 1_000 <= session_timeout_ms <= 86_400_000:
        raise ValueError("session timeout must be in 1000..86400000 milliseconds")

    app: dict[str, object] = {
        "existing_instance_policy": existing_instance_policy,
        "graceful_quit_timeout_ms": 10_000,
        "launch_arguments": [],
        "launch_timeout_ms": 30_000,
        "leave_open_on_success": leave_open_on_success,
    }
    if app_bundle_id is not None:
        app["bundle_id"] = app_bundle_id
    else:
        app["bundle_path"] = str(app_bundle_path)

    return {
        "app": app,
        "label": label,
        "processes": [
            {
                "argv": [
                    str(watcher_executable),
                    "--read-only",
                    "--socket",
                    str(socket_path),
                    "--audit-log",
                    str(audit_log),
                ],
                "cwd": str(cwd),
                "environment": {
                    "allow": [],
                    "inherit": "none",
                    "secret_names": [],
                    "set": {},
                },
                "graceful_stop_timeout_ms": 10_000,
                "idle_timeout_ms": session_timeout_ms,
                "io_mode": "pipes",
                "max_output_bytes": 4 * 1024 * 1024,
                "process_id": "civ5_read_only_watcher",
                "retain_raw_output": False,
                "run_timeout_ms": session_timeout_ms,
                "start_timeout_ms": 10_000,
                "stop_signal": "SIGINT",
            }
        ],
        "session_timeout_ms": session_timeout_ms,
        "spec_version": AUTOMATION_FRAMEWORK_SESSION_SPEC_VERSION,
    }


def build_ui_session_spec(
    *,
    label: str,
    app_bundle_id: str | None,
    app_bundle_path: Path | None,
    existing_instance_policy: str,
    leave_open_on_success: bool,
    watcher_executable: Path,
    cwd: Path,
    socket_path: Path,
    audit_log: Path,
    session_timeout_ms: int,
    continue_x_ratio: float,
    continue_y_ratio: float,
    expected_game_executable_path: Path,
    ui_timeout_ms: int = 300_000,
    authorization_timeout_ms: int = 300_000,
    identity_handoff_timeout_ms: int = 300_000,
) -> dict[str, object]:
    """Build a private candidate SessionSpec v2 for the two verified UI gates."""
    if app_bundle_id is not None and app_bundle_id != CIV5_APP_BUNDLE_ID:
        raise ValueError("UI session app bundle identifier is not the verified Civ V bundle")
    if app_bundle_path is not None and app_bundle_path != CIV5_APP_BUNDLE_PATH:
        raise ValueError("UI session app bundle path is not the verified Civ V bundle")
    if expected_game_executable_path != CIV5_GAME_EXECUTABLE_PATH:
        raise ValueError(
            "UI session successor executable is not the verified Civ V game executable"
        )
    for name, value in (
        ("continue x ratio", continue_x_ratio),
        ("continue y ratio", continue_y_ratio),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number")
        if not math.isfinite(value) or not 0 < value < 1:
            raise ValueError(f"{name} must be finite and strictly between zero and one")
    for name, value in (
        ("UI timeout", ui_timeout_ms),
        ("authorization timeout", authorization_timeout_ms),
        ("identity handoff timeout", identity_handoff_timeout_ms),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        if not 1 <= value <= 300_000:
            raise ValueError(f"{name} must be in 1..300000 milliseconds")

    spec = build_session_spec(
        label=label,
        app_bundle_id=app_bundle_id,
        app_bundle_path=app_bundle_path,
        existing_instance_policy=existing_instance_policy,
        leave_open_on_success=leave_open_on_success,
        watcher_executable=watcher_executable,
        cwd=cwd,
        socket_path=socket_path,
        audit_log=audit_log,
        session_timeout_ms=session_timeout_ms,
    )
    spec["spec_version"] = AUTOMATION_FRAMEWORK_V2_CANDIDATE_SESSION_SPEC_VERSION
    spec["ui_steps"] = [
        _play_ui_step(
            expected_game_executable_path=expected_game_executable_path,
            ui_timeout_ms=ui_timeout_ms,
            authorization_timeout_ms=authorization_timeout_ms,
            identity_handoff_timeout_ms=identity_handoff_timeout_ms,
        ),
        {
            "step_id": "click_game_continue",
            "target": {
                "bundle_id": CIV5_APP_BUNDLE_ID,
                "window_title": CIV5_WINDOW_TITLE,
            },
            "action": {
                "kind": "window_relative_click",
                "x_ratio": float(continue_x_ratio),
                "y_ratio": float(continue_y_ratio),
            },
            "timeout_ms": ui_timeout_ms,
            "authorization_timeout_ms": authorization_timeout_ms,
        },
    ]
    return spec


def _play_ui_step(
    *,
    expected_game_executable_path: Path,
    ui_timeout_ms: int,
    authorization_timeout_ms: int,
    identity_handoff_timeout_ms: int,
) -> dict[str, object]:
    return {
        "step_id": "press_launcher_play",
        "target": {
            "bundle_id": CIV5_APP_BUNDLE_ID,
            "window_title": CIV5_WINDOW_TITLE,
        },
        "action": {
            "kind": "accessibility_press",
            "role": CIV5_LAUNCHER_BUTTON_ROLE,
            "title": CIV5_LAUNCHER_BUTTON_TITLE,
        },
        "timeout_ms": ui_timeout_ms,
        "authorization_timeout_ms": authorization_timeout_ms,
        "identity_handoff": {
            "kind": "same_process_executable",
            "expected_executable_path": str(expected_game_executable_path),
            "timeout_ms": identity_handoff_timeout_ms,
        },
    }


def build_manual_ui_session_spec(
    *,
    label: str,
    app_bundle_id: str | None,
    app_bundle_path: Path | None,
    existing_instance_policy: str,
    leave_open_on_success: bool,
    watcher_executable: Path,
    cwd: Path,
    socket_path: Path,
    audit_log: Path,
    session_timeout_ms: int,
    expected_game_executable_path: Path,
    manual_confirmation_timeout_ms: int = 1_200_000,
    ui_timeout_ms: int = 300_000,
    authorization_timeout_ms: int = 300_000,
    identity_handoff_timeout_ms: int = 300_000,
) -> dict[str, object]:
    """Build an offline candidate: one exact PLAY, then a human-only game gate."""
    if app_bundle_id is not None and app_bundle_id != CIV5_APP_BUNDLE_ID:
        raise ValueError("UI session app bundle identifier is not the verified Civ V bundle")
    if app_bundle_path is not None and app_bundle_path != CIV5_APP_BUNDLE_PATH:
        raise ValueError("UI session app bundle path is not the verified Civ V bundle")
    if expected_game_executable_path != CIV5_GAME_EXECUTABLE_PATH:
        raise ValueError("UI session successor executable is not the verified Civ V game executable")
    for name, value, maximum in (
        ("manual confirmation timeout", manual_confirmation_timeout_ms, 3_600_000),
        ("UI timeout", ui_timeout_ms, 300_000),
        ("authorization timeout", authorization_timeout_ms, 300_000),
        ("identity handoff timeout", identity_handoff_timeout_ms, 300_000),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError(f"{name} must be an integer in 1..{maximum} milliseconds")
    if (
        ui_timeout_ms + identity_handoff_timeout_ms + manual_confirmation_timeout_ms
        >= session_timeout_ms
    ):
        raise ValueError("session timeout must exceed UI, handoff, and manual-gate bounds")
    spec = build_session_spec(
        label=label,
        app_bundle_id=app_bundle_id,
        app_bundle_path=app_bundle_path,
        existing_instance_policy=existing_instance_policy,
        leave_open_on_success=leave_open_on_success,
        watcher_executable=watcher_executable,
        cwd=cwd,
        socket_path=socket_path,
        audit_log=audit_log,
        session_timeout_ms=session_timeout_ms,
    )
    spec["spec_version"] = AUTOMATION_FRAMEWORK_V2_CANDIDATE_SESSION_SPEC_VERSION
    spec["ui_steps"] = [
        _play_ui_step(
            expected_game_executable_path=expected_game_executable_path,
            ui_timeout_ms=ui_timeout_ms,
            authorization_timeout_ms=authorization_timeout_ms,
            identity_handoff_timeout_ms=identity_handoff_timeout_ms,
        )
    ]
    spec["manual_gates"] = [
        {
            "gate_id": CIV5_MANUAL_GAME_ENTRY_GATE_ID,
            "confirmation_timeout_ms": manual_confirmation_timeout_ms,
        }
    ]
    return spec


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="civ5-read-only",
        description="Read-only watcher integration for an external composition root",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="emit one sanitized watcher summary")
    probe.add_argument("--socket", type=Path, default=default_socket_path())
    probe.add_argument("--request-timeout", type=float, default=3.0)
    probe.add_argument("--wait-timeout", type=float, default=30.0)
    probe.add_argument("--require-active-match", action="store_true")

    spec = subparsers.add_parser("session-spec", help="emit external SessionSpec v1 JSON")
    spec.add_argument("--label", default="civ5-read-only-session")
    identity = spec.add_mutually_exclusive_group(required=True)
    identity.add_argument("--app-bundle-id")
    identity.add_argument("--app-bundle-path", type=Path)
    spec.add_argument(
        "--existing-instance-policy",
        choices=["reject", "observe_verified"],
        default="reject",
    )
    spec.add_argument("--leave-open-on-success", action="store_true")
    spec.add_argument("--watcher-executable", required=True, type=Path)
    spec.add_argument("--cwd", required=True, type=Path)
    spec.add_argument("--socket", required=True, type=Path)
    spec.add_argument("--audit-log", required=True, type=Path)
    spec.add_argument("--session-timeout-ms", type=int, default=900_000)

    ui_spec = subparsers.add_parser(
        "ui-session-spec",
        help="emit candidate external SessionSpec v2 JSON with two UI checkpoints",
    )
    ui_spec.add_argument("--label", default="civ5-read-only-ui-session")
    ui_identity = ui_spec.add_mutually_exclusive_group(required=True)
    ui_identity.add_argument("--app-bundle-id")
    ui_identity.add_argument("--app-bundle-path", type=Path)
    ui_spec.add_argument(
        "--existing-instance-policy",
        choices=["reject", "observe_verified"],
        default="reject",
    )
    ui_spec.add_argument("--leave-open-on-success", action="store_true")
    ui_spec.add_argument("--watcher-executable", required=True, type=Path)
    ui_spec.add_argument("--cwd", required=True, type=Path)
    ui_spec.add_argument("--socket", required=True, type=Path)
    ui_spec.add_argument("--audit-log", required=True, type=Path)
    ui_spec.add_argument("--session-timeout-ms", type=int, default=900_000)
    ui_spec.add_argument("--continue-x-ratio", required=True, type=float)
    ui_spec.add_argument("--continue-y-ratio", required=True, type=float)
    ui_spec.add_argument("--expected-game-executable", required=True, type=Path)
    ui_spec.add_argument("--ui-timeout-ms", type=int, default=300_000)
    ui_spec.add_argument("--authorization-timeout-ms", type=int, default=300_000)
    ui_spec.add_argument("--identity-handoff-timeout-ms", type=int, default=300_000)

    manual_spec = subparsers.add_parser(
        "manual-ui-session-spec",
        help="emit offline candidate v2 PLAY plus manual game-entry gate",
    )
    manual_spec.add_argument("--label", default="civ5-read-only-manual-ui-session")
    manual_identity = manual_spec.add_mutually_exclusive_group(required=True)
    manual_identity.add_argument("--app-bundle-id")
    manual_identity.add_argument("--app-bundle-path", type=Path)
    manual_spec.add_argument(
        "--existing-instance-policy",
        choices=["reject", "observe_verified"],
        default="reject",
    )
    manual_spec.add_argument("--leave-open-on-success", action="store_true")
    manual_spec.add_argument("--watcher-executable", required=True, type=Path)
    manual_spec.add_argument("--cwd", required=True, type=Path)
    manual_spec.add_argument("--socket", required=True, type=Path)
    manual_spec.add_argument("--audit-log", required=True, type=Path)
    manual_spec.add_argument("--session-timeout-ms", type=int, default=3_600_000)
    manual_spec.add_argument("--expected-game-executable", required=True, type=Path)
    manual_spec.add_argument(
        "--manual-confirmation-timeout-ms", type=int, default=1_200_000
    )
    manual_spec.add_argument("--ui-timeout-ms", type=int, default=300_000)
    manual_spec.add_argument("--authorization-timeout-ms", type=int, default=300_000)
    manual_spec.add_argument("--identity-handoff-timeout-ms", type=int, default=300_000)

    challenge = subparsers.add_parser(
        "checkpoint-challenge",
        help="create a private fresh operator-presence challenge",
    )
    challenge.add_argument("--file", required=True, type=Path)
    challenge.add_argument("--checkpoint-id", required=True)
    challenge.add_argument("--step-id", required=True, choices=sorted(CHECKPOINT_STEPS))
    challenge.add_argument("--task-id", required=True)
    challenge.add_argument(
        "--checkpoint-requested-at", required=True, type=parse_checkpoint_time
    )

    authorize = subparsers.add_parser(
        "checkpoint-authorize",
        help="validate and consume one exact operator-presence challenge",
    )
    authorize.add_argument("--file", required=True, type=Path)
    authorize.add_argument("--checkpoint-id", required=True)
    authorize.add_argument("--step-id", required=True, choices=sorted(CHECKPOINT_STEPS))
    authorize.add_argument("--task-id", required=True)
    authorize.add_argument("--response", required=True)
    authorize.add_argument("--max-age-seconds", type=int, default=300)

    play_grant = subparsers.add_parser(
        "play-grant-create",
        help="create one private PLAY grant from this task's exact session initiation",
    )
    play_grant.add_argument("--file", required=True, type=Path)
    play_grant.add_argument("--framework-session-id", required=True)
    play_grant.add_argument("--checkpoint-id", required=True)
    play_grant.add_argument("--spec-sha256", required=True)
    play_grant.add_argument("--task-id", required=True)
    play_grant.add_argument("--initiation-text", required=True)
    play_grant.add_argument("--initiated-at", required=True, type=parse_checkpoint_time)
    play_grant.add_argument(
        "--checkpoint-requested-at", required=True, type=parse_checkpoint_time
    )
    play_grant.add_argument(
        "--checkpoint-expires-at", required=True, type=parse_checkpoint_time
    )

    play_consume = subparsers.add_parser(
        "play-grant-consume",
        help="consume one exact session/spec/checkpoint PLAY grant before pass",
    )
    play_consume.add_argument("--file", required=True, type=Path)
    play_consume.add_argument("--framework-session-id", required=True)
    play_consume.add_argument("--checkpoint-id", required=True)
    play_consume.add_argument("--spec-sha256", required=True)
    play_consume.add_argument("--task-id", required=True)
    return parser


def _emit(value: object) -> None:
    print(json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            _emit(
                read_sanitized_summary(
                    args.socket,
                    request_timeout=args.request_timeout,
                    wait_timeout=args.wait_timeout,
                    require_active_match=args.require_active_match,
                )
            )
            return 0
        if args.command == "session-spec":
            _emit(
                build_session_spec(
                    label=args.label,
                    app_bundle_id=args.app_bundle_id,
                    app_bundle_path=args.app_bundle_path,
                    existing_instance_policy=args.existing_instance_policy,
                    leave_open_on_success=args.leave_open_on_success,
                    watcher_executable=args.watcher_executable,
                    cwd=args.cwd,
                    socket_path=args.socket,
                    audit_log=args.audit_log,
                    session_timeout_ms=args.session_timeout_ms,
                )
            )
            return 0
        if args.command == "ui-session-spec":
            _emit(
                build_ui_session_spec(
                    label=args.label,
                    app_bundle_id=args.app_bundle_id,
                    app_bundle_path=args.app_bundle_path,
                    existing_instance_policy=args.existing_instance_policy,
                    leave_open_on_success=args.leave_open_on_success,
                    watcher_executable=args.watcher_executable,
                    cwd=args.cwd,
                    socket_path=args.socket,
                    audit_log=args.audit_log,
                    session_timeout_ms=args.session_timeout_ms,
                    continue_x_ratio=args.continue_x_ratio,
                    continue_y_ratio=args.continue_y_ratio,
                    expected_game_executable_path=args.expected_game_executable,
                    ui_timeout_ms=args.ui_timeout_ms,
                    authorization_timeout_ms=args.authorization_timeout_ms,
                    identity_handoff_timeout_ms=args.identity_handoff_timeout_ms,
                )
            )
            return 0
        if args.command == "manual-ui-session-spec":
            _emit(
                build_manual_ui_session_spec(
                    label=args.label,
                    app_bundle_id=args.app_bundle_id,
                    app_bundle_path=args.app_bundle_path,
                    existing_instance_policy=args.existing_instance_policy,
                    leave_open_on_success=args.leave_open_on_success,
                    watcher_executable=args.watcher_executable,
                    cwd=args.cwd,
                    socket_path=args.socket,
                    audit_log=args.audit_log,
                    session_timeout_ms=args.session_timeout_ms,
                    expected_game_executable_path=args.expected_game_executable,
                    manual_confirmation_timeout_ms=args.manual_confirmation_timeout_ms,
                    ui_timeout_ms=args.ui_timeout_ms,
                    authorization_timeout_ms=args.authorization_timeout_ms,
                    identity_handoff_timeout_ms=args.identity_handoff_timeout_ms,
                )
            )
            return 0
        if args.command == "checkpoint-challenge":
            _emit(
                create_checkpoint_challenge(
                    args.file,
                    checkpoint_id=args.checkpoint_id,
                    step_id=args.step_id,
                    task_id=args.task_id,
                    requested_at_unix=args.checkpoint_requested_at,
                )
            )
            return 0
        if args.command == "checkpoint-authorize":
            _emit(
                authorize_checkpoint_challenge(
                    args.file,
                    checkpoint_id=args.checkpoint_id,
                    step_id=args.step_id,
                    task_id=args.task_id,
                    response=args.response,
                    max_age_seconds=args.max_age_seconds,
                )
            )
            return 0
        if args.command == "play-grant-create":
            _emit(
                create_play_session_grant(
                    args.file,
                    framework_session_id=args.framework_session_id,
                    checkpoint_id=args.checkpoint_id,
                    spec_sha256=args.spec_sha256,
                    task_id=args.task_id,
                    initiation_text=args.initiation_text,
                    initiated_at_unix=args.initiated_at,
                    checkpoint_requested_at_unix=args.checkpoint_requested_at,
                    checkpoint_expires_at_unix=args.checkpoint_expires_at,
                )
            )
            return 0
        if args.command == "play-grant-consume":
            _emit(
                consume_play_session_grant(
                    args.file,
                    framework_session_id=args.framework_session_id,
                    checkpoint_id=args.checkpoint_id,
                    spec_sha256=args.spec_sha256,
                    task_id=args.task_id,
                )
            )
            return 0
        parser.error("unsupported command")
    except ReadOnlyIntegrationError as error:
        _emit({"error": {"code": error.code, "message": str(error)}, "ok": False})
        return 1
    except ValueError as error:
        _emit({"error": {"code": "invalid_input", "message": str(error)}, "ok": False})
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
