from __future__ import annotations

import json
import os
import stat
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_audit_path() -> Path:
    return Path.home() / "Library" / "Logs" / "civ5-agent" / "commands.jsonl"


class CommandAuditLog:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def ensure_ready(self) -> None:
        with self._lock:
            fd = self._open()
            os.close(fd)

    def append(
        self,
        operation: str,
        result: dict[str, Any],
        arguments: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "arguments": arguments or {},
            "result": result,
        }
        encoded = json.dumps(record, separators=(",", ":"), sort_keys=True).encode() + b"\n"
        with self._lock:
            fd = self._open()
            try:
                view = memoryview(encoded)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError("audit log write made no progress")
                    view = view[written:]
            finally:
                os.close(fd)

    def _open(self) -> int:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o600)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise OSError(f"audit path is not a regular file: {self.path}")
        os.fchmod(fd, 0o600)
        return fd
