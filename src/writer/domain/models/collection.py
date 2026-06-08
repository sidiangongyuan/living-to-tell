"""Collection — an ordered table of contents over multiple articles."""
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
    """An article's position inside a collection."""

    id: str
    collection_id: str
    entry_id: str
    sort_order: int = 0
    created_at: Optional[str] = None

    @property
    def work_id(self) -> str:
        """Legacy alias for old tests/import paths."""
        return self.entry_id
