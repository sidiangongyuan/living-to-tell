"""Outline items for article collections."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CollectionOutlineItem:
    id: str
    collection_id: str
    parent_id: Optional[str] = None
    entry_id: Optional[str] = None
    title: str = ""
    item_type: str = "scene"
    status: str = "idea"
    summary: str = ""
    notes: str = ""
    pov: str = ""
    setting: str = ""
    timeline: str = ""
    tags_text: str = ""
    target_word_count: Optional[int] = None
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def tags(self) -> list[str]:
        return [part.strip() for part in self.tags_text.split(",") if part.strip()]
