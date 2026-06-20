"""Domain models for the motif star-map feature."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


MOTIF_SOURCE_ARTICLE = "article"
MOTIF_SOURCE_REFERENCE = "reference"
MOTIF_SOURCE_KINDS = {MOTIF_SOURCE_ARTICLE, MOTIF_SOURCE_REFERENCE}


@dataclass(frozen=True)
class MotifNode:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    note: str = ""
    tags: list[str] = field(default_factory=list)
    pinned: bool = False
    excerpt_count: int = 0
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


@dataclass(frozen=True)
class MotifGraphEdge:
    source_id: str
    target_id: str
    weight: int
    shared_excerpts: int = 0
    shared_sources: int = 0
