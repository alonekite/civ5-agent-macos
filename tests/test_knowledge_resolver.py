import unittest

from civ5_agent.knowledge import (
    Entity,
    KnowledgeBundle,
    ResolutionContext,
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
    )
    return KnowledgeBundle(3, RULESET, (source,), entities)


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


if __name__ == "__main__":
    unittest.main()
