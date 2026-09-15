import json
import tempfile
import threading
import unittest
from pathlib import Path

from civ5_agent.journal import JournalError, JournalStore
from civ5_agent.journal.codec import MAX_RECORD_BYTES, JournalCodecError, decode_record

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
                        turn=index,
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


if __name__ == "__main__":
    unittest.main()
