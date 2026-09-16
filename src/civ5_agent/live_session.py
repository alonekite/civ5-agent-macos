from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .errors import SafetyError
from .preflight import (
    CIV_EXECUTABLE,
    FIREWALL_TOOL,
    SafetyStatus,
    default_config_path,
    inspect_safety,
)


STATE_SCHEMA_VERSION = 1
SUDO_TOOL = Path("/usr/bin/sudo")
CommandRunner = Callable[[Path, str, str], str]


class LiveSessionError(SafetyError):
    pass


@dataclass(frozen=True)
class SessionBaseline:
    schema_version: int
    phase: str
    firewall_enabled: bool
    civ_rule_present: bool
    civ_incoming_blocked: bool


def default_session_dir() -> Path:
    return Path.home() / "Library/Application Support/civ5-agent"


def prepare(
    *,
    config_path: Path | None = None,
    session_dir: Path | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, object]:
    config = config_path or default_config_path()
    directory = session_dir or default_session_dir()
    state_path = directory / "live-session.json"
    backup_path = directory / "live-session-config.backup"
    runner = command_runner or _run_firewall_command

    if state_path.exists():
        baseline = _read_state(state_path)
        if baseline.phase != "prepared":
            raise LiveSessionError(
                "an interrupted prepare exists; run live-session restore first"
            )
        if not backup_path.is_file():
            raise LiveSessionError("recorded live session is missing its config backup")
        status = inspect_safety("ready", config_path=config)
        if not status.ok:
            raise LiveSessionError(
                "recorded live session is not safe: " + "; ".join(status.issues)
            )
        return _result("already_prepared", baseline, status)

    starting = inspect_safety("status", config_path=config)
    _require_clean_start(starting)
    baseline = SessionBaseline(
        schema_version=STATE_SCHEMA_VERSION,
        phase="preparing",
        firewall_enabled=bool(starting.firewall_enabled),
        civ_rule_present=bool(starting.civ_rule_present),
        civ_incoming_blocked=bool(starting.civ_incoming_blocked),
    )

    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    shutil.copy2(config, backup_path)
    os.chmod(backup_path, 0o600)
    _write_state(state_path, baseline)

    try:
        if not baseline.civ_rule_present:
            runner(FIREWALL_TOOL, "--add", str(CIV_EXECUTABLE))
            runner(FIREWALL_TOOL, "--blockapp", str(CIV_EXECUTABLE))
        elif not baseline.civ_incoming_blocked:
            runner(FIREWALL_TOOL, "--blockapp", str(CIV_EXECUTABLE))
        guarded = inspect_safety("status", config_path=config)
        if (
            guarded.civ_rule_present is not True
            or guarded.civ_incoming_blocked is not True
        ):
            raise LiveSessionError("Civ V block-incoming rule verification failed")
        if not baseline.firewall_enabled:
            runner(FIREWALL_TOOL, "--setglobalstate", "on")
        _set_firetuner(config, enabled=True)
        status = inspect_safety("ready", config_path=config)
        if not status.ok:
            raise LiveSessionError("ready verification failed: " + "; ".join(status.issues))
        prepared = SessionBaseline(**{**asdict(baseline), "phase": "prepared"})
        _write_state(state_path, prepared)
        return _result("prepared", prepared, status)
    except Exception as error:
        try:
            rollback_status = inspect_safety("status", config_path=config)
            _restore_baseline(
                baseline,
                config=config,
                backup=backup_path,
                runner=runner,
                current=rollback_status,
            )
        except Exception as rollback_error:
            raise LiveSessionError(
                f"prepare failed ({error}); rollback also failed ({rollback_error})"
            ) from error
        state_path.unlink(missing_ok=True)
        backup_path.unlink(missing_ok=True)
        raise LiveSessionError(f"prepare failed and was rolled back: {error}") from error


def restore(
    *,
    config_path: Path | None = None,
    session_dir: Path | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, object]:
    config = config_path or default_config_path()
    directory = session_dir or default_session_dir()
    state_path = directory / "live-session.json"
    backup_path = directory / "live-session-config.backup"
    runner = command_runner or _run_firewall_command

    if not state_path.exists():
        status = inspect_safety("shutdown", config_path=config)
        if not status.ok:
            raise LiveSessionError(
                "no recovery state exists and shutdown is unsafe: "
                + "; ".join(status.issues)
            )
        return {"ok": True, "result": "already_restored", "safety": asdict(status)}

    baseline = _read_state(state_path)
    current = inspect_safety("status", config_path=config)
    if current.port_4318_listening is not False:
        raise LiveSessionError("quit Civilization V before restoring the live session")
    if current.agent_socket_present is not False:
        raise LiveSessionError("stop the watcher before restoring the live session")
    if not backup_path.is_file():
        raise LiveSessionError("live-session configuration backup is missing")

    _restore_baseline(
        baseline,
        config=config,
        backup=backup_path,
        runner=runner,
        current=current,
    )
    restored = inspect_safety("shutdown", config_path=config)
    _verify_restored(restored, baseline)
    state_path.unlink()
    backup_path.unlink()
    return _result("restored", baseline, restored)


def _require_clean_start(status: SafetyStatus) -> None:
    if status.issues:
        raise LiveSessionError("cannot inspect starting state: " + "; ".join(status.issues))
    if status.firetuner_enabled is not False:
        raise LiveSessionError("FireTuner must be disabled before preparing a session")
    if status.port_4318_listening is not False:
        raise LiveSessionError("Civilization V must be quit before preparing a session")
    if status.agent_socket_present is not False:
        raise LiveSessionError("the watcher must be stopped before preparing a session")
    if status.firewall_enabled is None or status.civ_rule_present is None:
        raise LiveSessionError("firewall baseline is incomplete")


def _restore_baseline(
    baseline: SessionBaseline,
    *,
    config: Path,
    backup: Path,
    runner: CommandRunner,
    current: SafetyStatus,
) -> None:
    shutil.copy2(backup, config)
    if baseline.civ_rule_present:
        if (
            current.civ_rule_present is not True
            or current.civ_incoming_blocked is not baseline.civ_incoming_blocked
        ):
            action = "--blockapp" if baseline.civ_incoming_blocked else "--unblockapp"
            runner(FIREWALL_TOOL, action, str(CIV_EXECUTABLE))
    elif current.civ_rule_present is True:
        # Preparation adds the executable path. socketfilterfw can display both
        # executable and bundle paths, but removal on the target requires the
        # exact executable path used by --add.
        runner(FIREWALL_TOOL, "--remove", str(CIV_EXECUTABLE))
    if current.firewall_enabled is not baseline.firewall_enabled:
        runner(
            FIREWALL_TOOL,
            "--setglobalstate",
            "on" if baseline.firewall_enabled else "off",
        )


def _verify_restored(status: SafetyStatus, baseline: SessionBaseline) -> None:
    issues = list(status.issues)
    if status.firewall_enabled is not baseline.firewall_enabled:
        issues.append("firewall state did not return to its baseline")
    if status.civ_rule_present is not baseline.civ_rule_present:
        issues.append("Civ V firewall-rule presence did not return to its baseline")
    if baseline.civ_rule_present and (
        status.civ_incoming_blocked is not baseline.civ_incoming_blocked
    ):
        issues.append("Civ V firewall-rule mode did not return to its baseline")
    if issues:
        raise LiveSessionError("restore verification failed: " + "; ".join(issues))


def _set_firetuner(config: Path, *, enabled: bool) -> None:
    original_mode = config.stat().st_mode & 0o777
    original = config.read_text(errors="surrogateescape")
    replacement = "1" if enabled else "0"
    updated, count = re.subn(
        r"^EnableTuner\s*=\s*[01]\s*$",
        f"EnableTuner = {replacement}",
        original,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise LiveSessionError(f"expected one boolean EnableTuner setting, found {count}")
    temporary = config.with_name(config.name + ".civ5-agent-tmp")
    temporary.write_text(updated, errors="surrogateescape")
    os.chmod(temporary, original_mode)
    os.replace(temporary, config)
    if f"EnableTuner = {replacement}" not in config.read_text(errors="replace"):
        raise LiveSessionError("FireTuner write verification failed")


def _run_firewall_command(executable: Path, action: str, argument: str) -> str:
    command = [str(executable), action, argument]
    if os.geteuid() != 0:
        command.insert(0, str(SUDO_TOOL))
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _write_state(path: Path, baseline: SessionBaseline) -> None:
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(asdict(baseline), stream, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def _read_state(path: Path) -> SessionBaseline:
    try:
        payload = json.loads(path.read_text())
        baseline = SessionBaseline(**payload)
    except (OSError, TypeError, ValueError) as error:
        raise LiveSessionError(f"invalid live-session state: {error}") from error
    if baseline.schema_version != STATE_SCHEMA_VERSION:
        raise LiveSessionError("unsupported live-session state schema")
    if baseline.phase not in {"preparing", "prepared"}:
        raise LiveSessionError("invalid live-session phase")
    for value in (
        baseline.firewall_enabled,
        baseline.civ_rule_present,
        baseline.civ_incoming_blocked,
    ):
        if not isinstance(value, bool):
            raise LiveSessionError("live-session state contains a non-boolean baseline")
    return baseline


def _result(
    result: str,
    baseline: SessionBaseline,
    status: SafetyStatus,
) -> dict[str, object]:
    return {
        "ok": True,
        "result": result,
        "baseline": asdict(baseline),
        "safety": asdict(status),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare or restore a bounded, firewall-guarded Civ V session"
    )
    parser.add_argument("action", choices=("prepare", "restore"))
    args = parser.parse_args()
    try:
        result = prepare() if args.action == "prepare" else restore()
    except (LiveSessionError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
