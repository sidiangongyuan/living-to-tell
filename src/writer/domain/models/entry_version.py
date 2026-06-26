"""EntryVersion domain model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class EntryVersion:
    id: str
    entry_id: str
    version_type: str
    content: str
    title_snapshot: str = ""
    tags_snapshot: str = ""
    label: str = ""
    reason: str = ""
    word_count: int = 0
    char_count: int = 0
    created_at: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
