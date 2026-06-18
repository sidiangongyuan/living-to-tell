"""Article collection API for reading order, preview, and export."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.collection import Collection as DomainCollection
from writer.domain.models.entry import Entry as DomainEntry

router = APIRouter(prefix="/api/collections", tags=["collections"])


class CollectionOut(BaseModel):
    id: str
    title: str
    description: str
    article_count: int = 0
    created_at: Optional[str]
    updated_at: Optional[str]


class CollectionCreate(BaseModel):
    title: str
    description: str = ""


class CollectionUpdate(BaseModel):
    title: str
    description: str = ""


class ArticleOut(BaseModel):
    id: str
    title: str
    body: str
    body_preview: str
    tags: list[str]
    word_count: int
    char_count: int
    sort_order: int = 0
    created_at: Optional[str]
    updated_at: Optional[str]


class AddArticlesRequest(BaseModel):
    entry_ids: list[str] = Field(default_factory=list)


class ReorderArticlesRequest(BaseModel):
    entry_ids: list[str] = Field(default_factory=list)


class EntryCollectionsRequest(BaseModel):
    collection_ids: list[str] = Field(default_factory=list)


def _word_count(body: str) -> int:
    if not body:
        return 0
    total = 0
    buf: list[str] = []
    for ch in body:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            if buf:
                if "".join(buf).strip():
                    total += 1
                buf = []
            total += 1
        else:
            buf.append(ch)
    if buf:
        total += len([token for token in "".join(buf).split() if token.strip()])
    return total


def _preview(body: str, limit: int = 120) -> str:
    compact = " ".join((body or "").split())
    return compact[:limit]


def _collection_to_dto(
    c: DomainCollection,
    *,
    container: AppContainer,
) -> CollectionOut:
    return CollectionOut(
        id=c.id,
        title=c.name or "",
        description=c.description or "",
        article_count=len(container.collection_repository.list_entry_items(c.id)),
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _entry_to_dto(entry: DomainEntry, *, sort_order: int = 0) -> ArticleOut:
    body = entry.body or ""
    return ArticleOut(
        id=entry.id,
        title=entry.title or "",
        body=body,
        body_preview=_preview(body),
        tags=entry.tags,
        word_count=_word_count(body),
        char_count=len(body),
        sort_order=sort_order,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _collection_or_404(collection_id: str, container: AppContainer) -> DomainCollection:
    collection = container.collection_repository.get(collection_id)
    if collection is None:
        raise HTTPException(404, "Collection not found")
    return collection


def _cleanup_temp_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


@router.get("", response_model=list[CollectionOut])
def list_collections(
    container: AppContainer = Depends(get_container),
) -> list[CollectionOut]:
    return [
        _collection_to_dto(collection, container=container)
        for collection in container.collection_repository.list_all()
    ]


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(
    data: CollectionCreate,
    container: AppContainer = Depends(get_container),
) -> CollectionOut:
    collection = container.collection_repository.create(
        name=data.title.strip() or "未命名作品集",
        description=data.description,
    )
    return _collection_to_dto(collection, container=container)


@router.get("/for-entry/{entry_id}", response_model=list[CollectionOut])
def list_collections_for_entry(
    entry_id: str,
    container: AppContainer = Depends(get_container),
) -> list[CollectionOut]:
    if container.entry_repository.get(entry_id) is None:
        raise HTTPException(404, "Article not found")
    return [
        _collection_to_dto(collection, container=container)
        for collection in container.collection_repository.list_collections_containing_entry(entry_id)
    ]


@router.post("/for-entry/{entry_id}", response_model=list[CollectionOut])
def add_entry_to_collections(
    entry_id: str,
    data: EntryCollectionsRequest,
    container: AppContainer = Depends(get_container),
) -> list[CollectionOut]:
    if container.entry_repository.get(entry_id) is None:
        raise HTTPException(404, "Article not found")
    for collection_id in dict.fromkeys(data.collection_ids):
        item = container.collection_repository.add_entry(collection_id, entry_id)
        if item is None:
            raise HTTPException(404, f"Collection not found: {collection_id}")
    return list_collections_for_entry(entry_id, container)


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionOut:
    return _collection_to_dto(
        _collection_or_404(collection_id, container),
        container=container,
    )


@router.put("/{collection_id}", response_model=CollectionOut)
def update_collection(
    collection_id: str,
    data: CollectionUpdate,
    container: AppContainer = Depends(get_container),
) -> CollectionOut:
    collection = container.collection_repository.rename(
        collection_id,
        data.title.strip() or "未命名作品集",
    )
    if collection is None:
        raise HTTPException(404, "Collection not found")
    collection = container.collection_repository.update_description(
        collection_id,
        data.description,
    )
    if collection is None:
        raise HTTPException(404, "Collection not found")
    return _collection_to_dto(collection, container=container)


@router.delete("/{collection_id}", status_code=204, response_class=Response)
def delete_collection(
    collection_id: str,
    container: AppContainer = Depends(get_container),
):
    if not container.collection_repository.delete(collection_id):
        raise HTTPException(404, "Collection not found")


@router.get("/{collection_id}/articles", response_model=list[ArticleOut])
def list_collection_articles(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> list[ArticleOut]:
    _collection_or_404(collection_id, container)
    items = {
        item.entry_id: item.sort_order
        for item in container.collection_repository.list_entry_items(collection_id)
    }
    return [
        _entry_to_dto(entry, sort_order=items.get(entry.id, 0))
        for entry in container.collection_repository.list_entries(collection_id)
    ]


@router.post("/{collection_id}/articles", response_model=list[ArticleOut], status_code=201)
def add_collection_articles(
    collection_id: str,
    data: AddArticlesRequest,
    container: AppContainer = Depends(get_container),
) -> list[ArticleOut]:
    _collection_or_404(collection_id, container)
    for entry_id in dict.fromkeys(data.entry_ids):
        item = container.collection_repository.add_entry(collection_id, entry_id)
        if item is None:
            raise HTTPException(404, f"Article not found: {entry_id}")
    return list_collection_articles(collection_id, container)


@router.put("/{collection_id}/articles/order", response_model=list[ArticleOut])
def reorder_collection_articles(
    collection_id: str,
    data: ReorderArticlesRequest,
    container: AppContainer = Depends(get_container),
) -> list[ArticleOut]:
    _collection_or_404(collection_id, container)
    container.collection_repository.reorder_entries(collection_id, data.entry_ids)
    return list_collection_articles(collection_id, container)


@router.delete("/{collection_id}/articles/{entry_id}", status_code=204, response_class=Response)
def remove_collection_article(
    collection_id: str,
    entry_id: str,
    container: AppContainer = Depends(get_container),
):
    _collection_or_404(collection_id, container)
    if not container.collection_repository.remove_entry(collection_id, entry_id):
        raise HTTPException(404, "Article is not in this collection")


@router.get("/{collection_id}/export")
def export_collection(
    collection_id: str,
    format: str = Query("md", pattern="^(txt|md|docx)$"),
    container: AppContainer = Depends(get_container),
):
    _collection_or_404(collection_id, container)
    if format == "txt":
        content = container.collection_export_service.export_collection_txt(collection_id)
        return Response(content, media_type="text/plain; charset=utf-8")
    if format == "md":
        content = container.collection_export_service.export_collection_md(collection_id)
        return Response(content, media_type="text/markdown; charset=utf-8")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.close()
    output = container.collection_export_service.export_collection_docx(
        collection_id,
        tmp.name,
    )
    filename = f"{_collection_or_404(collection_id, container).name or 'collection'}.docx"
    return FileResponse(
        output,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        background=BackgroundTask(_cleanup_temp_file, output),
    )


# Legacy work endpoints are intentionally not exposed in the Tauri MVP UI.
