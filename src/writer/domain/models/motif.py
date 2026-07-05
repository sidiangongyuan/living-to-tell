"""Domain models for the motif star-map feature."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


MOTIF_SOURCE_ARTICLE = "article"
MOTIF_SOURCE_REFERENCE = "reference"
MOTIF_SOURCE_KINDS = {MOTIF_SOURCE_ARTICLE, MOTIF_SOURCE_REFERENCE}


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


@dataclass(frozen=True)
class MotifWritingExcerptSnippet:
    id: str
    source_kind: str
    source_id: str
    source_title: str
    source_author: str = ""
    excerpt_text: str = ""
    note: str = ""


@dataclass(frozen=True)
class MotifWritingMotif:
    id: str
    name: str
    tags: list[str] = field(default_factory=list)
    excerpt_count: int = 0
    pinned: bool = False
    definition: str = ""
    core_tension: str = ""
    writing_functions: list[str] = field(default_factory=list)
    scene_triggers: list[str] = field(default_factory=list)
    character_signals: list[str] = field(default_factory=list)
    excerpts: list[MotifWritingExcerptSnippet] = field(default_factory=list)


@dataclass(frozen=True)
class MotifWritingGroup:
    label: str
    motif_count: int
    excerpt_count: int
    motif_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MotifWritingSource:
    source_kind: str
    source_id: str
    source_title: str
    source_author: str = ""
    motif_count: int = 0
    excerpt_count: int = 0
    motif_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MotifWritingIndex:
    tags: list[MotifWritingGroup] = field(default_factory=list)
    functions: list[MotifWritingGroup] = field(default_factory=list)
    sources: list[MotifWritingSource] = field(default_factory=list)
    motifs: list[MotifWritingMotif] = field(default_factory=list)
