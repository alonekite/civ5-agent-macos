from __future__ import annotations

import copy
from dataclasses import dataclass

from ..errors import ValidationError
from .index import KnowledgeIndex
from .models import Entity, KnowledgeBundle, Reference, Ruleset, Source


class RulesetResolutionError(ValidationError):
    """Raised when per-game context cannot be resolved without guessing."""


@dataclass(frozen=True)
class ResolutionContext:
    ruleset: Ruleset
    game_speed_type_id: str
    handicap_type_id: str
    world_size_type_id: str
    civilization_type_id: str
    adopted_policy_type_ids: tuple[str, ...] = ()
    active_belief_type_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedRuleset:
    """Validated selection over an unchanged base knowledge bundle."""

    context: ResolutionContext
    game_speed: Entity
    handicap: Entity
    world_size: Entity
    civilization: Entity
    adopted_policies: tuple[Entity, ...]
    active_beliefs: tuple[Entity, ...]
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class ResolvedClassMember:
    class_entity: Entity
    selected_entity: Entity | None
    base_reference: Reference | None
    civilization_reference: Reference | None


class RulesetResolver:
    def __init__(self, bundle: KnowledgeBundle):
        self.index = KnowledgeIndex(bundle)

    def resolve(self, context: ResolutionContext) -> ResolvedRuleset:
        if context.ruleset != self.index.bundle.ruleset:
            raise RulesetResolutionError(
                "resolution context ruleset does not match knowledge bundle"
            )
        policy_ids = _canonical_unique(
            "adopted policy", context.adopted_policy_type_ids
        )
        belief_ids = _canonical_unique(
            "active belief", context.active_belief_type_ids
        )
        canonical_context = ResolutionContext(
            ruleset=context.ruleset,
            game_speed_type_id=context.game_speed_type_id,
            handicap_type_id=context.handicap_type_id,
            world_size_type_id=context.world_size_type_id,
            civilization_type_id=context.civilization_type_id,
            adopted_policy_type_ids=policy_ids,
            active_belief_type_ids=belief_ids,
        )
        try:
            return ResolvedRuleset(
                context=canonical_context,
                game_speed=_detached_entity(
                    self.index.entity("game_speed", context.game_speed_type_id)
                ),
                handicap=_detached_entity(
                    self.index.entity("handicap", context.handicap_type_id)
                ),
                world_size=_detached_entity(
                    self.index.entity("world_size", context.world_size_type_id)
                ),
                civilization=_detached_entity(
                    self.index.entity("civilization", context.civilization_type_id)
                ),
                adopted_policies=tuple(
                    _detached_entity(self.index.entity("policy", type_id))
                    for type_id in policy_ids
                ),
                active_beliefs=tuple(
                    _detached_entity(self.index.entity("belief", type_id))
                    for type_id in belief_ids
                ),
                sources=self.index.bundle.sources,
            )
        except KeyError as error:
            raise RulesetResolutionError(str(error)) from error

    def resolve_unit_class(
        self, resolved: ResolvedRuleset, unit_class_type_id: str
    ) -> ResolvedClassMember:
        return self._resolve_class_member(
            resolved,
            class_kind="unit_class",
            class_type_id=unit_class_type_id,
            member_kind="unit",
            default_kind="default_unit",
            unique_kind="unique_unit",
            disabled_kind="disables_unit_class",
            membership_kind="belongs_to_unit_class",
        )

    def resolve_building_class(
        self, resolved: ResolvedRuleset, building_class_type_id: str
    ) -> ResolvedClassMember:
        return self._resolve_class_member(
            resolved,
            class_kind="building_class",
            class_type_id=building_class_type_id,
            member_kind="building",
            default_kind="default_building",
            unique_kind="unique_building",
            disabled_kind="disables_building_class",
            membership_kind="belongs_to_building_class",
        )

    def _resolve_class_member(
        self,
        resolved: ResolvedRuleset,
        *,
        class_kind: str,
        class_type_id: str,
        member_kind: str,
        default_kind: str,
        unique_kind: str,
        disabled_kind: str,
        membership_kind: str,
    ) -> ResolvedClassMember:
        if resolved.context.ruleset != self.index.bundle.ruleset:
            raise RulesetResolutionError(
                "resolved context ruleset does not match knowledge bundle"
            )
        try:
            class_entity = self.index.entity(class_kind, class_type_id)
            defaults = self.index.outgoing(class_kind, class_type_id, default_kind)
            civilization_refs = self.index.outgoing(
                "civilization", resolved.context.civilization_type_id
            )
            disabled = tuple(
                reference
                for reference in civilization_refs
                if reference.kind == disabled_kind
                and reference.target_kind == class_kind
                and reference.target_type_id == class_type_id
            )
            unique: list[Reference] = []
            for reference in civilization_refs:
                if reference.kind != unique_kind or reference.target_kind != member_kind:
                    continue
                memberships = self.index.outgoing(
                    member_kind,
                    reference.target_type_id,
                    membership_kind,
                )
                if any(
                    membership.target_kind == class_kind
                    and membership.target_type_id == class_type_id
                    for membership in memberships
                ):
                    unique.append(reference)
        except KeyError as error:
            raise RulesetResolutionError(str(error)) from error

        if len(defaults) > 1 or len(disabled) > 1 or len(unique) > 1:
            raise RulesetResolutionError(
                f"ambiguous {class_kind} resolution: {class_type_id}"
            )
        if disabled and unique:
            raise RulesetResolutionError(
                f"conflicting civilization override for {class_kind}: "
                f"{class_type_id}"
            )
        base_reference = _detached_reference(defaults[0]) if defaults else None
        if disabled:
            return ResolvedClassMember(
                _detached_entity(class_entity),
                None,
                base_reference,
                _detached_reference(disabled[0]),
            )
        selected_reference = unique[0] if unique else (defaults[0] if defaults else None)
        if selected_reference is None:
            raise RulesetResolutionError(
                f"no effective member for {class_kind}: {class_type_id}"
            )
        try:
            selected = self.index.entity(
                selected_reference.target_kind,
                selected_reference.target_type_id,
            )
        except KeyError as error:
            raise RulesetResolutionError(str(error)) from error
        return ResolvedClassMember(
            _detached_entity(class_entity),
            _detached_entity(selected),
            base_reference,
            _detached_reference(unique[0]) if unique else None,
        )


def _canonical_unique(label: str, type_ids: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(type_ids, tuple) or any(
        not isinstance(type_id, str) for type_id in type_ids
    ):
        raise RulesetResolutionError(f"{label} identifiers must be a tuple of strings")
    if len(set(type_ids)) != len(type_ids):
        raise RulesetResolutionError(f"duplicate {label} identifier")
    return tuple(sorted(type_ids))


def _detached_entity(entity: Entity) -> Entity:
    return Entity(
        entity.kind,
        entity.type_id,
        copy.deepcopy(entity.attributes),
        entity.source_paths,
    )


def _detached_reference(reference: Reference) -> Reference:
    return Reference(
        reference.kind,
        reference.source_kind,
        reference.source_type_id,
        reference.target_kind,
        reference.target_type_id,
        reference.source_paths,
        copy.deepcopy(reference.attributes),
        reference.context,
    )
