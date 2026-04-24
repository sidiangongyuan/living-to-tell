"""Entry domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from writer.domain.enums import EntryType


@dataclass
class Entry:
    id: str
    title: str = ""
    body: str = ""
    entry_type: str = EntryType.FRAGMENT.value
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    project_id: Optional[str] = None
    chapter_id: Optional[str] = None
    sequence_order: Optional[int] = None
