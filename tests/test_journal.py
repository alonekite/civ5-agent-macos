import json
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from civ5_agent.journal import (
    JournalCapture,
    JournalError,
    JournalStore,
    export_redacted_journal,
    replay_journal,
    verify_journal,
)
from civ5_agent.journal.codec import MAX_RECORD_BYTES, JournalCodecError, decode_record
from civ5_agent.journal_cli import main as journal_main
from civ5_agent.models import GameState

MATCH_ID = "123e4567-e89b-42d3-a456-426614174010"
SESSION_ONE = "123e4567-e89b-42d3-a456-426614174011"
SESSION_TWO = "123e4567-e89b-42d3-a456-426614174012"


class JournalStoreTest(unittest.TestCase):
    def create_store(self, directory):
        path = Path(directory) / "match.jsonl"
        return JournalStore.create(
            path,
            SESSION_ONE,
            match_id=MATCH_ID,
        )

    def test_create_append_reopen_and_verify_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            appended = store.append(
                "snapshot",
                {"schema_version": 5, "gold": 7},
                bridge_session_id=SESSION_ONE,
                turn=3,
            )
            reopened = JournalStore.open(store.path)
            records = reopened.read_all()

            self.assertEqual(reopened.match_id, MATCH_ID)
            self.assertEqual([record.sequence for record in records], [0, 1])
            self.assertEqual(records[1], appended)
            self.assertEqual(records[1].previous_hash, records[0].record_hash)
            self.assertEqual(store.path.stat().st_mode & 0o777, 0o600)

    def test_requires_explicit_session_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            with self.assertRaisesRegex(JournalError, "not bound"):
                store.append(
                    "snapshot",
                    {},
                    bridge_session_id=SESSION_TWO,
                    turn=1,
                )

            binding = store.bind_session(SESSION_TWO)
            record = store.append(
                "snapshot",
                {},
                bridge_session_id=SESSION_TWO,
                turn=1,
            )
            self.assertEqual(binding.kind, "session_binding")
            self.assertEqual(record.bridge_session_id, SESSION_TWO)
            with self.assertRaisesRegex(JournalError, "already bound"):
                store.bind_session(SESSION_TWO)
            with self.assertRaisesRegex(JournalError, "operator"):
                store.bind_session(
                    "123e4567-e89b-42d3-a456-426614174013",
                    authority="automatic",
                )

    def test_live_record_requires_session_and_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            with self.assertRaisesRegex(JournalError, "bridge_session_id"):
                store.append("snapshot", {}, turn=1)
            with self.assertRaisesRegex(JournalError, "requires turn"):
                store.append(
                    "snapshot",
                    {},
                    bridge_session_id=SESSION_ONE,
                )

    def test_correction_must_target_existing_record(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            with self.assertRaisesRegex(JournalError, "supersedes_sequence"):
                store.append("correction", {"supersedes_sequence": 4})
            correction = store.append("correction", {"supersedes_sequence": 0})
            self.assertEqual(correction.kind, "correction")

    def test_rejects_turn_regression_without_partial_append(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            store.append(
                "snapshot",
                {},
                bridge_session_id=SESSION_ONE,
                turn=8,
            )
            before = store.path.read_bytes()
            with self.assertRaisesRegex(JournalError, "backwards"):
                store.append(
                    "snapshot",
                    {},
                    bridge_session_id=SESSION_ONE,
                    turn=7,
                )
            self.assertEqual(store.path.read_bytes(), before)

    def test_detects_tampering_and_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            store.append(
                "snapshot",
                {"gold": 7},
                bridge_session_id=SESSION_ONE,
                turn=1,
            )
            original = store.path.read_bytes()
            store.path.write_bytes(original.replace(b'"gold":7', b'"gold":8'))
            with self.assertRaisesRegex(JournalError, "record_hash"):
                JournalStore.open(store.path)

            store.path.write_bytes(original[:-1])
            with self.assertRaisesRegex(JournalError, "truncated"):
                JournalStore.open(store.path)

    def test_refuses_symbolic_link_and_existing_file_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.jsonl"
            target.write_text("private")
            link = root / "link.jsonl"
            link.symlink_to(target)
            with self.assertRaises(JournalError):
                JournalStore.open(link)
            with self.assertRaises(JournalError):
                JournalStore.create(target, SESSION_ONE, match_id=MATCH_ID)
            self.assertEqual(target.read_text(), "private")

    def test_rejects_oversized_record_without_partial_append(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            before = store.path.read_bytes()
            with self.assertRaisesRegex(JournalError, "maximum size"):
                store.append(
                    "snapshot",
                    {"value": "x" * MAX_RECORD_BYTES},
                    bridge_session_id=SESSION_ONE,
                    turn=1,
                )
            self.assertEqual(store.path.read_bytes(), before)

    def test_concurrent_appends_keep_contiguous_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.create_store(directory)
            errors = []

            def append(index):
                try:
                    store.append(
                        "snapshot",
                        {"index": index},
                        bridge_session_id=SESSION_ONE,
                        turn=8,
                    )
                except Exception as error:  # captured for assertion in main thread
                    errors.append(error)

            threads = [threading.Thread(target=append, args=(index,)) for index in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            records = store.read_all()
            self.assertEqual([record.sequence for record in records], list(range(9)))


class JournalCodecTest(unittest.TestCase):
    def test_rejects_duplicate_keys_non_finite_and_unknown_fields(self):
        with self.assertRaisesRegex(JournalCodecError, "duplicate JSON key"):
            decode_record(b'{"schema_version":1,"schema_version":1}\n')
        with self.assertRaisesRegex(JournalCodecError, "invalid JSON constant"):
            decode_record(b'{"value":NaN}\n')

        valid_record = {
            "schema_version": 1,
            "sequence": 0,
            "match_id": MATCH_ID,
            "bridge_session_id": SESSION_ONE,
            "captured_at": "2026-09-16T00:30:00Z",
            "turn": None,
            "kind": "journal_started",
            "payload": {},
            "previous_hash": None,
            "record_hash": "0" * 64,
            "unexpected": True,
        }
        with self.assertRaisesRegex(JournalCodecError, "unknown"):
            decode_record(
                json.dumps(valid_record, separators=(",", ":")).encode() + b"\n"
            )


class JournalCaptureTest(unittest.TestCase):
    def test_records_validated_snapshot_and_command_result_in_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            capture = JournalCapture.start(path, SESSION_ONE, "new")
            capture.record_snapshot(
                GameState(
                    schema_version=2,
                    turn=4,
                    active_player=0,
                    gold=7,
                    turn_active=True,
                    can_end_turn=True,
                    end_turn_blocking_type=0,
                )
            )
            capture.record_command_submitted(
                "end_turn",
                {},
                "123e4567-e89b-42d3-a456-426614174020",
                4,
            )
            recorded = capture.record_command_result(
                "end_turn",
                {},
                {
                    "id": "123e4567-e89b-42d3-a456-426614174020",
                    "status": "success",
                    "before": {"turn": 4},
                    "after": {"turn": 5},
                },
            )

            self.assertTrue(recorded)
            records = capture.store.read_all()
            self.assertEqual(
                [record.kind for record in records],
                [
                    "journal_started",
                    "snapshot",
                    "command_submitted",
                    "command_result",
                ],
            )
            self.assertEqual(
                records[3].payload["result"]["id"],
                "123e4567-e89b-42d3-a456-426614174020",
            )

    def test_records_observed_turn_transition_and_failed_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            capture = JournalCapture.start(path, SESSION_ONE, "new")
            capture.record_snapshot(
                GameState(
                    schema_version=2,
                    turn=5,
                    active_player=0,
                    gold=7,
                    turn_active=True,
                    can_end_turn=False,
                    end_turn_blocking_type=1,
                ),
                previous_turn=4,
            )
            capture.record_command_result(
                "end_turn",
                {},
                {
                    "id": "123e4567-e89b-42d3-a456-426614174021",
                    "status": "error",
                    "message": "turn did not advance",
                    "before": {"turn": 5},
                    "after": {"turn": 5},
                },
            )

            records = capture.store.read_all()
            self.assertEqual(
                [record.kind for record in records],
                [
                    "journal_started",
                    "turn_transition",
                    "snapshot",
                    "command_result",
                    "verification_error",
                ],
            )
            self.assertEqual(records[1].payload["from_turn"], 4)
            self.assertEqual(
                records[-1].payload["stage"], "execution_or_postcondition"
            )

    def test_records_unknown_command_outcome_as_verification_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            capture = JournalCapture.start(path, SESSION_ONE, "new")
            capture.record_command_outcome_unknown(
                "end_turn",
                "123e4567-e89b-42d3-a456-426614174022",
                5,
                "FireTuner response was incomplete",
            )

            record = capture.store.read_all()[-1]
            self.assertEqual(record.kind, "verification_error")
            self.assertEqual(record.turn, 5)
            self.assertEqual(
                record.payload["stage"], "execution_outcome_unknown"
            )

    def test_rejects_unvalidated_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            capture = JournalCapture.start(path, SESSION_ONE, "new")
            with self.assertRaisesRegex(ValueError, "live state is missing"):
                capture.record_snapshot(
                    GameState(schema_version=2, turn=4, active_player=0, gold=7)
                )
            self.assertEqual(len(capture.store.read_all()), 1)

    def test_resume_is_explicit_and_unanchored_result_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            JournalCapture.start(path, SESSION_ONE, "new")
            resumed = JournalCapture.start(path, SESSION_TWO, "resume")
            self.assertFalse(
                resumed.record_command_result(
                    "choose_research",
                    {"tech_type": None},
                    {"status": "error", "before": None, "after": None},
                )
            )
            records = resumed.store.read_all()
            self.assertEqual(records[-1].kind, "session_binding")
            self.assertEqual(records[-1].bridge_session_id, SESSION_TWO)


class JournalVerificationTest(unittest.TestCase):
    def test_returns_deterministic_payload_free_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            store = JournalStore.create(path, SESSION_ONE, match_id=MATCH_ID)
            store.append(
                "snapshot",
                {"private_player_name": "not included in summary"},
                bridge_session_id=SESSION_ONE,
                turn=2,
            )

            verification = verify_journal(path)

            self.assertEqual(verification.match_id, MATCH_ID)
            self.assertEqual(verification.record_count, 2)
            self.assertEqual(verification.first_turn, 2)
            self.assertEqual(verification.last_turn, 2)
            self.assertEqual(verification.bridge_session_count, 1)
            self.assertEqual(
                verification.kind_counts,
                {"journal_started": 1, "snapshot": 1},
            )
            self.assertNotIn("private_player_name", str(verification.to_dict()))

    def test_cli_reports_corruption_without_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            path.write_text("broken\n")
            output = StringIO()

            with redirect_stdout(output):
                status = journal_main(["verify", str(path)])

            response = json.loads(output.getvalue())
            self.assertEqual(status, 1)
            self.assertFalse(response["ok"])


class JournalReplayTest(unittest.TestCase):
    def test_replays_verified_records_in_original_order_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            store = JournalStore.create(path, SESSION_ONE, match_id=MATCH_ID)
            store.append(
                "snapshot",
                {"state": {"turn": 3, "private_player_name": "local"}},
                bridge_session_id=SESSION_ONE,
                turn=3,
            )
            store.append("correction", {"supersedes_sequence": 1})

            events = replay_journal(path)

            self.assertEqual([event.sequence for event in events], [0, 1, 2])
            self.assertEqual(
                [event.kind for event in events],
                ["journal_started", "snapshot", "correction"],
            )
            self.assertEqual(events[1].payload["state"]["turn"], 3)
            events[1].payload["state"]["turn"] = 99
            self.assertEqual(store.read_all()[1].payload["state"]["turn"], 3)

    def test_cli_requires_explicit_private_payload_acknowledgement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            JournalStore.create(path, SESSION_ONE, match_id=MATCH_ID)
            output = StringIO()

            with redirect_stdout(output):
                status = journal_main(
                    ["replay", str(path), "--include-private-payloads"]
                )

            response = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertTrue(response["ok"])
            self.assertEqual(response["events"][0]["kind"], "journal_started")

            with redirect_stdout(StringIO()), redirect_stderr(
                StringIO()
            ), self.assertRaises(SystemExit) as raised:
                journal_main(["replay", str(path)])
            self.assertEqual(raised.exception.code, 2)


class JournalExportTest(unittest.TestCase):
    def test_writes_private_redacted_structural_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "match.jsonl"
            destination = root / "export.json"
            store = JournalStore.create(source, SESSION_ONE, match_id=MATCH_ID)
            store.append(
                "snapshot",
                {"state": {"turn": 7, "private_player_name": "local"}},
                bridge_session_id=SESSION_ONE,
                turn=7,
            )

            report = export_redacted_journal(source, destination)
            second_destination = root / "export-again.json"
            export_redacted_journal(source, second_destination)
            exported = json.loads(destination.read_text())

            self.assertEqual(report.record_count, 2)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            self.assertEqual(destination.read_bytes(), second_destination.read_bytes())
            self.assertEqual(
                exported["events"],
                [
                    {"kind": "journal_started", "sequence": 0, "turn": None},
                    {"kind": "snapshot", "sequence": 1, "turn": 7},
                ],
            )
            serialized = destination.read_text()
            for private_value in (
                "private_player_name",
                "local",
                MATCH_ID,
                SESSION_ONE,
                "captured_at",
                "record_hash",
            ):
                self.assertNotIn(private_value, serialized)

    def test_refuses_existing_or_symbolic_link_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "match.jsonl"
            JournalStore.create(source, SESSION_ONE, match_id=MATCH_ID)
            existing = root / "existing.json"
            existing.write_text("keep")
            link = root / "link.json"
            link.symlink_to(existing)

            with self.assertRaisesRegex(JournalError, "cannot create"):
                export_redacted_journal(source, existing)
            with self.assertRaisesRegex(JournalError, "cannot create"):
                export_redacted_journal(source, link)

            self.assertEqual(existing.read_text(), "keep")

    def test_removes_new_destination_after_write_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "match.jsonl"
            destination = root / "partial.json"
            JournalStore.create(source, SESSION_ONE, match_id=MATCH_ID)

            with patch(
                "civ5_agent.journal.export.os.write",
                return_value=0,
            ), self.assertRaisesRegex(JournalError, "made no progress"):
                export_redacted_journal(source, destination)

            self.assertFalse(destination.exists())

    def test_cli_exports_without_printing_destination_or_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "match.jsonl"
            destination = root / "export.json"
            JournalStore.create(source, SESSION_ONE, match_id=MATCH_ID)
            output = StringIO()

            with redirect_stdout(output):
                status = journal_main(["export", str(source), str(destination)])

            response = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertTrue(response["ok"])
            self.assertEqual(response["export"]["record_count"], 1)
            self.assertNotIn(str(destination), output.getvalue())


if __name__ == "__main__":
    unittest.main()
