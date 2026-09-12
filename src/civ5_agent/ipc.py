from __future__ import annotations

import json
import os
import socket
import socketserver
import stat
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any


MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def default_socket_path() -> Path:
    return Path(tempfile.gettempdir()) / f"civ5-agent-{os.getuid()}.sock"


def request(
    payload: dict[str, Any],
    *,
    socket_path: Path | None = None,
    timeout: float = 35.0,
) -> dict[str, Any]:
    path = socket_path or default_socket_path()
    encoded = json.dumps(payload, separators=(",", ":")).encode() + b"\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        connection.sendall(encoded)
        response = _receive_line(connection)
    parsed = json.loads(response)
    if not isinstance(parsed, dict):
        raise ValueError("local bridge returned a non-object response")
    return parsed


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        line = self.rfile.readline(MAX_REQUEST_BYTES + 1)
        if len(line) > MAX_REQUEST_BYTES:
            response = {"ok": False, "error": "request too large"}
        else:
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("request must be a JSON object")
                response = self.server.callback(payload)  # type: ignore[attr-defined]
            except (ConnectionError, json.JSONDecodeError, OSError, TimeoutError, ValueError) as error:
                response = {"ok": False, "error": str(error)}
        self.wfile.write(json.dumps(response, separators=(",", ":")).encode() + b"\n")


class _UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class LocalControlServer:
    def __init__(
        self,
        callback: Callable[[dict[str, Any]], dict[str, Any]],
        socket_path: Path | None = None,
    ):
        self.callback = callback
        self.socket_path = socket_path or default_socket_path()
        self._server: _UnixServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return
        _remove_stale_socket(self.socket_path)
        server = _UnixServer(str(self.socket_path), _Handler)
        server.callback = self.callback  # type: ignore[attr-defined]
        os.chmod(self.socket_path, 0o600)
        thread = threading.Thread(target=server.serve_forever, name="civ5-agent-ipc", daemon=True)
        thread.start()
        self._server = server
        self._thread = thread

    def close(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        if self.socket_path.exists() and stat.S_ISSOCK(self.socket_path.stat().st_mode):
            self.socket_path.unlink()

    def __enter__(self) -> LocalControlServer:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _remove_stale_socket(path: Path) -> None:
    if not path.exists():
        return
    if not stat.S_ISSOCK(path.stat().st_mode):
        raise FileExistsError(f"refusing to replace non-socket path: {path}")
    try:
        request({"op": "ping"}, socket_path=path, timeout=0.25)
    except (ConnectionError, OSError, TimeoutError):
        path.unlink()
        return
    raise RuntimeError(f"another civ5-agent watcher is already serving {path}")


def _receive_line(connection: socket.socket) -> str:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            raise ConnectionError("local bridge closed before sending a response")
        newline = chunk.find(b"\n")
        if newline >= 0:
            size += newline
            if size > MAX_RESPONSE_BYTES:
                raise ValueError("local bridge response too large")
            chunks.append(chunk[:newline])
            break
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise ValueError("local bridge response too large")
    return b"".join(chunks).decode()
