from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .ipc import LocalControlServer, request
from .live_session import LiveSessionError, prepare, restore
from .preflight import CIV_APP_BUNDLE, UnsafeSessionError, inspect_safety
from .watcher_client import WatcherBridgeClient


STATE_SCHEMA_VERSION = 1
PROFILE_M11 = "m11-research-runtime-c4"
PROFILES = (PROFILE_M11,)
CHECKPOINTS = (
    "live_state",
    "repeated_read",
    "ui_agreement",
    "overflow_precondition",
    "overflow_completion",
    "selection_stability",
    "overflow_application",
    "audit_clean",
)
OPEN_TOOL = Path("/usr/bin/open")
OSASCRIPT_TOOL = Path("/usr/bin/osascript")
MAX_NOTE_LENGTH = 160
MAX_STATE_BYTES = 32 * 1024
CONFIRMABLE_CHECKPOINTS = ("ui_agreement",)
FORBIDDEN_PERSISTED_KEYS = {
    "active_player",
    "bridge_session_id",
    "cities",
    "civilization",
    "diplomacy",
    "player_name",
    "units",
    "victory",
}


class LiveTestingError(RuntimeError):
    pass


class DataInconsistencyError(LiveTestingError):
    pass


def default_runtime_dir() -> Path:
    return Path.home() / "Library/Application Support/civ5-agent/live-testing"


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    state: Path
    lock: Path
    control_socket: Path
    watcher_socket: Path
    audit: Path

    @classmethod
    def under(cls, root: Path) -> RuntimePaths:
        return cls(
            root=root,
            state=root / "session.json",
            lock=root / "session.lock",
            control_socket=root / "control.sock",
            watcher_socket=root / "watcher.sock",
            audit=root / "command-audit.jsonl",
        )


class SessionLock:
    def __init__(self, path: Path):
        self.path = path
        self._stream: Any = None

    def __enter__(self) -> SessionLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        self._stream = os.fdopen(descriptor, "r+")
        try:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self._stream.close()
            self._stream = None
            raise LiveTestingError("another live-test supervisor owns the session") from error
        os.chmod(self.path, 0o600)
        return self

    def __exit__(self, *_: object) -> None:
        if self._stream is not None:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
            self._stream.close()
            self._stream = None


class M11ResearchRuntimeProfile:
    name = PROFILE_M11
    checkpoints = CHECKPOINTS

    def run(
        self,
        name: str,
        state: dict[str, Any],
        client: WatcherBridgeClient,
        paths: RuntimePaths,
    ) -> dict[str, Any]:
        if name not in self.checkpoints:
            raise LiveTestingError(f"unknown checkpoint: {name}")
        if name == "audit_clean":
            return self._audit_clean(paths.audit)
        if name == "ui_agreement":
            return {
                "status": "awaiting_confirmation",
                "reason": "compare the bounded summary with the stock UI",
            }

        first_session, first_state = client.read_state()
        first = _research_summary(first_state)
        if name == "live_state":
            _require_supported_live_state(first)
            return {"status": "pass", "evidence": first}
        if name == "repeated_read":
            second_session, second_state = client.read_state()
            second = _research_summary(second_state)
            _require_supported_live_state(first)
            _require_supported_live_state(second)
            if first_session != second_session or first != second:
                raise DataInconsistencyError(
                    "repeated reads changed within one action window"
                )
            return {"status": "pass", "evidence": first}
        if name == "overflow_precondition":
            _require_supported_live_state(first)
            current = _require_current(first)
            remaining = current["cost"] * 100 - current["progress_times100"]
            science = first["science_per_turn_times100"]
            surplus = science - remaining
            evidence = {
                "turn": first["turn"],
                "technology": current["type"],
                "cost": current["cost"],
                "progress_times100": current["progress_times100"],
                "science_per_turn_times100": science,
                "remaining_times100": remaining,
                "surplus_times100": surplus,
                "expected_whole_overflow": surplus // 100 if surplus >= 0 else None,
                "fractional_surplus_times100": surplus % 100 if surplus >= 0 else None,
                "overflow_before": first["overflow_research"],
            }
            if not (0 < remaining and remaining + 100 <= science):
                return {
                    "status": "pending",
                    "reason": "exact positive whole-point overflow precondition is absent",
                    "evidence": evidence,
                }
            return {"status": "pass", "evidence": evidence}
        if name == "overflow_completion":
            prior = _passed_evidence(state, "overflow_precondition")
            _require_supported_live_state(first)
            expected = prior["expected_whole_overflow"]
            current = first.get("current")
            completed = (
                first["turn"] > prior["turn"]
                and (current is None or current["type"] != prior["technology"])
            )
            evidence = {
                "turn": first["turn"],
                "prior_technology": prior["technology"],
                "current_technology": current["type"] if current else None,
                "surplus_times100": prior["surplus_times100"],
                "expected_whole_overflow": expected,
                "fractional_surplus_times100": prior["fractional_surplus_times100"],
                "observed_overflow": first["overflow_research"],
            }
            if not completed:
                raise DataInconsistencyError(
                    "prior technology was not observed complete after interturn"
                )
            if first["overflow_research"] != expected or expected <= 0:
                raise DataInconsistencyError(
                    "whole-point overflow does not match the exact pre-interturn surplus"
                )
            return {"status": "pass", "evidence": evidence}
        if name == "selection_stability":
            prior = _passed_evidence(state, "overflow_completion")
            _require_supported_live_state(first)
            current = _require_current(first)
            evidence = {
                "turn": first["turn"],
                "selected_technology": current["type"],
                "progress_times100": current["progress_times100"],
                "overflow_research": first["overflow_research"],
            }
            if first["turn"] != prior["turn"]:
                raise DataInconsistencyError(
                    "turn advanced before selection-stability observation"
                )
            if first["overflow_research"] != prior["observed_overflow"]:
                raise DataInconsistencyError(
                    "technology selection immediately changed recorded overflow"
                )
            return {"status": "pass", "evidence": evidence}
        if name == "overflow_application":
            prior = _passed_evidence(state, "selection_stability")
            _require_supported_live_state(first)
            current = first.get("current")
            progress_after = current["progress_times100"] if current else None
            advanced = first["turn"] > prior["turn"]
            reflected = advanced and (
                current is None
                or current["type"] != prior["selected_technology"]
                or progress_after > prior["progress_times100"]
            )
            evidence = {
                "turn": first["turn"],
                "prior_turn": prior["turn"],
                "selected_technology": prior["selected_technology"],
                "current_technology": current["type"] if current else None,
                "prior_progress_times100": prior["progress_times100"],
                "current_progress_times100": progress_after,
                "overflow_research": first["overflow_research"],
            }
            if not reflected:
                raise DataInconsistencyError(
                    "following interturn did not reflect research application"
                )
            return {"status": "pass", "evidence": evidence}
        raise AssertionError("unreachable checkpoint")

    @staticmethod
    def _audit_clean(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {
                "status": "pass",
                "evidence": {"records": 0, "permissions": "not_applicable"},
            }
        mode = stat.S_IMODE(path.stat().st_mode)
        records = 0 if path.stat().st_size == 0 else 1
        evidence = {"records": records, "permissions": f"{mode:03o}"}
        if records or mode != 0o600:
            raise DataInconsistencyError("read-only command audit is not empty and private")
        return {"status": "pass", "evidence": evidence}


def _research_summary(game_state: Any) -> dict[str, Any]:
    facts = game_state.research_runtime_facts
    current = facts.get("current") if isinstance(facts, dict) else None
    context = game_state.runtime_context
    dimensions: dict[str, str] = {}
    if isinstance(context, dict):
        for key, value in sorted(context.items()):
            if isinstance(value, dict) and isinstance(value.get("status"), str):
                dimensions[key] = value["status"]
    return {
        "schema_version": game_state.schema_version,
        "turn": game_state.turn,
        "research_type": (
            game_state.research.get("type")
            if isinstance(game_state.research, dict)
            else None
        ),
        "status": facts.get("status") if isinstance(facts, dict) else None,
        "reason": facts.get("reason") if isinstance(facts, dict) else None,
        "phase": facts.get("phase") if isinstance(facts, dict) else None,
        "science_per_turn_times100": (
            facts.get("science_per_turn_times100")
            if isinstance(facts, dict)
            else None
        ),
        "overflow_research": (
            facts.get("overflow_research") if isinstance(facts, dict) else None
        ),
        "current": (
            {
                "type": current.get("type"),
                "cost": current.get("cost"),
                "progress_times100": current.get("progress_times100"),
                "turns_left_with_overflow": current.get("turns_left_with_overflow"),
            }
            if isinstance(current, dict)
            else None
        ),
        "candidate_count": (
            len(facts.get("candidates", [])) if isinstance(facts, dict) else None
        ),
        "runtime_context_status": dimensions,
    }


def _require_supported_live_state(summary: dict[str, Any]) -> None:
    if summary["schema_version"] != 8:
        raise DataInconsistencyError("M11 live state must use schema 8")
    if summary["status"] != "supported" or summary["reason"] is not None:
        raise DataInconsistencyError("ordinary research runtime facts are not supported")
    if summary["phase"] != "action_window_after_interturn_research_resolution":
        raise DataInconsistencyError("state is outside the ordinary research action window")
    if not isinstance(summary["science_per_turn_times100"], int):
        raise DataInconsistencyError("science-per-turn fact is unavailable")
    if not isinstance(summary["overflow_research"], int):
        raise DataInconsistencyError("overflow fact is unavailable")


def _require_current(summary: dict[str, Any]) -> dict[str, Any]:
    current = summary.get("current")
    if not isinstance(current, dict):
        raise DataInconsistencyError("current ordinary research is unavailable")
    if not isinstance(current.get("type"), str):
        raise DataInconsistencyError("current research identifier is unavailable")
    for key in ("cost", "progress_times100"):
        if not isinstance(current.get(key), int):
            raise DataInconsistencyError(f"current research {key} is unavailable")
    return current


def _passed_evidence(state: dict[str, Any], checkpoint: str) -> dict[str, Any]:
    record = state.get("checkpoints", {}).get(checkpoint)
    if not isinstance(record, dict) or record.get("status") != "pass":
        raise LiveTestingError(f"checkpoint {checkpoint} must pass first")
    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        raise LiveTestingError(f"checkpoint {checkpoint} has no bounded evidence")
    return evidence


PROFILE_FACTORIES: dict[str, Callable[[], M11ResearchRuntimeProfile]] = {
    PROFILE_M11: M11ResearchRuntimeProfile,
}


def _profile_for(name: str) -> M11ResearchRuntimeProfile:
    try:
        return PROFILE_FACTORIES[name]()
    except KeyError as error:
        raise LiveTestingError(f"unsupported live-test profile: {name}") from error


class Supervisor:
    def __init__(
        self,
        paths: RuntimePaths,
        state: dict[str, Any],
        *,
        watcher_process: subprocess.Popen[Any] | None = None,
        profile: M11ResearchRuntimeProfile | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.paths = paths
        self.state = state
        self.watcher_process = watcher_process
        self.profile = profile or _profile_for(state["profile"])
        self.monotonic = monotonic
        self.stop_event = threading.Event()
        self.exit_reason = "finish_requested"

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "profile": self.state["profile"],
            "phase": self.state["phase"],
            "checkpoints": self.state.get("checkpoints", {}),
            "last_error": self.state.get("last_error"),
        }

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = payload.get("op")
        if operation in {"ping", "status"}:
            return self.status()
        if operation == "finish":
            self.state["phase"] = "finishing"
            _write_state(self.paths.state, self.state)
            self.exit_reason = "finish_requested"
            self.stop_event.set()
            return {"ok": True, "result": "finish_requested"}
        if operation == "checkpoint":
            if self.state["phase"] == "paused_data_inconsistency":
                return {"ok": False, "error": "session is paused for data inconsistency"}
            name = payload.get("name")
            if not isinstance(name, str):
                return {"ok": False, "error": "checkpoint name is required"}
            try:
                result = self.profile.run(
                    name,
                    self.state,
                    WatcherBridgeClient(socket_path=self.paths.watcher_socket),
                    self.paths,
                )
                self.state.setdefault("checkpoints", {})[name] = result
                _write_state(self.paths.state, self.state)
                return {"ok": True, "checkpoint": name, **result}
            except DataInconsistencyError as error:
                message = _sanitize_message(str(error))
                record = {"status": "inconsistent", "reason": message}
                self.state.setdefault("checkpoints", {})[name] = record
                self.state["phase"] = "paused_data_inconsistency"
                self.state["last_error"] = message
                _write_state(self.paths.state, self.state)
                return {"ok": False, "checkpoint": name, **record}
            except (LiveTestingError, OSError, TimeoutError, ValueError) as error:
                return {"ok": False, "error": _sanitize_message(str(error))}
        if operation == "confirm":
            try:
                return self._confirm(payload)
            except LiveTestingError as error:
                return {"ok": False, "error": _sanitize_message(str(error))}
        return {"ok": False, "error": f"unsupported operation: {operation!r}"}

    def _confirm(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload.get("name")
        result = payload.get("result")
        source = payload.get("source")
        note = payload.get("note", "")
        if name not in CONFIRMABLE_CHECKPOINTS:
            raise LiveTestingError("checkpoint does not accept visual confirmation")
        if result not in {"pass", "fail"}:
            raise LiveTestingError("confirmation result must be pass or fail")
        if source not in {"codex", "user"}:
            raise LiveTestingError("confirmation source must be codex or user")
        if not isinstance(note, str) or len(note) > MAX_NOTE_LENGTH:
            raise LiveTestingError(
                f"confirmation note must be at most {MAX_NOTE_LENGTH} characters"
            )
        if any(character in note for character in ("\n", "\r", "\x00")):
            raise LiveTestingError("confirmation note must be one line")
        record = {
            "status": result,
            "confirmation": {"source": source, "note_present": bool(note)},
        }
        self.state.setdefault("checkpoints", {})[name] = record
        if result == "fail":
            self.state["phase"] = "paused_data_inconsistency"
            self.state["last_error"] = f"{name} confirmation failed"
        _write_state(self.paths.state, self.state)
        return {"ok": result == "pass", "checkpoint": name, **record}

    def serve(self, *, monitor_interval: float = 2.0) -> int:
        self.state["phase"] = (
            self.state["phase"]
            if self.state["phase"] == "paused_data_inconsistency"
            else "running"
        )
        _write_state(self.paths.state, self.state)
        with LocalControlServer(self.handle, self.paths.control_socket):
            while not self.stop_event.wait(monitor_interval):
                safety = inspect_safety("live", socket_path=self.paths.watcher_socket)
                if not safety.ok:
                    self.state["phase"] = "safety_failure"
                    self.state["last_error"] = _sanitize_message(
                        "; ".join(safety.issues)
                    )
                    _write_state(self.paths.state, self.state)
                    self.exit_reason = "safety_failure"
                    break
                if self.watcher_process is not None and self.watcher_process.poll() is not None:
                    self.state["phase"] = "safety_failure"
                    self.state["last_error"] = "read-only watcher exited unexpectedly"
                    _write_state(self.paths.state, self.state)
                    self.exit_reason = "safety_failure"
                    break
        return 0 if self.exit_reason == "finish_requested" else 1


def _new_state(profile: str) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "profile": profile,
        "phase": "starting",
        "watcher_pid": None,
        "checkpoints": {},
        "last_error": None,
    }


def _write_state(path: Path, state: dict[str, Any]) -> None:
    _validate_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(state, stream, allow_nan=False, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _read_state(path: Path) -> dict[str, Any]:
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise LiveTestingError("live-test recovery state is not private")
    try:
        if path.stat().st_size > MAX_STATE_BYTES:
            raise LiveTestingError("live-test recovery state is too large")
        state = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise LiveTestingError(f"invalid live-test recovery state: {error}") from error
    _validate_state(state)
    return state


def _validate_state(state: Any) -> None:
    if not isinstance(state, dict):
        raise LiveTestingError("live-test state must be an object")
    allowed = {
        "schema_version",
        "profile",
        "phase",
        "watcher_pid",
        "checkpoints",
        "last_error",
    }
    if set(state) != allowed:
        raise LiveTestingError("live-test state contains unsupported fields")
    if state["schema_version"] != STATE_SCHEMA_VERSION:
        raise LiveTestingError("unsupported live-test state schema")
    if state["profile"] not in PROFILES:
        raise LiveTestingError("unsupported live-test profile")
    if state["phase"] not in {
        "starting",
        "running",
        "paused_data_inconsistency",
        "finishing",
        "safety_failure",
        "restore_failed",
    }:
        raise LiveTestingError("invalid live-test phase")
    if state["watcher_pid"] is not None and (
        isinstance(state["watcher_pid"], bool)
        or not isinstance(state["watcher_pid"], int)
        or state["watcher_pid"] <= 0
    ):
        raise LiveTestingError("invalid watcher process identity")
    if not isinstance(state["checkpoints"], dict):
        raise LiveTestingError("invalid checkpoint state")
    if set(state["checkpoints"]) - set(CHECKPOINTS):
        raise LiveTestingError("live-test state contains an unknown checkpoint")
    if _contains_forbidden_key(state["checkpoints"]):
        raise LiveTestingError("live-test state contains forbidden snapshot fields")
    encoded = json.dumps(state, allow_nan=False, sort_keys=True).encode()
    if len(encoded) > MAX_STATE_BYTES:
        raise LiveTestingError("live-test recovery state is too large")
    if state["last_error"] is not None and not isinstance(state["last_error"], str):
        raise LiveTestingError("invalid live-test error")
    if isinstance(state["last_error"], str) and len(state["last_error"]) > 300:
        raise LiveTestingError("live-test error is too long")


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        if set(value) & FORBIDDEN_PERSISTED_KEYS:
            return True
        return any(_contains_forbidden_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _sanitize_message(message: str) -> str:
    sanitized = message.replace(str(Path.home()), "<home>")
    sanitized = re.sub(
        r"(?<![A-Za-z0-9_>])/(?:[^\s;:,]+/?)+",
        "<path>",
        sanitized,
    )
    sanitized = sanitized.replace("\n", " ").replace("\r", " ").replace("\x00", "")
    return sanitized[:300]


def _launch_game() -> None:
    subprocess.run([str(OPEN_TOOL), str(CIV_APP_BUNDLE)], check=True)


def _request_game_quit() -> None:
    subprocess.run(
        [
            str(OSASCRIPT_TOOL),
            "-e",
            'tell application "Civilization V Campaign Edition" to quit',
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _wait_for_live(paths: RuntimePaths, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_issues: list[str] = []
    while time.monotonic() < deadline:
        status = inspect_safety("live", socket_path=paths.watcher_socket)
        if status.ok:
            return
        last_issues = status.issues
        time.sleep(0.5)
    raise UnsafeSessionError("; ".join(last_issues) or "Civ V did not become live")


def _launch_watcher(paths: RuntimePaths) -> subprocess.Popen[Any]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "civ5_agent.watch",
            "--read-only",
            "--socket",
            str(paths.watcher_socket),
            "--audit-log",
            str(paths.audit),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LiveTestingError("read-only watcher exited during startup")
        try:
            response = request(
                {"op": "ping"}, socket_path=paths.watcher_socket, timeout=0.5
            )
            if response.get("ok") and response.get("read_only") is True:
                return process
            raise LiveTestingError("watcher did not prove server-enforced read-only mode")
        except (ConnectionError, FileNotFoundError, OSError, TimeoutError):
            time.sleep(0.1)
    process.terminate()
    process.wait(timeout=5)
    raise LiveTestingError("read-only watcher did not create its private socket")


def _stop_watcher(process: subprocess.Popen[Any] | None, paths: RuntimePaths) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    paths.watcher_socket.unlink(missing_ok=True)


def _wait_for_game_exit(paths: RuntimePaths, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = inspect_safety("status", socket_path=paths.watcher_socket)
        if status.port_4318_listening is False:
            return
        time.sleep(0.5)
    raise LiveTestingError(
        "Civilization V did not quit normally; it was not force-killed"
    )


def _cleanup(
    supervisor: Supervisor,
    *,
    request_quit: bool,
) -> None:
    errors: list[str] = []
    if request_quit:
        try:
            _request_game_quit()
            _wait_for_game_exit(supervisor.paths)
        except (LiveTestingError, OSError, subprocess.CalledProcessError) as error:
            errors.append(str(error))
    _stop_watcher(supervisor.watcher_process, supervisor.paths)
    if not errors:
        try:
            restore()
        except (LiveSessionError, OSError, subprocess.CalledProcessError) as error:
            errors.append(str(error))
    if errors:
        supervisor.state["phase"] = "restore_failed"
        supervisor.state["last_error"] = _sanitize_message("; ".join(errors))
        _write_state(supervisor.paths.state, supervisor.state)
        raise LiveTestingError("; ".join(errors))
    supervisor.paths.state.unlink(missing_ok=True)
    supervisor.paths.audit.unlink(missing_ok=True)


def run_start(
    profile: str,
    *,
    runtime_dir: Path | None = None,
    live_timeout: float = 180.0,
) -> int:
    paths = RuntimePaths.under(runtime_dir or default_runtime_dir())
    with SessionLock(paths.lock):
        if paths.state.exists():
            raise LiveTestingError("recovery state exists; run recover instead")
        state = _new_state(profile)
        _write_state(paths.state, state)
        supervisor = Supervisor(paths, state)
        prepared = False
        launched = False
        try:
            prepare()
            prepared = True
            _launch_game()
            launched = True
            _wait_for_live(paths, live_timeout)
            supervisor.watcher_process = _launch_watcher(paths)
            state["watcher_pid"] = supervisor.watcher_process.pid
            _write_state(paths.state, state)
            print(
                json.dumps(
                    {"ok": True, "result": "supervisor_started", "profile": profile},
                    sort_keys=True,
                ),
                flush=True,
            )
            _install_signal_handlers(supervisor)
            result = supervisor.serve()
            _cleanup(supervisor, request_quit=True)
            return result
        except BaseException:
            if prepared:
                try:
                    _cleanup(supervisor, request_quit=launched)
                except LiveTestingError:
                    pass
            raise


def run_recover(*, runtime_dir: Path | None = None) -> int:
    paths = RuntimePaths.under(runtime_dir or default_runtime_dir())
    with SessionLock(paths.lock):
        if not paths.state.exists():
            raise LiveTestingError("no interrupted live-test session exists")
        state = _read_state(paths.state)
        status = inspect_safety("status", socket_path=paths.watcher_socket)
        supervisor = Supervisor(paths, state)
        if status.port_4318_listening is False:
            _stop_orphan_watcher(state.get("watcher_pid"), paths)
            restore()
            paths.state.unlink(missing_ok=True)
            paths.audit.unlink(missing_ok=True)
            print(json.dumps({"ok": True, "result": "restored_closed_session"}, sort_keys=True))
            return 0
        live = inspect_safety("live", socket_path=paths.watcher_socket)
        if not live.ok:
            supervisor.state["phase"] = "safety_failure"
            supervisor.state["last_error"] = _sanitize_message("; ".join(live.issues))
            _write_state(paths.state, supervisor.state)
            _cleanup(supervisor, request_quit=True)
            return 1
        _stop_orphan_watcher(state.get("watcher_pid"), paths)
        supervisor.watcher_process = _launch_watcher(paths)
        state["watcher_pid"] = supervisor.watcher_process.pid
        _write_state(paths.state, state)
        print(
            json.dumps(
                {
                    "ok": True,
                    "result": "supervision_recovered",
                    "profile": state["profile"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
        _install_signal_handlers(supervisor)
        result = supervisor.serve()
        _cleanup(supervisor, request_quit=True)
        return result


def _stop_orphan_watcher(pid: Any, paths: RuntimePaths) -> None:
    if isinstance(pid, int) and pid > 0:
        inspection = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
        )
        command = inspection.stdout.strip()
        if inspection.returncode == 0 and command and not (
            "civ5_agent.watch" in command
            and "--read-only" in command
            and str(paths.watcher_socket) in command
        ):
            raise LiveTestingError(
                "recorded watcher process identity is ambiguous; refusing to signal it"
            )
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError as error:
            raise LiveTestingError("cannot stop recorded watcher process") from error
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            raise LiveTestingError(
                "recorded read-only watcher did not stop normally; refusing to force it"
            )
    paths.watcher_socket.unlink(missing_ok=True)


def _install_signal_handlers(supervisor: Supervisor) -> None:
    def stop(_signum: int, _frame: Any) -> None:
        supervisor.exit_reason = "finish_requested"
        supervisor.stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)


def _control_request(paths: RuntimePaths, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return request(payload, socket_path=paths.control_socket, timeout=10.0)
    except (ConnectionError, OSError, TimeoutError, ValueError) as error:
        raise LiveTestingError(
            "live-test supervisor unavailable: " + _sanitize_message(str(error))
        ) from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Supervise bounded, read-only Civilization V live tests"
    )
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime_dir())
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--profile", choices=PROFILES, default=PROFILE_M11)
    start_parser.add_argument("--live-timeout", type=float, default=180.0)
    subparsers.add_parser("status")
    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument("name", choices=CHECKPOINTS)
    confirm_parser = subparsers.add_parser("confirm")
    confirm_parser.add_argument("name", choices=CHECKPOINTS)
    confirm_parser.add_argument("--result", choices=("pass", "fail"), required=True)
    confirm_parser.add_argument("--source", choices=("codex", "user"), required=True)
    confirm_parser.add_argument("--note", default="")
    subparsers.add_parser("finish")
    subparsers.add_parser("recover")
    args = parser.parse_args()
    paths = RuntimePaths.under(args.runtime_dir)

    try:
        if args.command == "start":
            if args.live_timeout <= 0:
                parser.error("--live-timeout must be greater than zero")
            return run_start(
                args.profile,
                runtime_dir=args.runtime_dir,
                live_timeout=args.live_timeout,
            )
        if args.command == "recover":
            return run_recover(runtime_dir=args.runtime_dir)
        payload: dict[str, Any] = {"op": args.command}
        if args.command == "checkpoint":
            payload["name"] = args.name
        if args.command == "confirm":
            payload.update(
                name=args.name,
                result=args.result,
                source=args.source,
                note=args.note,
            )
        response = _control_request(paths, payload)
        print(json.dumps(response, allow_nan=False, sort_keys=True))
        return 0 if response.get("ok") else 1
    except (
        LiveTestingError,
        LiveSessionError,
        UnsafeSessionError,
        OSError,
        subprocess.CalledProcessError,
    ) as error:
        print(
            json.dumps(
                {"ok": False, "error": _sanitize_message(str(error))},
                sort_keys=True,
            )
        )
        return 1
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": "interrupted"}, sort_keys=True))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
