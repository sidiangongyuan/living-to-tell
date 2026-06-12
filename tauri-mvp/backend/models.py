"""Domain models for the FastAPI backend."""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EntryType(str, Enum):
    FRAGMENT = "fragment"


class CurationStatus(str, Enum):
    UNSORTED = "unsorted"
    INCLUDED = "included"
    PARKING = "parking"
    DISCARDED = "discarded"


class Entry(BaseModel):
    """Entry domain model."""
    id: str
    title: str = ""
    body: str = ""
    entry_type: str = EntryType.FRAGMENT.value
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    project_id: Optional[str] = None
    chapter_id: Optional[str] = None
    sequence_order: Optional[int] = None
    archived_at: Optional[str] = None
    curation_status: str = CurationStatus.UNSORTED.value

    class Config:
        from_attributes = True


class EntryCreate(BaseModel):
    """Schema for creating a new entry."""
    title: str = ""
    body: str = ""
    entry_type: str = EntryType.FRAGMENT.value
    tags: list[str] = Field(default_factory=list)


class EntryUpdate(BaseModel):
    """Schema for updating an entry."""
    title: str
    body: str
    tags: Optional[list[str]] = None
