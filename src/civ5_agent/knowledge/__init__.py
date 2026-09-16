"""Versioned, deterministic Civilization V ruleset knowledge."""

from .codec import bundle_sha256, dumps, loads
from .index import KnowledgeIndex
from .models import (
    Entity,
    KnowledgeBundle,
    Reference,
    ReferenceContext,
    Ruleset,
    Source,
)
from .resolver import (
    ResolutionContext,
    ResolvedClassMember,
    ResolvedRuleset,
    RulesetResolutionError,
    RulesetResolver,
)
from .validation import (
    SUPPORTED_KNOWLEDGE_SCHEMA_VERSIONS,
    KnowledgeValidationError,
    validate_bundle,
)

__all__ = [
    "Entity",
    "KnowledgeBundle",
    "KnowledgeIndex",
    "KnowledgeValidationError",
    "Reference",
    "ReferenceContext",
    "ResolutionContext",
    "ResolvedClassMember",
    "ResolvedRuleset",
    "Ruleset",
    "RulesetResolutionError",
    "RulesetResolver",
    "Source",
    "SUPPORTED_KNOWLEDGE_SCHEMA_VERSIONS",
    "bundle_sha256",
    "dumps",
    "loads",
    "validate_bundle",
]
