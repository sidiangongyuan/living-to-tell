"""Project domain model (M5)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
