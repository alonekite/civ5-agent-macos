from __future__ import annotations

import copy
from dataclasses import dataclass

from .index import KnowledgeIndex
from .models import Entity, KnowledgeBundle, Ruleset, Source


class RulesetResolutionError(ValueError):
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
