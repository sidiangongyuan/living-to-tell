"""Collection — an ordered table of contents over multiple Works (M8)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Collection:
    id: str
    name: str = ""
    description: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class CollectionItem:
    """A work's position inside a collection."""

    id: str
    collection_id: str
    work_id: str
    sort_order: int = 0
    created_at: Optional[str] = None
