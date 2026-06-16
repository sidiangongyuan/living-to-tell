"""Articles feature: entry CRUD + tags + search.

Exposes the EntryRepository and SearchService from the existing writer backend.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.entry import Entry as DomainEntry
from writer.services.epigraph import detect_epigraph, strip_epigraph

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


def _entry_or_404(entry_id: str, container: AppContainer) -> DomainEntry:
    entry = container.entry_repository.get(entry_id)
    if entry is None:
        raise HTTPException(404, "Entry not found")
    return entry


def _entry_export_filename(entry: DomainEntry, ext: str) -> str:
    title = (entry.title or "").strip() or "article"
    sanitized = "".join(ch for ch in title if ch not in '<>:"/\\|?*').strip()
    return f"{sanitized or 'article'}.{ext}"


def _export_entry_docx(entry: DomainEntry, output_path: str) -> str:
    try:
        from docx import Document  # type: ignore
        from docx.enum.text import WD_ALIGN_PARAGRAPH  # type: ignore
        from docx.shared import Inches, Pt  # type: ignore
    except ImportError as exc:  # pragma: no cover - env-specific
        raise RuntimeError(
            "python-docx is required for DOCX export. Install it with: pip install python-docx"
        ) from exc

    document = Document()
    document.add_heading(entry.title.strip() or "Untitled", level=1)
    body = (entry.body or "").strip()
    if body:
        epigraph = detect_epigraph(body)
        rendered_body = strip_epigraph(body).rstrip() if epigraph is not None else body
        if epigraph is not None:
            for line in epigraph.quote.splitlines():
                para = document.add_paragraph()
                para.paragraph_format.left_indent = Inches(0.35)
                para.paragraph_format.right_indent = Inches(0.55)
                para.paragraph_format.space_after = Pt(0)
                run = para.add_run(line)
                run.italic = True

            attr_para = document.add_paragraph()
            attr_para.paragraph_format.right_indent = Inches(0.55)
            attr_para.paragraph_format.space_after = Pt(8)
            attr_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            attr_para.add_run(epigraph.attribution)

        if rendered_body:
            for para in rendered_body.split("\n\n"):
                document.add_paragraph(para)
    document.save(output_path)
    return output_path


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
    return _to_dto(_entry_or_404(entry_id, container))


@router.get("/{entry_id}/export")
def export_entry(
    entry_id: str,
    format: str = Query("md", pattern="^(txt|md|docx)$"),
    container: AppContainer = Depends(get_container),
):
    entry = _entry_or_404(entry_id, container)
    if format == "txt":
        content = container.text_exporter.export_entry(entry)
        return Response(content, media_type="text/plain; charset=utf-8")
    if format == "md":
        content = container.markdown_exporter.export_entry(entry)
        return Response(content, media_type="text/markdown; charset=utf-8")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.close()
    output = _export_entry_docx(entry, tmp.name)
    return FileResponse(
        output,
        filename=_entry_export_filename(entry, "docx"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


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
