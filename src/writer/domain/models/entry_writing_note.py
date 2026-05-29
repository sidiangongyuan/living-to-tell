"""Fragment-bound writing note model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


NOTE_STATUS_OPEN = "open"
NOTE_STATUS_DONE = "done"
NOTE_BOARD_WIDTH_DEFAULT = 188
NOTE_COLOR_KEY_DEFAULT = "cream"
NOTE_Z_INDEX_DEFAULT = 0


@dataclass(frozen=True)
class EntryWritingNote:
    id: str
    entry_id: str
    body: str
    status: str = NOTE_STATUS_OPEN
    pinned: bool = False
    sort_order: int = 0
    board_x: Optional[int] = None
    board_y: Optional[int] = None
    board_width: int = NOTE_BOARD_WIDTH_DEFAULT
    color_key: str = NOTE_COLOR_KEY_DEFAULT
    z_index: int = NOTE_Z_INDEX_DEFAULT
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
