import json
import unittest

from civ5_agent.knowledge import (
    Entity,
    KnowledgeBundle,
    KnowledgeIndex,
    KnowledgeValidationError,
    Reference,
    ReferenceContext,
    Ruleset,
    Source,
    bundle_sha256,
    dumps,
    loads,
    validate_bundle,
)


SOURCE_PATH = "Assets/Gameplay/XML/Technologies/CIV5Technologies.xml"
SOURCE_HASH = "a" * 64


def valid_bundle(**changes):
    values = {
        "schema_version": 1,
        "ruleset": Ruleset("bnw", "1.0.3.279", ("Expansion2",), ()),
        "sources": (Source(SOURCE_PATH, SOURCE_HASH, 1200),),
        "entities": (
            Entity("technology", "TECH_AGRICULTURE", {"cost": 20}, (SOURCE_PATH,)),
            Entity("technology", "TECH_POTTERY", {"cost": 35}, (SOURCE_PATH,)),
        ),
        "references": (
            Reference(
                "requires_all",
                "technology",
                "TECH_POTTERY",
                "technology",
                "TECH_AGRICULTURE",
                (SOURCE_PATH,),
            ),
        ),
    }
    values.update(changes)
    return KnowledgeBundle(**values)


def schema_two_bundle(**changes):
    reference = Reference(
        "yield_change",
        "technology",
        "TECH_POTTERY",
        "technology",
        "TECH_AGRICULTURE",
        (SOURCE_PATH,),
        {"amount": 2},
    )
    values = {"schema_version": 2, "references": (reference,)}
    values.update(changes)
    return valid_bundle(**values)


def schema_three_bundle(**changes):
    reference = Reference(
        "yield_change",
        "technology",
        "TECH_POTTERY",
        "technology",
        "TECH_AGRICULTURE",
        (SOURCE_PATH,),
        {"amount": 2},
        (ReferenceContext("during_technology", "technology", "TECH_POTTERY"),),
    )
    values = {"schema_version": 3, "references": (reference,)}
    values.update(changes)
    return valid_bundle(**values)


class KnowledgeValidationTest(unittest.TestCase):
    def test_accepts_versioned_bundle_with_provenance(self):
        bundle = valid_bundle()
        self.assertIs(validate_bundle(bundle), bundle)

    def test_rejects_duplicate_entities(self):
        entity = valid_bundle().entities[0]
        with self.assertRaisesRegex(KnowledgeValidationError, "duplicate entity"):
            validate_bundle(valid_bundle(entities=(entity, entity)))

    def test_rejects_missing_reference_target(self):
        bundle = valid_bundle(entities=(valid_bundle().entities[1],))
        with self.assertRaisesRegex(KnowledgeValidationError, "target does not exist"):
            validate_bundle(bundle)

    def test_rejects_unknown_entity_source(self):
        entity = Entity("technology", "TECH_POTTERY", {}, ("missing.xml",))
        with self.assertRaisesRegex(KnowledgeValidationError, "unknown source path"):
            validate_bundle(valid_bundle(entities=(entity,), references=()))

    def test_rejects_non_relative_source_path(self):
        source = Source("/absolute/CIV5Technologies.xml", SOURCE_HASH, 12)
        with self.assertRaisesRegex(KnowledgeValidationError, "must be relative"):
            validate_bundle(valid_bundle(sources=(source,)))

    def test_rejects_ai_fields_at_any_attribute_depth(self):
        entity = Entity(
            "leader",
            "LEADER_ALEXANDER",
            {"metadata": {"warFlavor": 8}},
            (SOURCE_PATH,),
        )
        with self.assertRaisesRegex(KnowledgeValidationError, "forbidden AI field"):
            validate_bundle(valid_bundle(entities=(entity,), references=()))

    def test_rejects_ai_entity_categories(self):
        entity = Entity("leader_flavor", "LEADER_ALEXANDER", {}, (SOURCE_PATH,))
        with self.assertRaisesRegex(KnowledgeValidationError, "forbidden AI data"):
            validate_bundle(valid_bundle(entities=(entity,), references=()))

    def test_allows_game_ids_that_use_personality_as_gameplay_term(self):
        entity = Entity(
            "policy",
            "POLICY_CULT_PERSONALITY",
            {"culture_cost": 10},
            (SOURCE_PATH,),
        )
        bundle = valid_bundle(entities=(entity,), references=())
        self.assertIs(validate_bundle(bundle), bundle)

    def test_rejects_boolean_schema_version(self):
        with self.assertRaisesRegex(KnowledgeValidationError, "schema_version"):
            validate_bundle(valid_bundle(schema_version=True))

    def test_schema_one_rejects_reference_attributes(self):
        reference = Reference(
            "requires_all",
            "technology",
            "TECH_POTTERY",
            "technology",
            "TECH_AGRICULTURE",
            (SOURCE_PATH,),
            {"amount": 1},
        )
        with self.assertRaisesRegex(
            KnowledgeValidationError, "schema_version 1 references"
        ):
            validate_bundle(valid_bundle(references=(reference,)))

    def test_schema_two_rejects_reference_context(self):
        reference = Reference(
            "yield_change",
            "technology",
            "TECH_POTTERY",
            "technology",
            "TECH_AGRICULTURE",
            (SOURCE_PATH,),
            {"amount": 1},
            (ReferenceContext("during_technology", "technology", "TECH_POTTERY"),),
        )
        with self.assertRaisesRegex(
            KnowledgeValidationError, "schema_version 2 references"
        ):
            validate_bundle(schema_two_bundle(references=(reference,)))

    def test_schema_three_rejects_missing_context_entity(self):
        reference = schema_three_bundle().references[0]
        missing = Reference(
            reference.kind,
            reference.source_kind,
            reference.source_type_id,
            reference.target_kind,
            reference.target_type_id,
            reference.source_paths,
            reference.attributes,
            (ReferenceContext("during_technology", "technology", "TECH_MISSING"),),
        )
        with self.assertRaisesRegex(KnowledgeValidationError, "context does not exist"):
            validate_bundle(schema_three_bundle(references=(missing,)))

    def test_schema_three_requires_sorted_unique_context(self):
        reference = schema_three_bundle().references[0]
        context = (
            ReferenceContext("second", "technology", "TECH_POTTERY"),
            ReferenceContext("first", "technology", "TECH_AGRICULTURE"),
        )
        unsorted = Reference(
            reference.kind,
            reference.source_kind,
            reference.source_type_id,
            reference.target_kind,
            reference.target_type_id,
            reference.source_paths,
            reference.attributes,
            context,
        )
        with self.assertRaisesRegex(KnowledgeValidationError, "sorted and unique"):
            validate_bundle(schema_three_bundle(references=(unsorted,)))

    def test_schema_three_allows_same_edge_with_different_context(self):
        reference = schema_three_bundle().references[0]
        other = Reference(
            reference.kind,
            reference.source_kind,
            reference.source_type_id,
            reference.target_kind,
            reference.target_type_id,
            reference.source_paths,
            {"amount": 3},
            (
                ReferenceContext(
                    "during_technology", "technology", "TECH_AGRICULTURE"
                ),
            ),
        )
        bundle = schema_three_bundle(references=(reference, other))
        self.assertIs(validate_bundle(bundle), bundle)
        with self.assertRaisesRegex(KnowledgeValidationError, "duplicate reference"):
            validate_bundle(schema_three_bundle(references=(reference, reference)))

    def test_rejects_non_string_game_version(self):
        ruleset = Ruleset("bnw", None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(KnowledgeValidationError, "game_version"):
            validate_bundle(valid_bundle(ruleset=ruleset))

    def test_rejects_unsorted_ruleset_components(self):
        ruleset = Ruleset("bnw", "1.0.3.279", ("Zulu", "Expansion2"), ())
        with self.assertRaisesRegex(KnowledgeValidationError, "sorted and unique"):
            validate_bundle(valid_bundle(ruleset=ruleset))


class KnowledgeCodecTest(unittest.TestCase):
    def test_round_trip_is_canonical(self):
        bundle = valid_bundle()
        encoded = dumps(bundle)
        self.assertEqual(dumps(loads(encoded)), encoded)
        self.assertEqual(bundle_sha256(loads(encoded)), bundle_sha256(bundle))

    def test_entity_order_does_not_change_canonical_hash(self):
        bundle = valid_bundle()
        reordered = valid_bundle(entities=tuple(reversed(bundle.entities)))
        self.assertEqual(bundle_sha256(bundle), bundle_sha256(reordered))

    def test_schema_two_reference_attributes_round_trip(self):
        bundle = schema_two_bundle()
        encoded = dumps(bundle)
        decoded = loads(encoded)
        self.assertEqual(decoded.references[0].attributes, {"amount": 2})
        self.assertNotIn("context", json.loads(encoded)["references"][0])
        self.assertEqual(dumps(decoded), encoded)

    def test_schema_three_reference_context_round_trip(self):
        bundle = schema_three_bundle()
        encoded = dumps(bundle)
        decoded = loads(encoded)
        self.assertEqual(decoded.references[0].context, bundle.references[0].context)
        self.assertEqual(dumps(decoded), encoded)

    def test_schema_one_encoding_remains_compatible(self):
        value = json.loads(dumps(valid_bundle()))
        self.assertNotIn("attributes", value["references"][0])

    def test_rejects_unknown_json_fields(self):
        value = json.loads(dumps(valid_bundle()))
        value["invented"] = True
        with self.assertRaisesRegex(KnowledgeValidationError, "unexpected invented"):
            loads(json.dumps(value))

    def test_rejects_non_finite_numbers(self):
        entity = Entity("technology", "TECH_POTTERY", {"cost": float("nan")}, (SOURCE_PATH,))
        with self.assertRaisesRegex(KnowledgeValidationError, "non-finite"):
            dumps(valid_bundle(entities=(entity,), references=()))

    def test_rejects_non_finite_reference_attributes(self):
        reference = schema_two_bundle().references[0]
        invalid = Reference(
            reference.kind,
            reference.source_kind,
            reference.source_type_id,
            reference.target_kind,
            reference.target_type_id,
            reference.source_paths,
            {"amount": float("inf")},
        )
        with self.assertRaisesRegex(KnowledgeValidationError, "non-finite"):
            dumps(schema_two_bundle(references=(invalid,)))


class KnowledgeIndexTest(unittest.TestCase):
    def test_queries_entities_and_typed_relations(self):
        index = KnowledgeIndex(valid_bundle())
        self.assertEqual(index.entity("technology", "TECH_POTTERY").attributes["cost"], 35)
        self.assertEqual(
            [item.type_id for item in index.entities("technology")],
            ["TECH_AGRICULTURE", "TECH_POTTERY"],
        )
        self.assertEqual(
            [item.type_id for item in index.targets("technology", "TECH_POTTERY", "requires_all")],
            ["TECH_AGRICULTURE"],
        )
        self.assertEqual(
            index.incoming("technology", "TECH_AGRICULTURE")[0].source_type_id,
            "TECH_POTTERY",
        )

    def test_unknown_entity_fails_closed(self):
        index = KnowledgeIndex(valid_bundle())
        with self.assertRaisesRegex(KeyError, "unknown knowledge entity"):
            index.outgoing("technology", "TECH_FUTURE_TECH")


if __name__ == "__main__":
    unittest.main()
