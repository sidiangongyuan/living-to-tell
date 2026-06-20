"""Motif star-map feature routes."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.motif import (
    MOTIF_SOURCE_ARTICLE,
    MOTIF_SOURCE_REFERENCE,
    MotifExcerpt,
    MotifGraphEdge,
    MotifGraphNode,
    MotifNode,
)

router = APIRouter(prefix="/api/motifs", tags=["motifs"])

SourceKind = Literal["article", "reference"]


class MotifNodeOut(BaseModel):
    id: str
    name: str
    aliases: list[str]
    note: str
    tags: list[str]
    pinned: bool
    excerpt_count: int
    created_at: Optional[str]
    updated_at: Optional[str]


class MotifNodeCreate(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    note: str = ""
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False


class MotifNodeUpdate(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    note: str = ""
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False


class MotifExcerptOut(BaseModel):
    id: str
    source_kind: SourceKind
    source_id: str
    source_title_snapshot: str
    excerpt_text: str
    note: str
    selection_start: Optional[int]
    selection_end: Optional[int]
    before_context: str
    after_context: str
    motif_ids: list[str]
    motif_names: list[str]
    source_exists: bool
    source_current_title: str
    created_at: Optional[str]
    updated_at: Optional[str]


class MotifExcerptCreate(BaseModel):
    source_kind: SourceKind
    source_id: str
    source_title_snapshot: str = ""
    excerpt_text: str
    note: str = ""
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    before_context: str = ""
    after_context: str = ""
    motif_ids: list[str] = Field(default_factory=list)
    motif_names: list[str] = Field(default_factory=list)


class MotifExcerptLookup(BaseModel):
    source_kind: SourceKind
    source_id: str
    excerpt_text: str = ""
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    before_context: str = ""
    after_context: str = ""


class MotifExcerptMotifsUpdate(BaseModel):
    motif_ids: list[str] = Field(default_factory=list)
    motif_names: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class MotifExcerptMotifsSetResult(BaseModel):
    excerpt: Optional[MotifExcerptOut]
    deleted: bool = False


class MotifGraphNodeOut(BaseModel):
    id: str
    name: str
    excerpt_count: int
    pinned: bool
    is_center: bool


class MotifGraphEdgeOut(BaseModel):
    source_id: str
    target_id: str
    weight: int
    shared_excerpts: int
    shared_sources: int


class MotifGraphOut(BaseModel):
    nodes: list[MotifGraphNodeOut]
    edges: list[MotifGraphEdgeOut]


def _node_to_dto(node: MotifNode) -> MotifNodeOut:
    return MotifNodeOut(
        id=node.id,
        name=node.name,
        aliases=node.aliases,
        note=node.note,
        tags=node.tags,
        pinned=node.pinned,
        excerpt_count=node.excerpt_count,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _excerpt_to_dto(excerpt: MotifExcerpt) -> MotifExcerptOut:
    source_kind = (
        MOTIF_SOURCE_REFERENCE
        if excerpt.source_kind == MOTIF_SOURCE_REFERENCE
        else MOTIF_SOURCE_ARTICLE
    )
    return MotifExcerptOut(
        id=excerpt.id,
        source_kind=source_kind,
        source_id=excerpt.source_id,
        source_title_snapshot=excerpt.source_title_snapshot,
        excerpt_text=excerpt.excerpt_text,
        note=excerpt.note,
        selection_start=excerpt.selection_start,
        selection_end=excerpt.selection_end,
        before_context=excerpt.before_context,
        after_context=excerpt.after_context,
        motif_ids=excerpt.motif_ids,
        motif_names=excerpt.motif_names,
        source_exists=excerpt.source_exists,
        source_current_title=excerpt.source_current_title,
        created_at=excerpt.created_at,
        updated_at=excerpt.updated_at,
    )


def _graph_to_dto(
    nodes: list[MotifGraphNode], edges: list[MotifGraphEdge]
) -> MotifGraphOut:
    return MotifGraphOut(
        nodes=[
            MotifGraphNodeOut(
                id=node.id,
                name=node.name,
                excerpt_count=node.excerpt_count,
                pinned=node.pinned,
                is_center=node.is_center,
            )
            for node in nodes
        ],
        edges=[
            MotifGraphEdgeOut(
                source_id=edge.source_id,
                target_id=edge.target_id,
                weight=edge.weight,
                shared_excerpts=edge.shared_excerpts,
                shared_sources=edge.shared_sources,
            )
            for edge in edges
        ],
    )


def _limit_from_density(density: Optional[int], fallback_limit: int) -> int:
    if density is None:
        return fallback_limit
    safe_density = max(0, min(100, density))
    safe_limit = max(1, fallback_limit)
    minimum = min(12, safe_limit)
    return max(1, round(minimum + (safe_limit - minimum) * (safe_density / 100)))


@router.get("", response_model=list[MotifNodeOut])
def list_motifs(
    q: str = "",
    limit: int = Query(500, le=1000),
    container: AppContainer = Depends(get_container),
) -> list[MotifNodeOut]:
    nodes = container.motif_repository.list_nodes(query=q, limit=limit)
    return [_node_to_dto(node) for node in nodes]


@router.post("", response_model=MotifNodeOut, status_code=201)
def create_motif(
    data: MotifNodeCreate,
    container: AppContainer = Depends(get_container),
) -> MotifNodeOut:
    try:
        node = container.motif_repository.create_node(
            name=data.name,
            aliases=data.aliases,
            note=data.note,
            tags=data.tags,
            pinned=data.pinned,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _node_to_dto(node)


@router.get("/graph", response_model=MotifGraphOut)
def motif_graph(
    q: str = "",
    limit: int = Query(80, ge=1, le=1000),
    density: Optional[int] = Query(None, ge=0, le=100),
    container: AppContainer = Depends(get_container),
) -> MotifGraphOut:
    nodes, edges = container.motif_repository.graph(query=q, limit=_limit_from_density(density, limit))
    return _graph_to_dto(nodes, edges)


@router.post("/excerpts", response_model=MotifExcerptOut, status_code=201)
def create_motif_excerpt(
    data: MotifExcerptCreate,
    container: AppContainer = Depends(get_container),
) -> MotifExcerptOut:
    try:
        excerpt = container.motif_repository.create_excerpt(
            source_kind=data.source_kind,
            source_id=data.source_id,
            source_title_snapshot=data.source_title_snapshot,
            excerpt_text=data.excerpt_text,
            note=data.note,
            selection_start=data.selection_start,
            selection_end=data.selection_end,
            before_context=data.before_context,
            after_context=data.after_context,
            motif_ids=data.motif_ids,
            motif_names=data.motif_names,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _excerpt_to_dto(excerpt)


@router.post("/excerpts/lookup", response_model=MotifExcerptOut)
def lookup_motif_excerpt(
    data: MotifExcerptLookup,
    container: AppContainer = Depends(get_container),
) -> MotifExcerptOut:
    excerpt = container.motif_repository.find_excerpt_for_selection(
        source_kind=data.source_kind,
        source_id=data.source_id,
        selection_start=data.selection_start,
        selection_end=data.selection_end,
        excerpt_text=data.excerpt_text,
        before_context=data.before_context,
        after_context=data.after_context,
    )
    if excerpt is None:
        raise HTTPException(404, "Motif excerpt not found")
    return _excerpt_to_dto(excerpt)


@router.get("/excerpts/source/{source_kind}/{source_id}", response_model=list[MotifExcerptOut])
def list_source_motif_excerpts(
    source_kind: SourceKind,
    source_id: str,
    limit: int = Query(500, ge=1, le=1000),
    container: AppContainer = Depends(get_container),
) -> list[MotifExcerptOut]:
    try:
        excerpts = container.motif_repository.list_excerpts_for_source(
            source_kind,
            source_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return [_excerpt_to_dto(excerpt) for excerpt in excerpts]


@router.post("/excerpts/{excerpt_id}/motifs", response_model=MotifExcerptOut)
def add_motifs_to_excerpt(
    excerpt_id: str,
    data: MotifExcerptMotifsUpdate,
    container: AppContainer = Depends(get_container),
) -> MotifExcerptOut:
    try:
        excerpt = container.motif_repository.add_motifs_to_excerpt(
            excerpt_id,
            motif_ids=data.motif_ids,
            motif_names=data.motif_names,
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if excerpt is None:
        raise HTTPException(404, "Motif excerpt not found")
    return _excerpt_to_dto(excerpt)


@router.put("/excerpts/{excerpt_id}/motifs", response_model=MotifExcerptMotifsSetResult)
def set_motifs_for_excerpt(
    excerpt_id: str,
    data: MotifExcerptMotifsUpdate,
    container: AppContainer = Depends(get_container),
) -> MotifExcerptMotifsSetResult:
    try:
        existed, excerpt = container.motif_repository.set_motifs_for_excerpt(
            excerpt_id,
            motif_ids=data.motif_ids,
            motif_names=data.motif_names,
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not existed:
        raise HTTPException(404, "Motif excerpt not found")
    return MotifExcerptMotifsSetResult(
        excerpt=_excerpt_to_dto(excerpt) if excerpt is not None else None,
        deleted=excerpt is None,
    )


@router.delete("/excerpts/{excerpt_id}/motifs/{motif_id}", status_code=204)
def unlink_motif_from_excerpt(
    excerpt_id: str,
    motif_id: str,
    container: AppContainer = Depends(get_container),
):
    if not container.motif_repository.unlink_motif_from_excerpt(excerpt_id, motif_id):
        raise HTTPException(404, "Motif excerpt link not found")


@router.delete("/excerpts/{excerpt_id}", status_code=204)
def delete_motif_excerpt(
    excerpt_id: str,
    container: AppContainer = Depends(get_container),
):
    if not container.motif_repository.delete_excerpt(excerpt_id):
        raise HTTPException(404, "Motif excerpt not found")


@router.get("/{motif_id}", response_model=MotifNodeOut)
def get_motif(
    motif_id: str,
    container: AppContainer = Depends(get_container),
) -> MotifNodeOut:
    node = container.motif_repository.get_node(motif_id)
    if node is None:
        raise HTTPException(404, "Motif not found")
    return _node_to_dto(node)


@router.put("/{motif_id}", response_model=MotifNodeOut)
def update_motif(
    motif_id: str,
    data: MotifNodeUpdate,
    container: AppContainer = Depends(get_container),
) -> MotifNodeOut:
    try:
        node = container.motif_repository.update_node(
            motif_id,
            name=data.name,
            aliases=data.aliases,
            note=data.note,
            tags=data.tags,
            pinned=data.pinned,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if node is None:
        raise HTTPException(404, "Motif not found")
    return _node_to_dto(node)


@router.delete("/{motif_id}", status_code=204)
def delete_motif(
    motif_id: str,
    container: AppContainer = Depends(get_container),
):
    if not container.motif_repository.delete_node(motif_id):
        raise HTTPException(404, "Motif not found")


@router.get("/{motif_id}/excerpts", response_model=list[MotifExcerptOut])
def list_motif_excerpts(
    motif_id: str,
    limit: int = Query(200, ge=1, le=1000),
    container: AppContainer = Depends(get_container),
) -> list[MotifExcerptOut]:
    if container.motif_repository.get_node(motif_id) is None:
        raise HTTPException(404, "Motif not found")
    excerpts = container.motif_repository.list_excerpts_for_node(
        motif_id, limit=limit
    )
    return [_excerpt_to_dto(excerpt) for excerpt in excerpts]


@router.get("/{motif_id}/graph", response_model=MotifGraphOut)
def motif_local_graph(
    motif_id: str,
    limit: int = Query(32, ge=1, le=300),
    container: AppContainer = Depends(get_container),
) -> MotifGraphOut:
    if container.motif_repository.get_node(motif_id) is None:
        raise HTTPException(404, "Motif not found")
    nodes, edges = container.motif_repository.local_graph(motif_id, limit=limit)
    return _graph_to_dto(nodes, edges)
