"""Work — a first-class finished-piece writing unit (M8).

A work is structurally distinct from a ``Fragment`` (entry):
- It owns ordered ``WorkSection`` blocks (its actual prose).
- It has a finite lifecycle (``WorkStatus``).
- It has its own version history.
- Fragments may be *included* into a work via the include-fragment flow,
  but the original fragments always continue to exist independently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from writer.domain.enums import WorkStatus


@dataclass
class Work:
    id: str
    title: str = ""
    summary: str = ""
    status: str = WorkStatus.IDEA.value
    tags: list[str] = field(default_factory=list)
    target_word_count: Optional[int] = None
    archived_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
