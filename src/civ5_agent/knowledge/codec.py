from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import Entity, KnowledgeBundle, Reference, Ruleset, Source
from .validation import KnowledgeValidationError, validate_bundle


def dumps(bundle: KnowledgeBundle) -> str:
    validate_bundle(bundle)
    return json.dumps(
        _to_dict(bundle),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def loads(payload: str) -> KnowledgeBundle:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise KnowledgeValidationError(f"invalid knowledge JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise KnowledgeValidationError("knowledge JSON must contain an object")
    _require_keys(
        value,
        {"schema_version", "ruleset", "sources", "entities", "references"},
        "bundle",
    )
    ruleset_value = _require_object(value["ruleset"], "ruleset")
    _require_keys(ruleset_value, {"family", "game_version", "dlc", "mods"}, "ruleset")
    sources_value = _require_list(value["sources"], "sources")
    entities_value = _require_list(value["entities"], "entities")
    references_value = _require_list(value["references"], "references")
    try:
        bundle = KnowledgeBundle(
            schema_version=value["schema_version"],
            ruleset=Ruleset(
                family=ruleset_value["family"],
                game_version=ruleset_value["game_version"],
                dlc=tuple(_require_list(ruleset_value["dlc"], "ruleset.dlc")),
                mods=tuple(_require_list(ruleset_value["mods"], "ruleset.mods")),
            ),
            sources=tuple(_source(item, index) for index, item in enumerate(sources_value)),
            entities=tuple(_entity(item, index) for index, item in enumerate(entities_value)),
            references=tuple(
                _reference(item, index) for index, item in enumerate(references_value)
            ),
        )
    except (KeyError, TypeError) as error:
        raise KnowledgeValidationError(f"invalid knowledge structure: {error}") from error
    return validate_bundle(bundle)


def bundle_sha256(bundle: KnowledgeBundle) -> str:
    return hashlib.sha256(dumps(bundle).encode("utf-8")).hexdigest()


def _to_dict(bundle: KnowledgeBundle) -> dict[str, Any]:
    return {
        "schema_version": bundle.schema_version,
        "ruleset": {
            "family": bundle.ruleset.family,
            "game_version": bundle.ruleset.game_version,
            "dlc": list(bundle.ruleset.dlc),
            "mods": list(bundle.ruleset.mods),
        },
        "sources": [
            {"path": item.path, "sha256": item.sha256, "size_bytes": item.size_bytes}
            for item in sorted(bundle.sources, key=lambda item: item.path)
        ],
        "entities": [
            {
                "kind": item.kind,
                "type_id": item.type_id,
                "attributes": item.attributes,
                "source_paths": list(item.source_paths),
            }
            for item in sorted(bundle.entities, key=lambda item: (item.kind, item.type_id))
        ],
        "references": [
            {
                "kind": item.kind,
                "source_kind": item.source_kind,
                "source_type_id": item.source_type_id,
                "target_kind": item.target_kind,
                "target_type_id": item.target_type_id,
                "source_paths": list(item.source_paths),
            }
            for item in sorted(
                bundle.references,
                key=lambda item: (
                    item.kind,
                    item.source_kind,
                    item.source_type_id,
                    item.target_kind,
                    item.target_type_id,
                ),
            )
        ],
    }


def _source(value: Any, index: int) -> Source:
    item = _require_object(value, f"sources[{index}]")
    _require_keys(item, {"path", "sha256", "size_bytes"}, f"sources[{index}]")
    return Source(path=item["path"], sha256=item["sha256"], size_bytes=item["size_bytes"])


def _entity(value: Any, index: int) -> Entity:
    item = _require_object(value, f"entities[{index}]")
    _require_keys(
        item,
        {"kind", "type_id", "attributes", "source_paths"},
        f"entities[{index}]",
    )
    attributes = _require_object(item["attributes"], f"entities[{index}].attributes")
    return Entity(
        kind=item["kind"],
        type_id=item["type_id"],
        attributes=attributes,
        source_paths=tuple(
            _require_list(item["source_paths"], f"entities[{index}].source_paths")
        ),
    )


def _reference(value: Any, index: int) -> Reference:
    item = _require_object(value, f"references[{index}]")
    keys = {
        "kind",
        "source_kind",
        "source_type_id",
        "target_kind",
        "target_type_id",
        "source_paths",
    }
    _require_keys(item, keys, f"references[{index}]")
    return Reference(
        kind=item["kind"],
        source_kind=item["source_kind"],
        source_type_id=item["source_type_id"],
        target_kind=item["target_kind"],
        target_type_id=item["target_type_id"],
        source_paths=tuple(
            _require_list(item["source_paths"], f"references[{index}].source_paths")
        ),
    )


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise KnowledgeValidationError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise KnowledgeValidationError(f"{label} must be an array")
    return value


def _require_keys(value: dict[str, Any], keys: set[str], label: str) -> None:
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise KnowledgeValidationError(f"{label} fields are invalid: {'; '.join(details)}")
