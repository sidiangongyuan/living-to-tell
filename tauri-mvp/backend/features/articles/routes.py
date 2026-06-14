"""Articles feature: entry CRUD + tags + search.

Exposes the EntryRepository and SearchService from the existing writer backend.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.entry import Entry as DomainEntry

router = APIRouter(prefix="/api/articles", tags=["articles"])


# ---- DTOs matching frontend contract ----
class EntryOut(BaseModel):
    id: str
    title: str
    body: str
    entry_type: str
    created_at: Optional[str]
    updated_at: Optional[str]
    tags: list[str]
    archived_at: Optional[str]
    curation_status: str


class EntryCreate(BaseModel):
    title: str = ""
    body: str = ""
    tags: list[str] = Field(default_factory=list)


class EntryUpdate(BaseModel):
    title: str
    body: str
    tags: Optional[list[str]] = None


def _to_dto(e: DomainEntry) -> EntryOut:
    return EntryOut(
        id=e.id,
        title=e.title,
        body=e.body,
        entry_type=e.entry_type,
        created_at=e.created_at,
        updated_at=e.updated_at,
        tags=e.tags,
        archived_at=e.archived_at,
        curation_status=e.curation_status,
    )


# ---- Routes ----
@router.get("", response_model=list[EntryOut])
def list_entries(
    limit: int = Query(100, le=500),
    include_archived: bool = False,
    container: AppContainer = Depends(get_container),
) -> list[EntryOut]:
    entries = container.entry_repository.list_recent(
        limit=limit, include_archived=include_archived
    )
    return [_to_dto(e) for e in entries]


@router.get("/search", response_model=list[EntryOut])
def search_entries(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, le=200),
    container: AppContainer = Depends(get_container),
) -> list[EntryOut]:
    results = container.search_service.search(q, limit=limit)
    return [_to_dto(e) for e in results]


@router.get("/{entry_id}", response_model=EntryOut)
def get_entry(
    entry_id: str,
    container: AppContainer = Depends(get_container),
) -> EntryOut:
    entry = container.entry_repository.get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    return _to_dto(entry)


@router.post("", response_model=EntryOut, status_code=201)
def create_entry(
    data: EntryCreate,
    container: AppContainer = Depends(get_container),
) -> EntryOut:
    entry = container.entry_repository.create(
        title=data.title, body=data.body, tags=data.tags
    )
    return _to_dto(entry)


@router.put("/{entry_id}", response_model=EntryOut)
def update_entry(
    entry_id: str,
    data: EntryUpdate,
    container: AppContainer = Depends(get_container),
) -> EntryOut:
    entry = container.entry_repository.update(
        entry_id, title=data.title, body=data.body, tags=data.tags
    )
    if not entry:
        raise HTTPException(404, "Entry not found")
    return _to_dto(entry)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(
    entry_id: str,
    container: AppContainer = Depends(get_container),
):
    success = container.entry_repository.delete(entry_id)
    if not success:
        raise HTTPException(404, "Entry not found")


@router.post("/{entry_id}/archive", response_model=EntryOut)
def archive_entry(
    entry_id: str,
    container: AppContainer = Depends(get_container),
) -> EntryOut:
    entry = container.entry_repository.archive(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    return _to_dto(entry)


@router.post("/{entry_id}/unarchive", response_model=EntryOut)
def unarchive_entry(
    entry_id: str,
    container: AppContainer = Depends(get_container),
) -> EntryOut:
    entry = container.entry_repository.unarchive(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    return _to_dto(entry)
