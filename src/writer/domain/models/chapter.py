"""Chapter domain model (M5)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Chapter:
    id: str
    project_id: str
    title: str = ""
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
