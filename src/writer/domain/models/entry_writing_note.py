"""Fragment-bound writing note model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


NOTE_STATUS_OPEN = "open"
NOTE_STATUS_DONE = "done"


@dataclass(frozen=True)
class EntryWritingNote:
    id: str
    entry_id: str
    body: str
    status: str = NOTE_STATUS_OPEN
    pinned: bool = False
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
