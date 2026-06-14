"""Library feature: 文脉标本库 (reference passages) + version history.

正确映射 Qt 版 ReferencePassage 的真实字段：
  id, source_title, content, source_author, tags, kind, usage_kind,
  personal_note, created_at, updated_at
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.reference_passage import ReferencePassage as DomainReference

router = APIRouter(prefix="/api/library", tags=["library"])


# ---- DTOs（对齐 Qt 版真实字段）----
class ReferenceOut(BaseModel):
    id: str
    source_title: str          # 出处标题（书名/篇名）
    content: str               # 标本正文（摘录的句子/段落）
    source_author: str         # 作者
    tags: list[str]            # 标签
    kind: str                  # 类型: excerpt 等
    usage_kind: str            # 用途: style/imagery/...
    personal_note: str         # 个人笔记
    created_at: Optional[str]
    updated_at: Optional[str]


class ReferenceCreate(BaseModel):
    source_title: str = ""
    content: str
    source_author: str = ""
    tags: list[str] = []
    kind: str = "excerpt"
    usage_kind: str = "style"
    personal_note: str = ""


class ReferenceUpdate(BaseModel):
    source_title: str
    content: str
    source_author: str = ""
    tags: list[str] = []
    kind: str = "excerpt"
    usage_kind: str = "style"
    personal_note: str = ""


class LibraryStatsOut(BaseModel):
    total: int
    by_usage_kind: dict[str, int]  # 按用途统计


def _tags_to_list(tags) -> list[str]:
    """ReferencePassage.tags 可能是逗号分隔字符串或列表。"""
    if isinstance(tags, list):
        return tags
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return []


def _tags_to_str(tags: list[str]) -> str:
    return ", ".join(t.strip() for t in tags if t.strip())


def _reference_to_dto(r: DomainReference) -> ReferenceOut:
    return ReferenceOut(
        id=r.id,
        source_title=r.source_title or "",
        content=r.content or "",
        source_author=r.source_author or "",
        tags=_tags_to_list(r.tags),
        kind=r.kind or "excerpt",
        usage_kind=r.usage_kind or "style",
        personal_note=r.personal_note or "",
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


# ---- 文脉标本库 (Reference passages) ----
@router.get("/references", response_model=list[ReferenceOut])
def list_references(
    limit: int = 500,
    kind: Optional[str] = None,
    usage_kind: Optional[str] = None,
    container: AppContainer = Depends(get_container),
) -> list[ReferenceOut]:
    refs = container.reference_repository.list_recent(
        limit=limit, kind=kind, usage_kind=usage_kind
    )
    return [_reference_to_dto(r) for r in refs]


@router.get("/references/search", response_model=list[ReferenceOut])
def search_references(
    q: str,
    limit: int = 100,
    container: AppContainer = Depends(get_container),
) -> list[ReferenceOut]:
    refs = container.reference_repository.search(q, limit=limit)
    return [_reference_to_dto(r) for r in refs]


@router.get("/references/{ref_id}", response_model=ReferenceOut)
def get_reference(
    ref_id: str,
    container: AppContainer = Depends(get_container),
) -> ReferenceOut:
    ref = container.reference_repository.get(ref_id)
    if not ref:
        raise HTTPException(404, "Reference not found")
    return _reference_to_dto(ref)


@router.post("/references", response_model=ReferenceOut, status_code=201)
def create_reference(
    data: ReferenceCreate,
    container: AppContainer = Depends(get_container),
) -> ReferenceOut:
    ref = container.reference_repository.create(
        source_title=data.source_title,
        content=data.content,
        source_author=data.source_author,
        tags=_tags_to_str(data.tags),
        kind=data.kind,
        usage_kind=data.usage_kind,
        personal_note=data.personal_note,
    )
    return _reference_to_dto(ref)


@router.put("/references/{ref_id}", response_model=ReferenceOut)
def update_reference(
    ref_id: str,
    data: ReferenceUpdate,
    container: AppContainer = Depends(get_container),
) -> ReferenceOut:
    ref = container.reference_repository.update(
        ref_id,
        source_title=data.source_title,
        content=data.content,
        source_author=data.source_author,
        tags=_tags_to_str(data.tags),
        kind=data.kind,
        usage_kind=data.usage_kind,
        personal_note=data.personal_note,
    )
    if not ref:
        raise HTTPException(404, "Reference not found")
    return _reference_to_dto(ref)


@router.delete("/references/{ref_id}", status_code=204)
def delete_reference(
    ref_id: str,
    container: AppContainer = Depends(get_container),
):
    success = container.reference_repository.delete(ref_id)
    if not success:
        raise HTTPException(404, "Reference not found")


@router.get("/stats", response_model=LibraryStatsOut)
def library_stats(
    container: AppContainer = Depends(get_container),
) -> LibraryStatsOut:
    """获取文脉库统计（总数 + 按用途分类）。"""
    all_refs = container.reference_repository.list_recent(limit=10000)

    # 按 usage_kind 统计
    by_usage: dict[str, int] = {}
    for ref in all_refs:
        kind = ref.usage_kind or "other"
        by_usage[kind] = by_usage.get(kind, 0) + 1

    result = LibraryStatsOut(
        total=len(all_refs),
        by_usage_kind=by_usage,
    )
    print(f"DEBUG: Returning {result.model_dump()}")  # 调试日志
    return result
