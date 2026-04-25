"""Reusable AI cards: style / character / setting (M10A)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiCard:
    id: str
    kind: str  # 'style' | 'character' | 'setting'
    name: str
    body: str
    created_at: str
    updated_at: str
