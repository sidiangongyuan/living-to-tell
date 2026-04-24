"""Reference passage domain model (M4A)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReferencePassage:
    id: str
    source_title: str
    content: str
    source_author: str = ""
    tags: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def display_label(self) -> str:
        if self.source_author:
            return f"{self.source_title} — {self.source_author}"
        return self.source_title
