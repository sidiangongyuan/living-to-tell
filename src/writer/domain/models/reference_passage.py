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


@dataclass
class ReferencePassage:
    id: str
    source_title: str
    content: str
    source_author: str = ""
    tags: str = ""
    kind: str = REFERENCE_KIND_EXCERPT
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def display_label(self) -> str:
        if self.source_author:
            return f"{self.source_title} — {self.source_author}"
        return self.source_title
