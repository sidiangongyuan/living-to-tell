"""Reference passage domain model (M4A)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Canonical reference kinds (M-RefTypes). The list is closed for this
# milestone; any unknown legacy value is normalised to ``"excerpt"`` on read.
REFERENCE_KIND_CHARACTER = "character"
REFERENCE_KIND_LOCATION = "location"
REFERENCE_KIND_SETTING = "setting"
REFERENCE_KIND_EXCERPT = "excerpt"

REFERENCE_KINDS: tuple[str, ...] = (
    REFERENCE_KIND_CHARACTER,
    REFERENCE_KIND_LOCATION,
    REFERENCE_KIND_SETTING,
    REFERENCE_KIND_EXCERPT,
)


def normalise_kind(value: Optional[str]) -> str:
    """Map any legacy / unknown kind to ``"excerpt"`` (the safe default)."""
    if value and value in REFERENCE_KINDS:
        return value
    return REFERENCE_KIND_EXCERPT


# Usage kinds for style specimens (文脉标本用途).
USAGE_KIND_STYLE = "style"
USAGE_KIND_IMAGERY = "imagery"
USAGE_KIND_TECHNIQUE = "technique"
USAGE_KIND_CHARACTER = "character"
USAGE_KIND_SETTING = "setting"
USAGE_KIND_OTHER = "other"
USAGE_KIND_QUOTE = "quote"

USAGE_KINDS: tuple[str, ...] = (
    USAGE_KIND_STYLE,
    USAGE_KIND_IMAGERY,
    USAGE_KIND_TECHNIQUE,
    USAGE_KIND_CHARACTER,
    USAGE_KIND_SETTING,
    USAGE_KIND_OTHER,
    USAGE_KIND_QUOTE,
)


def normalise_usage_kind(value: Optional[str]) -> str:
    """Map any unknown usage_kind to ``"style"`` (the safe default)."""
    if value and value in USAGE_KINDS:
        return value
    return USAGE_KIND_STYLE


@dataclass
class ReferencePassage:
    id: str
    source_title: str
    content: str
    source_author: str = ""
    tags: str = ""
    kind: str = REFERENCE_KIND_EXCERPT
    usage_kind: str = USAGE_KIND_STYLE
    personal_note: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def display_label(self) -> str:
        if self.source_author:
            return f"{self.source_title} — {self.source_author}"
        return self.source_title
