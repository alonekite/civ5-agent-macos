import json
import tempfile
import unittest
from pathlib import Path

from civ5_agent.audit import CommandAuditLog


class CommandAuditLogTest(unittest.TestCase):
    def test_appends_json_lines_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "commands.jsonl"
            audit = CommandAuditLog(path)
            audit.append("end_turn", {"id": "abc", "status": "success"})
            audit.append(
                "skip_unit",
                {"id": "def", "status": "error"},
                {"unit_id": 8},
                bridge_session_id="123e4567-e89b-42d3-a456-426614174000",
            )

            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([record["operation"] for record in records], ["end_turn", "skip_unit"])
            self.assertEqual(records[0]["result"]["id"], "abc")
            self.assertEqual(records[0]["arguments"], {})
            self.assertEqual(records[1]["arguments"], {"unit_id": 8})
            self.assertEqual(
                records[1]["bridge_session_id"],
                "123e4567-e89b-42d3-a456-426614174000",
            )
            self.assertIn("timestamp", records[0])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_refuses_symbolic_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("user data")
            link = root / "commands.jsonl"
            link.symlink_to(target)
            with self.assertRaises(OSError):
                CommandAuditLog(link).append("end_turn", {})
            self.assertEqual(target.read_text(), "user data")


if __name__ == "__main__":
    unittest.main()
