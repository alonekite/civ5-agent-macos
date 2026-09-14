from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RulesetFamily = Literal["vanilla", "gk", "bnw"]


@dataclass(frozen=True)
class Ruleset:
    family: RulesetFamily
    game_version: str
    dlc: tuple[str, ...] = ()
    mods: tuple[str, ...] = ()


@dataclass(frozen=True)
class Source:
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class Entity:
    kind: str
    type_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
    source_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Reference:
    kind: str
    source_kind: str
    source_type_id: str
    target_kind: str
    target_type_id: str
    source_paths: tuple[str, ...] = ()
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeBundle:
    schema_version: int
    ruleset: Ruleset
    sources: tuple[Source, ...]
    entities: tuple[Entity, ...]
    references: tuple[Reference, ...] = ()
