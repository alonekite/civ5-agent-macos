from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from .codec import dumps
from .models import (
    Entity,
    KnowledgeBundle,
    Reference,
    ReferenceContext,
    Ruleset,
    Source,
)
from .validation import KnowledgeValidationError, validate_bundle


GODS_AND_KINGS_PACKAGE_ID = "0E3751A1F8404E1B9706519BF484E59D"
BRAVE_NEW_WORLD_PACKAGE_ID = "6DA0763641234018B6436575B4EC336B"


def _snake_case(value: str) -> str:
    words = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", words).lower()


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

UNIT_FIELDS = {
    "Combat": ("combat", "integer"),
    "RangedCombat": ("ranged_combat", "integer"),
    "Cost": ("cost", "integer"),
    "FaithCost": ("faith_cost", "integer"),
    "RequiresFaithPurchaseEnabled": ("requires_faith_purchase", "boolean"),
    "PurchaseOnly": ("purchase_only", "boolean"),
    "MoveAfterPurchase": ("move_after_purchase", "boolean"),
    "Moves": ("moves", "integer"),
    "Immobile": ("immobile", "boolean"),
    "Range": ("range", "integer"),
    "BaseSightRange": ("base_sight_range", "integer"),
    "Special": ("special_unit", "identifier"),
    "Capture": ("capture_unit", "identifier"),
    "CombatClass": ("combat_class", "identifier"),
    "Domain": ("domain", "identifier"),
    "Food": ("food_production", "boolean"),
    "NoBadGoodies": ("no_bad_ancient_ruins", "boolean"),
    "RivalTerritory": ("rival_territory", "boolean"),
    "MilitarySupport": ("military_support", "boolean"),
    "MilitaryProduction": ("military_production", "boolean"),
    "Pillage": ("can_pillage", "boolean"),
    "PillagePrereqTech": ("pillage_prerequisite_technology", "identifier"),
    "Found": ("can_found_city", "boolean"),
    "FoundAbroad": ("can_found_abroad", "boolean"),
    "CultureBombRadius": ("culture_bomb_radius", "integer"),
    "GoldenAgeTurns": ("golden_age_turns", "integer"),
    "FreePolicies": ("free_policies", "integer"),
    "OneShotTourism": ("one_shot_tourism", "integer"),
    "OneShotTourismPercentOthers": ("one_shot_tourism_percent_others", "integer"),
    "IgnoreBuildingDefense": ("ignore_building_defense", "boolean"),
    "PrereqResources": ("requires_resources", "boolean"),
    "Mechanized": ("mechanized", "boolean"),
    "Suicide": ("suicide", "boolean"),
    "CaptureWhileEmbarked": ("capture_while_embarked", "boolean"),
    "PrereqTech": ("prerequisite_technology", "identifier"),
    "ObsoleteTech": ("obsolete_technology", "identifier"),
    "GoodyHutUpgradeUnitClass": ("ancient_ruin_upgrade_unit_class", "identifier"),
    "HurryCostModifier": ("hurry_cost_modifier", "integer"),
    "AdvancedStartCost": ("advanced_start_cost", "integer"),
    "MinAreaSize": ("minimum_area_size", "integer"),
    "AirInterceptRange": ("air_intercept_range", "integer"),
    "AirUnitCap": ("air_unit_cap", "integer"),
    "NukeDamageLevel": ("nuclear_damage_level", "integer"),
    "WorkRate": ("work_rate", "integer"),
    "NumFreeTechs": ("free_technologies", "integer"),
    "BaseBeakersTurnsToCount": ("base_science_turns_to_count", "integer"),
    "BaseCultureTurnsToCount": ("base_culture_turns_to_count", "integer"),
    "RushBuilding": ("can_rush_building", "boolean"),
    "BaseHurry": ("base_hurry", "integer"),
    "HurryMultiplier": ("hurry_multiplier", "integer"),
    "BaseGold": ("base_gold", "integer"),
    "NumGoldPerEra": ("gold_per_era", "integer"),
    "SpreadReligion": ("can_spread_religion", "boolean"),
    "RemoveHeresy": ("can_remove_heresy", "boolean"),
    "ReligionSpreads": ("religion_spreads", "integer"),
    "ReligiousStrength": ("religious_strength", "integer"),
    "FoundReligion": ("can_found_religion", "boolean"),
    "RequiresEnhancedReligion": ("requires_enhanced_religion", "boolean"),
    "ProhibitsSpread": ("prohibits_religious_spread", "boolean"),
    "CanBuyCityState": ("can_buy_city_state", "boolean"),
    "CombatLimit": ("combat_limit", "integer"),
    "RangeAttackOnlyInDomain": ("range_attack_only_in_domain", "boolean"),
    "RangeAttackIgnoreLOS": ("range_attack_ignores_line_of_sight", "boolean"),
    "Trade": ("trade_unit", "boolean"),
    "NumExoticGoods": ("exotic_goods", "integer"),
    "PolicyType": ("required_policy", "identifier"),
    "RangedCombatLimit": ("ranged_combat_limit", "integer"),
    "XPValueAttack": ("experience_value_attack", "integer"),
    "XPValueDefense": ("experience_value_defense", "integer"),
    "SpecialCargo": ("special_cargo", "identifier"),
    "DomainCargo": ("domain_cargo", "identifier"),
    "Conscription": ("conscription", "integer"),
    "ExtraMaintenanceCost": ("extra_maintenance_cost", "integer"),
    "NoMaintenance": ("no_maintenance", "boolean"),
    "Unhappiness": ("unhappiness", "integer"),
    "ProjectPrereq": ("prerequisite_project", "identifier"),
    "SpaceshipProject": ("spaceship_project", "identifier"),
    "LeaderPromotion": ("leader_promotion", "identifier"),
    "LeaderExperience": ("leader_experience", "integer"),
}
UNIT_REFERENCE_COLUMNS = (
    ("Capture", "captured_as_unit_class", "unit_class"),
    ("PillagePrereqTech", "pillage_unlocked_by_technology", "technology"),
    ("PrereqTech", "unlocked_by_technology", "technology"),
    ("ObsoleteTech", "obsoleted_by_technology", "technology"),
    ("GoodyHutUpgradeUnitClass", "ancient_ruin_upgrade", "unit_class"),
    ("PolicyType", "requires_policy", "policy"),
    ("SpecialCargo", "carries_special_unit", "special_unit"),
    ("DomainCargo", "carries_domain", "domain"),
    ("ProjectPrereq", "requires_project", "project"),
    ("SpaceshipProject", "completes_project", "project"),
    ("LeaderPromotion", "grants_leader_promotion", "promotion"),
)

UNIT_CLASS_FIELDS = {
    "MaxGlobalInstances": ("maximum_global_instances", "integer"),
    "MaxTeamInstances": ("maximum_team_instances", "integer"),
    "MaxPlayerInstances": ("maximum_player_instances", "integer"),
    "InstanceCostModifier": ("instance_cost_modifier", "integer"),
}

PROMOTION_BOOLEAN_COLUMNS = (
    "CannotBeChosen",
    "LostWithUpgrade",
    "NotWithUpgrade",
    "InstaHeal",
    "Leader",
    "Blitz",
    "Amphib",
    "River",
    "EnemyRoute",
    "RivalTerritory",
    "MustSetUpToRangedAttack",
    "RangedSupportFire",
    "CanMoveAfterAttacking",
    "AlwaysHeal",
    "HealOutsideFriendly",
    "HillsDoubleMove",
    "RoughTerrainEndsTurn",
    "IgnoreTerrainCost",
    "HoveringUnit",
    "FlatMovementCost",
    "CanMoveImpassable",
    "NoCapture",
    "OnlyDefensive",
    "NoDefensiveBonus",
    "NukeImmune",
    "HiddenNationality",
    "AlwaysHostile",
    "NoRevealMap",
    "Recon",
    "CanMoveAllTerrain",
    "FreePillageMoves",
    "AirSweepCapable",
    "AllowsEmbarkation",
    "EmbarkedAllWater",
    "HealIfDestroyExcludesBarbarians",
    "RangeAttackIgnoreLOS",
    "CityAttackOnly",
    "CaptureDefeatedEnemy",
    "HealOnPillage",
    "IgnoreGreatGeneralBenefit",
    "IgnoreZOC",
    "HasPostCombatPromotions",
    "PostCombatPromotionsExclusive",
    "GreatGeneral",
    "GreatAdmiral",
    "GreatGeneralReceivesMovement",
    "Sapper",
    "HeavyCharge",
)

PROMOTION_INTEGER_COLUMNS = (
    "RangedAttackModifier",
    "InterceptionCombatModifier",
    "InterceptionDefenseDamageModifier",
    "AirSweepCombatModifier",
    "ExtraAttacks",
    "ExtraNavalMovement",
    "VisibilityChange",
    "MovesChange",
    "MoveDiscountChange",
    "RangeChange",
    "InterceptChanceChange",
    "NumInterceptionChange",
    "EvasionChange",
    "CargoChange",
    "EnemyHealChange",
    "NeutralHealChange",
    "FriendlyHealChange",
    "SameTileHealChange",
    "AdjacentTileHealChange",
    "EnemyDamageChance",
    "NeutralDamageChance",
    "EnemyDamage",
    "NeutralDamage",
    "CombatPercent",
    "CityAttack",
    "CityDefense",
    "RangedDefenseMod",
    "HillsAttack",
    "HillsDefense",
    "OpenAttack",
    "OpenRangedAttackMod",
    "OpenDefense",
    "RoughAttack",
    "RoughRangedAttackMod",
    "RoughDefense",
    "AttackFortifiedMod",
    "AttackWoundedMod",
    "FlankAttackModifier",
    "NearbyEnemyCombatMod",
    "NearbyEnemyCombatRange",
    "UpgradeDiscount",
    "ExperiencePercent",
    "AdjacentMod",
    "AttackMod",
    "DefenseMod",
    "DropRange",
    "GreatGeneralModifier",
    "GreatGeneralCombatModifier",
    "FriendlyLandsModifier",
    "FriendlyLandsAttackModifier",
    "OutsideFriendlyLandsModifier",
    "HPHealedIfDestroyEnemy",
    "ExtraWithdrawal",
    "EmbarkExtraVisibility",
    "EmbarkDefenseModifier",
    "CapitalDefenseModifier",
    "CapitalDefenseFalloff",
    "CityAttackPlunderModifier",
    "ReligiousStrengthLossRivalTerritory",
    "TradeMissionInfluenceModifier",
    "TradeMissionGoldModifier",
    "GoldenAgeValueFromKills",
)

PROMOTION_IDENTIFIER_COLUMNS = ("Invisible", "SeeInvisible")
PROMOTION_PREREQUISITE_COLUMNS = (
    "PromotionPrereq",
    "PromotionPrereqOr1",
    "PromotionPrereqOr2",
    "PromotionPrereqOr3",
    "PromotionPrereqOr4",
    "PromotionPrereqOr5",
    "PromotionPrereqOr6",
    "PromotionPrereqOr7",
    "PromotionPrereqOr8",
    "PromotionPrereqOr9",
)
PROMOTION_FIELDS = {
    **{column: (_snake_case(column), "boolean") for column in PROMOTION_BOOLEAN_COLUMNS},
    **{column: (_snake_case(column), "integer") for column in PROMOTION_INTEGER_COLUMNS},
    **{
        column: (_snake_case(column), "identifier")
        for column in PROMOTION_IDENTIFIER_COLUMNS
    },
}

POLICY_INTEGER_COLUMNS = (
    "NumExtraBranches",
    "CultureCost",
    "GridX",
    "GridY",
    "Level",
    "PolicyCostModifier",
    "CulturePerCity",
    "CulturePerWonder",
    "CultureWonderMultiplier",
    "CulturePerTechResearched",
    "CultureImprovementChange",
    "CultureFromKills",
    "CultureFromBarbarianKills",
    "GoldFromKills",
    "EmbarkedExtraMoves",
    "AttackBonusTurns",
    "GoldenAgeTurns",
    "GoldenAgeMeterMod",
    "GoldenAgeDurationMod",
    "NumFreeTechs",
    "NumFreePolicies",
    "NumFreeGreatPeople",
    "StrategicResourceMod",
    "WonderProductionModifier",
    "BuildingProductionModifier",
    "GreatPeopleRateModifier",
    "GreatGeneralRateModifier",
    "GreatAdmiralRateModifier",
    "GreatWriterRateModifier",
    "GreatArtistRateModifier",
    "GreatMusicianRateModifier",
    "GreatMerchantRateModifier",
    "GreatScientistRateModifier",
    "ExtraHappiness",
    "ExtraHappinessPerCity",
    "UnhappinessMod",
    "CityCountUnhappinessMod",
    "OccupiedPopulationUnhappinessMod",
    "CapitalUnhappinessMod",
    "FreeExperience",
    "WorkerSpeedModifier",
    "MilitaryProductionModifier",
    "HappinessPerGarrisonedUnit",
    "CulturePerGarrisonedUnit",
    "HappinessPerTradeRoute",
    "ExtraHappinessPerLuxury",
    "PlotGoldCostMod",
    "PlotCultureCostModifier",
    "UnitPurchaseCostModifier",
    "BuildingPurchaseCostModifier",
    "FaithCostModifier",
    "GoldPerUnit",
    "GoldPerMilitaryUnit",
    "RouteGoldMaintenanceMod",
    "BuildingGoldMaintenanceMod",
    "UnitGoldMaintenanceMod",
    "UnitSupplyMod",
    "UnitUpgradeCostMod",
    "CityStrengthMod",
    "CityGrowthMod",
    "CapitalGrowthMod",
    "SettlerProductionModifier",
    "CapitalSettlerProductionModifier",
    "NewCityExtraPopulation",
    "FreeFoodBox",
    "UnitSightRangeChange",
    "WoundedUnitDamageMod",
    "BarbarianCombatBonus",
    "MinorQuestFriendshipMod",
    "MinorGoldFriendshipMod",
    "MinorFriendshipMinimum",
    "MinorFriendshipDecayMod",
    "OtherPlayersMinorFriendshipDecayMod",
    "CityStateUnitFrequencyModifier",
    "CommonFoeTourismModifier",
    "LessHappyTourismModifier",
    "SharedIdeologyTourismModifier",
    "LandTradeRouteGoldChange",
    "SeaTradeRouteGoldChange",
    "SharedIdeologyTradeGoldChange",
    "RiggingElectionModifier",
    "MilitaryUnitGiftExtraInfluence",
    "ProtectedMinorPerTurnInfluence",
    "AfraidMinorPerTurnInfluence",
    "MinorBullyScoreModifier",
    "CityStateTradeChange",
    "ThemingBonusMultiplier",
    "InternalTradeRouteYieldModifier",
    "SharedReligionTourismModifier",
    "TradeRouteTourismModifier",
    "OpenBordersTourismModifier",
)

POLICY_BOOLEAN_COLUMNS = (
    "MilitaryFoodProduction",
    "HalfSpecialistUnhappiness",
    "HalfSpecialistFood",
    "AlwaysSeeBarbCamps",
    "RevealAllCapitals",
    "MinorGreatPeopleAllies",
    "MinorScienceAllies",
    "MinorResourceBonus",
    "GarrisonFreeMaintenance",
    "GoldenAgeCultureBonusDisabled",
    "SecondReligionPantheon",
    "AddReformationBelief",
    "EnablesSSPartHurry",
    "EnablesSSPartPurchase",
    "AbleToAnnexCityStates",
    "OneShot",
    "IncludesOneShotFreeUnits",
)

POLICY_FIELDS = {
    **{column: (_snake_case(column), "integer") for column in POLICY_INTEGER_COLUMNS},
    **{column: (_snake_case(column), "boolean") for column in POLICY_BOOLEAN_COLUMNS},
    "FreeBuildingOnConquest": ("free_building_on_conquest", "identifier"),
}

POLICY_BRANCH_FIELDS = {
    "FirstAdopterFreePolicies": ("first_adopter_free_policies", "integer"),
    "SecondAdopterFreePolicies": ("second_adopter_free_policies", "integer"),
    "PurchaseByLevel": ("purchase_by_level", "boolean"),
    "LockedWithoutReligion": ("locked_without_religion", "boolean"),
}

BUILDING_INTEGER_COLUMNS = (
    "GoldMaintenance",
    "MutuallyExclusiveGroup",
    "Cost",
    "FaithCost",
    "LeagueCost",
    "NumCityCostMod",
    "HurryCostModifier",
    "MinAreaSize",
    "ConquestProb",
    "CitiesPrereq",
    "LevelPrereq",
    "CultureRateModifier",
    "GlobalCultureRateModifier",
    "GreatPeopleRateModifier",
    "GlobalGreatPeopleRateModifier",
    "GreatGeneralRateModifier",
    "GreatPersonExpendGold",
    "GoldenAgeModifier",
    "UnitUpgradeCostMod",
    "Experience",
    "GlobalExperience",
    "FoodKept",
    "AirModifier",
    "NukeModifier",
    "HealRateChange",
    "Happiness",
    "UnmoddedHappiness",
    "UnhappinessModifier",
    "HappinessPerCity",
    "HappinessPerXPolicies",
    "CityCountUnhappinessMod",
    "WorkerSpeedModifier",
    "MilitaryProductionModifier",
    "SpaceProductionModifier",
    "GlobalSpaceProductionModifier",
    "BuildingProductionModifier",
    "WonderProductionModifier",
    "Gold",
    "Defense",
    "ExtraCityHitPoints",
    "SpecialistCount",
    "GreatWorkCount",
    "GreatPeopleRateChange",
    "ExtraLeagueVotes",
)

BUILDING_BOOLEAN_COLUMNS = (
    "TeamShare",
    "Water",
    "River",
    "FreshWater",
    "Mountain",
    "NearbyMountainRequired",
    "Hill",
    "Flat",
    "FoundsReligion",
    "IsReligious",
    "BorderObstacle",
    "PlayerBorderObstacle",
    "Capital",
    "GoldenAge",
    "MapCentering",
    "NeverCapture",
    "NukeImmune",
    "AllowsWaterRoutes",
    "ExtraLuxuries",
    "DiplomaticVoting",
    "AffectSpiesNow",
    "NullifyInfluenceModifier",
    "UnlockedByBelief",
    "UnlockedByLeague",
    "HolyCity",
    "Airlift",
    "NoOccupiedUnhappiness",
    "AllowsRangeStrike",
    "Espionage",
    "AllowsFoodTradeRoutes",
    "AllowsProductionTradeRoutes",
    "CityWall",
)

BUILDING_IDENTIFIER_COLUMNS = (
    "NearbyTerrainRequired",
    "ProhibitedCityTerrain",
    "VictoryPrereq",
    "FreeBuilding",
    "FreeBuildingThisCity",
    "SpecialistType",
    "GreatWorkSlotType",
    "FreeGreatWork",
)

BUILDING_FIELDS = {
    **{column: (_snake_case(column), "integer") for column in BUILDING_INTEGER_COLUMNS},
    **{column: (_snake_case(column), "boolean") for column in BUILDING_BOOLEAN_COLUMNS},
    **{
        column: (_snake_case(column), "identifier")
        for column in BUILDING_IDENTIFIER_COLUMNS
    },
}

BUILDING_CLASS_FIELDS = {
    "MaxGlobalInstances": ("maximum_global_instances", "integer"),
    "MaxTeamInstances": ("maximum_team_instances", "integer"),
    "MaxPlayerInstances": ("maximum_player_instances", "integer"),
    "ExtraPlayerInstances": ("extra_player_instances", "integer"),
    "NoLimit": ("no_limit", "boolean"),
    "Monument": ("monument", "boolean"),
}

BUILDING_REFERENCE_COLUMNS = (
    ("FreeStartEra", "free_start_era", "era"),
    ("MaxStartEra", "maximum_start_era", "era"),
    ("ObsoleteTech", "obsoleted_by_technology", "technology"),
    ("EnhancedYieldTech", "enhanced_by_technology", "technology"),
    ("FreePromotion", "grants_promotion", "promotion"),
    ("TrainedFreePromotion", "grants_trained_unit_promotion", "promotion"),
    ("FreePromotionRemoved", "removes_promotion", "promotion"),
    ("ReplacementBuildingClass", "replaces_building_class", "building_class"),
    ("PrereqTech", "unlocked_by_technology", "technology"),
    ("PolicyBranchType", "requires_policy_branch", "policy_branch"),
)

RESOURCE_INTEGER_COLUMNS = (
    "Happiness",
    "WonderProductionMod",
    "StartingResourceQuantity",
    "PlacementOrder",
    "ConstAppearance",
    "MinAreaSize",
    "MinLatitude",
    "MaxLatitude",
    "RandApp1",
    "RandApp2",
    "RandApp3",
    "RandApp4",
    "Player",
    "TilesPer",
    "MinLandPercent",
    "Unique",
    "GroupRange",
    "GroupRand",
    "ResourceUsage",
)

RESOURCE_BOOLEAN_COLUMNS = (
    "PresentOnAllValidPlots",
    "Area",
    "Hills",
    "Flatlands",
    "NoRiverSide",
    "Normalize",
    "OnlyMinorCivs",
)

RESOURCE_FIELDS = {
    **{column: (_snake_case(column), "integer") for column in RESOURCE_INTEGER_COLUMNS},
    **{column: (_snake_case(column), "boolean") for column in RESOURCE_BOOLEAN_COLUMNS},
}

RESOURCE_CLASS_FIELDS = {
    "UniqueRange": ("unique_range", "integer"),
}

RESOURCE_REFERENCE_COLUMNS = (
    ("ResourceClassType", "belongs_to_resource_class", "resource_class"),
    ("TechReveal", "revealed_by_technology", "technology"),
    ("PolicyReveal", "revealed_by_policy", "policy"),
    ("TechCityTrade", "trade_enabled_by_technology", "technology"),
    ("TechObsolete", "obsoleted_by_technology", "technology"),
    ("WonderProductionModObsoleteEra", "wonder_bonus_obsoleted_by_era", "era"),
)

CIVILIZATION_FIELDS = {
    # AIPlayable is intentionally excluded: it is an engine control flag for AI use,
    # not a rules fact needed by the read/write core.
    "Playable": ("playable", "boolean"),
}

TRAIT_INTEGER_COLUMNS = (
    "LevelExperienceModifier",
    "GreatPeopleRateModifier",
    "GreatScientistRateModifier",
    "GreatGeneralRateModifier",
    "GreatGeneralExtraBonus",
    "GreatPersonGiftInfluence",
    "MaxGlobalBuildingProductionModifier",
    "MaxTeamBuildingProductionModifier",
    "MaxPlayerBuildingProductionModifier",
    "CityUnhappinessModifier",
    "PopulationUnhappinessModifier",
    "CityStateBonusModifier",
    "CityStateFriendshipModifier",
    "CityStateCombatModifier",
    "LandBarbarianConversionPercent",
    "LandBarbarianConversionExtraUnits",
    "SeaBarbarianConversionPercent",
    "LandUnitMaintenanceModifier",
    "NavalUnitMaintenanceModifier",
    "CapitalBuildingModifier",
    "PlotBuyCostModifier",
    "PlotCultureCostModifier",
    "CultureFromKills",
    "FaithFromKills",
    "CityCultureBonus",
    "CapitalThemingBonusModifier",
    "PolicyCostModifier",
    "CityConnectionTradeRouteChange",
    "WonderProductionModifier",
    "PlunderModifier",
    "ImprovementMaintenanceModifier",
    "GoldenAgeDurationModifier",
    "GoldenAgeMoveChange",
    "GoldenAgeCombatModifier",
    "GoldenAgeTourismModifier",
    "GoldenAgeGreatArtistRateModifier",
    "GoldenAgeGreatMusicianRateModifier",
    "GoldenAgeGreatWriterRateModifier",
    "ExtraEmbarkMoves",
    "NaturalWonderFirstFinderGold",
    "NaturalWonderSubsequentFinderGold",
    "NaturalWonderYieldModifier",
    "NaturalWonderHappinessModifier",
    "NearbyImprovementCombatBonus",
    "NearbyImprovementBonusRange",
    "CultureBuildingYieldChange",
    "CombatBonusVsHigherTech",
    "CombatBonusVsLargerCiv",
    "RazeSpeedModifier",
    "DOFGreatPersonModifier",
    "LuxuryHappinessRetention",
    "ExtraSpies",
    "UnresearchedTechBonusFromKills",
    "ExtraFoundedCityTerritoryClaimRange",
    "FreeSocialPoliciesPerEra",
    "NumTradeRoutesModifier",
    "TradeRouteResourceModifier",
    "UniqueLuxuryCities",
    "UniqueLuxuryQuantity",
    "WorkerSpeedModifier",
    "AfraidMinorPerTurnInfluence",
    "LandTradeRouteRangeBonus",
    "TradeReligionModifier",
    "TradeBuildingModifier",
)

TRAIT_BOOLEAN_COLUMNS = (
    "FightWellDamaged",
    "MoveFriendlyWoodsAsRoad",
    "FasterAlongRiver",
    "FasterInHills",
    "EmbarkedAllWater",
    "EmbarkedToLandFlatCost",
    "NoHillsImprovementMaintenance",
    "TechBoostFromCapitalScienceBuildings",
    "StaysAliveZeroCities",
    "FaithFromUnimprovedForest",
    "BonusReligiousBelief",
    "AbleToAnnexCityStates",
    "CrossesMountainsAfterGreatGeneral",
    "MayaCalendarBonuses",
    "NoAnnexing",
    "TechFromCityConquer",
    "UniqueLuxuryRequiresNewArea",
    "RiverTradeRoad",
    "AngerFreeIntrusionOfCityStates",
)

TRAIT_FIELDS = {
    **{column: (_snake_case(column), "integer") for column in TRAIT_INTEGER_COLUMNS},
    **{column: (_snake_case(column), "boolean") for column in TRAIT_BOOLEAN_COLUMNS},
}

TRAIT_REFERENCE_COLUMNS = (
    ("FreeUnit", "grants_unit_class", "unit_class"),
    (
        "FreeUnitPrereqTech",
        "free_unit_unlocked_by_technology",
        "technology",
    ),
    ("FreeBuilding", "grants_free_building", "building"),
    ("FreeBuildingOnConquest", "grants_building_on_conquest", "building"),
    ("CombatBonusImprovement", "combat_bonus_near_improvement", "improvement"),
    ("ObsoleteTech", "obsoleted_by_technology", "technology"),
    ("PrereqTech", "unlocked_by_technology", "technology"),
)

BELIEF_BOOLEAN_COLUMNS = (
    "Pantheon",
    "Founder",
    "Follower",
    "Enhancer",
    "Reformation",
    "RequiresPeace",
    "ConvertsBarbarians",
    "FaithPurchaseAllGreatPeople",
)

BELIEF_INTEGER_COLUMNS = (
    "MinPopulation",
    "MinFollowers",
    "MaxDistance",
    "CityGrowthModifier",
    "FaithFromKills",
    "FaithFromDyingUnits",
    "RiverHappiness",
    "HappinessPerCity",
    "HappinessPerXPeacefulForeignFollowers",
    "PlotCultureCostModifier",
    "CityRangeStrikeModifier",
    "CombatModifierEnemyCities",
    "CombatModifierFriendlyCities",
    "FriendlyHealChange",
    "CityStateFriendshipModifier",
    "LandBarbarianConversionPercent",
    "WonderProductionModifier",
    "PlayerHappiness",
    "PlayerCultureModifier",
    "GoldPerFollowingCity",
    "GoldPerXFollowers",
    "GoldPerFirstCityConversion",
    "SciencePerOtherReligionFollower",
    "SpreadDistanceModifier",
    "SpreadStrengthModifier",
    "ProphetStrengthModifier",
    "ProphetCostModifier",
    "MissionaryStrengthModifier",
    "MissionaryCostModifier",
    "FriendlyCityStateSpreadModifier",
    "GreatPersonExpendedFaith",
    "CityStateMinimumInfluence",
    "CityStateInfluenceModifier",
    "OtherReligionPressureErosion",
    "SpyPressure",
    "InquisitorPressureRetention",
    "FaithBuildingTourism",
)

BELIEF_FIELDS = {
    **{column: (_snake_case(column), "boolean") for column in BELIEF_BOOLEAN_COLUMNS},
    **{column: (_snake_case(column), "integer") for column in BELIEF_INTEGER_COLUMNS},
    "HappinessPerFollowingCity": ("happiness_per_following_city", "number"),
}

BELIEF_REFERENCE_COLUMNS = (
    ("ObsoleteEra", "obsoleted_by_era", "era"),
    ("ResourceRevealed", "reveals_resource", "resource"),
    (
        "SpreadModifierDoublingTech",
        "spread_modifier_doubled_by_technology",
        "technology",
    ),
)

SPECIALIST_FIELDS = {
    "Visible": ("visible", "boolean"),
    "Cost": ("cost", "integer"),
    "Experience": ("experience", "integer"),
    "GreatPeopleRateChange": ("great_people_rate_change", "integer"),
    "CulturePerTurn": ("culture_per_turn", "integer"),
}

TERRAIN_FIELDS = {
    **{
        column: (_snake_case(column), "boolean")
        for column in (
            "Water",
            "Impassable",
            "Found",
            "FoundCoast",
            "FoundFreshWater",
        )
    },
    **{
        column: (_snake_case(column), "integer")
        for column in (
            "Movement",
            "SeeFrom",
            "SeeThrough",
            "BuildModifier",
            "Defense",
            "InfluenceCost",
        )
    },
}

FEATURE_BOOLEAN_COLUMNS = (
    "YieldNotAdditive",
    "NoCoast",
    "NoRiver",
    "NoAdjacent",
    "RequiresFlatlands",
    "RequiresRiver",
    "AddsFreshWater",
    "Impassable",
    "NoCity",
    "NoImprovement",
    "VisibleAlways",
    "NukeImmune",
    "NaturalWonder",
    "Rough",
)
FEATURE_INTEGER_COLUMNS = (
    "StartingLocationWeight",
    "Movement",
    "SeeThrough",
    "Defense",
    "InfluenceCost",
    "AppearanceProbability",
    "DisappearanceProbability",
    "Growth",
    "TurnDamage",
    "FirstFinderGold",
    "InBorderHappiness",
    "OccurrenceFrequency",
    "AdvancedStartRemoveCost",
)
FEATURE_FIELDS = {
    **{
        column: (_snake_case(column), "boolean")
        for column in FEATURE_BOOLEAN_COLUMNS
    },
    **{
        column: (_snake_case(column), "integer")
        for column in FEATURE_INTEGER_COLUMNS
    },
}
FAKE_FEATURE_FIELDS = {
    **{
        column: (_snake_case(column), "boolean")
        for column in FEATURE_BOOLEAN_COLUMNS
    },
    **{
        column: (_snake_case(column), "integer")
        for column in (
            "StartingLocationWeight",
            "SeeThrough",
            "Defense",
            "InfluenceCost",
            "AppearanceProbability",
            "DisappearanceProbability",
            "Growth",
            "TurnDamage",
            "AdvancedStartRemoveCost",
        )
    },
}
FEATURE_REFERENCE_COLUMNS = (
    ("GrowthTerrainType", "grows_on_terrain", "terrain"),
    (
        "AdjacentUnitFreePromotion",
        "grants_adjacent_unit_promotion",
        "promotion",
    ),
)

IMPROVEMENT_BOOLEAN_COLUMNS = (
    "SpecificCivRequired",
    "HillsMakesValid",
    "FreshWaterMakesValid",
    "RiverSideMakesValid",
    "NoFreshWater",
    "RequiresFlatlands",
    "RequiresFlatlandsOrFreshWater",
    "RequiresFeature",
    "RequiresImprovement",
    "RemovesResource",
    "PromptWhenComplete",
    "Coastal",
    "Water",
    "DestroyedWhenPillaged",
    "DisplacePillager",
    "BuildableOnResources",
    "BarbarianCamp",
    "Goody",
    "Permanent",
    "OutsideBorders",
    "InAdjacentFriendly",
    "IgnoreOwnership",
    "OnlyCityStateTerritory",
    "CreatedByGreatPerson",
    "NoTwoAdjacent",
    "AdjacentLuxury",
    "AllowsWalkWater",
)
IMPROVEMENT_INTEGER_COLUMNS = (
    "CultureAdjacentSameType",
    "TilesPerGoody",
    "GoodyRange",
    "FeatureGrowth",
    "UpgradeTime",
    "RiverSideUpgradeMod",
    "CoastalLandUpgradeMod",
    "HillsUpgradeMod",
    "FreshWaterUpgradeMod",
    "DefenseModifier",
    "NearbyEnemyDamage",
    "PillageGold",
    "ResourceExtractionMod",
    "LuxuryCopiesSiphonedFromMinor",
    "GoldMaintenance",
    "CultureBombRadius",
    "RequiresXAdjacentLand",
)
IMPROVEMENT_FIELDS = {
    **{
        column: (_snake_case(column), "boolean")
        for column in IMPROVEMENT_BOOLEAN_COLUMNS
    },
    **{
        column: (_snake_case(column), "integer")
        for column in IMPROVEMENT_INTEGER_COLUMNS
    },
}
IMPROVEMENT_REFERENCE_COLUMNS = (
    ("ImprovementPillage", "pillaged_form", "improvement"),
    ("ImprovementUpgrade", "upgrades_to_improvement", "improvement"),
    ("CivilizationType", "restricted_to_civilization", "civilization"),
)

ROUTE_FIELDS = {
    **{
        column: (_snake_case(column), "integer")
        for column in (
            "AdvancedStartCost",
            "Value",
            "Movement",
            "FlatMovement",
            "GoldMaintenance",
        )
    },
    "Industrial": ("industrial", "boolean"),
}

YIELD_FIELDS = {
    column: (_snake_case(column), "integer")
    for column in (
        "HillsChange",
        "MountainChange",
        "LakeChange",
        "CityChange",
        "PopulationChangeOffset",
        "PopulationChangeDivisor",
        "MinCity",
        "GoldenAgeYield",
        "GoldenAgeYieldThreshold",
        "GoldenAgeYieldMod",
    )
}

BUILD_FIELDS = {
    "Time": ("time", "optional_integer"),
    "Cost": ("cost", "integer"),
    "CostIncreasePerImprovement": ("cost_increase_per_improvement", "integer"),
    "Kill": ("kill", "boolean"),
    "Repair": ("repair", "boolean"),
    "RemoveRoute": ("remove_route", "boolean"),
    "Water": ("water", "boolean"),
    "CanBeEmbarked": ("can_be_embarked", "boolean"),
}
BUILD_REFERENCE_COLUMNS = (
    ("PrereqTech", "unlocked_by_technology", "technology"),
    ("ImprovementType", "creates_improvement", "improvement"),
    ("RouteType", "creates_route", "route"),
)

PROJECT_FIELDS = {
    **{
        column: (_snake_case(column), "integer")
        for column in (
            "MaxGlobalInstances",
            "MaxTeamInstances",
            "Cost",
            "NukeInterception",
            "CultureBranchesRequired",
            "TechShare",
            "VictoryDelayPercent",
        )
    },
    **{
        column: (_snake_case(column), "boolean")
        for column in ("Spaceship", "Religious", "AllowsNukes")
    },
}
PROJECT_REFERENCE_COLUMNS = (
    ("VictoryPrereq", "requires_victory", "victory"),
    ("TechPrereq", "unlocked_by_technology", "technology"),
    ("AnyonePrereqProject", "requires_anyone_project", "project"),
)
PROCESS_REFERENCE_COLUMNS = (
    ("TechPrereq", "unlocked_by_technology", "technology"),
)
VICTORY_FIELDS = {
    **{
        column: (_snake_case(column), "boolean")
        for column in (
            "WinsGame",
            "TargetScore",
            "EndScore",
            "Conquest",
            "Influential",
            "DiploVote",
            "Permanent",
            "ReligionInAllCities",
            "FindAllNaturalWonders",
        )
    },
    **{
        column: (_snake_case(column), "integer")
        for column in (
            "PopulationPercentLead",
            "LandPercent",
            "MinLandPercent",
            "NumCultureCities",
            "TotalCultureRatio",
            "VictoryDelayTurns",
        )
    },
}
SPECIAL_UNIT_FIELDS = {
    "Valid": ("valid", "boolean"),
    "CityLoad": ("city_load", "boolean"),
}

PLAIN_REFERENCE_TABLES = (
    (
        "Belief_BuildingClassFaithPurchase", "BeliefType", "BuildingClassType",
        "allows_faith_purchase", "belief", "building_class",
    ),
    (
        "Belief_EraFaithUnitPurchase", "BeliefType", "EraType",
        "allows_faith_unit_purchase_from_era", "belief", "era",
    ),
    (
        "Building_ClassesNeededInCity", "BuildingType", "BuildingClassType",
        "requires_building_class_in_city", "building", "building_class",
    ),
    (
        "Building_LocalResourceAnds", "BuildingType", "ResourceType",
        "requires_all_local_resources", "building", "resource",
    ),
    (
        "Building_LocalResourceOrs", "BuildingType", "ResourceType",
        "requires_any_local_resource", "building", "resource",
    ),
    (
        "Policy_FreePromotions", "PolicyType", "PromotionType",
        "grants_free_promotion", "policy", "promotion",
    ),
    (
        "Resource_FeatureBooleans", "ResourceType", "FeatureType",
        "allowed_on_feature", "resource", "feature",
    ),
    (
        "Resource_FeatureTerrainBooleans", "ResourceType", "TerrainType",
        "allowed_on_feature_terrain", "resource", "terrain",
    ),
    (
        "Resource_TerrainBooleans", "ResourceType", "TerrainType",
        "allowed_on_terrain", "resource", "terrain",
    ),
    (
        "Trait_NoTrain", "TraitType", "UnitClassType",
        "cannot_train_unit_class", "trait", "unit_class",
    ),
    (
        "UnitPromotions_CivilianUnitType", "PromotionType", "UnitType",
        "applies_to_civilian_unit", "promotion", "unit",
    ),
    (
        "UnitPromotions_PostCombatRandomPromotion", "PromotionType",
        "NewPromotion", "may_gain_after_combat", "promotion", "promotion",
    ),
    (
        "Unit_BuildingClassRequireds", "UnitType", "BuildingClassType",
        "requires_building_class", "unit", "building_class",
    ),
    (
        "Unit_Builds", "UnitType", "BuildType", "can_perform_build", "unit",
        "build",
    ),
)

QUANTITY_REFERENCE_TABLES = (
    (
        "Terrain_Yields", "TerrainType", "YieldType", "yield",
        "terrain", "yield", "Yield", "amount",
    ),
    (
        "Terrain_HillsYieldChanges", "TerrainType", "YieldType",
        "hills_yield_change", "terrain", "yield", "Yield", "amount",
    ),
    (
        "Terrain_RiverYieldChanges", "TerrainType", "YieldType",
        "river_yield_change", "terrain", "yield", "Yield", "amount",
    ),
    (
        "Feature_YieldChanges", "FeatureType", "YieldType", "yield_change",
        "feature", "yield", "Yield", "amount",
    ),
    (
        "Feature_HillsYieldChanges", "FeatureType", "YieldType",
        "hills_yield_change", "feature", "yield", "Yield", "amount",
    ),
    (
        "Feature_RiverYieldChanges", "FeatureType", "YieldType",
        "river_yield_change", "feature", "yield", "Yield", "amount",
    ),
    (
        "Improvement_Yields", "ImprovementType", "YieldType", "yield_change",
        "improvement", "yield", "Yield", "amount",
    ),
    (
        "Improvement_FreshWaterYields", "ImprovementType", "YieldType",
        "fresh_water_yield_change", "improvement", "yield", "Yield", "amount",
    ),
    (
        "Improvement_HillsYields", "ImprovementType", "YieldType",
        "hills_yield_change", "improvement", "yield", "Yield", "amount",
    ),
    (
        "Improvement_RiverSideYields", "ImprovementType", "YieldType",
        "river_yield_change", "improvement", "yield", "Yield", "amount",
    ),
    (
        "Improvement_CoastalLandYields", "ImprovementType", "YieldType",
        "coastal_land_yield_change", "improvement", "yield", "Yield", "amount",
    ),
    (
        "Improvement_YieldPerEra", "ImprovementType", "YieldType",
        "yield_change_per_era", "improvement", "yield", "Yield", "amount",
    ),
    (
        "Route_Yields", "RouteType", "YieldType", "yield_change",
        "route", "yield", "Yield", "amount",
    ),
    (
        "Route_TechMovementChanges", "RouteType", "TechType",
        "movement_changed_by_technology", "route", "technology",
        "MovementChange", "movement_change",
    ),
    (
        "Build_TechTimeChanges", "BuildType", "TechType",
        "time_changed_by_technology", "build", "technology",
        "TimeChange", "time_change",
    ),
    (
        "Belief_CityYieldChanges", "BeliefType", "YieldType",
        "city_yield_change", "belief", "yield", "Yield", "amount",
    ),
    (
        "Belief_HolyCityYieldChanges", "BeliefType", "YieldType",
        "holy_city_yield_change", "belief", "yield", "Yield", "amount",
    ),
    (
        "Belief_MaxYieldModifierPerFollower", "BeliefType", "YieldType",
        "max_yield_modifier_per_follower", "belief", "yield", "Max",
        "max_percent",
    ),
    (
        "Belief_YieldChangeAnySpecialist", "BeliefType", "YieldType",
        "specialist_yield_change", "belief", "yield", "Yield", "amount",
    ),
    (
        "Belief_YieldChangeNaturalWonder", "BeliefType", "YieldType",
        "natural_wonder_yield_change", "belief", "yield", "Yield", "amount",
    ),
    (
        "Belief_YieldChangePerForeignCity", "BeliefType", "YieldType",
        "yield_change_per_foreign_city", "belief", "yield", "Yield", "amount",
    ),
    (
        "Belief_YieldChangePerXForeignFollowers", "BeliefType", "YieldType",
        "yield_change_per_foreign_followers", "belief", "yield",
        "ForeignFollowers", "followers_per_change",
    ),
    (
        "Belief_YieldChangeTradeRoute", "BeliefType", "YieldType",
        "trade_route_yield_change", "belief", "yield", "Yield", "amount",
    ),
    (
        "Belief_YieldChangeWorldWonder", "BeliefType", "YieldType",
        "world_wonder_yield_change", "belief", "yield", "Yield", "amount",
    ),
    (
        "Belief_YieldModifierNaturalWonder", "BeliefType", "YieldType",
        "natural_wonder_yield_modifier", "belief", "yield", "Yield", "percent",
    ),
    (
        "Building_AreaYieldModifiers", "BuildingType", "YieldType",
        "area_yield_modifier", "building", "yield", "Yield", "percent",
    ),
    (
        "Building_GlobalYieldModifiers", "BuildingType", "YieldType",
        "global_yield_modifier", "building", "yield", "Yield", "percent",
    ),
    (
        "Building_LakePlotYieldChanges", "BuildingType", "YieldType",
        "lake_plot_yield_change", "building", "yield", "Yield", "amount",
    ),
    (
        "Building_ResourceQuantity", "BuildingType", "ResourceType",
        "provides_resource", "building", "resource", "Quantity", "amount",
    ),
    (
        "Building_ResourceQuantityRequirements", "BuildingType", "ResourceType",
        "requires_resource", "building", "resource", "Cost", "amount",
    ),
    (
        "Building_RiverPlotYieldChanges", "BuildingType", "YieldType",
        "river_plot_yield_change", "building", "yield", "Yield", "amount",
    ),
    (
        "Building_SeaPlotYieldChanges", "BuildingType", "YieldType",
        "sea_plot_yield_change", "building", "yield", "Yield", "amount",
    ),
    (
        "Building_SeaResourceYieldChanges", "BuildingType", "YieldType",
        "sea_resource_yield_change", "building", "yield", "Yield", "amount",
    ),
    (
        "Building_YieldChanges", "BuildingType", "YieldType",
        "yield_change", "building", "yield", "Yield", "amount",
    ),
    (
        "Building_YieldChangesPerPop", "BuildingType", "YieldType",
        "yield_change_per_population", "building", "yield", "Yield",
        "hundredths_per_population",
    ),
    (
        "Building_YieldChangesPerReligion", "BuildingType", "YieldType",
        "yield_change_per_religion", "building", "yield", "Yield", "amount",
    ),
    (
        "Building_YieldModifiers", "BuildingType", "YieldType",
        "yield_modifier", "building", "yield", "Yield", "percent",
    ),
    (
        "Policy_CapitalYieldChanges", "PolicyType", "YieldType",
        "capital_yield_change", "policy", "yield", "Yield", "amount",
    ),
    (
        "Policy_CapitalYieldModifiers", "PolicyType", "YieldType",
        "capital_yield_modifier", "policy", "yield", "Yield", "percent",
    ),
    (
        "Policy_CapitalYieldPerPopChanges", "PolicyType", "YieldType",
        "capital_yield_change_per_population", "policy", "yield", "Yield",
        "hundredths_per_population",
    ),
    (
        "Policy_CityYieldChanges", "PolicyType", "YieldType",
        "city_yield_change", "policy", "yield", "Yield", "amount",
    ),
    (
        "Policy_CoastalCityYieldChanges", "PolicyType", "YieldType",
        "coastal_city_yield_change", "policy", "yield", "Yield", "amount",
    ),
    (
        "Policy_GreatWorkYieldChanges", "PolicyType", "YieldType",
        "great_work_yield_change", "policy", "yield", "Yield", "amount",
    ),
    (
        "Policy_SpecialistExtraYields", "PolicyType", "YieldType",
        "specialist_yield_change", "policy", "yield", "Yield", "amount",
    ),
    (
        "Policy_YieldModifiers", "PolicyType", "YieldType",
        "yield_modifier", "policy", "yield", "Yield", "percent",
    ),
    (
        "Resource_YieldChanges", "ResourceType", "YieldType",
        "yield_change", "resource", "yield", "Yield", "amount",
    ),
    (
        "SpecialistYields", "SpecialistType", "YieldType",
        "yield", "specialist", "yield", "Yield", "amount",
    ),
    (
        "Unit_ResourceQuantityRequirements", "UnitType", "ResourceType",
        "requires_resource", "unit", "resource", "Cost", "amount",
    ),
    (
        "Project_ResourceQuantityRequirements", "ProjectType", "ResourceType",
        "requires_resource", "project", "resource", "Quantity", "amount",
    ),
    (
        "Project_Prereqs", "ProjectType", "PrereqProjectType",
        "requires_project", "project", "project", "AmountNeeded", "amount",
    ),
    (
        "Process_ProductionYields", "ProcessType", "YieldType",
        "converts_production_to", "process", "yield", "Yield", "percent",
    ),
    (
        "Building_UnitCombatFreeExperiences", "BuildingType", "UnitCombatType",
        "grants_experience", "building", "unit_combat", "Experience", "amount",
    ),
    (
        "Building_UnitCombatProductionModifiers", "BuildingType", "UnitCombatType",
        "production_modifier", "building", "unit_combat", "Modifier", "percent",
    ),
    (
        "Policy_UnitCombatFreeExperiences", "PolicyType", "UnitCombatType",
        "grants_experience", "policy", "unit_combat", "FreeExperience", "amount",
    ),
    (
        "Policy_UnitCombatProductionModifiers", "PolicyType", "UnitCombatType",
        "production_modifier", "policy", "unit_combat", "ProductionModifier",
        "percent",
    ),
    (
        "Trait_MaintenanceModifierUnitCombats", "TraitType", "UnitCombatType",
        "maintenance_modifier", "trait", "unit_combat", "MaintenanceModifier",
        "percent",
    ),
    (
        "Trait_MovesChangeUnitCombats", "TraitType", "UnitCombatType",
        "movement_change", "trait", "unit_combat", "MovesChange", "amount",
    ),
    (
        "UnitPromotions_UnitCombatMods", "PromotionType", "UnitCombatType",
        "combat_modifier", "promotion", "unit_combat", "Modifier", "percent",
    ),
)

CONTEXTUAL_QUANTITY_REFERENCE_TABLES = (
    (
        "Belief_BuildingClassYieldChanges",
        "BeliefType",
        "YieldType",
        "yield_change",
        "belief",
        "yield",
        "BuildingClassType",
        "building_class",
        "for_building_class",
        "YieldChange",
        "amount",
    ),
    (
        "Belief_FeatureYieldChanges",
        "BeliefType",
        "YieldType",
        "yield_change",
        "belief",
        "yield",
        "FeatureType",
        "feature",
        "for_feature",
        "Yield",
        "amount",
    ),
    (
        "Belief_ImprovementYieldChanges",
        "BeliefType",
        "YieldType",
        "yield_change",
        "belief",
        "yield",
        "ImprovementType",
        "improvement",
        "for_improvement",
        "Yield",
        "amount",
    ),
    (
        "Belief_ResourceYieldChanges",
        "BeliefType",
        "YieldType",
        "yield_change",
        "belief",
        "yield",
        "ResourceType",
        "resource",
        "for_resource",
        "Yield",
        "amount",
    ),
    (
        "Belief_TerrainYieldChanges",
        "BeliefType",
        "YieldType",
        "yield_change",
        "belief",
        "yield",
        "TerrainType",
        "terrain",
        "for_terrain",
        "Yield",
        "amount",
    ),
    (
        "Building_BuildingClassYieldChanges",
        "BuildingType",
        "YieldType",
        "yield_change",
        "building",
        "yield",
        "BuildingClassType",
        "building_class",
        "for_building_class",
        "YieldChange",
        "amount",
    ),
    (
        "Building_FeatureYieldChanges",
        "BuildingType",
        "YieldType",
        "yield_change",
        "building",
        "yield",
        "FeatureType",
        "feature",
        "for_feature",
        "Yield",
        "amount",
    ),
    (
        "Building_ResourceYieldChanges",
        "BuildingType",
        "YieldType",
        "yield_change",
        "building",
        "yield",
        "ResourceType",
        "resource",
        "for_resource",
        "Yield",
        "amount",
    ),
    (
        "Building_ResourceYieldModifiers",
        "BuildingType",
        "YieldType",
        "yield_modifier",
        "building",
        "yield",
        "ResourceType",
        "resource",
        "for_resource",
        "Yield",
        "percent",
    ),
    (
        "Building_SpecialistYieldChanges",
        "BuildingType",
        "YieldType",
        "yield_change",
        "building",
        "yield",
        "SpecialistType",
        "specialist",
        "for_specialist",
        "Yield",
        "amount",
    ),
    (
        "Building_TerrainYieldChanges",
        "BuildingType",
        "YieldType",
        "yield_change",
        "building",
        "yield",
        "TerrainType",
        "terrain",
        "for_terrain",
        "Yield",
        "amount",
    ),
    (
        "Improvement_ResourceType_Yields",
        "ImprovementType",
        "YieldType",
        "yield_change",
        "improvement",
        "yield",
        "ResourceType",
        "resource",
        "with_resource",
        "Yield",
        "amount",
    ),
    (
        "Improvement_RouteYieldChanges",
        "ImprovementType",
        "YieldType",
        "yield_change",
        "improvement",
        "yield",
        "RouteType",
        "route",
        "with_route",
        "Yield",
        "amount",
    ),
    (
        "Improvement_TechFreshWaterYieldChanges",
        "ImprovementType",
        "YieldType",
        "fresh_water_yield_change",
        "improvement",
        "yield",
        "TechType",
        "technology",
        "enabled_by_technology",
        "Yield",
        "amount",
    ),
    (
        "Improvement_TechNoFreshWaterYieldChanges",
        "ImprovementType",
        "YieldType",
        "no_fresh_water_yield_change",
        "improvement",
        "yield",
        "TechType",
        "technology",
        "enabled_by_technology",
        "Yield",
        "amount",
    ),
    (
        "Improvement_TechYieldChanges",
        "ImprovementType",
        "YieldType",
        "yield_change",
        "improvement",
        "yield",
        "TechType",
        "technology",
        "enabled_by_technology",
        "Yield",
        "amount",
    ),
    (
        "Policy_BuildingClassYieldChanges",
        "PolicyType",
        "YieldType",
        "yield_change",
        "policy",
        "yield",
        "BuildingClassType",
        "building_class",
        "for_building_class",
        "YieldChange",
        "amount",
    ),
    (
        "Policy_BuildingClassYieldModifiers",
        "PolicyType",
        "YieldType",
        "yield_modifier",
        "policy",
        "yield",
        "BuildingClassType",
        "building_class",
        "for_building_class",
        "YieldMod",
        "percent",
    ),
    (
        "Policy_ImprovementYieldChanges",
        "PolicyType",
        "YieldType",
        "yield_change",
        "policy",
        "yield",
        "ImprovementType",
        "improvement",
        "for_improvement",
        "Yield",
        "amount",
    ),
)

CONTEXTUAL_REFERENCE_TABLES = (
    (
        "Policy_FreePromotionUnitCombats",
        "PolicyType",
        "PromotionType",
        "grants_free_promotion",
        "policy",
        "promotion",
        "UnitCombatType",
        "unit_combat",
        "for_unit_combat",
    ),
    (
        "Trait_FreePromotionUnitCombats",
        "TraitType",
        "PromotionType",
        "grants_free_promotion",
        "trait",
        "promotion",
        "UnitCombatType",
        "unit_combat",
        "for_unit_combat",
    ),
)

ATTRIBUTED_REFERENCE_TABLES = (
    (
        "UnitPromotions_Domains",
        "PromotionType",
        "DomainType",
        "domain_combat_modifier",
        "promotion",
        "domain",
        (("Modifier", "percent", "integer"),),
    ),
    (
        "UnitPromotions_Features",
        "PromotionType",
        "FeatureType",
        "feature_modifier",
        "promotion",
        "feature",
        (
            ("Attack", "attack_percent", "integer"),
            ("Defense", "defense_percent", "integer"),
            ("DoubleMove", "double_move", "boolean"),
            ("Impassable", "impassable", "boolean"),
        ),
    ),
    (
        "UnitPromotions_Terrains",
        "PromotionType",
        "TerrainType",
        "terrain_modifier",
        "promotion",
        "terrain",
        (
            ("Attack", "attack_percent", "integer"),
            ("Defense", "defense_percent", "integer"),
            ("DoubleMove", "double_move", "boolean"),
            ("Impassable", "impassable", "boolean"),
        ),
    ),
    (
        "UnitPromotions_UnitClasses",
        "PromotionType",
        "UnitClassType",
        "unit_class_modifier",
        "promotion",
        "unit_class",
        (
            ("Modifier", "percent", "optional_integer"),
            ("Attack", "attack_percent", "optional_integer"),
            ("Defense", "defense_percent", "optional_integer"),
        ),
    ),
)


class KnowledgeImportError(ValueError):
    pass


def import_ruleset(
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
                "DownloadableContent",
                {"PackageID", "IsActive"},
            )
            active_packages = _active_packages(connection)
            _validate_ruleset_family(ruleset.family, active_packages)
            if ruleset.dlc and ruleset.dlc != active_packages:
                raise KnowledgeImportError(
                    "declared DLC package IDs do not match active database content"
                )
            ruleset = Ruleset(
                ruleset.family,
                ruleset.game_version,
                active_packages,
                ruleset.mods,
            )
            _require_columns(
                connection,
                "Technologies",
                {"Type", "Era", *TECHNOLOGY_FIELDS},
            )
            _require_columns(connection, "Eras", {"Type", *ERA_FIELDS})
            _require_columns(
                connection, "Units", {"Type", "Class", "CombatClass", *UNIT_FIELDS}
            )
            _require_columns(
                connection,
                "UnitClasses",
                {"Type", "DefaultUnit", *UNIT_CLASS_FIELDS},
            )
            _require_columns(
                connection,
                "Unit_ClassUpgrades",
                {"UnitType", "UnitClassType"},
            )
            _require_columns(
                connection,
                "UnitPromotions",
                {
                    "Type",
                    "TechPrereq",
                    *PROMOTION_PREREQUISITE_COLUMNS,
                    *PROMOTION_FIELDS,
                },
            )
            _require_columns(
                connection,
                "Unit_FreePromotions",
                {"UnitType", "PromotionType"},
            )
            _require_columns(connection, "UnitCombatInfos", {"Type"})
            _require_columns(connection, "Domains", {"Type"})
            _require_columns(
                connection, "SpecialUnits", {"Type", *SPECIAL_UNIT_FIELDS}
            )
            _require_columns(
                connection,
                "UnitPromotions_UnitCombats",
                {"PromotionType", "UnitCombatType"},
            )
            _require_columns(
                connection,
                "Policies",
                {"Type", "PolicyBranchType", "TechPrereq", *POLICY_FIELDS},
            )
            _require_columns(
                connection,
                "PolicyBranchTypes",
                {
                    "Type",
                    "EraPrereq",
                    "FreePolicy",
                    "FreeFinishingPolicy",
                    *POLICY_BRANCH_FIELDS,
                },
            )
            for table, columns in (
                ("Policy_PrereqPolicies", {"PolicyType", "PrereqPolicy"}),
                ("Policy_PrereqORPolicies", {"PolicyType", "PrereqPolicy"}),
                ("Policy_Disables", {"PolicyType", "PolicyDisable"}),
                (
                    "PolicyBranch_Disables",
                    {"PolicyBranchType", "PolicyBranchDisable"},
                ),
            ):
                _require_columns(connection, table, columns)
            for (
                table,
                source_column,
                target_column,
                _kind,
                _source_kind,
                _target_kind,
            ) in PLAIN_REFERENCE_TABLES:
                _require_columns(
                    connection,
                    table,
                    {source_column, target_column},
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
                _require_columns(
                    connection,
                    table,
                    {source_column, target_column, value_column},
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
                _require_columns(
                    connection,
                    table,
                    {
                        source_column,
                        target_column,
                        context_column,
                        value_column,
                    },
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
                _require_columns(
                    connection,
                    table,
                    {source_column, target_column, context_column},
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
                _require_columns(
                    connection,
                    table,
                    {
                        source_column,
                        target_column,
                        *(column for column, _attribute, _value_type in fields),
                        *(
                            {"PassableTech"}
                            if table
                            in {
                                "UnitPromotions_Features",
                                "UnitPromotions_Terrains",
                            }
                            else set()
                        ),
                    },
                )
            _require_columns(
                connection,
                "Buildings",
                {
                    "Type",
                    "BuildingClass",
                    *(column for column, _, _ in BUILDING_REFERENCE_COLUMNS),
                    *BUILDING_FIELDS,
                },
            )
            _require_columns(
                connection,
                "BuildingClasses",
                {"Type", "DefaultBuilding", *BUILDING_CLASS_FIELDS},
            )
            _require_columns(
                connection,
                "Resources",
                {
                    "Type",
                    *(column for column, _, _ in RESOURCE_REFERENCE_COLUMNS),
                    *RESOURCE_FIELDS,
                },
            )
            _require_columns(
                connection,
                "ResourceClasses",
                {"Type", *RESOURCE_CLASS_FIELDS},
            )
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
            _require_columns(
                connection,
                "Civilizations",
                {"Type", *CIVILIZATION_FIELDS},
            )
            _require_columns(connection, "Leaders", {"Type"})
            _require_columns(
                connection,
                "Traits",
                {
                    "Type",
                    *(column for column, _, _ in TRAIT_REFERENCE_COLUMNS),
                    *TRAIT_FIELDS,
                },
            )
            _require_columns(
                connection,
                "Civilization_Leaders",
                {"CivilizationType", "LeaderheadType"},
            )
            _require_columns(
                connection,
                "Leader_Traits",
                {"LeaderType", "TraitType"},
            )
            _require_columns(
                connection,
                "Civilization_UnitClassOverrides",
                {"CivilizationType", "UnitClassType", "UnitType"},
            )
            _require_columns(
                connection,
                "Civilization_BuildingClassOverrides",
                {"CivilizationType", "BuildingClassType", "BuildingType"},
            )
            _require_columns(connection, "Religions", {"Type"})
            _require_columns(
                connection,
                "Beliefs",
                {
                    "Type",
                    *(column for column, _, _ in BELIEF_REFERENCE_COLUMNS),
                    *BELIEF_FIELDS,
                },
            )
            _require_columns(
                connection,
                "Specialists",
                {"Type", "GreatPeopleUnitClass", *SPECIALIST_FIELDS},
            )
            _require_columns(
                connection,
                "Civilization_Religions",
                {"CivilizationType", "ReligionType"},
            )
            _require_columns(
                connection,
                "Unit_GreatPersons",
                {"UnitType", "GreatPersonType"},
            )
            _require_columns(connection, "Terrains", {"Type", *TERRAIN_FIELDS})
            _require_columns(
                connection,
                "Features",
                {
                    "Type",
                    *(column for column, _, _ in FEATURE_REFERENCE_COLUMNS),
                    *FEATURE_FIELDS,
                },
            )
            _require_columns(
                connection,
                "FakeFeatures",
                {"Type", *FAKE_FEATURE_FIELDS},
            )
            _require_columns(
                connection,
                "Improvements",
                {
                    "Type",
                    *(column for column, _, _ in IMPROVEMENT_REFERENCE_COLUMNS),
                    *IMPROVEMENT_FIELDS,
                },
            )
            _require_columns(connection, "Routes", {"Type", *ROUTE_FIELDS})
            _require_columns(connection, "Yields", {"Type", *YIELD_FIELDS})
            _require_columns(
                connection,
                "Builds",
                {
                    "Type",
                    *(column for column, _, _ in BUILD_REFERENCE_COLUMNS),
                    *BUILD_FIELDS,
                },
            )
            _require_columns(
                connection,
                "Projects",
                {
                    "Type",
                    *(column for column, _, _ in PROJECT_REFERENCE_COLUMNS),
                    *PROJECT_FIELDS,
                },
            )
            _require_columns(
                connection,
                "Processes",
                {
                    "Type",
                    *(column for column, _, _ in PROCESS_REFERENCE_COLUMNS),
                },
            )
            _require_columns(connection, "Victories", {"Type", *VICTORY_FIELDS})
            _require_columns(
                connection,
                "Project_VictoryThresholds",
                {"ProjectType", "VictoryType", "Threshold", "MinThreshold"},
            )
            for table, columns in (
                (
                    "Feature_TerrainBooleans",
                    {"FeatureType", "TerrainType"},
                ),
                (
                    "Improvement_ValidTerrains",
                    {"ImprovementType", "TerrainType"},
                ),
                (
                    "Improvement_ValidFeatures",
                    {"ImprovementType", "FeatureType"},
                ),
                (
                    "Improvement_ValidImprovements",
                    {"ImprovementType", "PrereqImprovement"},
                ),
            ):
                _require_columns(connection, table, columns)
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
            unit_class_columns = ["Type", "DefaultUnit", *UNIT_CLASS_FIELDS]
            unit_class_select = ", ".join(
                f'"{column}"' for column in unit_class_columns
            )
            unit_class_rows = connection.execute(
                f'SELECT {unit_class_select} FROM "UnitClasses" ORDER BY "Type"'
            ).fetchall()
            if not unit_class_rows:
                raise KnowledgeImportError("UnitClasses table is empty")
            unit_class_entities = tuple(
                _scalar_entity("unit_class", row, UNIT_CLASS_FIELDS, source_label)
                for row in unit_class_rows
            )
            unit_combat_rows = _select_scalar_rows(connection, "UnitCombatInfos", {})
            unit_combat_entities = tuple(
                _scalar_entity("unit_combat", row, {}, source_label)
                for row in unit_combat_rows
            )
            domain_rows = _select_scalar_rows(connection, "Domains", {})
            domain_entities = tuple(
                _scalar_entity("domain", row, {}, source_label)
                for row in domain_rows
            )
            special_unit_rows = _select_scalar_rows(
                connection, "SpecialUnits", SPECIAL_UNIT_FIELDS
            )
            special_unit_entities = tuple(
                _scalar_entity("special_unit", row, SPECIAL_UNIT_FIELDS, source_label)
                for row in special_unit_rows
            )
            unit_columns = ["Type", "Class", *UNIT_FIELDS]
            unit_select = ", ".join(f'"{column}"' for column in unit_columns)
            unit_rows = connection.execute(
                f'SELECT {unit_select} FROM "Units" ORDER BY "Type"'
            ).fetchall()
            if not unit_rows:
                raise KnowledgeImportError("Units table is empty")
            unit_entities = tuple(
                _scalar_entity("unit", row, UNIT_FIELDS, source_label)
                for row in unit_rows
            )
            promotion_columns = [
                "Type",
                "TechPrereq",
                *PROMOTION_PREREQUISITE_COLUMNS,
                *PROMOTION_FIELDS,
            ]
            promotion_select = ", ".join(
                f'"{column}"' for column in promotion_columns
            )
            promotion_rows = connection.execute(
                f'SELECT {promotion_select} FROM "UnitPromotions" ORDER BY "Type"'
            ).fetchall()
            if not promotion_rows:
                raise KnowledgeImportError("UnitPromotions table is empty")
            promotion_entities = tuple(
                _scalar_entity("promotion", row, PROMOTION_FIELDS, source_label)
                for row in promotion_rows
            )
            policy_columns = ["Type", "PolicyBranchType", "TechPrereq", *POLICY_FIELDS]
            policy_select = ", ".join(f'"{column}"' for column in policy_columns)
            policy_rows = connection.execute(
                f'SELECT {policy_select} FROM "Policies" ORDER BY "Type"'
            ).fetchall()
            if not policy_rows:
                raise KnowledgeImportError("Policies table is empty")
            policy_entities = tuple(
                _scalar_entity("policy", row, POLICY_FIELDS, source_label)
                for row in policy_rows
            )
            branch_columns = [
                "Type",
                "EraPrereq",
                "FreePolicy",
                "FreeFinishingPolicy",
                *POLICY_BRANCH_FIELDS,
            ]
            branch_select = ", ".join(f'"{column}"' for column in branch_columns)
            branch_rows = connection.execute(
                f'SELECT {branch_select} FROM "PolicyBranchTypes" ORDER BY "Type"'
            ).fetchall()
            if not branch_rows:
                raise KnowledgeImportError("PolicyBranchTypes table is empty")
            branch_entities = tuple(
                _scalar_entity("policy_branch", row, POLICY_BRANCH_FIELDS, source_label)
                for row in branch_rows
            )
            building_columns = [
                "Type",
                "BuildingClass",
                *(column for column, _, _ in BUILDING_REFERENCE_COLUMNS),
                *BUILDING_FIELDS,
            ]
            building_select = ", ".join(
                f'"{column}"' for column in building_columns
            )
            building_rows = connection.execute(
                f'SELECT {building_select} FROM "Buildings" ORDER BY "Type"'
            ).fetchall()
            if not building_rows:
                raise KnowledgeImportError("Buildings table is empty")
            building_entities = tuple(
                _scalar_entity("building", row, BUILDING_FIELDS, source_label)
                for row in building_rows
            )
            building_class_columns = [
                "Type",
                "DefaultBuilding",
                *BUILDING_CLASS_FIELDS,
            ]
            building_class_select = ", ".join(
                f'"{column}"' for column in building_class_columns
            )
            building_class_rows = connection.execute(
                f'SELECT {building_class_select} FROM "BuildingClasses" ORDER BY "Type"'
            ).fetchall()
            if not building_class_rows:
                raise KnowledgeImportError("BuildingClasses table is empty")
            building_class_entities = tuple(
                _scalar_entity(
                    "building_class", row, BUILDING_CLASS_FIELDS, source_label
                )
                for row in building_class_rows
            )
            resource_columns = [
                "Type",
                *(column for column, _, _ in RESOURCE_REFERENCE_COLUMNS),
                *RESOURCE_FIELDS,
            ]
            resource_select = ", ".join(
                f'"{column}"' for column in resource_columns
            )
            resource_rows = connection.execute(
                f'SELECT {resource_select} FROM "Resources" ORDER BY "Type"'
            ).fetchall()
            if not resource_rows:
                raise KnowledgeImportError("Resources table is empty")
            resource_entities = tuple(
                _scalar_entity("resource", row, RESOURCE_FIELDS, source_label)
                for row in resource_rows
            )
            resource_class_columns = ["Type", *RESOURCE_CLASS_FIELDS]
            resource_class_select = ", ".join(
                f'"{column}"' for column in resource_class_columns
            )
            resource_class_rows = connection.execute(
                f'SELECT {resource_class_select} FROM "ResourceClasses" ORDER BY "Type"'
            ).fetchall()
            if not resource_class_rows:
                raise KnowledgeImportError("ResourceClasses table is empty")
            resource_class_entities = tuple(
                _scalar_entity(
                    "resource_class", row, RESOURCE_CLASS_FIELDS, source_label
                )
                for row in resource_class_rows
            )
            civilization_columns = ["Type", *CIVILIZATION_FIELDS]
            civilization_select = ", ".join(
                f'"{column}"' for column in civilization_columns
            )
            civilization_rows = connection.execute(
                f'SELECT {civilization_select} FROM "Civilizations" ORDER BY "Type"'
            ).fetchall()
            if not civilization_rows:
                raise KnowledgeImportError("Civilizations table is empty")
            civilization_entities = tuple(
                _scalar_entity(
                    "civilization", row, CIVILIZATION_FIELDS, source_label
                )
                for row in civilization_rows
            )
            leader_rows = connection.execute(
                'SELECT "Type" FROM "Leaders" ORDER BY "Type"'
            ).fetchall()
            if not leader_rows:
                raise KnowledgeImportError("Leaders table is empty")
            # Leaders are stable identifiers here. All descriptive, art, flavor,
            # and personality columns are deliberately outside the allowlist.
            leader_entities = tuple(
                _scalar_entity("leader", row, {}, source_label)
                for row in leader_rows
            )
            trait_columns = [
                "Type",
                *(column for column, _, _ in TRAIT_REFERENCE_COLUMNS),
                *TRAIT_FIELDS,
            ]
            trait_select = ", ".join(f'"{column}"' for column in trait_columns)
            trait_rows = connection.execute(
                f'SELECT {trait_select} FROM "Traits" ORDER BY "Type"'
            ).fetchall()
            if not trait_rows:
                raise KnowledgeImportError("Traits table is empty")
            trait_entities = tuple(
                _scalar_entity("trait", row, TRAIT_FIELDS, source_label)
                for row in trait_rows
            )
            religion_rows = connection.execute(
                'SELECT "Type" FROM "Religions" ORDER BY "Type"'
            ).fetchall()
            if not religion_rows:
                raise KnowledgeImportError("Religions table is empty")
            religion_entities = tuple(
                _scalar_entity("religion", row, {}, source_label)
                for row in religion_rows
            )
            belief_columns = [
                "Type",
                *(column for column, _, _ in BELIEF_REFERENCE_COLUMNS),
                *BELIEF_FIELDS,
            ]
            belief_select = ", ".join(f'"{column}"' for column in belief_columns)
            belief_rows = connection.execute(
                f'SELECT {belief_select} FROM "Beliefs" ORDER BY "Type"'
            ).fetchall()
            if not belief_rows:
                raise KnowledgeImportError("Beliefs table is empty")
            belief_entities = tuple(
                _scalar_entity("belief", row, BELIEF_FIELDS, source_label)
                for row in belief_rows
            )
            specialist_columns = [
                "Type",
                "GreatPeopleUnitClass",
                *SPECIALIST_FIELDS,
            ]
            specialist_select = ", ".join(
                f'"{column}"' for column in specialist_columns
            )
            specialist_rows = connection.execute(
                f'SELECT {specialist_select} FROM "Specialists" ORDER BY "Type"'
            ).fetchall()
            if not specialist_rows:
                raise KnowledgeImportError("Specialists table is empty")
            specialist_entities = tuple(
                _scalar_entity("specialist", row, SPECIALIST_FIELDS, source_label)
                for row in specialist_rows
            )
            terrain_rows = _select_scalar_rows(
                connection, "Terrains", TERRAIN_FIELDS
            )
            terrain_entities = tuple(
                _scalar_entity("terrain", row, TERRAIN_FIELDS, source_label)
                for row in terrain_rows
            )
            feature_rows = _select_scalar_rows(
                connection,
                "Features",
                FEATURE_FIELDS,
                tuple(column for column, _, _ in FEATURE_REFERENCE_COLUMNS),
            )
            feature_entities = tuple(
                _scalar_entity("feature", row, FEATURE_FIELDS, source_label)
                for row in feature_rows
            )
            fake_feature_rows = _select_scalar_rows(
                connection,
                "FakeFeatures",
                FAKE_FEATURE_FIELDS,
            )
            fake_feature_entities = tuple(
                _fake_feature_entity(row, source_label)
                for row in fake_feature_rows
            )
            improvement_rows = _select_scalar_rows(
                connection,
                "Improvements",
                IMPROVEMENT_FIELDS,
                tuple(column for column, _, _ in IMPROVEMENT_REFERENCE_COLUMNS),
            )
            improvement_entities = tuple(
                _scalar_entity(
                    "improvement", row, IMPROVEMENT_FIELDS, source_label
                )
                for row in improvement_rows
            )
            route_rows = _select_scalar_rows(connection, "Routes", ROUTE_FIELDS)
            route_entities = tuple(
                _scalar_entity("route", row, ROUTE_FIELDS, source_label)
                for row in route_rows
            )
            yield_rows = _select_scalar_rows(connection, "Yields", YIELD_FIELDS)
            yield_entities = tuple(
                _scalar_entity("yield", row, YIELD_FIELDS, source_label)
                for row in yield_rows
            )
            build_rows = _select_scalar_rows(
                connection,
                "Builds",
                BUILD_FIELDS,
                tuple(column for column, _, _ in BUILD_REFERENCE_COLUMNS),
            )
            build_entities = tuple(
                _scalar_entity("build", row, BUILD_FIELDS, source_label)
                for row in build_rows
            )
            project_rows = _select_scalar_rows(
                connection,
                "Projects",
                PROJECT_FIELDS,
                tuple(column for column, _, _ in PROJECT_REFERENCE_COLUMNS),
            )
            project_entities = tuple(
                _scalar_entity("project", row, PROJECT_FIELDS, source_label)
                for row in project_rows
            )
            process_rows = _select_scalar_rows(
                connection,
                "Processes",
                {},
                tuple(column for column, _, _ in PROCESS_REFERENCE_COLUMNS),
            )
            process_entities = tuple(
                _scalar_entity("process", row, {}, source_label)
                for row in process_rows
            )
            victory_rows = _select_scalar_rows(
                connection, "Victories", VICTORY_FIELDS
            )
            victory_entities = tuple(
                _scalar_entity("victory", row, VICTORY_FIELDS, source_label)
                for row in victory_rows
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
                + _promotion_references(promotion_rows, source_label)
                + _free_promotion_references(connection, source_label)
                + _unit_class_references(
                    connection, unit_rows, unit_class_rows, source_label
                )
                + _unit_combat_references(connection, unit_rows, source_label)
                + _policy_references(
                    connection, policy_rows, branch_rows, source_label
                )
                + _building_references(
                    building_rows, building_class_rows, source_label
                )
                + _resource_references(resource_rows, source_label)
                + _civilization_references(
                    connection,
                    unit_rows,
                    building_rows,
                    source_label,
                )
                + _trait_references(trait_rows, source_label)
                + _religion_references(
                    connection, belief_rows, specialist_rows, source_label
                )
                + _map_references(
                    connection,
                    feature_rows,
                    improvement_rows,
                    build_rows,
                    source_label,
                )
                + _project_references(
                    connection, project_rows, process_rows, source_label
                )
                + _plain_references(connection, source_label)
                + _quantity_references(connection, source_label)
                + _contextual_quantity_references(connection, source_label)
                + _contextual_references(connection, source_label)
                + _attributed_references(connection, source_label)
                + _promotion_passable_references(connection, source_label)
            )
    except sqlite3.DatabaseError as error:
        raise KnowledgeImportError(f"cannot read Civ V database: {error}") from error

    digest_after = _sha256(database_path)
    if digest_after != digest_before or database_path.stat().st_size != size_before:
        raise KnowledgeImportError("database changed during import; close Civ V and retry")
    return validate_bundle(
        KnowledgeBundle(
            schema_version=3,
            ruleset=ruleset,
            sources=(source,),
            entities=(
                era_entities
                + technology_entities
                + unit_entities
                + unit_class_entities
                + unit_combat_entities
                + domain_entities
                + special_unit_entities
                + promotion_entities
                + policy_entities
                + branch_entities
                + building_entities
                + building_class_entities
                + resource_entities
                + resource_class_entities
                + civilization_entities
                + leader_entities
                + trait_entities
                + religion_entities
                + belief_entities
                + specialist_entities
                + terrain_entities
                + feature_entities
                + fake_feature_entities
                + improvement_entities
                + route_entities
                + yield_entities
                + build_entities
                + project_entities
                + process_entities
                + victory_entities
            ),
            references=references,
        )
    )


def import_technologies(
    database_path: Path,
    source_label: str,
    ruleset: Ruleset,
) -> KnowledgeBundle:
    """Backward-compatible name for the ruleset importer."""
    return import_ruleset(database_path, source_label, ruleset)


def _select_scalar_rows(
    connection: sqlite3.Connection,
    table: str,
    fields: dict[str, tuple[str, str]],
    extra_columns: tuple[str, ...] = (),
) -> list[sqlite3.Row]:
    columns = ["Type", *extra_columns, *fields]
    select = ", ".join(f'"{column}"' for column in columns)
    rows = connection.execute(
        f'SELECT {select} FROM "{table}" ORDER BY "Type"'
    ).fetchall()
    if not rows:
        raise KnowledgeImportError(f"{table} table is empty")
    return rows


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
        elif value_type in {"integer", "optional_integer"}:
            if value_type == "optional_integer" and value is None:
                attributes[attribute] = value
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                raise KnowledgeImportError(
                    f"{kind} {row['Type']} has invalid integer {column}: {value}"
                )
        elif value_type == "number":
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise KnowledgeImportError(
                    f"{kind} {row['Type']} has invalid number {column}: {value}"
                )
        elif value is not None and not isinstance(value, str):
            raise KnowledgeImportError(
                f"{kind} {row['Type']} has invalid identifier {column}: {value}"
            )
        attributes[attribute] = value
    return Entity(kind, row["Type"], attributes, (source_label,))


def _fake_feature_entity(row: sqlite3.Row, source_label: str) -> Entity:
    entity = _scalar_entity("feature", row, FAKE_FEATURE_FIELDS, source_label)
    return Entity(
        entity.kind,
        entity.type_id,
        {**entity.attributes, "fake": True},
        entity.source_paths,
    )


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


def _promotion_references(
    rows: list[sqlite3.Row], source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for row in rows:
        if row["TechPrereq"] is not None:
            references.append(
                Reference(
                    "unlocked_by_technology",
                    "promotion",
                    row["Type"],
                    "technology",
                    row["TechPrereq"],
                    (source_label,),
                )
            )
        for column in PROMOTION_PREREQUISITE_COLUMNS:
            prerequisite = row[column]
            if prerequisite is None:
                continue
            references.append(
                Reference(
                    "requires_all" if column == "PromotionPrereq" else "requires_any",
                    "promotion",
                    row["Type"],
                    "promotion",
                    prerequisite,
                    (source_label,),
                )
            )
    return references


def _free_promotion_references(
    connection: sqlite3.Connection, source_label: str
) -> list[Reference]:
    rows = connection.execute(
        'SELECT "UnitType", "PromotionType" FROM "Unit_FreePromotions" '
        'ORDER BY "UnitType", "PromotionType"'
    ).fetchall()
    return [
        Reference(
            "starts_with_promotion",
            "unit",
            row["UnitType"],
            "promotion",
            row["PromotionType"],
            (source_label,),
        )
        for row in rows
    ]


def _unit_combat_references(
    connection: sqlite3.Connection,
    unit_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references = [
        Reference(
            "belongs_to_unit_combat",
            "unit",
            row["Type"],
            "unit_combat",
            row["CombatClass"],
            (source_label,),
        )
        for row in unit_rows
        if row["CombatClass"] not in (None, "NONE")
    ]
    for row in unit_rows:
        for column, kind, target_kind in (
            ("Domain", "belongs_to_domain", "domain"),
            ("Special", "belongs_to_special_unit", "special_unit"),
            *UNIT_REFERENCE_COLUMNS,
        ):
            target = row[column]
            if target in (None, "NONE"):
                continue
            references.append(
                Reference(
                    kind,
                    "unit",
                    row["Type"],
                    target_kind,
                    target,
                    (source_label,),
                )
            )
    references.extend(
        _two_column_references(
            connection,
            "UnitPromotions_UnitCombats",
            "PromotionType",
            "UnitCombatType",
            "valid_for_unit_combat",
            "promotion",
            "unit_combat",
            source_label,
        )
    )
    return references


def _unit_class_references(
    connection: sqlite3.Connection,
    unit_rows: list[sqlite3.Row],
    unit_class_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references = [
        Reference(
            "belongs_to_unit_class",
            "unit",
            row["Type"],
            "unit_class",
            row["Class"],
            (source_label,),
        )
        for row in unit_rows
        if row["Class"] not in (None, "NONE")
    ]
    references.extend(
        Reference(
            "default_unit",
            "unit_class",
            row["Type"],
            "unit",
            row["DefaultUnit"],
            (source_label,),
        )
        for row in unit_class_rows
        if row["DefaultUnit"] not in (None, "NONE")
    )
    upgrade_rows = connection.execute(
        'SELECT DISTINCT "UnitType", "UnitClassType" FROM "Unit_ClassUpgrades" '
        'ORDER BY "UnitType", "UnitClassType"'
    ).fetchall()
    references.extend(
        Reference(
            "upgrades_to_unit_class",
            "unit",
            row["UnitType"],
            "unit_class",
            row["UnitClassType"],
            (source_label,),
        )
        for row in upgrade_rows
    )
    return references


def _policy_references(
    connection: sqlite3.Connection,
    policy_rows: list[sqlite3.Row],
    branch_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references: list[Reference] = []
    for row in policy_rows:
        if row["PolicyBranchType"] not in (None, "NONE"):
            references.append(
                Reference(
                    "belongs_to_policy_branch",
                    "policy",
                    row["Type"],
                    "policy_branch",
                    row["PolicyBranchType"],
                    (source_label,),
                )
            )
        if row["TechPrereq"] not in (None, "NONE"):
            references.append(
                Reference(
                    "unlocked_by_technology",
                    "policy",
                    row["Type"],
                    "technology",
                    row["TechPrereq"],
                    (source_label,),
                )
            )
    for row in branch_rows:
        for column, kind, target_kind in (
            ("EraPrereq", "unlocked_by_era", "era"),
            ("FreePolicy", "opening_policy", "policy"),
            ("FreeFinishingPolicy", "finishing_policy", "policy"),
        ):
            target = row[column]
            if target in (None, "NONE"):
                continue
            references.append(
                Reference(
                    kind,
                    "policy_branch",
                    row["Type"],
                    target_kind,
                    target,
                    (source_label,),
                )
            )
    references.extend(
        _two_column_references(
            connection,
            "Policy_PrereqPolicies",
            "PolicyType",
            "PrereqPolicy",
            "requires_all",
            "policy",
            "policy",
            source_label,
        )
    )
    references.extend(
        _two_column_references(
            connection,
            "Policy_PrereqORPolicies",
            "PolicyType",
            "PrereqPolicy",
            "requires_any",
            "policy",
            "policy",
            source_label,
        )
    )
    references.extend(
        _two_column_references(
            connection,
            "Policy_Disables",
            "PolicyType",
            "PolicyDisable",
            "disables",
            "policy",
            "policy",
            source_label,
        )
    )
    references.extend(
        _two_column_references(
            connection,
            "PolicyBranch_Disables",
            "PolicyBranchType",
            "PolicyBranchDisable",
            "disables",
            "policy_branch",
            "policy_branch",
            source_label,
        )
    )
    return references


def _two_column_references(
    connection: sqlite3.Connection,
    table: str,
    source_column: str,
    target_column: str,
    kind: str,
    source_kind: str,
    target_kind: str,
    source_label: str,
) -> list[Reference]:
    rows = connection.execute(
        f'SELECT DISTINCT "{source_column}", "{target_column}" FROM "{table}" '
        f'ORDER BY "{source_column}", "{target_column}"'
    ).fetchall()
    return [
        Reference(
            kind,
            source_kind,
            row[source_column],
            target_kind,
            row[target_column],
            (source_label,),
        )
        for row in rows
    ]


def _building_references(
    building_rows: list[sqlite3.Row],
    building_class_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references: list[Reference] = []
    for row in building_rows:
        if row["BuildingClass"] not in (None, "NONE"):
            references.append(
                Reference(
                    "belongs_to_building_class",
                    "building",
                    row["Type"],
                    "building_class",
                    row["BuildingClass"],
                    (source_label,),
                )
            )
        for column, kind, target_kind in BUILDING_REFERENCE_COLUMNS:
            target = row[column]
            if target in (None, "NONE"):
                continue
            references.append(
                Reference(
                    kind,
                    "building",
                    row["Type"],
                    target_kind,
                    target,
                    (source_label,),
                )
            )
    references.extend(
        Reference(
            "default_building",
            "building_class",
            row["Type"],
            "building",
            row["DefaultBuilding"],
            (source_label,),
        )
        for row in building_class_rows
        if row["DefaultBuilding"] not in (None, "NONE")
    )
    return references


def _resource_references(
    resource_rows: list[sqlite3.Row], source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for row in resource_rows:
        for column, kind, target_kind in RESOURCE_REFERENCE_COLUMNS:
            target = row[column]
            if target in (None, "NONE"):
                continue
            references.append(
                Reference(
                    kind,
                    "resource",
                    row["Type"],
                    target_kind,
                    target,
                    (source_label,),
                )
            )
    return references


def _trait_references(
    trait_rows: list[sqlite3.Row], source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for row in trait_rows:
        for column, kind, target_kind in TRAIT_REFERENCE_COLUMNS:
            target = row[column]
            if target in (None, "NONE"):
                continue
            references.append(
                Reference(
                    kind,
                    "trait",
                    row["Type"],
                    target_kind,
                    target,
                    (source_label,),
                )
            )
    return references


def _religion_references(
    connection: sqlite3.Connection,
    belief_rows: list[sqlite3.Row],
    specialist_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references: list[Reference] = []
    for row in belief_rows:
        for column, kind, target_kind in BELIEF_REFERENCE_COLUMNS:
            target = row[column]
            if target in (None, "NONE"):
                continue
            references.append(
                Reference(
                    kind,
                    "belief",
                    row["Type"],
                    target_kind,
                    target,
                    (source_label,),
                )
            )
    for row in specialist_rows:
        target = row["GreatPeopleUnitClass"]
        if target in (None, "NONE"):
            continue
        references.append(
            Reference(
                "generates_great_person_unit_class",
                "specialist",
                row["Type"],
                "unit_class",
                target,
                (source_label,),
            )
        )
    references.extend(
        _two_column_references(
            connection,
            "Civilization_Religions",
            "CivilizationType",
            "ReligionType",
            "preferred_religion",
            "civilization",
            "religion",
            source_label,
        )
    )
    references.extend(
        _two_column_references(
            connection,
            "Unit_GreatPersons",
            "UnitType",
            "GreatPersonType",
            "great_person_for_specialist",
            "unit",
            "specialist",
            source_label,
        )
    )
    return references


def _map_references(
    connection: sqlite3.Connection,
    feature_rows: list[sqlite3.Row],
    improvement_rows: list[sqlite3.Row],
    build_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references: list[Reference] = []
    for source_kind, rows, columns in (
        ("feature", feature_rows, FEATURE_REFERENCE_COLUMNS),
        ("improvement", improvement_rows, IMPROVEMENT_REFERENCE_COLUMNS),
        ("build", build_rows, BUILD_REFERENCE_COLUMNS),
    ):
        for row in rows:
            for column, kind, target_kind in columns:
                target = row[column]
                if target in (None, "NONE"):
                    continue
                references.append(
                    Reference(
                        kind,
                        source_kind,
                        row["Type"],
                        target_kind,
                        target,
                        (source_label,),
                    )
                )
    for arguments in (
        (
            "Feature_TerrainBooleans",
            "FeatureType",
            "TerrainType",
            "valid_on_terrain",
            "feature",
            "terrain",
        ),
        (
            "Improvement_ValidTerrains",
            "ImprovementType",
            "TerrainType",
            "valid_on_terrain",
            "improvement",
            "terrain",
        ),
        (
            "Improvement_ValidFeatures",
            "ImprovementType",
            "FeatureType",
            "valid_on_feature",
            "improvement",
            "feature",
        ),
        (
            "Improvement_ValidImprovements",
            "ImprovementType",
            "PrereqImprovement",
            "valid_on_improvement",
            "improvement",
            "improvement",
        ),
    ):
        references.extend(
            _two_column_references(connection, *arguments, source_label)
        )
    return references


def _project_references(
    connection: sqlite3.Connection,
    project_rows: list[sqlite3.Row],
    process_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references: list[Reference] = []
    for source_kind, rows, columns in (
        ("project", project_rows, PROJECT_REFERENCE_COLUMNS),
        ("process", process_rows, PROCESS_REFERENCE_COLUMNS),
    ):
        for row in rows:
            for column, kind, target_kind in columns:
                target = row[column]
                if target in (None, "NONE"):
                    continue
                references.append(
                    Reference(
                        kind,
                        source_kind,
                        row["Type"],
                        target_kind,
                        target,
                        (source_label,),
                    )
                )

    rows = connection.execute(
        'SELECT "ProjectType", "VictoryType", "Threshold", "MinThreshold" '
        'FROM "Project_VictoryThresholds" '
        'ORDER BY "ProjectType", "VictoryType", "Threshold", "MinThreshold"'
    ).fetchall()
    for row in rows:
        threshold = row["Threshold"]
        minimum = row["MinThreshold"]
        for column, value in (("Threshold", threshold), ("MinThreshold", minimum)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise KnowledgeImportError(
                    f"Project_VictoryThresholds has invalid integer {column}: {value}"
                )
        references.append(
            Reference(
                "victory_threshold",
                "project",
                row["ProjectType"],
                "victory",
                row["VictoryType"],
                (source_label,),
                {"threshold": threshold, "minimum_threshold": minimum},
            )
        )
    return references


def _plain_references(
    connection: sqlite3.Connection, source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for (
        table,
        source_column,
        target_column,
        kind,
        source_kind,
        target_kind,
    ) in PLAIN_REFERENCE_TABLES:
        references.extend(
            _two_column_references(
                connection,
                table,
                source_column,
                target_column,
                kind,
                source_kind,
                target_kind,
                source_label,
            )
        )
    return references


def _quantity_references(
    connection: sqlite3.Connection, source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for (
        table,
        source_column,
        target_column,
        kind,
        source_kind,
        target_kind,
        value_column,
        attribute,
    ) in QUANTITY_REFERENCE_TABLES:
        rows = connection.execute(
            f'SELECT "{source_column}", "{target_column}", "{value_column}" '
            f'FROM "{table}" ORDER BY "{source_column}", "{target_column}", '
            f'"{value_column}"'
        ).fetchall()
        for row in rows:
            value = row[value_column]
            if not isinstance(value, int) or isinstance(value, bool):
                raise KnowledgeImportError(
                    f"{table} has invalid integer {value_column}: {value}"
                )
            references.append(
                Reference(
                    kind,
                    source_kind,
                    row[source_column],
                    target_kind,
                    row[target_column],
                    (source_label,),
                    {attribute: value},
                )
            )
    return references


def _contextual_quantity_references(
    connection: sqlite3.Connection, source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for (
        table,
        source_column,
        target_column,
        kind,
        source_kind,
        target_kind,
        context_column,
        context_kind,
        context_role,
        value_column,
        attribute,
    ) in CONTEXTUAL_QUANTITY_REFERENCE_TABLES:
        rows = connection.execute(
            f'SELECT "{source_column}", "{target_column}", '
            f'"{context_column}", "{value_column}" FROM "{table}" '
            f'ORDER BY "{source_column}", "{target_column}", '
            f'"{context_column}", "{value_column}"'
        ).fetchall()
        for row in rows:
            value = row[value_column]
            if not isinstance(value, int) or isinstance(value, bool):
                raise KnowledgeImportError(
                    f"{table} has invalid integer {value_column}: {value}"
                )
            references.append(
                Reference(
                    kind,
                    source_kind,
                    row[source_column],
                    target_kind,
                    row[target_column],
                    (source_label,),
                    {attribute: value},
                    (
                        ReferenceContext(
                            context_role,
                            context_kind,
                            row[context_column],
                        ),
                    ),
                )
            )
    return references


def _contextual_references(
    connection: sqlite3.Connection, source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for (
        table,
        source_column,
        target_column,
        kind,
        source_kind,
        target_kind,
        context_column,
        context_kind,
        context_role,
    ) in CONTEXTUAL_REFERENCE_TABLES:
        rows = connection.execute(
            f'SELECT "{source_column}", "{target_column}", "{context_column}" '
            f'FROM "{table}" ORDER BY "{source_column}", "{target_column}", '
            f'"{context_column}"'
        ).fetchall()
        references.extend(
            Reference(
                kind,
                source_kind,
                row[source_column],
                target_kind,
                row[target_column],
                (source_label,),
                {},
                (
                    ReferenceContext(
                        context_role,
                        context_kind,
                        row[context_column],
                    ),
                ),
            )
            for row in rows
        )
    return references


def _attributed_references(
    connection: sqlite3.Connection, source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for (
        table,
        source_column,
        target_column,
        kind,
        source_kind,
        target_kind,
        fields,
    ) in ATTRIBUTED_REFERENCE_TABLES:
        value_columns = tuple(column for column, _attribute, _value_type in fields)
        select_columns = (source_column, target_column, *value_columns)
        select = ", ".join(f'"{column}"' for column in select_columns)
        order = ", ".join(f'"{column}"' for column in select_columns)
        rows = connection.execute(
            f'SELECT {select} FROM "{table}" ORDER BY {order}'
        ).fetchall()
        for row in rows:
            attributes: dict[str, int | bool] = {}
            for column, attribute, value_type in fields:
                value = row[column]
                if value_type == "optional_integer" and value is None:
                    continue
                if value_type in {"integer", "optional_integer"}:
                    if not isinstance(value, int) or isinstance(value, bool):
                        raise KnowledgeImportError(
                            f"{table} has invalid integer {column}: {value}"
                        )
                    attributes[attribute] = value
                elif value_type == "boolean":
                    if not isinstance(value, int) or value not in (0, 1):
                        raise KnowledgeImportError(
                            f"{table} has invalid boolean {column}: {value}"
                        )
                    attributes[attribute] = bool(value)
                else:
                    raise AssertionError(
                        f"unsupported attributed reference type: {value_type}"
                    )
            references.append(
                Reference(
                    kind,
                    source_kind,
                    row[source_column],
                    target_kind,
                    row[target_column],
                    (source_label,),
                    attributes,
                )
            )
    return references


def _promotion_passable_references(
    connection: sqlite3.Connection, source_label: str
) -> list[Reference]:
    references: list[Reference] = []
    for table, target_column, target_kind in (
        ("UnitPromotions_Features", "FeatureType", "feature"),
        ("UnitPromotions_Terrains", "TerrainType", "terrain"),
    ):
        rows = connection.execute(
            f'SELECT "PromotionType", "{target_column}", "PassableTech" '
            f'FROM "{table}" WHERE "PassableTech" IS NOT NULL '
            'AND "PassableTech" <> \'NONE\' '
            f'ORDER BY "PromotionType", "{target_column}", "PassableTech"'
        ).fetchall()
        references.extend(
            Reference(
                "passable_with_technology",
                "promotion",
                row["PromotionType"],
                target_kind,
                row[target_column],
                (source_label,),
                {},
                (
                    ReferenceContext(
                        "enabled_by_technology",
                        "technology",
                        row["PassableTech"],
                    ),
                ),
            )
            for row in rows
        )
    return references


def _civilization_references(
    connection: sqlite3.Connection,
    unit_rows: list[sqlite3.Row],
    building_rows: list[sqlite3.Row],
    source_label: str,
) -> list[Reference]:
    references = _two_column_references(
        connection,
        "Civilization_Leaders",
        "CivilizationType",
        "LeaderheadType",
        "led_by",
        "civilization",
        "leader",
        source_label,
    )
    references.extend(
        _two_column_references(
            connection,
            "Leader_Traits",
            "LeaderType",
            "TraitType",
            "has_trait",
            "leader",
            "trait",
            source_label,
        )
    )
    references.extend(
        _civilization_override_references(
            connection,
            table="Civilization_UnitClassOverrides",
            slot_column="UnitClassType",
            target_column="UnitType",
            target_kind="unit",
            slot_kind="unit_class",
            target_slots={row["Type"]: row["Class"] for row in unit_rows},
            unique_kind="unique_unit",
            disabled_kind="disables_unit_class",
            source_label=source_label,
        )
    )
    references.extend(
        _civilization_override_references(
            connection,
            table="Civilization_BuildingClassOverrides",
            slot_column="BuildingClassType",
            target_column="BuildingType",
            target_kind="building",
            slot_kind="building_class",
            target_slots={row["Type"]: row["BuildingClass"] for row in building_rows},
            unique_kind="unique_building",
            disabled_kind="disables_building_class",
            source_label=source_label,
        )
    )
    return references


def _civilization_override_references(
    connection: sqlite3.Connection,
    *,
    table: str,
    slot_column: str,
    target_column: str,
    target_kind: str,
    slot_kind: str,
    target_slots: dict[str, str | None],
    unique_kind: str,
    disabled_kind: str,
    source_label: str,
) -> list[Reference]:
    rows = connection.execute(
        f'SELECT "CivilizationType", "{slot_column}", "{target_column}" '
        f'FROM "{table}" ORDER BY "CivilizationType", "{slot_column}", '
        f'"{target_column}"'
    ).fetchall()
    slots: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        key = (row["CivilizationType"], row[slot_column])
        targets = slots.setdefault(key, set())
        target = row[target_column]
        if target not in (None, "NONE"):
            targets.add(target)

    references: list[Reference] = []
    for (civilization, slot), targets in sorted(slots.items()):
        if len(targets) > 1:
            raise KnowledgeImportError(
                f"{table} has multiple replacements for {civilization}/{slot}: "
                + ", ".join(sorted(targets))
            )
        if targets:
            target = next(iter(targets))
            declared_slot = target_slots.get(target)
            if declared_slot is None:
                raise KnowledgeImportError(
                    f"{table} references unknown {target_kind}: {target}"
                )
            if declared_slot != slot:
                raise KnowledgeImportError(
                    f"{table} replacement {target} belongs to {declared_slot}, "
                    f"not {slot}"
                )
            references.append(
                Reference(
                    unique_kind,
                    "civilization",
                    civilization,
                    target_kind,
                    target,
                    (source_label,),
                )
            )
        else:
            references.append(
                Reference(
                    disabled_kind,
                    "civilization",
                    civilization,
                    slot_kind,
                    slot,
                    (source_label,),
                )
            )
    return references


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


def _active_packages(connection: sqlite3.Connection) -> tuple[str, ...]:
    rows = connection.execute(
        'SELECT "PackageID", "IsActive" FROM "DownloadableContent" '
        'ORDER BY "PackageID"'
    ).fetchall()
    active: list[str] = []
    for row in rows:
        if row["IsActive"] not in (0, 1):
            raise KnowledgeImportError(
                f"downloadable content {row['PackageID']} has invalid IsActive"
            )
        if row["IsActive"] == 1:
            active.append(row["PackageID"])
    return tuple(active)


def _validate_ruleset_family(family: str, active_packages: tuple[str, ...]) -> None:
    active = set(active_packages)
    has_gk = GODS_AND_KINGS_PACKAGE_ID in active
    has_bnw = BRAVE_NEW_WORLD_PACKAGE_ID in active
    valid = (
        (family == "vanilla" and not has_gk and not has_bnw)
        or (family == "gk" and has_gk and not has_bnw)
        or (family == "bnw" and has_bnw)
    )
    if not valid:
        detected = "bnw" if has_bnw else "gk" if has_gk else "vanilla"
        raise KnowledgeImportError(
            f"declared ruleset family {family} does not match detected {detected} content"
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
        description="Import deterministic ruleset knowledge from Civ V SQLite"
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--family", choices=("vanilla", "gk", "bnw"), required=True)
    parser.add_argument("--game-version", required=True)
    parser.add_argument(
        "--dlc",
        action="append",
        default=[],
        help="expected active DLC PackageID; repeat as needed (auto-detected if omitted)",
    )
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
        bundle = import_ruleset(args.database, args.source_label, ruleset)
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
