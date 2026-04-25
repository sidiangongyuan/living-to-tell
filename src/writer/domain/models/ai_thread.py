"""AI thread + message domain models (M10A)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AiThread:
    id: str
    scope_kind: str
    scope_id: Optional[str]
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AiMessage:
    id: str
    thread_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    meta_json: str
    created_at: str
