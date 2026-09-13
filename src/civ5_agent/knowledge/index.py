from __future__ import annotations

from collections import defaultdict

from .models import Entity, KnowledgeBundle, Reference
from .validation import validate_bundle


class KnowledgeIndex:
    """Validated, immutable-by-convention lookup index for one ruleset bundle."""

    def __init__(self, bundle: KnowledgeBundle):
        self.bundle = validate_bundle(bundle)
        self._entities = {
            (entity.kind, entity.type_id): entity for entity in bundle.entities
        }
        outgoing: dict[tuple[str, str], list[Reference]] = defaultdict(list)
        incoming: dict[tuple[str, str], list[Reference]] = defaultdict(list)
        for reference in bundle.references:
            outgoing[(reference.source_kind, reference.source_type_id)].append(reference)
            incoming[(reference.target_kind, reference.target_type_id)].append(reference)
        self._outgoing = {
            key: tuple(sorted(values, key=_reference_key))
            for key, values in outgoing.items()
        }
        self._incoming = {
            key: tuple(sorted(values, key=_reference_key))
            for key, values in incoming.items()
        }

    def entity(self, kind: str, type_id: str) -> Entity:
        try:
            return self._entities[(kind, type_id)]
        except KeyError as error:
            raise KeyError(f"unknown knowledge entity: {kind}/{type_id}") from error

    def entities(self, kind: str | None = None) -> tuple[Entity, ...]:
        values = (
            self._entities.values()
            if kind is None
            else (entity for entity in self._entities.values() if entity.kind == kind)
        )
        return tuple(sorted(values, key=lambda entity: (entity.kind, entity.type_id)))

    def outgoing(
        self,
        source_kind: str,
        source_type_id: str,
        reference_kind: str | None = None,
    ) -> tuple[Reference, ...]:
        self.entity(source_kind, source_type_id)
        references = self._outgoing.get((source_kind, source_type_id), ())
        if reference_kind is None:
            return references
        return tuple(item for item in references if item.kind == reference_kind)

    def incoming(
        self,
        target_kind: str,
        target_type_id: str,
        reference_kind: str | None = None,
    ) -> tuple[Reference, ...]:
        self.entity(target_kind, target_type_id)
        references = self._incoming.get((target_kind, target_type_id), ())
        if reference_kind is None:
            return references
        return tuple(item for item in references if item.kind == reference_kind)

    def targets(
        self,
        source_kind: str,
        source_type_id: str,
        reference_kind: str,
    ) -> tuple[Entity, ...]:
        return tuple(
            self.entity(reference.target_kind, reference.target_type_id)
            for reference in self.outgoing(
                source_kind, source_type_id, reference_kind
            )
        )


def _reference_key(reference: Reference) -> tuple[str, str, str, str, str]:
    return (
        reference.kind,
        reference.source_kind,
        reference.source_type_id,
        reference.target_kind,
        reference.target_type_id,
    )
