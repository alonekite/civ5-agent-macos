import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from civ5_agent.knowledge import Ruleset
from civ5_agent.knowledge.import_sqlite import (
    KnowledgeImportError,
    ERA_FIELDS,
    TECHNOLOGY_FIELDS,
    import_technologies,
)


def create_database(path: Path, *, invalid_boolean: bool = False) -> None:
    definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
    definitions.append("Era TEXT NOT NULL")
    for column, (_, value_type) in TECHNOLOGY_FIELDS.items():
        sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
        definitions.append(f'"{column}" {sql_type}')
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(f"CREATE TABLE Technologies ({', '.join(definitions)})")
        era_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        for column in ERA_FIELDS:
            era_definitions.append(f'"{column}" INTEGER')
        connection.execute(f"CREATE TABLE Eras ({', '.join(era_definitions)})")
        connection.execute(
            "CREATE TABLE Technology_PrereqTechs (TechType TEXT, PrereqTech TEXT)"
        )
        connection.execute(
            "CREATE TABLE Technology_ORPrereqTechs (TechType TEXT, PrereqTech TEXT)"
        )
        era_columns = ["Type", *ERA_FIELDS]
        connection.execute(
            f"INSERT INTO Eras ({', '.join(era_columns)}) VALUES "
            f"({', '.join('?' for _ in era_columns)})",
            ["ERA_ANCIENT", *([0] * len(ERA_FIELDS))],
        )
        columns = ["Type", "Era", *TECHNOLOGY_FIELDS]
        placeholders = ", ".join("?" for _ in columns)
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        for type_id, cost in (("TECH_AGRICULTURE", 20), ("TECH_POTTERY", 35)):
            values = []
            for column in TECHNOLOGY_FIELDS:
                _, value_type = TECHNOLOGY_FIELDS[column]
                if column == "Cost":
                    value = cost
                elif column == "Era":
                    value = "ERA_ANCIENT"
                elif value_type == "boolean":
                    value = 2 if invalid_boolean and column == "Trade" else 0
                elif value_type == "integer":
                    value = 0
                else:
                    value = None
                values.append(value)
            connection.execute(
                f"INSERT INTO Technologies ({quoted_columns}) VALUES ({placeholders})",
                [type_id, "ERA_ANCIENT", *values],
            )
        connection.execute(
            "INSERT INTO Technology_PrereqTechs VALUES (?, ?)",
            ("TECH_POTTERY", "TECH_AGRICULTURE"),
        )
        connection.commit()


class TechnologyImportTest(unittest.TestCase):
    def test_imports_allowlisted_facts_and_relationships(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Civ5DebugDatabase.db"
            create_database(database)
            bundle = import_technologies(
                database,
                "cache/Civ5DebugDatabase.db",
                Ruleset("bnw", "1.0.3.279", ("Expansion2",), ()),
            )
        self.assertEqual(len(bundle.entities), 3)
        self.assertEqual(len(bundle.references), 3)
        pottery = next(item for item in bundle.entities if item.type_id == "TECH_POTTERY")
        self.assertEqual(pottery.attributes["cost"], 35)
        self.assertNotIn("ai_weight", pottery.attributes)
        prerequisite = next(item for item in bundle.references if item.kind == "requires_all")
        self.assertEqual(prerequisite.target_type_id, "TECH_AGRICULTURE")
        era = next(
            item
            for item in bundle.references
            if item.kind == "belongs_to" and item.source_type_id == "TECH_POTTERY"
        )
        self.assertEqual(era.target_type_id, "ERA_ANCIENT")

    def test_records_source_hash_without_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Civ5DebugDatabase.db"
            create_database(database)
            expected_hash = hashlib.sha256(database.read_bytes()).hexdigest()
            bundle = import_technologies(
                database,
                "cache/Civ5DebugDatabase.db",
                Ruleset("bnw", "1.0.3.279"),
            )
        self.assertEqual(bundle.sources[0].path, "cache/Civ5DebugDatabase.db")
        self.assertEqual(bundle.sources[0].sha256, expected_hash)

    def test_rejects_invalid_database_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad.db"
            create_database(database, invalid_boolean=True)
            with self.assertRaisesRegex(KnowledgeImportError, "invalid boolean Trade"):
                import_technologies(database, "cache/bad.db", Ruleset("bnw", "test"))

    def test_rejects_missing_required_table(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "empty.db"
            sqlite3.connect(database).close()
            with self.assertRaisesRegex(KnowledgeImportError, "required table"):
                import_technologies(database, "cache/empty.db", Ruleset("bnw", "test"))


if __name__ == "__main__":
    unittest.main()
