import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from civ5_agent.storage import UserDataStateReader


class UserDataStateReaderTest(unittest.TestCase):
    def test_reads_game_state_from_simple_values(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE SimpleValues(Name TEXT PRIMARY KEY, Value VARIANT)")
                connection.executemany(
                    "INSERT INTO SimpleValues(Name, Value) VALUES (?, ?)",
                    [("turn", 42), ("active_player", 0), ("gold", 137)],
                )
                connection.commit()

            state = UserDataStateReader(database).read_state()

            self.assertEqual(state.turn, 42)
            self.assertEqual(state.active_player, 0)
            self.assertEqual(state.gold, 137)

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                UserDataStateReader(database).read_state()
            self.assertFalse(database.exists())


if __name__ == "__main__":
    unittest.main()
