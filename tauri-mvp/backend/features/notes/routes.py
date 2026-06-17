"""Article-bound writing notes API for the Tauri frontend."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.entry_writing_note import EntryWritingNote

router = APIRouter(prefix="/api/articles/{entry_id}/notes", tags=["notes"])


class WritingNoteOut(BaseModel):
    id: str
    entry_id: str
    body: str
    status: str
    pinned: bool
    sort_order: int
    created_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]


class WritingNoteCreate(BaseModel):
    body: str
    pinned: bool = False


class WritingNoteUpdate(BaseModel):
    body: str


class WritingNotePinnedUpdate(BaseModel):
    pinned: bool


class WritingNoteDoneUpdate(BaseModel):
    done: bool


def _note_to_dto(note: EntryWritingNote) -> WritingNoteOut:
    return WritingNoteOut(
        id=note.id,
        entry_id=note.entry_id,
        body=note.body,
        status=note.status,
        pinned=note.pinned,
        sort_order=note.sort_order,
        created_at=note.created_at,
        updated_at=note.updated_at,
        completed_at=note.completed_at,
    )


def _require_entry(entry_id: str, container: AppContainer) -> None:
    if container.entry_repository.get(entry_id) is None:
        raise HTTPException(404, "Article not found")


def _require_note_for_entry(
    entry_id: str,
    note_id: str,
    container: AppContainer,
) -> EntryWritingNote:
    note = container.entry_writing_note_repository.get(note_id)
    if note is None or note.entry_id != entry_id:
        raise HTTPException(404, "Writing note not found")
    return note


@router.get("", response_model=list[WritingNoteOut])
def list_article_notes(
    entry_id: str,
    include_done: bool = True,
    container: AppContainer = Depends(get_container),
) -> list[WritingNoteOut]:
    _require_entry(entry_id, container)
    notes = container.entry_writing_note_repository.list_for_entry(
        entry_id,
        include_done=include_done,
    )
    return [_note_to_dto(note) for note in notes]


@router.post("", response_model=WritingNoteOut, status_code=201)
def create_article_note(
    entry_id: str,
    data: WritingNoteCreate,
    container: AppContainer = Depends(get_container),
) -> WritingNoteOut:
    _require_entry(entry_id, container)
    try:
        note = container.entry_writing_note_repository.create(
            entry_id=entry_id,
            body=data.body,
            pinned=data.pinned,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _note_to_dto(note)


@router.put("/{note_id}", response_model=WritingNoteOut)
def update_article_note(
    entry_id: str,
    note_id: str,
    data: WritingNoteUpdate,
    container: AppContainer = Depends(get_container),
) -> WritingNoteOut:
    _require_note_for_entry(entry_id, note_id, container)
    try:
        note = container.entry_writing_note_repository.update_body(note_id, data.body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if note is None:
        raise HTTPException(404, "Writing note not found")
    return _note_to_dto(note)


@router.put("/{note_id}/pinned", response_model=WritingNoteOut)
def update_article_note_pinned(
    entry_id: str,
    note_id: str,
    data: WritingNotePinnedUpdate,
    container: AppContainer = Depends(get_container),
) -> WritingNoteOut:
    _require_note_for_entry(entry_id, note_id, container)
    note = container.entry_writing_note_repository.set_pinned(note_id, data.pinned)
    if note is None:
        raise HTTPException(404, "Writing note not found")
    return _note_to_dto(note)


@router.put("/{note_id}/done", response_model=WritingNoteOut)
def update_article_note_done(
    entry_id: str,
    note_id: str,
    data: WritingNoteDoneUpdate,
    container: AppContainer = Depends(get_container),
) -> WritingNoteOut:
    _require_note_for_entry(entry_id, note_id, container)
    note = container.entry_writing_note_repository.set_done(note_id, data.done)
    if note is None:
        raise HTTPException(404, "Writing note not found")
    return _note_to_dto(note)


@router.delete("/{note_id}", status_code=204)
def delete_article_note(
    entry_id: str,
    note_id: str,
    container: AppContainer = Depends(get_container),
):
    _require_note_for_entry(entry_id, note_id, container)
    container.entry_writing_note_repository.delete(note_id)

