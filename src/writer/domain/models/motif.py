"""Domain models for the motif star-map feature."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


MOTIF_SOURCE_ARTICLE = "article"
MOTIF_SOURCE_REFERENCE = "reference"
MOTIF_SOURCE_KINDS = {MOTIF_SOURCE_ARTICLE, MOTIF_SOURCE_REFERENCE}

MOTIF_RELATION_ECHO = "echo"
MOTIF_RELATION_CONTRAST = "contrast"
MOTIF_RELATION_TRANSFORMATION = "transformation"
MOTIF_RELATION_CONTAINS = "contains"
MOTIF_RELATION_ASSOCIATED = "associated"
MOTIF_RELATION_TYPES = {
    MOTIF_RELATION_ECHO,
    MOTIF_RELATION_CONTRAST,
    MOTIF_RELATION_TRANSFORMATION,
    MOTIF_RELATION_CONTAINS,
    MOTIF_RELATION_ASSOCIATED,
}
MOTIF_DIRECTED_RELATION_TYPES = {
    MOTIF_RELATION_TRANSFORMATION,
    MOTIF_RELATION_CONTAINS,
}

MOTIF_RELATION_UNDIRECTED = "undirected"
MOTIF_RELATION_A_TO_B = "a_to_b"
MOTIF_RELATION_B_TO_A = "b_to_a"
MOTIF_RELATION_DIRECTIONS = {
    MOTIF_RELATION_UNDIRECTED,
    MOTIF_RELATION_A_TO_B,
    MOTIF_RELATION_B_TO_A,
}


@dataclass(frozen=True)
class MotifNode:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    note: str = ""
    profile: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    pinned: bool = False
    excerpt_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class MotifRelation:
    id: str
    motif_a_id: str
    motif_a_name: str
    motif_b_id: str
    motif_b_name: str
    relation_type: str
    direction: str
    reason: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class MotifExcerpt:
    id: str
    source_kind: str
    source_id: str
    source_title_snapshot: str
    excerpt_text: str
    note: str = ""
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    before_context: str = ""
    after_context: str = ""
    motif_ids: list[str] = field(default_factory=list)
    motif_names: list[str] = field(default_factory=list)
    source_exists: bool = False
    source_current_title: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class MotifGraphNode:
    id: str
    name: str
    excerpt_count: int
    pinned: bool = False
    is_center: bool = False
    relation_count: int = 0
    needs_enrichment: bool = False


@dataclass(frozen=True)
class MotifGraphEdge:
    source_id: str
    target_id: str
    weight: int
    shared_excerpts: int = 0
    shared_sources: int = 0
    relation_id: Optional[str] = None
    relation_type: Optional[str] = None
    relation_direction: Optional[str] = None
    relation_reason: str = ""
