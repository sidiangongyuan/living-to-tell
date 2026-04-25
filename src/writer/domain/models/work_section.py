"""WorkSection — one ordered prose block inside a Work (M8)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from writer.domain.enums import SectionType


@dataclass
class WorkSection:
    id: str
    work_id: str
    section_type: str = SectionType.BODY.value
    content: str = ""
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
