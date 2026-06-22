"""Reusable AI cards: style / character / scene."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiCard:
    id: str
    kind: str  # 'style' | 'character' | 'scene'
    name: str
    body: str
    created_at: str
    updated_at: str
