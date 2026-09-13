from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from .codec import dumps
from .models import Entity, KnowledgeBundle, Reference, Ruleset, Source
from .validation import KnowledgeValidationError, validate_bundle


TECHNOLOGY_FIELDS = {
    "Cost": ("cost", "integer"),
    "AdvancedStartCost": ("advanced_start_cost", "integer"),
    "FirstFreeUnitClass": ("first_free_unit_class", "identifier"),
    "FeatureProductionModifier": ("feature_production_modifier", "integer"),
    "UnitFortificationModifier": ("unit_fortification_modifier", "integer"),
    "UnitBaseHealModifier": ("unit_base_heal_modifier", "integer"),
    "WorkerSpeedModifier": ("worker_speed_modifier", "integer"),
    "FirstFreeTechs": ("first_free_techs", "integer"),
    "EmbarkedMoveChange": ("embarked_move_change", "integer"),
    "InternationalTradeRoutesChange": ("international_trade_routes_change", "integer"),
    "InfluenceSpreadModifier": ("influence_spread_modifier", "integer"),
    "ExtraVotesPerDiplomat": ("extra_votes_per_diplomat", "integer"),
    "EndsGame": ("ends_game", "boolean"),
    "AllowsEmbarking": ("allows_embarking", "boolean"),
    "AllowsDefensiveEmbarking": ("allows_defensive_embarking", "boolean"),
    "EmbarkedAllWaterPassage": ("embarked_all_water_passage", "boolean"),
    "AllowsBarbarianBoats": ("allows_barbarian_boats", "boolean"),
    "Repeat": ("repeat", "boolean"),
    "Trade": ("trade", "boolean"),
    "Disable": ("disabled", "boolean"),
    "GoodyTech": ("available_from_ancient_ruin", "boolean"),
    "ExtraWaterSeeFrom": ("extra_water_see_from", "boolean"),
    "MapCentering": ("map_centering", "boolean"),
    "MapVisible": ("map_visible", "boolean"),
    "MapTrading": ("map_trading", "boolean"),
    "TechTrading": ("technology_trading", "boolean"),
    "GoldTrading": ("gold_trading", "boolean"),
    "AllowEmbassyTradingAllowed": ("embassy_trading", "boolean"),
    "OpenBordersTradingAllowed": ("open_borders_trading", "boolean"),
    "DefensivePactTradingAllowed": ("defensive_pact_trading", "boolean"),
    "ResearchAgreementTradingAllowed": ("research_agreement_trading", "boolean"),
    "TradeAgreementTradingAllowed": ("trade_agreement_trading", "boolean"),
    "PermanentAllianceTradingAllowed": ("permanent_alliance_trading", "boolean"),
    "BridgeBuilding": ("bridge_building", "boolean"),
    "WaterWork": ("water_work", "boolean"),
    "TriggersArchaeologicalSites": ("triggers_archaeological_sites", "boolean"),
    "AllowsWorldCongress": ("allows_world_congress", "boolean"),
    "GridX": ("grid_x", "integer"),
    "GridY": ("grid_y", "integer"),
}

ERA_FIELDS = {
    "NoGoodies": ("no_ancient_ruins", "boolean"),
    "NoBarbUnits": ("no_barbarian_units", "boolean"),
    "NoReligion": ("no_religion", "boolean"),
    "ResearchAgreementCost": ("research_agreement_cost", "integer"),
    "EmbarkedUnitDefense": ("embarked_unit_defense", "integer"),
    "StartingUnitMultiplier": ("starting_unit_multiplier", "integer"),
    "StartingDefenseUnits": ("starting_defense_units", "integer"),
    "StartingWorkerUnits": ("starting_worker_units", "integer"),
    "StartingExploreUnits": ("starting_explore_units", "integer"),
    "StartingGold": ("starting_gold", "integer"),
    "StartingCulture": ("starting_culture", "integer"),
    "FreePopulation": ("free_population", "integer"),
    "LaterEraBuildingConstructMod": ("later_era_building_construct_modifier", "integer"),
    "StartPercent": ("start_percent", "integer"),
    "BuildingMaintenancePercent": ("building_maintenance_percent", "integer"),
    "GrowthPercent": ("growth_percent", "integer"),
    "TrainPercent": ("train_percent", "integer"),
    "ConstructPercent": ("construct_percent", "integer"),
    "CreatePercent": ("create_percent", "integer"),
    "ResearchPercent": ("research_percent", "integer"),
    "BuildPercent": ("build_percent", "integer"),
    "ImprovementPercent": ("improvement_percent", "integer"),
    "GreatPeoplePercent": ("great_people_percent", "integer"),
    "CulturePercent": ("culture_percent", "integer"),
    "TradeRouteFoodBonusTimes100": ("trade_route_food_bonus_times100", "integer"),
    "TradeRouteProductionBonusTimes100": (
        "trade_route_production_bonus_times100",
        "integer",
    ),
    "EventChancePerTurn": ("event_chance_per_turn", "integer"),
    "SpiesGrantedForPlayer": ("spies_granted_for_player", "integer"),
    "SpiesGrantedForEveryone": ("spies_granted_for_everyone", "integer"),
    "FaithCostMultiplier": ("faith_cost_multiplier", "integer"),
    "LeaguePercent": ("league_percent", "integer"),
    "WarmongerPercent": ("warmonger_percent", "integer"),
}


class KnowledgeImportError(ValueError):
    pass


def import_technologies(
    database_path: Path,
    source_label: str,
    ruleset: Ruleset,
) -> KnowledgeBundle:
    database_path = database_path.resolve(strict=True)
    if not database_path.is_file():
        raise KnowledgeImportError(f"database is not a regular file: {database_path}")
    wal_path = Path(f"{database_path}-wal")
    if wal_path.exists() and wal_path.stat().st_size:
        raise KnowledgeImportError("database has a non-empty WAL; close Civ V and retry")

    digest_before = _sha256(database_path)
    size_before = database_path.stat().st_size
    source = Source(source_label, digest_before, size_before)
    uri = database_path.as_uri() + "?mode=ro&immutable=1"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            _require_columns(
                connection,
                "Technologies",
                {"Type", "Era", *TECHNOLOGY_FIELDS},
            )
            _require_columns(connection, "Eras", {"Type", *ERA_FIELDS})
            _require_columns(
                connection,
                "Technology_PrereqTechs",
                {"TechType", "PrereqTech"},
            )
            _require_columns(
                connection,
                "Technology_ORPrereqTechs",
                {"TechType", "PrereqTech"},
            )
            era_columns = ["Type", *ERA_FIELDS]
            era_select = ", ".join(f'"{column}"' for column in era_columns)
            era_rows = connection.execute(
                f'SELECT {era_select} FROM "Eras" ORDER BY "Type"'
            ).fetchall()
            if not era_rows:
                raise KnowledgeImportError("Eras table is empty")
            era_entities = tuple(
                _scalar_entity("era", row, ERA_FIELDS, source_label)
                for row in era_rows
            )
            columns = ["Type", "Era", *TECHNOLOGY_FIELDS]
            select = ", ".join(f'"{column}"' for column in columns)
            rows = connection.execute(
                f'SELECT {select} FROM "Technologies" ORDER BY "Type"'
            ).fetchall()
            if not rows:
                raise KnowledgeImportError("Technologies table is empty")
            technology_entities = tuple(
                _scalar_entity("technology", row, TECHNOLOGY_FIELDS, source_label)
                for row in rows
            )
            era_references = [
                Reference(
                    "belongs_to",
                    "technology",
                    row["Type"],
                    "era",
                    row["Era"],
                    (source_label,),
                )
                for row in rows
            ]
            references = tuple(
                era_references
                + _technology_references(
                    connection,
                    "Technology_PrereqTechs",
                    "requires_all",
                    source_label,
                )
                + _technology_references(
                    connection,
                    "Technology_ORPrereqTechs",
                    "requires_any",
                    source_label,
                )
            )
    except sqlite3.DatabaseError as error:
        raise KnowledgeImportError(f"cannot read Civ V database: {error}") from error

    digest_after = _sha256(database_path)
    if digest_after != digest_before or database_path.stat().st_size != size_before:
        raise KnowledgeImportError("database changed during import; close Civ V and retry")
    return validate_bundle(
        KnowledgeBundle(
            schema_version=1,
            ruleset=ruleset,
            sources=(source,),
            entities=era_entities + technology_entities,
            references=references,
        )
    )


def _scalar_entity(
    kind: str,
    row: sqlite3.Row,
    fields: dict[str, tuple[str, str]],
    source_label: str,
) -> Entity:
    attributes: dict[str, Any] = {}
    for column, (attribute, value_type) in fields.items():
        value = row[column]
        if value_type == "boolean":
            if value not in (0, 1):
                raise KnowledgeImportError(
                    f"{kind} {row['Type']} has invalid boolean {column}: {value}"
                )
            value = bool(value)
        elif value_type == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                raise KnowledgeImportError(
                    f"{kind} {row['Type']} has invalid integer {column}: {value}"
                )
        elif value is not None and not isinstance(value, str):
            raise KnowledgeImportError(
                f"{kind} {row['Type']} has invalid identifier {column}: {value}"
            )
        attributes[attribute] = value
    return Entity(kind, row["Type"], attributes, (source_label,))


def _technology_references(
    connection: sqlite3.Connection,
    table: str,
    kind: str,
    source_label: str,
) -> list[Reference]:
    rows = connection.execute(
        f'SELECT "TechType", "PrereqTech" FROM "{table}" '
        'ORDER BY "TechType", "PrereqTech"'
    ).fetchall()
    return [
        Reference(
            kind,
            "technology",
            row["TechType"],
            "technology",
            row["PrereqTech"],
            (source_label,),
        )
        for row in rows
    ]


def _require_columns(
    connection: sqlite3.Connection, table: str, required: set[str]
) -> None:
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    if table_exists is None:
        raise KnowledgeImportError(f"required table is missing: {table}")
    columns = {
        row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')
    }
    missing = sorted(required - columns)
    if missing:
        raise KnowledgeImportError(
            f"required columns are missing from {table}: {', '.join(missing)}"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_output(path: Path, payload: str, force: bool) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise KnowledgeImportError(f"output already exists: {path}; pass --force to replace")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import a deterministic technology catalog from Civ V SQLite"
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--family", choices=("vanilla", "gk", "bnw"), required=True)
    parser.add_argument("--game-version", required=True)
    parser.add_argument("--dlc", action="append", default=[])
    parser.add_argument("--mod", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        ruleset = Ruleset(
            args.family,
            args.game_version,
            tuple(sorted(set(args.dlc))),
            tuple(sorted(set(args.mod))),
        )
        bundle = import_technologies(args.database, args.source_label, ruleset)
        payload = dumps(bundle)
        if args.output is None:
            print(payload)
        else:
            _write_output(args.output, payload, args.force)
            print(
                json.dumps(
                    {
                        "status": "success",
                        "output": str(args.output),
                        "entities": len(bundle.entities),
                        "references": len(bundle.references),
                    },
                    sort_keys=True,
                )
            )
        return 0
    except (KnowledgeImportError, KnowledgeValidationError, OSError) as error:
        print(json.dumps({"status": "error", "message": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
