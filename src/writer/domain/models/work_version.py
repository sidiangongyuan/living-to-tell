"""WorkVersion — a saved snapshot of an entire work (M8).

The snapshot is stored as a JSON document of the work's sections so we
can faithfully restore section structure (not just a single body string).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkVersion:
    id: str
    work_id: str
    version_type: str
    content_json: str
    label: str = ""
    created_at: Optional[str] = None
