"""Dates feature: 日历视图 + 每日统计 + 每日引用。

提供按创建日期的统计、当日条目、每日文脉引用。
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from deps import get_container
from writer.app.container import AppContainer

router = APIRouter(prefix="/api/dates", tags=["dates"])


# ---- DTOs ----
class DailyStat(BaseModel):
    date: str  # ISO format YYYY-MM-DD
    entry_count: int
    word_count: int
    has_curated: bool


class DailyEntrySummary(BaseModel):
    id: str
    title: str
    body_preview: str
    created_at: str
    tags: list[str]
    curation_status: str


class DailyQuote(BaseModel):
    id: str
    text: str
    source_title: str
    source_author: str


def _tags_to_list(tags) -> list[str]:
    if isinstance(tags, list):
        return tags
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return []


# ---- Routes ----
@router.get("/stats", response_model=list[DailyStat])
def get_daily_stats(
    year: int = Query(...),
    month: int = Query(...),
    container: AppContainer = Depends(get_container),
) -> list[DailyStat]:
    """获取某月每日统计（条目数 + 字数 + 是否有策展）。"""
    # daily_stats_for_month 返回 Dict[date, DailyStat]
    stats_map = container.entry_repository.daily_stats_for_month(year, month)
    result = []
    for day, stat in sorted(stats_map.items()):
        result.append(
            DailyStat(
                date=day.isoformat(),
                entry_count=stat.entry_count,
                word_count=stat.total_word_count,
                has_curated=stat.has_curated,
            )
        )
    return result


@router.get("/entries", response_model=list[DailyEntrySummary])
def get_entries_by_date(
    date_str: str = Query(..., description="ISO format YYYY-MM-DD"),
    container: AppContainer = Depends(get_container),
) -> list[DailyEntrySummary]:
    """获取某天创建/更新的所有条目。"""
    target_date = date.fromisoformat(date_str)
    entries = container.entry_repository.list_by_local_date(target_date)
    return [
        DailyEntrySummary(
            id=e.id,
            title=e.title or "无标题",
            body_preview=(e.body or "")[:100],
            created_at=e.created_at or "",
            tags=_tags_to_list(e.tags),
            curation_status=e.curation_status,
        )
        for e in entries
    ]


@router.get("/quote", response_model=Optional[DailyQuote])
def get_daily_quote(
    date_str: str = Query(..., description="ISO format YYYY-MM-DD"),
    container: AppContainer = Depends(get_container),
) -> Optional[DailyQuote]:
    """获取某天的每日引用（从文脉库确定性选取）。"""
    target_date = date.fromisoformat(date_str)
    all_refs = container.reference_repository.list_recent(limit=1000)
    if not all_refs:
        return None

    # 基于日期确定性选取一条
    day_offset = (target_date - date(2024, 1, 1)).days
    selected = all_refs[day_offset % len(all_refs)]

    # 取第一句作为引用
    content = selected.content or ""
    # 按中文句号或英文句号断句
    for sep in ["。", ". ", "\n"]:
        if sep in content:
            quote_text = content.split(sep)[0] + (sep.strip() if sep != "\n" else "")
            break
    else:
        quote_text = content[:200]

    return DailyQuote(
        id=selected.id,
        text=quote_text.strip(),
        source_title=selected.source_title or "",
        source_author=selected.source_author or "",
    )
