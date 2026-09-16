from __future__ import annotations

import math
import re
from pathlib import PurePosixPath
from typing import Any

from ..errors import ValidationError
from .models import KnowledgeBundle, ReferenceContext


TYPE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_FAMILIES = {"vanilla", "gk", "bnw"}
FORBIDDEN_ATTRIBUTE_FRAGMENTS = ("flavor", "personality")
SUPPORTED_KNOWLEDGE_SCHEMA_VERSIONS = frozenset({1, 2, 3})


class KnowledgeValidationError(ValidationError):
    pass


def validate_bundle(bundle: KnowledgeBundle) -> KnowledgeBundle:
    if (
        not isinstance(bundle.schema_version, int)
        or isinstance(bundle.schema_version, bool)
        or bundle.schema_version not in SUPPORTED_KNOWLEDGE_SCHEMA_VERSIONS
    ):
        raise KnowledgeValidationError(
            f"unsupported knowledge schema_version: {bundle.schema_version}"
        )
    if (
        not isinstance(bundle.ruleset.family, str)
        or bundle.ruleset.family not in ALLOWED_FAMILIES
    ):
        raise KnowledgeValidationError(
            f"unsupported ruleset family: {bundle.ruleset.family}"
        )
    if (
        not isinstance(bundle.ruleset.game_version, str)
        or not bundle.ruleset.game_version.strip()
    ):
        raise KnowledgeValidationError("ruleset game_version must not be empty")
    _validate_sorted_unique(bundle.ruleset.dlc, "ruleset dlc")
    _validate_sorted_unique(bundle.ruleset.mods, "ruleset mods")

    source_paths: set[str] = set()
    for source in bundle.sources:
        _validate_source_path(source.path)
        if source.path in source_paths:
            raise KnowledgeValidationError(f"duplicate source path: {source.path}")
        source_paths.add(source.path)
        if not SHA256_PATTERN.fullmatch(source.sha256):
            raise KnowledgeValidationError(
                f"source {source.path} has invalid sha256"
            )
        if (
            not isinstance(source.size_bytes, int)
            or isinstance(source.size_bytes, bool)
            or source.size_bytes < 0
        ):
            raise KnowledgeValidationError(
                f"source {source.path} has invalid size_bytes"
            )

    entity_keys: set[tuple[str, str]] = set()
    for entity in bundle.entities:
        _validate_kind(entity.kind, "entity kind")
        _validate_type_id(entity.type_id, "entity type_id")
        key = (entity.kind, entity.type_id)
        if key in entity_keys:
            raise KnowledgeValidationError(
                f"duplicate entity: {entity.kind}/{entity.type_id}"
            )
        entity_keys.add(key)
        _validate_source_links(entity.source_paths, source_paths, str(key))
        _validate_json_value(entity.attributes, f"attributes for {entity.type_id}")

    reference_keys: set[tuple[Any, ...]] = set()
    for reference in bundle.references:
        _validate_kind(reference.kind, "reference kind")
        _validate_kind(reference.source_kind, "reference source_kind")
        _validate_type_id(reference.source_type_id, "reference source_type_id")
        _validate_kind(reference.target_kind, "reference target_kind")
        _validate_type_id(reference.target_type_id, "reference target_type_id")
        source_key = (reference.source_kind, reference.source_type_id)
        target_key = (reference.target_kind, reference.target_type_id)
        if source_key not in entity_keys:
            raise KnowledgeValidationError(
                f"reference source does not exist: {source_key[0]}/{source_key[1]}"
            )
        if target_key not in entity_keys:
            raise KnowledgeValidationError(
                f"reference target does not exist: {target_key[0]}/{target_key[1]}"
            )
        for item in reference.context:
            if not isinstance(item, ReferenceContext):
                raise KnowledgeValidationError(
                    f"context for {reference.kind}/{reference.source_type_id} "
                    "contains an invalid item"
                )
            _validate_kind(item.role, "reference context role")
            _validate_kind(item.kind, "reference context kind")
            _validate_type_id(item.type_id, "reference context type_id")
            if (item.kind, item.type_id) not in entity_keys:
                raise KnowledgeValidationError(
                    "reference context does not exist: "
                    f"{item.kind}/{item.type_id}"
                )
        if tuple(sorted(set(reference.context))) != reference.context:
            raise KnowledgeValidationError(
                f"context for {reference.kind}/{reference.source_type_id} "
                "must be sorted and unique"
            )
        context_key = tuple(
            (item.role, item.kind, item.type_id) for item in reference.context
        )
        key = (
            reference.kind,
            reference.source_kind,
            reference.source_type_id,
            reference.target_kind,
            reference.target_type_id,
            context_key,
        )
        if key in reference_keys:
            raise KnowledgeValidationError(
                "duplicate reference: "
                + "/".join(
                    (
                        reference.kind,
                        reference.source_kind,
                        reference.source_type_id,
                        reference.target_kind,
                        reference.target_type_id,
                    )
                )
            )
        reference_keys.add(key)
        _validate_source_links(reference.source_paths, source_paths, str(key))
        if bundle.schema_version == 1 and reference.attributes:
            raise KnowledgeValidationError(
                "schema_version 1 references cannot contain attributes"
            )
        if bundle.schema_version < 3 and reference.context:
            raise KnowledgeValidationError(
                f"schema_version {bundle.schema_version} references cannot "
                "contain context"
            )
        _validate_json_value(
            reference.attributes,
            f"attributes for {reference.kind}/{reference.source_type_id}",
        )
    return bundle


def _validate_sorted_unique(values: tuple[str, ...], label: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise KnowledgeValidationError(f"{label} entries must be non-empty strings")
    if tuple(sorted(set(values))) != values:
        raise KnowledgeValidationError(f"{label} must be sorted and unique")


def _validate_source_path(path: str) -> None:
    if not isinstance(path, str) or not path:
        raise KnowledgeValidationError("source path must not be empty")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or "\\" in path:
        raise KnowledgeValidationError(f"source path must be relative: {path}")
    if str(parsed) != path or path == ".":
        raise KnowledgeValidationError(f"source path is not canonical: {path}")


def _validate_kind(value: str, label: str) -> None:
    if not isinstance(value, str) or not KIND_PATTERN.fullmatch(value):
        raise KnowledgeValidationError(f"{label} must be lower_snake_case")
    _reject_ai_name(value, label)


def _validate_type_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not TYPE_ID_PATTERN.fullmatch(value):
        raise KnowledgeValidationError(f"{label} must be a stable uppercase ID")


def _reject_ai_name(value: str, label: str) -> None:
    normalized = value.lower()
    if any(fragment in normalized for fragment in FORBIDDEN_ATTRIBUTE_FRAGMENTS):
        raise KnowledgeValidationError(f"{label} contains forbidden AI data: {value}")


def _validate_source_links(
    links: tuple[str, ...], known_paths: set[str], owner: str
) -> None:
    if not links:
        raise KnowledgeValidationError(f"{owner} must cite at least one source")
    if tuple(sorted(set(links))) != links:
        raise KnowledgeValidationError(
            f"source paths for {owner} must be sorted and unique"
        )
    missing = [path for path in links if path not in known_paths]
    if missing:
        raise KnowledgeValidationError(
            f"unknown source path for {owner}: {', '.join(missing)}"
        )


def _validate_json_value(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise KnowledgeValidationError(f"{label} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise KnowledgeValidationError(
                    f"{label} contains a non-string or empty key"
                )
            normalized = key.lower().replace("-", "_")
            if any(fragment in normalized for fragment in FORBIDDEN_ATTRIBUTE_FRAGMENTS):
                raise KnowledgeValidationError(
                    f"{label} contains forbidden AI field: {key}"
                )
            _validate_json_value(item, f"{label}.{key}")
        return
    raise KnowledgeValidationError(
        f"{label} contains unsupported value type: {type(value).__name__}"
    )
