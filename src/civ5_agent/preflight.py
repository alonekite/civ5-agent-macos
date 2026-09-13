from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .ipc import default_socket_path


FIREWALL_TOOL = Path("/usr/libexec/ApplicationFirewall/socketfilterfw")
LSOF_TOOL = Path("/usr/sbin/lsof")
CIV_EXECUTABLE = Path(
    "/Applications/Civilization V Campaign Edition.app/Contents/MacOS/"
    "Civilization V Campaign Edition"
)


def default_config_path() -> Path:
    return (
        Path.home()
        / "Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/"
        "Civilization V Campaign Edition/config.ini"
    )


@dataclass
class SafetyStatus:
    phase: str
    firetuner_enabled: bool | None = None
    firewall_enabled: bool | None = None
    civ_rule_present: bool | None = None
    civ_incoming_blocked: bool | None = None
    port_4318_listening: bool | None = None
    agent_socket_present: bool | None = None
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def inspect_safety(
    phase: str,
    *,
    config_path: Path | None = None,
    socket_path: Path | None = None,
) -> SafetyStatus:
    status = SafetyStatus(phase=phase)
    config = config_path or default_config_path()
    socket_file = socket_path or default_socket_path()

    try:
        status.firetuner_enabled = _read_firetuner_enabled(config)
    except (OSError, ValueError) as error:
        status.issues.append(f"config unavailable: {error}")

    try:
        global_output = _run_command(FIREWALL_TOOL, "--getglobalstate")
        status.firewall_enabled = _parse_firewall_enabled(global_output)
        apps_output = _run_command(FIREWALL_TOOL, "--listapps")
        status.civ_rule_present, status.civ_incoming_blocked = _parse_civ_rule(
            apps_output, CIV_EXECUTABLE
        )
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        status.issues.append(f"firewall status unavailable: {error}")

    try:
        lsof = subprocess.run(
            [str(LSOF_TOOL), "-nP", "-iTCP:4318", "-sTCP:LISTEN"],
            check=False,
            capture_output=True,
            text=True,
        )
        if lsof.returncode not in (0, 1):
            raise OSError(lsof.stderr.strip() or f"lsof exited {lsof.returncode}")
        status.port_4318_listening = lsof.returncode == 0 and bool(lsof.stdout.strip())
    except OSError as error:
        status.issues.append(f"port status unavailable: {error}")

    try:
        status.agent_socket_present = os.path.lexists(socket_file)
    except OSError as error:
        status.issues.append(f"agent socket status unavailable: {error}")

    status.issues.extend(_phase_issues(status))
    return status


def _read_firetuner_enabled(config_path: Path) -> bool:
    matches = re.findall(
        r"^EnableTuner\s*=\s*([01])\s*$",
        config_path.read_text(errors="replace"),
        flags=re.MULTILINE,
    )
    if len(matches) != 1:
        raise ValueError(f"expected one EnableTuner setting, found {len(matches)}")
    return matches[0] == "1"


def _run_command(executable: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [str(executable), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _parse_firewall_enabled(output: str) -> bool:
    match = re.search(r"State\s*=\s*([01])", output)
    if not match:
        raise ValueError("unrecognized global firewall status")
    return match.group(1) == "1"


def _parse_civ_rule(output: str, executable: Path) -> tuple[bool, bool]:
    lines = output.splitlines()
    expected = str(executable)
    for index, line in enumerate(lines):
        if line.strip().endswith(expected):
            following = lines[index + 1].strip() if index + 1 < len(lines) else ""
            if following == "(Block incoming connections)":
                return True, True
            if following == "(Allow incoming connections)":
                return True, False
            raise ValueError("unrecognized Civ V firewall rule")
    return False, False


def _phase_issues(status: SafetyStatus) -> list[str]:
    issues: list[str] = []
    if status.phase in {"ready", "live"}:
        if status.firetuner_enabled is not True:
            issues.append("FireTuner must be enabled")
        if status.firewall_enabled is not True:
            issues.append("macOS application firewall must be enabled")
        if status.civ_rule_present is not True or status.civ_incoming_blocked is not True:
            issues.append("Civ V must have an explicit block-incoming firewall rule")
    if status.phase == "live" and status.port_4318_listening is not True:
        issues.append("Civ V is not listening on TCP 4318")
    if status.phase == "shutdown":
        if status.firetuner_enabled is not False:
            issues.append("FireTuner must be restored to disabled")
        if status.port_4318_listening is not False:
            issues.append("TCP 4318 must not be listening")
        if status.agent_socket_present is not False:
            issues.append("agent Unix socket must be absent")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Civ V bridge safety checks")
    parser.add_argument("phase", choices=["status", "ready", "live", "shutdown"])
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--socket", type=Path, default=default_socket_path())
    args = parser.parse_args()

    status = inspect_safety(args.phase, config_path=args.config, socket_path=args.socket)
    output = asdict(status)
    output["ok"] = status.ok
    print(json.dumps(output, sort_keys=True))
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
