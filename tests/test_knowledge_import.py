import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from civ5_agent.knowledge import Ruleset
from civ5_agent.knowledge.import_sqlite import (
    BRAVE_NEW_WORLD_PACKAGE_ID,
    BUILDING_CLASS_FIELDS,
    BUILDING_FIELDS,
    BUILDING_REFERENCE_COLUMNS,
    KnowledgeImportError,
    ERA_FIELDS,
    PROMOTION_FIELDS,
    PROMOTION_PREREQUISITE_COLUMNS,
    POLICY_BRANCH_FIELDS,
    POLICY_FIELDS,
    TECHNOLOGY_FIELDS,
    UNIT_FIELDS,
    UNIT_CLASS_FIELDS,
    import_ruleset,
)


def create_database(path: Path, *, invalid_boolean: bool = False) -> None:
    definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
    definitions.append("Era TEXT NOT NULL")
    for column, (_, value_type) in TECHNOLOGY_FIELDS.items():
        sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
        definitions.append(f'"{column}" {sql_type}')
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            "CREATE TABLE DownloadableContent (PackageID TEXT, IsActive INTEGER)"
        )
        connection.execute(
            "INSERT INTO DownloadableContent VALUES (?, 1)",
            (BRAVE_NEW_WORLD_PACKAGE_ID,),
        )
        connection.execute(f"CREATE TABLE Technologies ({', '.join(definitions)})")
        era_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        for column in ERA_FIELDS:
            era_definitions.append(f'"{column}" INTEGER')
        connection.execute(f"CREATE TABLE Eras ({', '.join(era_definitions)})")
        unit_definitions = ["Type TEXT NOT NULL PRIMARY KEY", "Class TEXT"]
        for column, (_, value_type) in UNIT_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            unit_definitions.append(f'"{column}" {sql_type}')
        connection.execute(f"CREATE TABLE Units ({', '.join(unit_definitions)})")
        unit_class_definitions = ["Type TEXT NOT NULL PRIMARY KEY", "DefaultUnit TEXT"]
        for column in UNIT_CLASS_FIELDS:
            unit_class_definitions.append(f'"{column}" INTEGER')
        connection.execute(
            f"CREATE TABLE UnitClasses ({', '.join(unit_class_definitions)})"
        )
        connection.execute(
            "CREATE TABLE Unit_ClassUpgrades (UnitType TEXT, UnitClassType TEXT)"
        )
        promotion_definitions = ["Type TEXT NOT NULL PRIMARY KEY", "TechPrereq TEXT"]
        promotion_definitions.extend(
            f'"{column}" TEXT' for column in PROMOTION_PREREQUISITE_COLUMNS
        )
        for column, (_, value_type) in PROMOTION_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            promotion_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE UnitPromotions ({', '.join(promotion_definitions)})"
        )
        connection.execute(
            "CREATE TABLE Unit_FreePromotions (UnitType TEXT, PromotionType TEXT)"
        )
        policy_definitions = [
            "Type TEXT NOT NULL PRIMARY KEY",
            "PolicyBranchType TEXT",
            "TechPrereq TEXT",
        ]
        for column, (_, value_type) in POLICY_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            policy_definitions.append(f'"{column}" {sql_type}')
        connection.execute(f"CREATE TABLE Policies ({', '.join(policy_definitions)})")
        branch_definitions = [
            "Type TEXT NOT NULL PRIMARY KEY",
            "EraPrereq TEXT",
            "FreePolicy TEXT",
            "FreeFinishingPolicy TEXT",
        ]
        for column, (_, value_type) in POLICY_BRANCH_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            branch_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE PolicyBranchTypes ({', '.join(branch_definitions)})"
        )
        connection.execute(
            "CREATE TABLE Policy_PrereqPolicies (PolicyType TEXT, PrereqPolicy TEXT)"
        )
        connection.execute(
            "CREATE TABLE Policy_PrereqORPolicies (PolicyType TEXT, PrereqPolicy TEXT)"
        )
        connection.execute(
            "CREATE TABLE Policy_Disables (PolicyType TEXT, PolicyDisable TEXT)"
        )
        connection.execute(
            "CREATE TABLE PolicyBranch_Disables "
            "(PolicyBranchType TEXT, PolicyBranchDisable TEXT)"
        )
        building_definitions = [
            "Type TEXT NOT NULL PRIMARY KEY",
            "BuildingClass TEXT",
        ]
        building_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in BUILDING_REFERENCE_COLUMNS
        )
        for column, (_, value_type) in BUILDING_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            building_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE Buildings ({', '.join(building_definitions)})"
        )
        building_class_definitions = [
            "Type TEXT NOT NULL PRIMARY KEY",
            "DefaultBuilding TEXT",
        ]
        for column, (_, value_type) in BUILDING_CLASS_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            building_class_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE BuildingClasses ({', '.join(building_class_definitions)})"
        )
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
        unit_class_columns = ["Type", "DefaultUnit", *UNIT_CLASS_FIELDS]
        quoted_unit_class_columns = ", ".join(
            f'"{column}"' for column in unit_class_columns
        )
        for type_id, default_unit in (
            ("UNITCLASS_WARRIOR", "UNIT_WARRIOR"),
            ("UNITCLASS_SWORDSMAN", "NONE"),
        ):
            connection.execute(
                f"INSERT INTO UnitClasses ({quoted_unit_class_columns}) VALUES "
                f"({', '.join('?' for _ in unit_class_columns)})",
                [type_id, default_unit, *([-1] * len(UNIT_CLASS_FIELDS))],
            )
        unit_columns = ["Type", "Class", *UNIT_FIELDS]
        unit_values = []
        for column, (_, value_type) in UNIT_FIELDS.items():
            if column == "Combat":
                value = 8
            elif column == "Cost":
                value = 40
            elif column == "PrereqTech":
                value = "TECH_AGRICULTURE"
            elif value_type == "boolean":
                value = 0
            elif value_type == "integer":
                value = 0
            else:
                value = None
            unit_values.append(value)
        connection.execute(
            f"INSERT INTO Units ({', '.join(f'\"{column}\"' for column in unit_columns)}) "
            f"VALUES ({', '.join('?' for _ in unit_columns)})",
            ["UNIT_WARRIOR", "UNITCLASS_WARRIOR", *unit_values],
        )
        connection.executemany(
            "INSERT INTO Unit_ClassUpgrades VALUES (?, ?)",
            [
                ("UNIT_WARRIOR", "UNITCLASS_SWORDSMAN"),
                ("UNIT_WARRIOR", "UNITCLASS_SWORDSMAN"),
            ],
        )
        promotion_columns = [
            "Type",
            "TechPrereq",
            *PROMOTION_PREREQUISITE_COLUMNS,
            *PROMOTION_FIELDS,
        ]
        quoted_promotion_columns = ", ".join(
            f'"{column}"' for column in promotion_columns
        )
        for type_id, or_prerequisite, tech_prerequisite, combat_percent in (
            ("PROMOTION_SHOCK_1", None, None, 15),
            ("PROMOTION_SHOCK_2", "PROMOTION_SHOCK_1", "TECH_AGRICULTURE", 15),
        ):
            promotion_values = []
            for column, (_, value_type) in PROMOTION_FIELDS.items():
                if column == "CombatPercent":
                    value = combat_percent
                elif value_type in {"boolean", "integer"}:
                    value = 0
                else:
                    value = None
                promotion_values.append(value)
            prerequisites = [None, or_prerequisite, *([None] * 8)]
            connection.execute(
                f"INSERT INTO UnitPromotions ({quoted_promotion_columns}) VALUES "
                f"({', '.join('?' for _ in promotion_columns)})",
                [type_id, tech_prerequisite, *prerequisites, *promotion_values],
            )
        connection.execute(
            "INSERT INTO Unit_FreePromotions VALUES (?, ?)",
            ("UNIT_WARRIOR", "PROMOTION_SHOCK_1"),
        )
        policy_columns = ["Type", "PolicyBranchType", "TechPrereq", *POLICY_FIELDS]
        quoted_policy_columns = ", ".join(f'"{column}"' for column in policy_columns)
        for type_id, culture_cost in (
            ("POLICY_TRADITION", 0),
            ("POLICY_TRADITION_FINISHER", 10),
        ):
            policy_values = []
            for column, (_, value_type) in POLICY_FIELDS.items():
                if column == "CultureCost":
                    value = culture_cost
                elif value_type in {"integer", "boolean"}:
                    value = 0
                else:
                    value = None
                policy_values.append(value)
            connection.execute(
                f"INSERT INTO Policies ({quoted_policy_columns}) VALUES "
                f"({', '.join('?' for _ in policy_columns)})",
                [type_id, "POLICY_BRANCH_TRADITION", None, *policy_values],
            )
        branch_columns = [
            "Type",
            "EraPrereq",
            "FreePolicy",
            "FreeFinishingPolicy",
            *POLICY_BRANCH_FIELDS,
        ]
        connection.execute(
            f"INSERT INTO PolicyBranchTypes "
            f"({', '.join(f'\"{column}\"' for column in branch_columns)}) VALUES "
            f"({', '.join('?' for _ in branch_columns)})",
            [
                "POLICY_BRANCH_TRADITION",
                "ERA_ANCIENT",
                "POLICY_TRADITION",
                "POLICY_TRADITION_FINISHER",
                *([0] * len(POLICY_BRANCH_FIELDS)),
            ],
        )
        connection.execute(
            "INSERT INTO Policy_PrereqPolicies VALUES (?, ?)",
            ("POLICY_TRADITION_FINISHER", "POLICY_TRADITION"),
        )
        building_columns = [
            "Type",
            "BuildingClass",
            *(column for column, _, _ in BUILDING_REFERENCE_COLUMNS),
            *BUILDING_FIELDS,
        ]
        building_values = []
        for column, (_, value_type) in BUILDING_FIELDS.items():
            if column == "Cost":
                value = 185
            elif value_type in {"integer", "boolean"}:
                value = 0
            else:
                value = None
            building_values.append(value)
        reference_values = {
            "PrereqTech": "TECH_AGRICULTURE",
        }
        connection.execute(
            f"INSERT INTO Buildings "
            f"({', '.join(f'\"{column}\"' for column in building_columns)}) VALUES "
            f"({', '.join('?' for _ in building_columns)})",
            [
                "BUILDING_PYRAMID",
                "BUILDINGCLASS_PYRAMID",
                *(reference_values.get(column) for column, _, _ in BUILDING_REFERENCE_COLUMNS),
                *building_values,
            ],
        )
        building_class_columns = [
            "Type",
            "DefaultBuilding",
            *BUILDING_CLASS_FIELDS,
        ]
        building_class_values = {
            "MaxGlobalInstances": 1,
            "MaxTeamInstances": -1,
            "MaxPlayerInstances": -1,
            "ExtraPlayerInstances": 0,
            "NoLimit": 0,
            "Monument": 0,
        }
        connection.execute(
            f"INSERT INTO BuildingClasses "
            f"({', '.join(f'\"{column}\"' for column in building_class_columns)}) "
            f"VALUES ({', '.join('?' for _ in building_class_columns)})",
            [
                "BUILDINGCLASS_PYRAMID",
                "BUILDING_PYRAMID",
                *(building_class_values[column] for column in BUILDING_CLASS_FIELDS),
            ],
        )
        connection.commit()


class RulesetImportTest(unittest.TestCase):
    def test_imports_allowlisted_facts_and_relationships(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Civ5DebugDatabase.db"
            create_database(database)
            bundle = import_ruleset(
                database,
                "cache/Civ5DebugDatabase.db",
                Ruleset("bnw", "1.0.3.279"),
            )
        self.assertEqual(len(bundle.entities), 13)
        self.assertEqual(len(bundle.references), 18)
        self.assertEqual(bundle.ruleset.dlc, (BRAVE_NEW_WORLD_PACKAGE_ID,))
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
        warrior = next(item for item in bundle.entities if item.type_id == "UNIT_WARRIOR")
        self.assertEqual(warrior.attributes["combat"], 8)
        self.assertEqual(warrior.attributes["cost"], 40)
        self.assertNotIn("default_unit_ai", warrior.attributes)
        self.assertNotIn("unit_class", warrior.attributes)
        shock = next(item for item in bundle.entities if item.type_id == "PROMOTION_SHOCK_2")
        self.assertEqual(shock.attributes["combat_percent"], 15)
        promotion_relations = {
            item.kind
            for item in bundle.references
            if item.source_type_id in {"PROMOTION_SHOCK_2", "UNIT_WARRIOR"}
            and item.kind
            in {"requires_any", "unlocked_by_technology", "starts_with_promotion"}
        }
        self.assertEqual(
            promotion_relations,
            {"requires_any", "unlocked_by_technology", "starts_with_promotion"},
        )
        warrior_relations = {
            (item.kind, item.target_type_id)
            for item in bundle.references
            if item.source_type_id == "UNIT_WARRIOR"
        }
        self.assertIn(
            ("belongs_to_unit_class", "UNITCLASS_WARRIOR"), warrior_relations
        )
        self.assertIn(
            ("upgrades_to_unit_class", "UNITCLASS_SWORDSMAN"), warrior_relations
        )
        self.assertEqual(
            sum(
                item.kind == "upgrades_to_unit_class"
                for item in bundle.references
            ),
            1,
        )
        tradition = next(item for item in bundle.entities if item.type_id == "POLICY_TRADITION")
        self.assertEqual(tradition.attributes["culture_cost"], 0)
        policy_relations = {
            (item.kind, item.source_type_id, item.target_type_id)
            for item in bundle.references
            if item.source_kind in {"policy", "policy_branch"}
        }
        self.assertIn(
            (
                "belongs_to_policy_branch",
                "POLICY_TRADITION",
                "POLICY_BRANCH_TRADITION",
            ),
            policy_relations,
        )
        pyramid = next(item for item in bundle.entities if item.type_id == "BUILDING_PYRAMID")
        self.assertEqual(pyramid.attributes["cost"], 185)
        pyramid_class = next(
            item for item in bundle.entities if item.type_id == "BUILDINGCLASS_PYRAMID"
        )
        self.assertEqual(pyramid_class.attributes["maximum_global_instances"], 1)
        building_relations = {
            (item.kind, item.source_type_id, item.target_type_id)
            for item in bundle.references
            if item.source_kind in {"building", "building_class"}
        }
        self.assertIn(
            (
                "belongs_to_building_class",
                "BUILDING_PYRAMID",
                "BUILDINGCLASS_PYRAMID",
            ),
            building_relations,
        )
        self.assertIn(
            ("unlocked_by_technology", "BUILDING_PYRAMID", "TECH_AGRICULTURE"),
            building_relations,
        )
        self.assertIn(
            ("default_building", "BUILDINGCLASS_PYRAMID", "BUILDING_PYRAMID"),
            building_relations,
        )
        self.assertIn(
            ("requires_all", "POLICY_TRADITION_FINISHER", "POLICY_TRADITION"),
            policy_relations,
        )
        self.assertIn(
            ("unlocked_by_era", "POLICY_BRANCH_TRADITION", "ERA_ANCIENT"),
            policy_relations,
        )

    def test_records_source_hash_without_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Civ5DebugDatabase.db"
            create_database(database)
            expected_hash = hashlib.sha256(database.read_bytes()).hexdigest()
            bundle = import_ruleset(
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
                import_ruleset(database, "cache/bad.db", Ruleset("bnw", "test"))

    def test_rejects_missing_required_table(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "empty.db"
            sqlite3.connect(database).close()
            with self.assertRaisesRegex(KnowledgeImportError, "required table"):
                import_ruleset(database, "cache/empty.db", Ruleset("bnw", "test"))

    def test_rejects_mislabeled_ruleset_family(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Civ5DebugDatabase.db"
            create_database(database)
            with self.assertRaisesRegex(KnowledgeImportError, "does not match detected bnw"):
                import_ruleset(
                    database,
                    "cache/Civ5DebugDatabase.db",
                    Ruleset("vanilla", "test"),
                )

    def test_rejects_declared_dlc_that_does_not_match_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "Civ5DebugDatabase.db"
            create_database(database)
            with self.assertRaisesRegex(KnowledgeImportError, "DLC package IDs"):
                import_ruleset(
                    database,
                    "cache/Civ5DebugDatabase.db",
                    Ruleset("bnw", "test", ("Expansion2",)),
                )


if __name__ == "__main__":
    unittest.main()
