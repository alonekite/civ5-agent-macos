import unittest

from civ5_agent.knowledge import (
    Entity,
    KnowledgeBundle,
    ResolutionContext,
    Reference,
    Ruleset,
    RulesetResolutionError,
    RulesetResolver,
    Source,
)


RULESET = Ruleset("bnw", "test", ("DLC_TEST",), ("MOD_TEST",))


def resolver_bundle() -> KnowledgeBundle:
    source = Source("cache/test.db", "a" * 64, 1)
    entities = (
        Entity("game_speed", "GAMESPEED_STANDARD", {"research_percent": 100}, (source.path,)),
        Entity("handicap", "HANDICAP_PRINCE", {"growth_percent": 100}, (source.path,)),
        Entity("world_size", "WORLDSIZE_STANDARD", {"grid_width": 80}, (source.path,)),
        Entity("civilization", "CIVILIZATION_TEST", {}, (source.path,)),
        Entity("policy", "POLICY_A", {}, (source.path,)),
        Entity("policy", "POLICY_B", {}, (source.path,)),
        Entity("belief", "BELIEF_A", {}, (source.path,)),
        Entity("belief", "BELIEF_B", {}, (source.path,)),
        Entity("unit_class", "UNITCLASS_A", {}, (source.path,)),
        Entity("unit_class", "UNITCLASS_DISABLED", {}, (source.path,)),
        Entity("unit", "UNIT_DEFAULT", {}, (source.path,)),
        Entity("unit", "UNIT_UNIQUE", {}, (source.path,)),
        Entity("unit", "UNIT_DISABLED_DEFAULT", {}, (source.path,)),
        Entity("building_class", "BUILDINGCLASS_A", {}, (source.path,)),
        Entity("building", "BUILDING_DEFAULT", {}, (source.path,)),
    )
    references = (
        Reference("default_unit", "unit_class", "UNITCLASS_A", "unit", "UNIT_DEFAULT", (source.path,)),
        Reference("belongs_to_unit_class", "unit", "UNIT_DEFAULT", "unit_class", "UNITCLASS_A", (source.path,)),
        Reference("belongs_to_unit_class", "unit", "UNIT_UNIQUE", "unit_class", "UNITCLASS_A", (source.path,)),
        Reference("unique_unit", "civilization", "CIVILIZATION_TEST", "unit", "UNIT_UNIQUE", (source.path,)),
        Reference("default_unit", "unit_class", "UNITCLASS_DISABLED", "unit", "UNIT_DISABLED_DEFAULT", (source.path,)),
        Reference("belongs_to_unit_class", "unit", "UNIT_DISABLED_DEFAULT", "unit_class", "UNITCLASS_DISABLED", (source.path,)),
        Reference("disables_unit_class", "civilization", "CIVILIZATION_TEST", "unit_class", "UNITCLASS_DISABLED", (source.path,)),
        Reference("default_building", "building_class", "BUILDINGCLASS_A", "building", "BUILDING_DEFAULT", (source.path,)),
        Reference("belongs_to_building_class", "building", "BUILDING_DEFAULT", "building_class", "BUILDINGCLASS_A", (source.path,)),
    )
    return KnowledgeBundle(3, RULESET, (source,), entities, references)


def context(**changes) -> ResolutionContext:
    values = {
        "ruleset": RULESET,
        "game_speed_type_id": "GAMESPEED_STANDARD",
        "handicap_type_id": "HANDICAP_PRINCE",
        "world_size_type_id": "WORLDSIZE_STANDARD",
        "civilization_type_id": "CIVILIZATION_TEST",
        "adopted_policy_type_ids": ("POLICY_B", "POLICY_A"),
        "active_belief_type_ids": ("BELIEF_B", "BELIEF_A"),
    }
    values.update(changes)
    return ResolutionContext(**values)


class RulesetResolverTest(unittest.TestCase):
    def test_resolves_and_canonicalizes_declared_context(self):
        bundle = resolver_bundle()
        resolver = RulesetResolver(bundle)
        resolved = resolver.resolve(context())

        self.assertEqual(
            resolved.context.adopted_policy_type_ids,
            ("POLICY_A", "POLICY_B"),
        )
        self.assertEqual(
            tuple(item.type_id for item in resolved.active_beliefs),
            ("BELIEF_A", "BELIEF_B"),
        )
        self.assertEqual(resolved.game_speed.attributes["research_percent"], 100)
        self.assertEqual(resolved.sources, bundle.sources)
        self.assertIsNot(
            resolved.game_speed,
            resolver.index.entity("game_speed", "GAMESPEED_STANDARD"),
        )

    def test_rejects_mismatched_ruleset(self):
        resolver = RulesetResolver(resolver_bundle())
        with self.assertRaisesRegex(RulesetResolutionError, "does not match"):
            resolver.resolve(context(ruleset=Ruleset("vanilla", "test")))

    def test_rejects_unknown_selected_entity(self):
        resolver = RulesetResolver(resolver_bundle())
        with self.assertRaisesRegex(RulesetResolutionError, "unknown knowledge entity"):
            resolver.resolve(context(game_speed_type_id="GAMESPEED_MISSING"))

    def test_rejects_duplicate_selected_modifier(self):
        resolver = RulesetResolver(resolver_bundle())
        with self.assertRaisesRegex(RulesetResolutionError, "duplicate adopted policy"):
            resolver.resolve(
                context(adopted_policy_type_ids=("POLICY_A", "POLICY_A"))
            )

    def test_does_not_mutate_base_entities(self):
        bundle = resolver_bundle()
        resolver = RulesetResolver(bundle)
        resolved = resolver.resolve(context())
        resolved.game_speed.attributes["research_percent"] = 50
        self.assertEqual(
            resolver.index.entity(
                "game_speed", "GAMESPEED_STANDARD"
            ).attributes["research_percent"],
            100,
        )

    def test_resolves_civilization_unique_unit_with_provenance(self):
        resolver = RulesetResolver(resolver_bundle())
        resolved = resolver.resolve(context())
        selection = resolver.resolve_unit_class(resolved, "UNITCLASS_A")
        self.assertEqual(selection.selected_entity.type_id, "UNIT_UNIQUE")
        self.assertEqual(selection.base_reference.kind, "default_unit")
        self.assertEqual(selection.civilization_reference.kind, "unique_unit")

    def test_resolves_disabled_unit_class(self):
        resolver = RulesetResolver(resolver_bundle())
        resolved = resolver.resolve(context())
        selection = resolver.resolve_unit_class(resolved, "UNITCLASS_DISABLED")
        self.assertIsNone(selection.selected_entity)
        self.assertEqual(
            selection.civilization_reference.kind,
            "disables_unit_class",
        )

    def test_resolves_default_building_without_override(self):
        resolver = RulesetResolver(resolver_bundle())
        resolved = resolver.resolve(context())
        selection = resolver.resolve_building_class(resolved, "BUILDINGCLASS_A")
        self.assertEqual(selection.selected_entity.type_id, "BUILDING_DEFAULT")
        self.assertEqual(selection.base_reference.kind, "default_building")
        self.assertIsNone(selection.civilization_reference)


if __name__ == "__main__":
    unittest.main()
