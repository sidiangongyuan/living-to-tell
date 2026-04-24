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
    created_at: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
