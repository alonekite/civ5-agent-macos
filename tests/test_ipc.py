import tempfile
import unittest
from pathlib import Path

from civ5_agent.ipc import MAX_REQUEST_BYTES, LocalControlServer, request


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


if __name__ == "__main__":
    unittest.main()
