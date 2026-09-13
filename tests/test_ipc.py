import json
import socket
import tempfile
import unittest
from pathlib import Path

from civ5_agent.ipc import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    LocalControlServer,
    request,
)


class LocalIpcTest(unittest.TestCase):
    def test_round_trip_and_socket_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bridge.sock"
            with LocalControlServer(lambda payload: {"ok": True, "echo": payload}, path):
                self.assertEqual(
                    request({"op": "ping"}, socket_path=path),
                    {"ok": True, "echo": {"op": "ping"}},
                )
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(path.exists())

    def test_refuses_to_replace_a_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bridge.sock"
            path.write_text("user data")
            server = LocalControlServer(lambda payload: payload, path)
            with self.assertRaises(FileExistsError):
                server.start()
            self.assertEqual(path.read_text(), "user data")

    def test_response_may_exceed_request_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bridge.sock"
            state_blob = "x" * (MAX_REQUEST_BYTES + 1)
            with LocalControlServer(lambda _payload: {"ok": True, "state": state_blob}, path):
                response = request({"op": "read_state"}, socket_path=path)
            self.assertEqual(response["state"], state_blob)

    def test_client_rejects_oversized_request_before_connecting(self):
        with self.assertRaisesRegex(ValueError, "request too large"):
            request({"value": "x" * MAX_REQUEST_BYTES})

    def test_server_replaces_oversized_response_with_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bridge.sock"
            state_blob = "x" * MAX_RESPONSE_BYTES
            with LocalControlServer(
                lambda _payload: {"ok": True, "state": state_blob},
                path,
            ):
                response = request({"op": "read_state"}, socket_path=path)
        self.assertFalse(response["ok"])
        self.assertIn("response too large", response["error"])

    def test_server_reports_unserializable_callback_response(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bridge.sock"
            with LocalControlServer(
                lambda _payload: {"ok": True, "bad": object()},
                path,
            ):
                response = request({"op": "ping"}, socket_path=path)
        self.assertFalse(response["ok"])
        self.assertIn("not valid JSON", response["error"])

    def test_server_reports_unexpected_callback_error(self):
        def fail(_payload):
            raise RuntimeError("private implementation detail")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bridge.sock"
            with LocalControlServer(fail, path):
                response = request({"op": "ping"}, socket_path=path)
        self.assertEqual(
            response,
            {"ok": False, "error": "internal bridge error: RuntimeError"},
        )

    def test_server_rejects_non_finite_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bridge.sock"
            with LocalControlServer(lambda payload: {"ok": True}, path):
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                    connection.connect(str(path))
                    connection.sendall(b'{"value":NaN}\n')
                    response = json.loads(connection.recv(4096))
        self.assertFalse(response["ok"])
        self.assertIn("invalid JSON constant", response["error"])


if __name__ == "__main__":
    unittest.main()
