import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from civ5_agent.knowledge import KnowledgeValidationError, ReferenceContext, Ruleset
from civ5_agent.knowledge.import_sqlite import (
    ANCIENT_RUIN_FIELDS,
    ANCIENT_RUIN_REFERENCE_COLUMNS,
    ATTRIBUTED_REFERENCE_TABLES,
    BRAVE_NEW_WORLD_PACKAGE_ID,
    BELIEF_FIELDS,
    BELIEF_REFERENCE_COLUMNS,
    BUILD_FIELDS,
    BUILD_FEATURE_FIELDS,
    BUILD_REFERENCE_COLUMNS,
    CONTEXTUAL_REFERENCE_TABLES,
    CONTEXTUAL_QUANTITY_REFERENCE_TABLES,
    BUILDING_CLASS_FIELDS,
    BUILDING_FIELDS,
    BUILDING_REFERENCE_COLUMNS,
    CLIMATE_FIELDS,
    CIVILIZATION_FIELDS,
    KnowledgeImportError,
    ERA_FIELDS,
    FEATURE_FIELDS,
    FAKE_FEATURE_FIELDS,
    FEATURE_REFERENCE_COLUMNS,
    GAME_OPTION_FIELDS,
    IMPROVEMENT_FIELDS,
    IMPROVEMENT_REFERENCE_COLUMNS,
    LEAGUE_PROJECT_FIELDS,
    LEAGUE_PROJECT_REFERENCE_COLUMNS,
    LEAGUE_PROJECT_REWARD_FIELDS,
    LEAGUE_PROJECT_REWARD_REFERENCE_COLUMNS,
    LEAGUE_SPECIAL_SESSION_FIELDS,
    LEAGUE_SPECIAL_SESSION_REFERENCE_COLUMNS,
    HURRY_FIELDS,
    GAME_SPEED_FIELDS,
    GREAT_WORK_ARTIFACT_CLASS_FIELDS,
    GREAT_WORK_FIELDS,
    GLOBAL_DEFINE_VALUE_TYPES,
    HANDICAP_FIELDS,
    PROMOTION_FIELDS,
    PROMOTION_PREREQUISITE_COLUMNS,
    PROMOTION_VISIBILITY_REFERENCE_COLUMNS,
    POLICY_BRANCH_FIELDS,
    POLICY_FIELDS,
    PLAIN_REFERENCE_TABLES,
    PROCESS_REFERENCE_COLUMNS,
    PROJECT_FIELDS,
    PROJECT_REFERENCE_COLUMNS,
    QUANTITY_REFERENCE_TABLES,
    RESOURCE_CLASS_FIELDS,
    RESOURCE_FIELDS,
    RESOURCE_REFERENCE_COLUMNS,
    RESOLUTION_FIELDS,
    RESOLUTION_REFERENCE_COLUMNS,
    ROUTE_FIELDS,
    SEA_LEVEL_FIELDS,
    SPECIAL_UNIT_FIELDS,
    SPECIALIST_FIELDS,
    TECHNOLOGY_FIELDS,
    THEMING_BONUS_BOOLEAN_COLUMNS,
    TRAIT_FIELDS,
    TRAIT_REFERENCE_COLUMNS,
    TERRAIN_FIELDS,
    UNIT_FIELDS,
    UNIT_CLASS_FIELDS,
    UNIT_REFERENCE_COLUMNS,
    VICTORY_FIELDS,
    VOTE_FIELDS,
    VOTE_SOURCE_FIELDS,
    VOTE_SOURCE_REFERENCE_COLUMNS,
    WORLD_SIZE_FIELDS,
    YIELD_FIELDS,
    import_ruleset,
)


FIXTURE_TYPE_IDS = {
    "belief": "BELIEF_TEST",
    "build": "BUILD_TEST",
    "building": "BUILDING_PYRAMID",
    "building_class": "BUILDINGCLASS_PYRAMID",
    "civilization": "CIVILIZATION_TEST",
    "feature": "FEATURE_TEST",
    "improvement": "IMPROVEMENT_TEST",
    "hurry": "HURRY_TEST",
    "great_work_class": "GREAT_WORK_CLASS_TEST",
    "great_work_slot": "GREAT_WORK_SLOT_TEST",
    "great_work": "GREAT_WORK_TEST",
    "great_work_artifact_class": "ARTIFACT_TEST",
    "handicap": "HANDICAP_PRINCE",
    "ancient_ruin_outcome": "GOODY_TEST",
    "league_project": "LEAGUE_PROJECT_TEST",
    "league_project_reward": "LEAGUE_PROJECT_REWARD_TEST",
    "league_special_session": "LEAGUE_SPECIAL_SESSION_TEST",
    "policy": "POLICY_TRADITION",
    "process": "PROCESS_TEST",
    "project": "PROJECT_TEST",
    "promotion": "PROMOTION_SHOCK_1",
    "resource": "RESOURCE_IRON",
    "resolution": "RESOLUTION_TEST",
    "resolution_decision": "RESOLUTION_DECISION_TEST",
    "region": "REGION_TEST",
    "route": "ROUTE_TEST",
    "special_unit": "SPECIALUNIT_TEST",
    "specialist": "SPECIALIST_TEST",
    "technology": "TECH_AGRICULTURE",
    "terrain": "TERRAIN_TEST",
    "trait": "TRAIT_TEST",
    "unit": "UNIT_WARRIOR",
    "unit_class": "UNITCLASS_WARRIOR",
    "unit_combat": "UNITCOMBAT_MELEE",
    "victory": "VICTORY_TEST",
    "vote": "VOTE_TEST",
    "vote_source": "DIPLOVOTE_TEST",
    "yield": "YIELD_TEST",
    "domain": "DOMAIN_LAND",
    "era": "ERA_ANCIENT",
}


def fixture_reference_attributes(fields):
    values = []
    attributes = {}
    for index, (_column, attribute, value_type) in enumerate(fields):
        if value_type == "optional_integer" and index == 0:
            values.append(None)
            continue
        value = 1 if value_type == "boolean" else index + 1
        values.append(value)
        attributes[attribute] = bool(value) if value_type == "boolean" else value
    return values, tuple(sorted(attributes.items()))


def create_database(
    path: Path, *, invalid_boolean: bool = False, invalid_number: bool = False
) -> None:
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
        connection.execute("CREATE TABLE Defines (Name TEXT PRIMARY KEY, Value)")
        connection.executemany(
            "INSERT INTO Defines VALUES (?, ?)",
            [
                (
                    name,
                    1.5 if value_type == "number" else 10,
                )
                for name, value_type in GLOBAL_DEFINE_VALUE_TYPES.items()
            ]
            + [("AI_TEST_DEFINE", 999)],
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
        connection.execute(
            "CREATE TABLE UnitCombatInfos (Type TEXT NOT NULL PRIMARY KEY)"
        )
        connection.execute("CREATE TABLE Domains (Type TEXT NOT NULL PRIMARY KEY)")
        special_unit_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        special_unit_definitions.extend(
            f'"{column}" INTEGER' for column in SPECIAL_UNIT_FIELDS
        )
        connection.execute(
            f"CREATE TABLE SpecialUnits ({', '.join(special_unit_definitions)})"
        )
        hurry_definitions = [
            "Type TEXT NOT NULL PRIMARY KEY",
            "PolicyPrereq TEXT",
            *(f'"{column}" INTEGER' for column in HURRY_FIELDS),
        ]
        connection.execute(
            f"CREATE TABLE HurryInfos ({', '.join(hurry_definitions)})"
        )
        connection.execute(
            "CREATE TABLE GreatWorkSlots (Type TEXT NOT NULL PRIMARY KEY)"
        )
        connection.execute(
            "CREATE TABLE GreatWorkClasses "
            "(Type TEXT NOT NULL PRIMARY KEY, SlotType TEXT)"
        )
        connection.execute(
            "CREATE TABLE GreatWorkArtifactClasses "
            "(Type TEXT NOT NULL PRIMARY KEY, Value INTEGER)"
        )
        connection.execute(
            "CREATE TABLE GreatWorks "
            "(Type TEXT NOT NULL PRIMARY KEY, GreatWorkClassType TEXT, "
            "ArtifactClassType TEXT, EraType TEXT, ArchaeologyOnly INTEGER)"
        )
        connection.execute(
            "CREATE TABLE Unit_UniqueNames (UnitType TEXT, GreatWorkType TEXT)"
        )
        connection.execute(
            "CREATE TABLE UnitPromotions_UnitCombats "
            "(PromotionType TEXT, UnitCombatType TEXT)"
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
        connection.execute(
            "CREATE TABLE Building_ThemingBonuses ("
            "BuildingType TEXT, Description TEXT, Bonus INTEGER, "
            + ", ".join(
                f'"{column}" INTEGER' for column in THEMING_BONUS_BOOLEAN_COLUMNS
            )
            + ", AIPriority INTEGER)"
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
        resource_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        resource_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in RESOURCE_REFERENCE_COLUMNS
        )
        for column, (_, value_type) in RESOURCE_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            resource_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE Resources ({', '.join(resource_definitions)})"
        )
        resource_class_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        for column, (_, value_type) in RESOURCE_CLASS_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            resource_class_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE ResourceClasses ({', '.join(resource_class_definitions)})"
        )
        civilization_definitions = [
            "Type TEXT NOT NULL PRIMARY KEY",
            "Playable INTEGER",
            "AIPlayable INTEGER",
        ]
        connection.execute(
            f"CREATE TABLE Civilizations ({', '.join(civilization_definitions)})"
        )
        connection.execute(
            "CREATE TABLE Leaders ("
            "Type TEXT NOT NULL PRIMARY KEY, Boldness INTEGER)"
        )
        trait_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        trait_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in TRAIT_REFERENCE_COLUMNS
        )
        for column, (_, value_type) in TRAIT_FIELDS.items():
            sql_type = "TEXT" if value_type == "identifier" else "INTEGER"
            trait_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE Traits ({', '.join(trait_definitions)})"
        )
        connection.execute(
            "CREATE TABLE Civilization_Leaders "
            "(CivilizationType TEXT, LeaderheadType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Leader_Traits (LeaderType TEXT, TraitType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Civilization_UnitClassOverrides "
            "(CivilizationType TEXT, UnitClassType TEXT, UnitType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Civilization_BuildingClassOverrides "
            "(CivilizationType TEXT, BuildingClassType TEXT, BuildingType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Civilization_Start_Along_Ocean "
            "(CivilizationType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Civilization_Start_Place_First_Along_Ocean "
            "(CivilizationType TEXT)"
        )
        connection.execute("CREATE TABLE Religions (Type TEXT NOT NULL PRIMARY KEY)")
        belief_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        belief_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in BELIEF_REFERENCE_COLUMNS
        )
        for column, (_, value_type) in BELIEF_FIELDS.items():
            sql_type = "REAL" if value_type == "number" else "INTEGER"
            belief_definitions.append(f'"{column}" {sql_type}')
        connection.execute(
            f"CREATE TABLE Beliefs ({', '.join(belief_definitions)})"
        )
        specialist_definitions = [
            "Type TEXT NOT NULL PRIMARY KEY",
            "GreatPeopleUnitClass TEXT",
        ]
        specialist_definitions.extend(
            f'"{column}" INTEGER' for column in SPECIALIST_FIELDS
        )
        connection.execute(
            f"CREATE TABLE Specialists ({', '.join(specialist_definitions)})"
        )
        connection.execute(
            "CREATE TABLE Civilization_Religions "
            "(CivilizationType TEXT, ReligionType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Unit_GreatPersons "
            "(UnitType TEXT, GreatPersonType TEXT)"
        )
        for table, fields in (
            ("Terrains", TERRAIN_FIELDS),
            ("Routes", ROUTE_FIELDS),
            ("Yields", YIELD_FIELDS),
        ):
            table_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
            table_definitions.extend(f'"{column}" INTEGER' for column in fields)
            if table == "Yields":
                table_definitions.append('"AIWeightPercent" INTEGER')
            connection.execute(
                f"CREATE TABLE {table} ({', '.join(table_definitions)})"
            )
        feature_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        feature_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in FEATURE_REFERENCE_COLUMNS
        )
        feature_definitions.extend(f'"{column}" INTEGER' for column in FEATURE_FIELDS)
        connection.execute(
            f"CREATE TABLE Features ({', '.join(feature_definitions)})"
        )
        fake_feature_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        fake_feature_definitions.extend(
            f'"{column}" INTEGER' for column in FAKE_FEATURE_FIELDS
        )
        connection.execute(
            f"CREATE TABLE FakeFeatures ({', '.join(fake_feature_definitions)})"
        )
        improvement_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        improvement_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in IMPROVEMENT_REFERENCE_COLUMNS
        )
        improvement_definitions.extend(
            f'"{column}" INTEGER' for column in IMPROVEMENT_FIELDS
        )
        connection.execute(
            f"CREATE TABLE Improvements ({', '.join(improvement_definitions)})"
        )
        build_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        build_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in BUILD_REFERENCE_COLUMNS
        )
        build_definitions.extend(f'"{column}" INTEGER' for column in BUILD_FIELDS)
        connection.execute(f"CREATE TABLE Builds ({', '.join(build_definitions)})")
        connection.execute(
            "CREATE TABLE BuildFeatures ("
            "BuildType TEXT, FeatureType TEXT, PrereqTech TEXT, "
            "Time INTEGER, Production INTEGER, Cost INTEGER, Remove INTEGER)"
        )
        project_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        project_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in PROJECT_REFERENCE_COLUMNS
        )
        project_definitions.extend(
            f'"{column}" INTEGER' for column in PROJECT_FIELDS
        )
        connection.execute(
            f"CREATE TABLE Projects ({', '.join(project_definitions)})"
        )
        process_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        process_definitions.extend(
            f'"{column}" TEXT' for column, _, _ in PROCESS_REFERENCE_COLUMNS
        )
        connection.execute(
            f"CREATE TABLE Processes ({', '.join(process_definitions)})"
        )
        victory_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        victory_definitions.extend(
            f'"{column}" INTEGER' for column in VICTORY_FIELDS
        )
        connection.execute(
            f"CREATE TABLE Victories ({', '.join(victory_definitions)})"
        )
        for table, fields, excluded_columns in (
            ("GameSpeeds", GAME_SPEED_FIELDS, ("Description", "PortraitIndex")),
            (
                "HandicapInfos",
                HANDICAP_FIELDS,
                (
                    "Description",
                    "CityProductionNumOptionsConsidered",
                    "AIDeclareWarProb",
                ),
            ),
            ("Worlds", WORLD_SIZE_FIELDS, ("Description", "PortraitIndex")),
        ):
            definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
            definitions.extend(f'"{column}" INTEGER' for column in fields)
            definitions.extend(
                f'"{column}" {"TEXT" if column == "Description" else "INTEGER"}'
                for column in excluded_columns
            )
            connection.execute(
                f'CREATE TABLE "{table}" ({", ".join(definitions)})'
            )
        for table, fields, extra_columns in (
            ("Climates", CLIMATE_FIELDS, ("Description TEXT",)),
            ("SeaLevels", SEA_LEVEL_FIELDS, ("Description TEXT",)),
            (
                "GameOptions",
                GAME_OPTION_FIELDS,
                ("Description TEXT", "Help TEXT", "Visible INTEGER"),
            ),
        ):
            definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
            definitions.extend(
                f'"{column}" {"REAL" if value_type == "number" else "INTEGER"}'
                for column, (_attribute, value_type) in fields.items()
            )
            definitions.extend(extra_columns)
            connection.execute(
                f'CREATE TABLE "{table}" ({", ".join(definitions)})'
            )
        connection.execute(
            "CREATE TABLE InvisibleInfos ("
            "Type TEXT NOT NULL PRIMARY KEY, Description TEXT)"
        )
        goody_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        goody_definitions.extend(
            f'"{column}" TEXT'
            for column, _kind, _target_kind in ANCIENT_RUIN_REFERENCE_COLUMNS
        )
        goody_definitions.extend(
            f'"{column}" INTEGER' for column in ANCIENT_RUIN_FIELDS
        )
        goody_definitions.extend(("Description TEXT", "Sound TEXT"))
        connection.execute(
            f'CREATE TABLE GoodyHuts ({", ".join(goody_definitions)})'
        )
        for table, fields, references in (
            (
                "LeagueProjectRewards",
                LEAGUE_PROJECT_REWARD_FIELDS,
                LEAGUE_PROJECT_REWARD_REFERENCE_COLUMNS,
            ),
            (
                "LeagueProjects",
                LEAGUE_PROJECT_FIELDS,
                LEAGUE_PROJECT_REFERENCE_COLUMNS,
            ),
            (
                "LeagueSpecialSessions",
                LEAGUE_SPECIAL_SESSION_FIELDS,
                LEAGUE_SPECIAL_SESSION_REFERENCE_COLUMNS,
            ),
            ("Resolutions", RESOLUTION_FIELDS, RESOLUTION_REFERENCE_COLUMNS),
            ("VoteSources", VOTE_SOURCE_FIELDS, VOTE_SOURCE_REFERENCE_COLUMNS),
        ):
            definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
            definitions.extend(
                f'"{column}" TEXT'
                for column, _kind, _target_kind in references
            )
            definitions.extend(f'"{column}" INTEGER' for column in fields)
            definitions.extend(("Description TEXT", "Help TEXT"))
            connection.execute(
                f'CREATE TABLE "{table}" ({", ".join(definitions)})'
            )
        connection.execute(
            "CREATE TABLE ResolutionDecisions ("
            "Type TEXT NOT NULL PRIMARY KEY, Description TEXT)"
        )
        vote_definitions = ["Type TEXT NOT NULL PRIMARY KEY"]
        vote_definitions.extend(f'"{column}" INTEGER' for column in VOTE_FIELDS)
        vote_definitions.append("Description TEXT")
        connection.execute(
            f'CREATE TABLE Votes ({", ".join(vote_definitions)})'
        )
        connection.execute(
            "CREATE TABLE MinorCivTraits ("
            "Type TEXT NOT NULL PRIMARY KEY, Description TEXT, TraitIcon TEXT)"
        )
        connection.execute(
            "CREATE TABLE MinorCivilizations ("
            "Type TEXT NOT NULL PRIMARY KEY, MinorCivTrait TEXT NOT NULL, "
            "Description TEXT, Civilopedia TEXT, ArtDefineTag TEXT)"
        )
        connection.execute(
            "CREATE TABLE Project_VictoryThresholds "
            "(ProjectType TEXT, VictoryType TEXT, Threshold INTEGER, "
            "MinThreshold INTEGER)"
        )
        connection.execute(
            "CREATE TABLE Feature_TerrainBooleans "
            "(FeatureType TEXT, TerrainType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Improvement_ValidTerrains "
            "(ImprovementType TEXT, TerrainType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Improvement_ValidFeatures "
            "(ImprovementType TEXT, FeatureType TEXT)"
        )
        connection.execute(
            "CREATE TABLE Improvement_ValidImprovements "
            "(ImprovementType TEXT, PrereqImprovement TEXT)"
        )
        for (
            table,
            source_column,
            target_column,
            _kind,
            _source_kind,
            _target_kind,
        ) in PLAIN_REFERENCE_TABLES:
            connection.execute(
                f'CREATE TABLE "{table}" '
                f'("{source_column}" TEXT, "{target_column}" TEXT)'
            )
        for (
            table,
            source_column,
            target_column,
            _kind,
            _source_kind,
            _target_kind,
            value_column,
            _attribute,
        ) in QUANTITY_REFERENCE_TABLES:
            connection.execute(
                f'CREATE TABLE "{table}" ('
                f'"{source_column}" TEXT, "{target_column}" TEXT, '
                f'"{value_column}" INTEGER)'
            )
        for (
            table,
            source_column,
            target_column,
            _kind,
            _source_kind,
            _target_kind,
            context_column,
            _context_kind,
            _context_role,
            value_column,
            _attribute,
        ) in CONTEXTUAL_QUANTITY_REFERENCE_TABLES:
            connection.execute(
                f'CREATE TABLE "{table}" ('
                f'"{source_column}" TEXT, "{target_column}" TEXT, '
                f'"{context_column}" TEXT, "{value_column}" INTEGER)'
            )
        for (
            table,
            source_column,
            target_column,
            _kind,
            _source_kind,
            _target_kind,
            context_column,
            _context_kind,
            _context_role,
        ) in CONTEXTUAL_REFERENCE_TABLES:
            connection.execute(
                f'CREATE TABLE "{table}" ('
                f'"{source_column}" TEXT, "{target_column}" TEXT, '
                f'"{context_column}" TEXT)'
            )
        for (
            table,
            source_column,
            target_column,
            _kind,
            _source_kind,
            _target_kind,
            fields,
        ) in ATTRIBUTED_REFERENCE_TABLES:
            definitions = [f'"{source_column}" TEXT', f'"{target_column}" TEXT']
            definitions.extend(f'"{column}" INTEGER' for column, _, _ in fields)
            if table in {"UnitPromotions_Features", "UnitPromotions_Terrains"}:
                definitions.append('"PassableTech" TEXT')
            connection.execute(
                f'CREATE TABLE "{table}" ({", ".join(definitions)})'
            )
        connection.execute(
            "CREATE TABLE Building_TechEnhancedYieldChanges "
            "(BuildingType TEXT, YieldType TEXT, Yield INTEGER)"
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
        connection.execute(
            "INSERT INTO UnitCombatInfos VALUES (?)", ("UNITCOMBAT_MELEE",)
        )
        connection.execute("INSERT INTO Domains VALUES (?)", ("DOMAIN_LAND",))
        connection.execute(
            "INSERT INTO SpecialUnits VALUES (?, ?, ?)",
            ("SPECIALUNIT_TEST", 1, 0),
        )
        connection.execute(
            f"INSERT INTO HurryInfos VALUES "
            f"({', '.join('?' for _ in range(2 + len(HURRY_FIELDS)))})",
            ("HURRY_TEST", "POLICY_TRADITION", *([1] * len(HURRY_FIELDS))),
        )
        connection.execute(
            "INSERT INTO GreatWorkSlots VALUES (?)",
            ("GREAT_WORK_SLOT_TEST",),
        )
        connection.execute(
            "INSERT INTO GreatWorkClasses VALUES (?, ?)",
            ("GREAT_WORK_CLASS_TEST", "GREAT_WORK_SLOT_TEST"),
        )
        connection.execute(
            "INSERT INTO GreatWorkArtifactClasses VALUES (?, ?)",
            ("ARTIFACT_TEST", 1),
        )
        connection.execute(
            "INSERT INTO GreatWorks VALUES (?, ?, ?, ?, ?)",
            (
                "GREAT_WORK_TEST",
                "GREAT_WORK_CLASS_TEST",
                "ARTIFACT_TEST",
                "ERA_ANCIENT",
                1,
            ),
        )
        connection.execute(
            "INSERT INTO Unit_UniqueNames VALUES (?, ?)",
            ("UNIT_WARRIOR", "GREAT_WORK_TEST"),
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
        quoted_unit_columns = ", ".join(f'"{column}"' for column in unit_columns)
        unit_values = []
        for column, (_, value_type) in UNIT_FIELDS.items():
            if column == "Combat":
                value = 8
            elif column == "Cost":
                value = 40
            elif column == "PrereqTech":
                value = "TECH_AGRICULTURE"
            elif column == "CombatClass":
                value = "UNITCOMBAT_MELEE"
            elif column == "Domain":
                value = "DOMAIN_LAND"
            elif column == "Special":
                value = "SPECIALUNIT_TEST"
            elif column == "Capture":
                value = "UNITCLASS_WARRIOR"
            elif column in {"PillagePrereqTech", "PrereqTech", "ObsoleteTech"}:
                value = "TECH_AGRICULTURE"
            elif column == "GoodyHutUpgradeUnitClass":
                value = "UNITCLASS_WARRIOR"
            elif column == "PolicyType":
                value = "POLICY_TRADITION"
            elif column == "SpecialCargo":
                value = "SPECIALUNIT_TEST"
            elif column == "DomainCargo":
                value = "DOMAIN_LAND"
            elif column in {"ProjectPrereq", "SpaceshipProject"}:
                value = "PROJECT_TEST"
            elif column == "LeaderPromotion":
                value = "PROMOTION_SHOCK_1"
            elif value_type == "boolean":
                value = 0
            elif value_type == "integer":
                value = 0
            else:
                value = None
            unit_values.append(value)
        connection.execute(
            f"INSERT INTO Units ({quoted_unit_columns}) "
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
                elif column in {"Invisible", "SeeInvisible"} and type_id == "PROMOTION_SHOCK_1":
                    value = "INVISIBLE_TEST"
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
        connection.execute(
            "INSERT INTO UnitPromotions_UnitCombats VALUES (?, ?)",
            ("PROMOTION_SHOCK_1", "UNITCOMBAT_MELEE"),
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
        quoted_branch_columns = ", ".join(
            f'"{column}"' for column in branch_columns
        )
        connection.execute(
            f"INSERT INTO PolicyBranchTypes "
            f"({quoted_branch_columns}) VALUES "
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
        quoted_building_columns = ", ".join(
            f'"{column}"' for column in building_columns
        )
        building_values = []
        for column, (_, value_type) in BUILDING_FIELDS.items():
            if column == "Cost":
                value = 185
            elif column == "GreatWorkSlotType":
                value = "GREAT_WORK_SLOT_TEST"
            elif column == "FreeGreatWork":
                value = "GREAT_WORK_TEST"
            elif value_type in {"integer", "boolean"}:
                value = 0
            else:
                value = None
            building_values.append(value)
        reference_values = {
            "EnhancedYieldTech": "TECH_POTTERY",
            "PrereqTech": "TECH_AGRICULTURE",
        }
        connection.execute(
            f"INSERT INTO Buildings "
            f"({quoted_building_columns}) VALUES "
            f"({', '.join('?' for _ in building_columns)})",
            [
                "BUILDING_PYRAMID",
                "BUILDINGCLASS_PYRAMID",
                *(reference_values.get(column) for column, _, _ in BUILDING_REFERENCE_COLUMNS),
                *building_values,
            ],
        )
        theming_columns = [
            "BuildingType",
            "Description",
            "Bonus",
            *THEMING_BONUS_BOOLEAN_COLUMNS,
            "AIPriority",
        ]
        theming_insert = (
            "INSERT INTO Building_ThemingBonuses ("
            + ", ".join(f'"{column}"' for column in theming_columns)
            + ") VALUES ("
            + ", ".join("?" for _ in theming_columns)
            + ")"
        )
        connection.execute(
            theming_insert,
            (
                "BUILDING_PYRAMID",
                "TXT_KEY_TEST_DESCRIPTION",
                2,
                *(
                    1 if column in {"SameEra", "MustBeArt", "RequiresOwner"} else None
                    for column in THEMING_BONUS_BOOLEAN_COLUMNS
                ),
                99,
            ),
        )
        connection.execute(
            theming_insert,
            (
                "BUILDING_PYRAMID",
                "TXT_KEY_ANOTHER_DESCRIPTION",
                1,
                *(
                    1
                    if column in {"UniqueEras", "MustBeArtifact"}
                    else None
                    for column in THEMING_BONUS_BOOLEAN_COLUMNS
                ),
                88,
            ),
        )
        connection.execute(
            "INSERT INTO Building_TechEnhancedYieldChanges VALUES (?, ?, ?)",
            ("BUILDING_PYRAMID", "YIELD_TEST", 2),
        )
        building_class_columns = [
            "Type",
            "DefaultBuilding",
            *BUILDING_CLASS_FIELDS,
        ]
        quoted_building_class_columns = ", ".join(
            f'"{column}"' for column in building_class_columns
        )
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
            f"({quoted_building_class_columns}) "
            f"VALUES ({', '.join('?' for _ in building_class_columns)})",
            [
                "BUILDINGCLASS_PYRAMID",
                "BUILDING_PYRAMID",
                *(building_class_values[column] for column in BUILDING_CLASS_FIELDS),
            ],
        )
        resource_class_columns = ["Type", *RESOURCE_CLASS_FIELDS]
        quoted_resource_class_columns = ", ".join(
            f'"{column}"' for column in resource_class_columns
        )
        connection.execute(
            f"INSERT INTO ResourceClasses "
            f"({quoted_resource_class_columns}) "
            f"VALUES ({', '.join('?' for _ in resource_class_columns)})",
            ["RESOURCECLASS_RUSH", *([1] * len(RESOURCE_CLASS_FIELDS))],
        )
        resource_columns = [
            "Type",
            *(column for column, _, _ in RESOURCE_REFERENCE_COLUMNS),
            *RESOURCE_FIELDS,
        ]
        quoted_resource_columns = ", ".join(
            f'"{column}"' for column in resource_columns
        )
        resource_values = []
        for column, (_, value_type) in RESOURCE_FIELDS.items():
            if column == "StartingResourceQuantity":
                value = 2
            elif column == "ResourceUsage":
                value = 1
            elif value_type in {"integer", "boolean"}:
                value = 0
            else:
                value = None
            resource_values.append(value)
        resource_reference_values = {
            "ResourceClassType": "RESOURCECLASS_RUSH",
            "TechReveal": "TECH_AGRICULTURE",
        }
        connection.execute(
            f"INSERT INTO Resources "
            f"({quoted_resource_columns}) VALUES "
            f"({', '.join('?' for _ in resource_columns)})",
            [
                "RESOURCE_IRON",
                *(
                    resource_reference_values.get(column)
                    for column, _, _ in RESOURCE_REFERENCE_COLUMNS
                ),
                *resource_values,
            ],
        )
        civilization_columns = ["Type", *CIVILIZATION_FIELDS, "AIPlayable"]
        connection.execute(
            f"INSERT INTO Civilizations "
            f"({', '.join(civilization_columns)}) VALUES "
            f"({', '.join('?' for _ in civilization_columns)})",
            ["CIVILIZATION_TEST", 1, 0],
        )
        connection.execute(
            "INSERT INTO Leaders (Type, Boldness) VALUES (?, ?)",
            ("LEADER_TEST", 10),
        )
        trait_columns = [
            "Type",
            *(column for column, _, _ in TRAIT_REFERENCE_COLUMNS),
            *TRAIT_FIELDS,
        ]
        trait_reference_values = {
            "FreeUnit": "UNITCLASS_WARRIOR",
            "FreeUnitPrereqTech": "TECH_AGRICULTURE",
            "CombatBonusImprovement": "IMPROVEMENT_TEST",
            "FreeBuilding": "BUILDING_PYRAMID",
            "PrereqTech": "TECH_POTTERY",
        }
        trait_values = []
        for column, (_, value_type) in TRAIT_FIELDS.items():
            if column == "WonderProductionModifier":
                value = 20
            elif column == "MoveFriendlyWoodsAsRoad":
                value = 1
            elif value_type in {"integer", "boolean"}:
                value = 0
            else:
                value = None
            trait_values.append(value)
        connection.execute(
            f"INSERT INTO Traits "
            f"({', '.join(trait_columns)}) VALUES "
            f"({', '.join('?' for _ in trait_columns)})",
            [
                "TRAIT_TEST",
                *(
                    trait_reference_values.get(column)
                    for column, _, _ in TRAIT_REFERENCE_COLUMNS
                ),
                *trait_values,
            ],
        )
        connection.execute(
            "INSERT INTO Civilization_Leaders VALUES (?, ?)",
            ("CIVILIZATION_TEST", "LEADER_TEST"),
        )
        connection.execute(
            "INSERT INTO Leader_Traits VALUES (?, ?)",
            ("LEADER_TEST", "TRAIT_TEST"),
        )
        connection.executemany(
            "INSERT INTO Civilization_UnitClassOverrides VALUES (?, ?, ?)",
            [
                ("CIVILIZATION_TEST", "UNITCLASS_WARRIOR", None),
                ("CIVILIZATION_TEST", "UNITCLASS_WARRIOR", "UNIT_WARRIOR"),
                ("CIVILIZATION_TEST", "UNITCLASS_SWORDSMAN", None),
            ],
        )
        connection.execute(
            "INSERT INTO Civilization_BuildingClassOverrides VALUES (?, ?, ?)",
            (
                "CIVILIZATION_TEST",
                "BUILDINGCLASS_PYRAMID",
                "BUILDING_PYRAMID",
            ),
        )
        connection.execute(
            "INSERT INTO Civilization_Start_Along_Ocean VALUES (?)",
            ("CIVILIZATION_TEST",),
        )
        connection.execute(
            "INSERT INTO Civilization_Start_Place_First_Along_Ocean VALUES (?)",
            ("CIVILIZATION_TEST",),
        )
        connection.execute("CREATE TABLE Regions (Type TEXT NOT NULL PRIMARY KEY)")
        connection.execute("INSERT INTO Regions VALUES (?)", ("REGION_TEST",))
        connection.execute(
            "INSERT INTO Religions VALUES (?)", ("RELIGION_TEST",)
        )
        belief_columns = [
            "Type",
            *(column for column, _, _ in BELIEF_REFERENCE_COLUMNS),
            *BELIEF_FIELDS,
        ]
        belief_reference_values = {
            "ObsoleteEra": "ERA_ANCIENT",
            "ResourceRevealed": "RESOURCE_IRON",
            "SpreadModifierDoublingTech": "TECH_AGRICULTURE",
        }
        belief_values = []
        for column, (_, value_type) in BELIEF_FIELDS.items():
            if column == "Founder":
                value = 1
            elif column == "GoldPerFollowingCity":
                value = 2
            elif column == "HappinessPerFollowingCity":
                value = "invalid" if invalid_number else 0.5
            elif value_type in {"integer", "boolean", "number"}:
                value = 0
            else:
                value = None
            belief_values.append(value)
        connection.execute(
            f"INSERT INTO Beliefs ({', '.join(belief_columns)}) VALUES "
            f"({', '.join('?' for _ in belief_columns)})",
            [
                "BELIEF_TEST",
                *(
                    belief_reference_values.get(column)
                    for column, _, _ in BELIEF_REFERENCE_COLUMNS
                ),
                *belief_values,
            ],
        )
        specialist_columns = ["Type", "GreatPeopleUnitClass", *SPECIALIST_FIELDS]
        specialist_values = []
        for column, (_, value_type) in SPECIALIST_FIELDS.items():
            if column == "GreatPeopleRateChange":
                value = 3
            elif column == "Visible":
                value = 1
            elif value_type in {"integer", "boolean"}:
                value = 0
            else:
                value = None
            specialist_values.append(value)
        connection.execute(
            f"INSERT INTO Specialists ({', '.join(specialist_columns)}) VALUES "
            f"({', '.join('?' for _ in specialist_columns)})",
            ["SPECIALIST_TEST", "UNITCLASS_WARRIOR", *specialist_values],
        )
        connection.execute(
            "INSERT INTO Civilization_Religions VALUES (?, ?)",
            ("CIVILIZATION_TEST", "RELIGION_TEST"),
        )
        connection.execute(
            "INSERT INTO Unit_GreatPersons VALUES (?, ?)",
            ("UNIT_WARRIOR", "SPECIALIST_TEST"),
        )
        for table, type_id, fields, overrides in (
            ("Terrains", "TERRAIN_TEST", TERRAIN_FIELDS, {"Movement": 1}),
            ("Routes", "ROUTE_TEST", ROUTE_FIELDS, {"Movement": 60}),
            ("Yields", "YIELD_TEST", YIELD_FIELDS, {"CityChange": 1}),
        ):
            scalar_columns = ["Type", *fields]
            scalar_values = [
                overrides.get(column, 0) for column in fields
            ]
            connection.execute(
                f"INSERT INTO {table} ({', '.join(scalar_columns)}) VALUES "
                f"({', '.join('?' for _ in scalar_columns)})",
                [type_id, *scalar_values],
            )
        connection.execute(
            "UPDATE Yields SET AIWeightPercent = 999 WHERE Type = ?",
            ("YIELD_TEST",),
        )
        feature_columns = [
            "Type",
            *(column for column, _, _ in FEATURE_REFERENCE_COLUMNS),
            *FEATURE_FIELDS,
        ]
        feature_references = {
            "GrowthTerrainType": "TERRAIN_TEST",
            "AdjacentUnitFreePromotion": "PROMOTION_SHOCK_1",
        }
        feature_values = [
            1 if column == "NaturalWonder" else 0 for column in FEATURE_FIELDS
        ]
        connection.execute(
            f"INSERT INTO Features ({', '.join(feature_columns)}) VALUES "
            f"({', '.join('?' for _ in feature_columns)})",
            [
                "FEATURE_TEST",
                *(
                    feature_references.get(column)
                    for column, _, _ in FEATURE_REFERENCE_COLUMNS
                ),
                *feature_values,
            ],
        )
        fake_feature_columns = ["Type", *FAKE_FEATURE_FIELDS]
        fake_feature_values = [
            1 if column == "Impassable" else 0
            for column in FAKE_FEATURE_FIELDS
        ]
        connection.execute(
            f"INSERT INTO FakeFeatures ({', '.join(fake_feature_columns)}) VALUES "
            f"({', '.join('?' for _ in fake_feature_columns)})",
            ["FEATURE_LAKE", *fake_feature_values],
        )
        improvement_columns = [
            "Type",
            *(column for column, _, _ in IMPROVEMENT_REFERENCE_COLUMNS),
            *IMPROVEMENT_FIELDS,
        ]
        improvement_references = {"CivilizationType": "CIVILIZATION_TEST"}
        improvement_values = [
            1 if column == "CreatedByGreatPerson" else 0
            for column in IMPROVEMENT_FIELDS
        ]
        connection.execute(
            f"INSERT INTO Improvements ({', '.join(improvement_columns)}) VALUES "
            f"({', '.join('?' for _ in improvement_columns)})",
            [
                "IMPROVEMENT_TEST",
                *(
                    improvement_references.get(column)
                    for column, _, _ in IMPROVEMENT_REFERENCE_COLUMNS
                ),
                *improvement_values,
            ],
        )
        build_columns = [
            "Type",
            *(column for column, _, _ in BUILD_REFERENCE_COLUMNS),
            *BUILD_FIELDS,
        ]
        build_references = {
            "PrereqTech": "TECH_AGRICULTURE",
            "ImprovementType": "IMPROVEMENT_TEST",
            "RouteType": "ROUTE_TEST",
        }
        build_values = [
            None if column == "Time" else 0 for column in BUILD_FIELDS
        ]
        connection.execute(
            f"INSERT INTO Builds ({', '.join(build_columns)}) VALUES "
            f"({', '.join('?' for _ in build_columns)})",
            [
                "BUILD_TEST",
                *(
                    build_references.get(column)
                    for column, _, _ in BUILD_REFERENCE_COLUMNS
                ),
                *build_values,
            ],
        )
        connection.executemany(
            "INSERT INTO BuildFeatures VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    "BUILD_TEST",
                    "FEATURE_TEST",
                    "TECH_AGRICULTURE",
                    None,
                    20,
                    0,
                    1,
                ),
                ("BUILD_TEST", "FEATURE_LAKE", None, 300, 0, 0, 1),
            ),
        )
        project_columns = [
            "Type",
            *(column for column, _, _ in PROJECT_REFERENCE_COLUMNS),
            *PROJECT_FIELDS,
        ]
        project_references = {
            "VictoryPrereq": "VICTORY_TEST",
            "TechPrereq": "TECH_AGRICULTURE",
            "AnyonePrereqProject": "PROJECT_TEST",
        }
        project_values = [
            1 if value_type == "boolean" else 10
            for _, value_type in PROJECT_FIELDS.values()
        ]
        connection.execute(
            f"INSERT INTO Projects ({', '.join(project_columns)}) VALUES "
            f"({', '.join('?' for _ in project_columns)})",
            [
                "PROJECT_TEST",
                *(
                    project_references[column]
                    for column, _, _ in PROJECT_REFERENCE_COLUMNS
                ),
                *project_values,
            ],
        )
        process_columns = [
            "Type",
            *(column for column, _, _ in PROCESS_REFERENCE_COLUMNS),
        ]
        connection.execute(
            f"INSERT INTO Processes ({', '.join(process_columns)}) VALUES "
            f"({', '.join('?' for _ in process_columns)})",
            ["PROCESS_TEST", "TECH_AGRICULTURE"],
        )
        victory_columns = ["Type", *VICTORY_FIELDS]
        victory_values = [
            1 if value_type == "boolean" else 10
            for _, value_type in VICTORY_FIELDS.values()
        ]
        connection.execute(
            f"INSERT INTO Victories ({', '.join(victory_columns)}) VALUES "
            f"({', '.join('?' for _ in victory_columns)})",
            ["VICTORY_TEST", *victory_values],
        )
        for table, type_id, fields, excluded in (
            (
                "GameSpeeds",
                "GAMESPEED_STANDARD",
                GAME_SPEED_FIELDS,
                ("TXT_KEY_SPEED", 999),
            ),
            (
                "HandicapInfos",
                "HANDICAP_PRINCE",
                HANDICAP_FIELDS,
                ("TXT_KEY_HANDICAP", 999, 999),
            ),
            (
                "Worlds",
                "WORLDSIZE_STANDARD",
                WORLD_SIZE_FIELDS,
                ("TXT_KEY_WORLD", 999),
            ),
        ):
            columns = ["Type", *fields]
            if table == "HandicapInfos":
                columns.extend(
                    (
                        "Description",
                        "CityProductionNumOptionsConsidered",
                        "AIDeclareWarProb",
                    )
                )
            else:
                columns.extend(("Description", "PortraitIndex"))
            scalar_values = [
                2.5 if value_type == "number" else 100
                for _attribute, value_type in fields.values()
            ]
            values = [type_id, *scalar_values, *excluded]
            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            connection.execute(
                f'INSERT INTO "{table}" ({quoted_columns}) VALUES '
                f'({", ".join("?" for _ in values)})',
                values,
            )
        for table, type_id, fields, excluded in (
            (
                "Climates",
                "CLIMATE_TEST",
                CLIMATE_FIELDS,
                ("TXT_KEY_CLIMATE",),
            ),
            (
                "SeaLevels",
                "SEALEVEL_TEST",
                SEA_LEVEL_FIELDS,
                ("TXT_KEY_SEA_LEVEL",),
            ),
            (
                "GameOptions",
                "GAMEOPTION_TEST",
                GAME_OPTION_FIELDS,
                ("TXT_KEY_GAME_OPTION", "TXT_KEY_GAME_OPTION_HELP", 1),
            ),
        ):
            columns = ["Type", *fields]
            if table == "GameOptions":
                columns.extend(("Description", "Help", "Visible"))
            else:
                columns.append("Description")
            scalar_values = [
                0.25 if value_type == "number" else 1
                for _attribute, value_type in fields.values()
            ]
            values = [type_id, *scalar_values, *excluded]
            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            connection.execute(
                f'INSERT INTO "{table}" ({quoted_columns}) VALUES '
                f'({", ".join("?" for _ in values)})',
                values,
            )
        connection.execute(
            "INSERT INTO InvisibleInfos VALUES (?, ?)",
            ("INVISIBLE_TEST", "TXT_KEY_INVISIBLE"),
        )
        goody_columns = [
            "Type",
            *(column for column, _kind, _target_kind in ANCIENT_RUIN_REFERENCE_COLUMNS),
            *ANCIENT_RUIN_FIELDS,
            "Description",
            "Sound",
        ]
        goody_values = [
            1 if value_type == "boolean" else 10
            for _attribute, value_type in ANCIENT_RUIN_FIELDS.values()
        ]
        connection.execute(
            f'INSERT INTO GoodyHuts ({", ".join(goody_columns)}) VALUES '
            f'({", ".join("?" for _ in goody_columns)})',
            [
                "GOODY_TEST",
                "UNITCLASS_WARRIOR",
                "UNITCLASS_WARRIOR",
                *goody_values,
                "TXT_KEY_GOODY",
                "AS2D_GOODY",
            ],
        )
        connection.execute(
            "INSERT INTO ResolutionDecisions VALUES (?, ?)",
            ("RESOLUTION_DECISION_TEST", "TXT_KEY_DECISION"),
        )
        world_congress_rows = (
            (
                "LeagueProjectRewards",
                "LEAGUE_PROJECT_REWARD_TEST",
                LEAGUE_PROJECT_REWARD_FIELDS,
                LEAGUE_PROJECT_REWARD_REFERENCE_COLUMNS,
                ("BUILDING_PYRAMID", "UNITCLASS_WARRIOR"),
            ),
            (
                "LeagueProjects",
                "LEAGUE_PROJECT_TEST",
                LEAGUE_PROJECT_FIELDS,
                LEAGUE_PROJECT_REFERENCE_COLUMNS,
                (
                    "PROCESS_TEST",
                    "LEAGUE_PROJECT_REWARD_TEST",
                    "LEAGUE_PROJECT_REWARD_TEST",
                    "LEAGUE_PROJECT_REWARD_TEST",
                ),
            ),
            (
                "Resolutions",
                "RESOLUTION_TEST",
                RESOLUTION_FIELDS,
                RESOLUTION_REFERENCE_COLUMNS,
                (
                    "RESOLUTION_DECISION_TEST",
                    "RESOLUTION_DECISION_TEST",
                    "TECH_AGRICULTURE",
                    "LEAGUE_PROJECT_TEST",
                ),
            ),
            (
                "LeagueSpecialSessions",
                "LEAGUE_SPECIAL_SESSION_TEST",
                LEAGUE_SPECIAL_SESSION_FIELDS,
                LEAGUE_SPECIAL_SESSION_REFERENCE_COLUMNS,
                ("ERA_ANCIENT", "RESOLUTION_TEST", "RESOLUTION_TEST"),
            ),
            (
                "VoteSources",
                "DIPLOVOTE_TEST",
                VOTE_SOURCE_FIELDS,
                VOTE_SOURCE_REFERENCE_COLUMNS,
                ("SPECIALIST_TEST", "POLICY_TRADITION"),
            ),
        )
        for table, type_id, fields, references, targets in world_congress_rows:
            columns = [
                "Type",
                *(column for column, _kind, _target_kind in references),
                *fields,
                "Description",
                "Help",
            ]
            scalar_values = [
                1 if value_type == "boolean" else 10
                for _attribute, value_type in fields.values()
            ]
            values = [
                type_id,
                *targets,
                *scalar_values,
                "TXT_KEY_DESCRIPTION",
                "TXT_KEY_HELP",
            ]
            connection.execute(
                f'INSERT INTO "{table}" ({", ".join(columns)}) VALUES '
                f'({", ".join("?" for _ in values)})',
                values,
            )
        vote_columns = ["Type", *VOTE_FIELDS, "Description"]
        vote_values = [
            1 if value_type == "boolean" else 10
            for _attribute, value_type in VOTE_FIELDS.values()
        ]
        connection.execute(
            f'INSERT INTO Votes ({", ".join(vote_columns)}) VALUES '
            f'({", ".join("?" for _ in vote_columns)})',
            ["VOTE_TEST", *vote_values, "TXT_KEY_VOTE"],
        )
        connection.execute(
            "INSERT INTO MinorCivTraits VALUES (?, ?, ?)",
            ("MINOR_TRAIT_TEST", "TXT_KEY_MINOR_TRAIT", "MINOR_TRAIT.dds"),
        )
        connection.execute(
            "INSERT INTO MinorCivilizations VALUES (?, ?, ?, ?, ?)",
            (
                "MINOR_CIV_TEST",
                "MINOR_TRAIT_TEST",
                "TXT_KEY_MINOR_CIV",
                "TXT_KEY_MINOR_CIV_PEDIA",
                "ART_DEF_MINOR_CIV",
            ),
        )
        connection.execute(
            "INSERT INTO Project_VictoryThresholds VALUES (?, ?, ?, ?)",
            ("PROJECT_TEST", "VICTORY_TEST", 3, 1),
        )
        connection.execute(
            "INSERT INTO Feature_TerrainBooleans VALUES (?, ?)",
            ("FEATURE_TEST", "TERRAIN_TEST"),
        )
        connection.execute(
            "INSERT INTO Improvement_ValidTerrains VALUES (?, ?)",
            ("IMPROVEMENT_TEST", "TERRAIN_TEST"),
        )
        connection.execute(
            "INSERT INTO Improvement_ValidFeatures VALUES (?, ?)",
            ("IMPROVEMENT_TEST", "FEATURE_TEST"),
        )
        connection.execute(
            "INSERT INTO Improvement_ValidImprovements VALUES (?, ?)",
            ("IMPROVEMENT_TEST", "IMPROVEMENT_TEST"),
        )
        for (
            table,
            _source_column,
            _target_column,
            _kind,
            source_kind,
            target_kind,
        ) in PLAIN_REFERENCE_TABLES:
            connection.execute(
                f'INSERT INTO "{table}" VALUES (?, ?)',
                (
                    FIXTURE_TYPE_IDS[source_kind],
                    FIXTURE_TYPE_IDS[target_kind],
                ),
            )
        for (
            table,
            _source_column,
            _target_column,
            _kind,
            source_kind,
            target_kind,
            _value_column,
            _attribute,
        ) in QUANTITY_REFERENCE_TABLES:
            connection.execute(
                f'INSERT INTO "{table}" VALUES (?, ?, ?)',
                (
                    FIXTURE_TYPE_IDS[source_kind],
                    FIXTURE_TYPE_IDS[target_kind],
                    1,
                ),
            )
        for (
            table,
            source_column,
            target_column,
            _kind,
            source_kind,
            target_kind,
            fields,
        ) in ATTRIBUTED_REFERENCE_TABLES:
            values, _attributes = fixture_reference_attributes(fields)
            columns = [source_column, target_column, *(column for column, _, _ in fields)]
            row = [
                FIXTURE_TYPE_IDS[source_kind],
                FIXTURE_TYPE_IDS[target_kind],
                *values,
            ]
            if table in {"UnitPromotions_Features", "UnitPromotions_Terrains"}:
                columns.append("PassableTech")
                row.append("TECH_AGRICULTURE")
            connection.execute(
                f'INSERT INTO "{table}" '
                f'({", ".join(columns)}) VALUES ({", ".join("?" for _ in row)})',
                row,
            )
        connection.execute(
            "INSERT INTO Feature_YieldChanges VALUES (?, ?, ?)",
            ("FEATURE_LAKE", "YIELD_TEST", 2),
        )
        for (
            table,
            _source_column,
            _target_column,
            _kind,
            source_kind,
            target_kind,
            _context_column,
            context_kind,
            _context_role,
            _value_column,
            _attribute,
        ) in CONTEXTUAL_QUANTITY_REFERENCE_TABLES:
            connection.execute(
                f'INSERT INTO "{table}" VALUES (?, ?, ?, ?)',
                (
                    FIXTURE_TYPE_IDS[source_kind],
                    FIXTURE_TYPE_IDS[target_kind],
                    FIXTURE_TYPE_IDS[context_kind],
                    1,
                ),
            )
        connection.execute(
            "INSERT INTO Improvement_TechYieldChanges VALUES (?, ?, ?, ?)",
            ("IMPROVEMENT_TEST", "YIELD_TEST", "TECH_POTTERY", 2),
        )
        for (
            table,
            _source_column,
            _target_column,
            _kind,
            source_kind,
            target_kind,
            _context_column,
            context_kind,
            _context_role,
        ) in CONTEXTUAL_REFERENCE_TABLES:
            connection.execute(
                f'INSERT INTO "{table}" VALUES (?, ?, ?)',
                (
                    FIXTURE_TYPE_IDS[source_kind],
                    FIXTURE_TYPE_IDS[target_kind],
                    FIXTURE_TYPE_IDS[context_kind],
                ),
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
        self.assertEqual(len(bundle.entities), 72)
        self.assertEqual(
            len(bundle.references),
            58
            + len(UNIT_REFERENCE_COLUMNS)
            + len(PLAIN_REFERENCE_TABLES)
            + len(QUANTITY_REFERENCE_TABLES)
            + 1
            + len(CONTEXTUAL_QUANTITY_REFERENCE_TABLES)
            + 1
            + len(ATTRIBUTED_REFERENCE_TABLES)
            + 2
            + 1
            + 1
            + 2
            + 5
            + 2
            + 2
            + 15
            + 1
            + 2,
        )
        self.assertEqual(bundle.schema_version, 3)
        self.assertEqual(bundle.ruleset.dlc, (BRAVE_NEW_WORLD_PACKAGE_ID,))
        city_growth = next(
            item for item in bundle.entities
            if item.type_id == "CITY_GROWTH_EXPONENT"
        )
        self.assertEqual(city_growth.kind, "global_define")
        self.assertEqual(city_growth.attributes, {"value": 1.5})
        self.assertFalse(
            any(item.type_id == "AI_TEST_DEFINE" for item in bundle.entities)
        )
        hurry = next(item for item in bundle.entities if item.type_id == "HURRY_TEST")
        self.assertEqual(hurry.attributes["gold_per_production"], 1)
        self.assertIn(
            ("requires_policy", "POLICY_TRADITION"),
            {
                (item.kind, item.target_type_id)
                for item in bundle.references
                if item.source_type_id == "HURRY_TEST"
            },
        )
        self.assertIn(
            ("uses_slot", "GREAT_WORK_CLASS_TEST", "GREAT_WORK_SLOT_TEST"),
            {
                (item.kind, item.source_type_id, item.target_type_id)
                for item in bundle.references
            },
        )
        self.assertIn(
            (
                "contains_great_work_slot",
                "BUILDING_PYRAMID",
                "GREAT_WORK_SLOT_TEST",
            ),
            {
                (item.kind, item.source_type_id, item.target_type_id)
                for item in bundle.references
            },
        )
        great_work = next(
            item for item in bundle.entities if item.type_id == "GREAT_WORK_TEST"
        )
        self.assertTrue(great_work.attributes["archaeology_only"])
        great_work_relations = {
            (item.kind, item.source_type_id, item.target_type_id)
            for item in bundle.references
            if item.target_type_id == "GREAT_WORK_TEST"
            or item.source_type_id == "GREAT_WORK_TEST"
        }
        self.assertEqual(
            great_work_relations,
            {
                (
                    "belongs_to_great_work_class",
                    "GREAT_WORK_TEST",
                    "GREAT_WORK_CLASS_TEST",
                ),
                ("has_artifact_class", "GREAT_WORK_TEST", "ARTIFACT_TEST"),
                ("associated_with_era", "GREAT_WORK_TEST", "ERA_ANCIENT"),
                (
                    "grants_free_great_work",
                    "BUILDING_PYRAMID",
                    "GREAT_WORK_TEST",
                ),
                ("can_create_great_work", "UNIT_WARRIOR", "GREAT_WORK_TEST"),
            },
        )
        plain_relations = {
            (
                item.kind,
                item.source_kind,
                item.source_type_id,
                item.target_kind,
                item.target_type_id,
            )
            for item in bundle.references
            if not item.attributes and not item.context
        }
        for (
            _table,
            _source_column,
            _target_column,
            kind,
            source_kind,
            target_kind,
        ) in PLAIN_REFERENCE_TABLES:
            self.assertIn(
                (
                    kind,
                    source_kind,
                    FIXTURE_TYPE_IDS[source_kind],
                    target_kind,
                    FIXTURE_TYPE_IDS[target_kind],
                ),
                plain_relations,
            )
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
        self.assertEqual(
            [rule["bonus"] for rule in pyramid.attributes["theming_bonuses"]],
            [1, 2],
        )
        self.assertTrue(pyramid.attributes["theming_bonuses"][0]["unique_eras"])
        self.assertTrue(pyramid.attributes["theming_bonuses"][1]["same_era"])
        serialized_theming = json.dumps(pyramid.attributes["theming_bonuses"])
        self.assertNotIn("DESCRIPTION", serialized_theming)
        self.assertNotIn("priority", serialized_theming.lower())
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
        iron = next(item for item in bundle.entities if item.type_id == "RESOURCE_IRON")
        self.assertEqual(iron.attributes["starting_resource_quantity"], 2)
        resource_relations = {
            (item.kind, item.target_type_id)
            for item in bundle.references
            if item.source_type_id == "RESOURCE_IRON" and not item.attributes
        }
        self.assertEqual(
            resource_relations,
            {
                ("belongs_to_resource_class", "RESOURCECLASS_RUSH"),
                ("revealed_by_technology", "TECH_AGRICULTURE"),
                ("allowed_on_feature", "FEATURE_TEST"),
                ("allowed_on_feature_terrain", "TERRAIN_TEST"),
                ("allowed_on_terrain", "TERRAIN_TEST"),
            },
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
        civilization = next(
            item for item in bundle.entities if item.type_id == "CIVILIZATION_TEST"
        )
        self.assertEqual(
            civilization.attributes,
            {
                "playable": True,
                "starts_along_ocean": True,
                "placed_first_along_ocean": True,
            },
        )
        leader = next(
            item for item in bundle.entities if item.type_id == "LEADER_TEST"
        )
        self.assertEqual(leader.attributes, {})
        trait = next(item for item in bundle.entities if item.type_id == "TRAIT_TEST")
        self.assertEqual(trait.attributes["wonder_production_modifier"], 20)
        self.assertTrue(trait.attributes["move_friendly_woods_as_road"])
        civilization_relations = {
            (
                item.kind,
                item.source_kind,
                item.source_type_id,
                item.target_kind,
                item.target_type_id,
            )
            for item in bundle.references
            if item.source_type_id
            in {"CIVILIZATION_TEST", "LEADER_TEST", "TRAIT_TEST"}
            and not item.attributes
            and not item.context
        }
        self.assertEqual(
            civilization_relations,
            {
                (
                    "led_by",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "leader",
                    "LEADER_TEST",
                ),
                (
                    "has_trait",
                    "leader",
                    "LEADER_TEST",
                    "trait",
                    "TRAIT_TEST",
                ),
                (
                    "unique_unit",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "unit",
                    "UNIT_WARRIOR",
                ),
                (
                    "disables_unit_class",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "unit_class",
                    "UNITCLASS_SWORDSMAN",
                ),
                (
                    "unique_building",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "building",
                    "BUILDING_PYRAMID",
                ),
                (
                    "preferred_religion",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "religion",
                    "RELIGION_TEST",
                ),
                (
                    "starts_with_building_class",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "building_class",
                    "BUILDINGCLASS_PYRAMID",
                ),
                (
                    "starts_with_technology",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "technology",
                    "TECH_AGRICULTURE",
                ),
                (
                    "avoids_start_region",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "region",
                    "REGION_TEST",
                ),
                (
                    "prefers_start_region",
                    "civilization",
                    "CIVILIZATION_TEST",
                    "region",
                    "REGION_TEST",
                ),
                (
                    "grants_unit_class",
                    "trait",
                    "TRAIT_TEST",
                    "unit_class",
                    "UNITCLASS_WARRIOR",
                ),
                (
                    "free_unit_unlocked_by_technology",
                    "trait",
                    "TRAIT_TEST",
                    "technology",
                    "TECH_AGRICULTURE",
                ),
                (
                    "grants_free_building",
                    "trait",
                    "TRAIT_TEST",
                    "building",
                    "BUILDING_PYRAMID",
                ),
                (
                    "unlocked_by_technology",
                    "trait",
                    "TRAIT_TEST",
                    "technology",
                    "TECH_POTTERY",
                ),
                (
                    "combat_bonus_near_improvement",
                    "trait",
                    "TRAIT_TEST",
                    "improvement",
                    "IMPROVEMENT_TEST",
                ),
                (
                    "cannot_train_unit_class",
                    "trait",
                    "TRAIT_TEST",
                    "unit_class",
                    "UNITCLASS_WARRIOR",
                ),
            },
        )
        belief = next(item for item in bundle.entities if item.type_id == "BELIEF_TEST")
        self.assertTrue(belief.attributes["founder"])
        self.assertEqual(belief.attributes["gold_per_following_city"], 2)
        self.assertEqual(belief.attributes["happiness_per_following_city"], 0.5)
        religion = next(
            item for item in bundle.entities if item.type_id == "RELIGION_TEST"
        )
        self.assertEqual(religion.attributes, {})
        specialist = next(
            item for item in bundle.entities if item.type_id == "SPECIALIST_TEST"
        )
        self.assertTrue(specialist.attributes["visible"])
        self.assertEqual(specialist.attributes["great_people_rate_change"], 3)
        religious_relations = {
            (item.kind, item.source_type_id, item.target_type_id)
            for item in bundle.references
            if item.source_type_id
            in {"BELIEF_TEST", "CIVILIZATION_TEST", "SPECIALIST_TEST"}
            and item.kind
            in {
                "obsoleted_by_era",
                "reveals_resource",
                "spread_modifier_doubled_by_technology",
                "preferred_religion",
                "generates_great_person_unit_class",
            }
        }
        self.assertEqual(
            religious_relations,
            {
                ("obsoleted_by_era", "BELIEF_TEST", "ERA_ANCIENT"),
                ("reveals_resource", "BELIEF_TEST", "RESOURCE_IRON"),
                (
                    "spread_modifier_doubled_by_technology",
                    "BELIEF_TEST",
                    "TECH_AGRICULTURE",
                ),
                ("preferred_religion", "CIVILIZATION_TEST", "RELIGION_TEST"),
                (
                    "generates_great_person_unit_class",
                    "SPECIALIST_TEST",
                    "UNITCLASS_WARRIOR",
                ),
            },
        )
        self.assertIn(
            ("great_person_for_specialist", "UNIT_WARRIOR", "SPECIALIST_TEST"),
            {
                (item.kind, item.source_type_id, item.target_type_id)
                for item in bundle.references
            },
        )
        terrain = next(
            item for item in bundle.entities if item.type_id == "TERRAIN_TEST"
        )
        self.assertEqual(terrain.attributes["movement"], 1)
        feature = next(
            item for item in bundle.entities if item.type_id == "FEATURE_TEST"
        )
        self.assertTrue(feature.attributes["natural_wonder"])
        improvement = next(
            item for item in bundle.entities if item.type_id == "IMPROVEMENT_TEST"
        )
        self.assertTrue(improvement.attributes["created_by_great_person"])
        build = next(item for item in bundle.entities if item.type_id == "BUILD_TEST")
        self.assertIsNone(build.attributes["time"])
        yield_entity = next(
            item for item in bundle.entities if item.type_id == "YIELD_TEST"
        )
        self.assertEqual(yield_entity.attributes["city_change"], 1)
        self.assertNotIn("ai_weight_percent", yield_entity.attributes)
        map_relations = {
            (item.kind, item.source_type_id, item.target_type_id)
            for item in bundle.references
            if item.source_type_id
            in {"FEATURE_TEST", "IMPROVEMENT_TEST", "BUILD_TEST"}
            and not item.attributes
        }
        self.assertEqual(
            map_relations,
            {
                ("grows_on_terrain", "FEATURE_TEST", "TERRAIN_TEST"),
                (
                    "grants_adjacent_unit_promotion",
                    "FEATURE_TEST",
                    "PROMOTION_SHOCK_1",
                ),
                ("valid_on_terrain", "FEATURE_TEST", "TERRAIN_TEST"),
                (
                    "restricted_to_civilization",
                    "IMPROVEMENT_TEST",
                    "CIVILIZATION_TEST",
                ),
                ("valid_on_terrain", "IMPROVEMENT_TEST", "TERRAIN_TEST"),
                ("valid_on_feature", "IMPROVEMENT_TEST", "FEATURE_TEST"),
                (
                    "valid_on_improvement",
                    "IMPROVEMENT_TEST",
                    "IMPROVEMENT_TEST",
                ),
                ("unlocked_by_technology", "BUILD_TEST", "TECH_AGRICULTURE"),
                ("creates_improvement", "BUILD_TEST", "IMPROVEMENT_TEST"),
                ("creates_route", "BUILD_TEST", "ROUTE_TEST"),
            },
        )
        quantity_relations = {
            (
                item.kind,
                item.source_type_id,
                item.target_type_id,
                tuple(sorted(item.attributes.items())),
            )
            for item in bundle.references
            if item.attributes and not item.context
        }
        expected_quantity_relations = {
            (
                kind,
                FIXTURE_TYPE_IDS[source_kind],
                FIXTURE_TYPE_IDS[target_kind],
                ((attribute, 1),),
            )
            for (
                _table,
                _source_column,
                _target_column,
                kind,
                source_kind,
                target_kind,
                _value_column,
                attribute,
            ) in QUANTITY_REFERENCE_TABLES
        }
        expected_quantity_relations.update(
            (
                kind,
                FIXTURE_TYPE_IDS[source_kind],
                FIXTURE_TYPE_IDS[target_kind],
                fixture_reference_attributes(fields)[1],
            )
            for (
                _table,
                _source_column,
                _target_column,
                kind,
                source_kind,
                target_kind,
                fields,
            ) in ATTRIBUTED_REFERENCE_TABLES
        )
        expected_quantity_relations.add(
            (
                "yield_change",
                "FEATURE_LAKE",
                "YIELD_TEST",
                (("amount", 2),),
            )
        )
        expected_quantity_relations.add(
            (
                "victory_threshold",
                "PROJECT_TEST",
                "VICTORY_TEST",
                (("minimum_threshold", 1), ("threshold", 3)),
            )
        )
        expected_quantity_relations.add(
            (
                "feature_build_rule",
                "BUILD_TEST",
                "FEATURE_LAKE",
                (
                    ("cost", 0),
                    ("production", 0),
                    ("removes_feature", True),
                    ("time", 300),
                ),
            )
        )
        self.assertEqual(quantity_relations, expected_quantity_relations)
        lake = next(
            item for item in bundle.entities if item.type_id == "FEATURE_LAKE"
        )
        self.assertEqual(lake.kind, "feature")
        self.assertTrue(lake.attributes["fake"])
        self.assertTrue(lake.attributes["impassable"])
        contextual_relations = {
            (
                item.kind,
                item.source_type_id,
                item.target_type_id,
                tuple(sorted(item.attributes.items())),
                item.context,
            )
            for item in bundle.references
            if item.context
        }
        expected_contextual_relations = {
            (
                kind,
                FIXTURE_TYPE_IDS[source_kind],
                FIXTURE_TYPE_IDS[target_kind],
                ((attribute, 1),),
                (
                    ReferenceContext(
                        context_role,
                        context_kind,
                        FIXTURE_TYPE_IDS[context_kind],
                    ),
                ),
            )
            for (
                _table,
                _source_column,
                _target_column,
                kind,
                source_kind,
                target_kind,
                _context_column,
                context_kind,
                context_role,
                _value_column,
                attribute,
            ) in CONTEXTUAL_QUANTITY_REFERENCE_TABLES
        }
        expected_contextual_relations.add(
            (
                "yield_change",
                "IMPROVEMENT_TEST",
                "YIELD_TEST",
                (("amount", 2),),
                (
                    ReferenceContext(
                        "enabled_by_technology",
                        "technology",
                        "TECH_POTTERY",
                    ),
                ),
            )
        )
        expected_contextual_relations.update(
            (
                kind,
                FIXTURE_TYPE_IDS[source_kind],
                FIXTURE_TYPE_IDS[target_kind],
                (),
                (
                    ReferenceContext(
                        context_role,
                        context_kind,
                        FIXTURE_TYPE_IDS[context_kind],
                    ),
                ),
            )
            for (
                _table,
                _source_column,
                _target_column,
                kind,
                source_kind,
                target_kind,
                _context_column,
                context_kind,
                context_role,
            ) in CONTEXTUAL_REFERENCE_TABLES
        )
        expected_contextual_relations.update(
            (
                "passable_with_technology",
                "PROMOTION_SHOCK_1",
                FIXTURE_TYPE_IDS[target_kind],
                (),
                (
                    ReferenceContext(
                        "enabled_by_technology",
                        "technology",
                        "TECH_AGRICULTURE",
                    ),
                ),
            )
            for target_kind in ("feature", "terrain")
        )
        expected_contextual_relations.add(
            (
                "enhanced_yield_change",
                "BUILDING_PYRAMID",
                "YIELD_TEST",
                (("amount", 2),),
                (
                    ReferenceContext(
                        "enabled_by_technology",
                        "technology",
                        "TECH_POTTERY",
                    ),
                ),
            )
        )
        expected_contextual_relations.add(
            (
                "feature_build_rule",
                "BUILD_TEST",
                "FEATURE_TEST",
                (
                    ("cost", 0),
                    ("production", 20),
                    ("removes_feature", True),
                ),
                (
                    ReferenceContext(
                        "enabled_by_technology",
                        "technology",
                        "TECH_AGRICULTURE",
                    ),
                ),
            )
        )
        self.assertEqual(contextual_relations, expected_contextual_relations)
        project = next(
            item for item in bundle.entities if item.type_id == "PROJECT_TEST"
        )
        self.assertTrue(project.attributes["spaceship"])
        process = next(
            item for item in bundle.entities if item.type_id == "PROCESS_TEST"
        )
        self.assertEqual(process.attributes, {})
        victory = next(
            item for item in bundle.entities if item.type_id == "VICTORY_TEST"
        )
        self.assertTrue(victory.attributes["wins_game"])
        game_speed = next(
            item for item in bundle.entities
            if item.type_id == "GAMESPEED_STANDARD"
        )
        self.assertEqual(game_speed.attributes["research_percent"], 100)
        self.assertNotIn("description", game_speed.attributes)
        self.assertNotIn("portrait_index", game_speed.attributes)
        handicap = next(
            item for item in bundle.entities if item.type_id == "HANDICAP_PRINCE"
        )
        self.assertEqual(handicap.attributes["ai_growth_percent"], 100)
        self.assertNotIn("city_production_num_options_considered", handicap.attributes)
        self.assertNotIn("ai_declare_war_prob", handicap.attributes)
        world_size = next(
            item for item in bundle.entities
            if item.type_id == "WORLDSIZE_STANDARD"
        )
        self.assertEqual(world_size.attributes["grid_width"], 100)
        self.assertEqual(world_size.attributes["num_cities_tech_cost_mod"], 2.5)
        self.assertNotIn("description", world_size.attributes)
        climate = next(
            item for item in bundle.entities if item.type_id == "CLIMATE_TEST"
        )
        self.assertEqual(climate.attributes["snow_latitude_change"], 0.25)
        self.assertEqual(climate.attributes["mountain_percent"], 1)
        self.assertNotIn("description", climate.attributes)
        sea_level = next(
            item for item in bundle.entities if item.type_id == "SEALEVEL_TEST"
        )
        self.assertEqual(sea_level.attributes["sea_level_change"], 1)
        self.assertNotIn("description", sea_level.attributes)
        game_option = next(
            item for item in bundle.entities if item.type_id == "GAMEOPTION_TEST"
        )
        self.assertTrue(game_option.attributes["default"])
        self.assertTrue(game_option.attributes["supports_single_player"])
        self.assertTrue(game_option.attributes["supports_multiplayer"])
        self.assertNotIn("visible", game_option.attributes)
        self.assertNotIn("description", game_option.attributes)
        self.assertNotIn("help", game_option.attributes)
        invisibility = next(
            item for item in bundle.entities if item.type_id == "INVISIBLE_TEST"
        )
        self.assertEqual(invisibility.attributes, {})
        self.assertEqual(
            {
                (item.kind, item.target_kind, item.target_type_id)
                for item in bundle.references
                if item.source_type_id == "PROMOTION_SHOCK_1"
                and item.kind in {"has_invisibility", "detects_invisibility"}
            },
            {
                ("has_invisibility", "invisibility", "INVISIBLE_TEST"),
                ("detects_invisibility", "invisibility", "INVISIBLE_TEST"),
            },
        )
        ancient_ruin = next(
            item for item in bundle.entities if item.type_id == "GOODY_TEST"
        )
        self.assertTrue(ancient_ruin.attributes["tech"])
        self.assertEqual(ancient_ruin.attributes["gold"], 10)
        self.assertNotIn("description", ancient_ruin.attributes)
        self.assertNotIn("sound", ancient_ruin.attributes)
        self.assertEqual(
            {
                (item.kind, item.target_kind, item.target_type_id)
                for item in bundle.references
                if item.source_type_id == "GOODY_TEST"
            },
            {
                ("grants_unit_class", "unit_class", "UNITCLASS_WARRIOR"),
                (
                    "spawns_barbarian_unit_class",
                    "unit_class",
                    "UNITCLASS_WARRIOR",
                ),
            },
        )
        resolution = next(
            item for item in bundle.entities if item.type_id == "RESOLUTION_TEST"
        )
        self.assertTrue(resolution.attributes["automatic_proposal"])
        self.assertEqual(resolution.attributes["quorum_percent"], 10)
        self.assertNotIn("description", resolution.attributes)
        self.assertNotIn("help", resolution.attributes)
        world_congress_kinds = {
            "league_project_reward",
            "league_project",
            "league_special_session",
            "resolution",
            "vote_source",
            "vote",
        }
        self.assertEqual(
            {
                (item.kind, item.source_kind, item.target_kind)
                for item in bundle.references
                if item.source_kind in world_congress_kinds
            },
            {
                ("grants_building", "league_project_reward", "building"),
                ("grants_unit_class", "league_project_reward", "unit_class"),
                ("uses_process", "league_project", "process"),
                (
                    "grants_tier_1_reward",
                    "league_project",
                    "league_project_reward",
                ),
                (
                    "grants_tier_2_reward",
                    "league_project",
                    "league_project_reward",
                ),
                (
                    "grants_tier_3_reward",
                    "league_project",
                    "league_project_reward",
                ),
                ("triggered_by_era", "league_special_session", "era"),
                (
                    "immediately_proposes",
                    "league_special_session",
                    "resolution",
                ),
                (
                    "recurringly_proposes",
                    "league_special_session",
                    "resolution",
                ),
                ("uses_voter_decision", "resolution", "resolution_decision"),
                (
                    "uses_proposer_decision",
                    "resolution",
                    "resolution_decision",
                ),
                ("requires_member_technology", "resolution", "technology"),
                ("enables_league_project", "resolution", "league_project"),
                ("grants_specialist", "vote_source", "specialist"),
                ("grants_policy", "vote_source", "policy"),
                ("uses_vote_source", "vote", "vote_source"),
            },
        )
        minor_civ = next(
            item for item in bundle.entities if item.type_id == "MINOR_CIV_TEST"
        )
        self.assertEqual(minor_civ.attributes, {})
        minor_trait = next(
            item for item in bundle.entities if item.type_id == "MINOR_TRAIT_TEST"
        )
        self.assertEqual(minor_trait.attributes, {})
        self.assertIn(
            (
                "has_minor_civ_trait",
                "MINOR_CIV_TEST",
                "MINOR_TRAIT_TEST",
            ),
            {
                (item.kind, item.source_type_id, item.target_type_id)
                for item in bundle.references
            },
        )
        project_relations = {
            (item.kind, item.source_type_id, item.target_type_id)
            for item in bundle.references
            if item.source_kind in {"project", "process"} and not item.attributes
        }
        self.assertEqual(
            project_relations,
            {
                ("requires_victory", "PROJECT_TEST", "VICTORY_TEST"),
                ("unlocked_by_technology", "PROJECT_TEST", "TECH_AGRICULTURE"),
                ("requires_anyone_project", "PROJECT_TEST", "PROJECT_TEST"),
                ("unlocked_by_technology", "PROCESS_TEST", "TECH_AGRICULTURE"),
            },
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

    def test_rejects_invalid_database_number(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-number.db"
            create_database(database, invalid_number=True)
            with self.assertRaisesRegex(
                KnowledgeImportError, "invalid number HappinessPerFollowingCity"
            ):
                import_ruleset(
                    database, "cache/bad-number.db", Ruleset("bnw", "test")
                )

    def test_rejects_invalid_game_speed_integer(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-game-speed.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE GameSpeeds SET ResearchPercent = ?",
                    ("invalid",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "game_speed GAMESPEED_STANDARD has invalid integer ResearchPercent",
            ):
                import_ruleset(
                    database,
                    "cache/bad-game-speed.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_climate_number(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-climate.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Climates SET SnowLatitudeChange = ?",
                    ("invalid",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "climate CLIMATE_TEST has invalid number SnowLatitudeChange",
            ):
                import_ruleset(
                    database,
                    "cache/bad-climate.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_promotion_with_missing_invisibility(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing-invisibility.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE UnitPromotions SET Invisible = ? "
                    "WHERE Type = ?",
                    ("INVISIBLE_MISSING", "PROMOTION_SHOCK_1"),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeValidationError,
                "reference target does not exist",
            ):
                import_ruleset(
                    database,
                    "cache/missing-invisibility.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_global_define_integer(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-global-define.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Defines SET Value = ? WHERE Name = ?",
                    ("invalid", "MAX_HIT_POINTS"),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "global define MAX_HIT_POINTS has invalid integer value",
            ):
                import_ruleset(
                    database,
                    "cache/bad-global-define.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_missing_required_global_define(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing-global-define.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "DELETE FROM Defines WHERE Name = ?",
                    ("MAX_HIT_POINTS",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "required global defines are missing: MAX_HIT_POINTS",
            ):
                import_ruleset(
                    database,
                    "cache/missing-global-define.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_ancient_ruin_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-goody.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("UPDATE GoodyHuts SET Tech = 2")
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "ancient_ruin_outcome GOODY_TEST has invalid boolean Tech",
            ):
                import_ruleset(
                    database,
                    "cache/bad-goody.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_resolution_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-resolution.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Resolutions SET AutomaticProposal = 2"
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "resolution RESOLUTION_TEST has invalid boolean AutomaticProposal",
            ):
                import_ruleset(
                    database,
                    "cache/bad-resolution.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_minor_civilization_with_missing_trait(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing-minor-trait.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE MinorCivilizations SET MinorCivTrait = ?",
                    ("MINOR_TRAIT_MISSING",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeValidationError,
                "reference target does not exist",
            ):
                import_ruleset(
                    database,
                    "cache/missing-minor-trait.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_theming_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-theming.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Building_ThemingBonuses SET SameEra = 2"
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError, "invalid theming boolean SameEra"
            ):
                import_ruleset(
                    database, "cache/bad-theming.db", Ruleset("bnw", "test")
                )

    def test_rejects_invalid_theming_bonus(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-theming-bonus.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Building_ThemingBonuses SET Bonus = ?", ("invalid",)
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError, "invalid theming Bonus"
            ):
                import_ruleset(
                    database,
                    "cache/bad-theming-bonus.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_theming_rule_with_missing_building(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing-theming-building.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Building_ThemingBonuses SET BuildingType = ?",
                    ("BUILDING_MISSING",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError, "references missing building"
            ):
                import_ruleset(
                    database,
                    "cache/missing-theming-building.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_duplicate_theming_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "duplicate-theming.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                columns = [
                    "BuildingType",
                    "Description",
                    "Bonus",
                    *THEMING_BONUS_BOOLEAN_COLUMNS,
                    "AIPriority",
                ]
                quoted = ", ".join(f'"{column}"' for column in columns)
                connection.execute(
                    f"INSERT INTO Building_ThemingBonuses ({quoted}) "
                    f"SELECT {quoted} FROM Building_ThemingBonuses LIMIT 1"
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError, "duplicate theming rule"
            ):
                import_ruleset(
                    database,
                    "cache/duplicate-theming.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_quantity_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-quantity.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Terrain_Yields SET Yield = ?", ("invalid",)
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError, "Terrain_Yields has invalid integer Yield"
            ):
                import_ruleset(
                    database, "cache/bad-quantity.db", Ruleset("bnw", "test")
                )

    def test_rejects_duplicate_quantity_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "duplicate-quantity.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "INSERT INTO Terrain_Yields VALUES (?, ?, ?)",
                    ("TERRAIN_TEST", "YIELD_TEST", 2),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeValidationError, "duplicate reference"
            ):
                import_ruleset(
                    database,
                    "cache/duplicate-quantity.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_contextual_quantity_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-contextual-quantity.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Improvement_TechYieldChanges SET Yield = ?",
                    ("invalid",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "Improvement_TechYieldChanges has invalid integer Yield",
            ):
                import_ruleset(
                    database,
                    "cache/bad-contextual-quantity.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_attributed_reference_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-attributed-reference.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE UnitPromotions_Terrains SET DoubleMove = 2"
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "UnitPromotions_Terrains has invalid boolean DoubleMove",
            ):
                import_ruleset(
                    database,
                    "cache/bad-attributed-reference.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_build_feature_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-build-feature.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("UPDATE BuildFeatures SET Remove = 2")
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "BuildFeatures has invalid boolean Remove",
            ):
                import_ruleset(
                    database,
                    "cache/bad-build-feature.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_build_feature_with_missing_technology(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing-build-feature-tech.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE BuildFeatures SET PrereqTech = ?",
                    ("TECH_MISSING",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeValidationError,
                "context does not exist",
            ):
                import_ruleset(
                    database,
                    "cache/missing-build-feature-tech.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_tech_enhanced_yield_without_technology(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing-enhanced-yield-tech.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Buildings SET EnhancedYieldTech = NULL"
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "requires Buildings.EnhancedYieldTech for BUILDING_PYRAMID",
            ):
                import_ruleset(
                    database,
                    "cache/missing-enhanced-yield-tech.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_invalid_project_victory_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-project-threshold.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Project_VictoryThresholds SET MinThreshold = ?",
                    ("invalid",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "Project_VictoryThresholds has invalid integer MinThreshold",
            ):
                import_ruleset(
                    database,
                    "cache/bad-project-threshold.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_civilization_replacement_in_wrong_class(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bad-override.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "UPDATE Civilization_UnitClassOverrides "
                    "SET UnitClassType = ? WHERE UnitType = ?",
                    ("UNITCLASS_SWORDSMAN", "UNIT_WARRIOR"),
                )
                connection.commit()
            with self.assertRaisesRegex(KnowledgeImportError, "belongs to"):
                import_ruleset(
                    database,
                    "cache/bad-override.db",
                    Ruleset("bnw", "test"),
                )

    def test_rejects_ocean_start_for_missing_civilization(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "missing-ocean-start-civilization.db"
            create_database(database)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    "INSERT INTO Civilization_Start_Along_Ocean VALUES (?)",
                    ("CIVILIZATION_MISSING",),
                )
                connection.commit()
            with self.assertRaisesRegex(
                KnowledgeImportError,
                "references missing civilization",
            ):
                import_ruleset(
                    database,
                    "cache/missing-ocean-start-civilization.db",
                    Ruleset("bnw", "test"),
                )

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
