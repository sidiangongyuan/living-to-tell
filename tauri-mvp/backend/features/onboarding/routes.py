"""Onboarding utilities such as an explicit disposable sample project."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

SAMPLE_MARKER_KEY = "tauri.onboarding.sample_project.v1"
SAMPLE_TAG = "示例项目"


class SampleProjectState(BaseModel):
    installed: bool
    collection_id: str | None = None
    entry_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    ai_card_ids: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None
    missing_ids: list[str] = Field(default_factory=list)


class SampleProjectActionOut(SampleProjectState):
    action: Literal["created", "already_installed", "removed", "not_installed"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _load_marker(container: AppContainer) -> dict:
    raw = container.settings_repository.get(SAMPLE_MARKER_KEY)
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _save_marker(container: AppContainer, marker: dict) -> None:
    container.settings_repository.set(SAMPLE_MARKER_KEY, json.dumps(marker, ensure_ascii=False))


def _marker_to_state(container: AppContainer, marker: dict) -> SampleProjectState:
    if not marker:
        return SampleProjectState(installed=False)

    collection_id = _string_or_none(marker.get("collection_id"))
    entry_ids = _string_list(marker.get("entry_ids"))
    reference_ids = _string_list(marker.get("reference_ids"))
    ai_card_ids = _string_list(marker.get("ai_card_ids"))
    note_ids = _string_list(marker.get("note_ids"))
    missing: list[str] = []

    if collection_id and container.collection_repository.get(collection_id) is None:
        missing.append(collection_id)
        collection_id = None

    entry_ids = [
        entry_id
        for entry_id in entry_ids
        if _exists_or_missing(container.entry_repository.get(entry_id), entry_id, missing)
    ]
    reference_ids = [
        ref_id
        for ref_id in reference_ids
        if _exists_or_missing(container.reference_repository.get(ref_id), ref_id, missing)
    ]
    ai_card_ids = [
        card_id
        for card_id in ai_card_ids
        if _exists_or_missing(container.ai_card_repository.get(card_id), card_id, missing)
    ]
    note_ids = [
        note_id
        for note_id in note_ids
        if _exists_or_missing(container.entry_writing_note_repository.get(note_id), note_id, missing)
    ]

    installed = bool(collection_id or entry_ids or reference_ids or ai_card_ids or note_ids)
    return SampleProjectState(
        installed=installed,
        collection_id=collection_id,
        entry_ids=entry_ids,
        reference_ids=reference_ids,
        ai_card_ids=ai_card_ids,
        note_ids=note_ids,
        created_at=_string_or_none(marker.get("created_at")),
        missing_ids=missing,
    )


def _exists_or_missing(value: object | None, item_id: str, missing: list[str]) -> bool:
    if value is not None:
        return True
    missing.append(item_id)
    return False


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


@router.get("/sample-project", response_model=SampleProjectState)
def get_sample_project_state(
    container: AppContainer = Depends(get_container),
) -> SampleProjectState:
    """Return whether the explicit local sample project is currently installed."""
    return _marker_to_state(container, _load_marker(container))


@router.post("/sample-project", response_model=SampleProjectActionOut, status_code=201)
def create_sample_project(
    container: AppContainer = Depends(get_container),
) -> SampleProjectActionOut:
    """Create a small, disposable project only after the user asks for it."""
    state = _marker_to_state(container, _load_marker(container))
    if state.installed:
        return SampleProjectActionOut(**state.model_dump(), action="already_installed")

    created_entry_ids: list[str] = []
    created_reference_ids: list[str] = []
    created_ai_card_ids: list[str] = []
    created_note_ids: list[str] = []
    created_collection_id: str | None = None
    try:
        article_one = container.entry_repository.create(
            title="示例｜第一章：雨夜来信",
            body=(
                "　　雨落在旧邮局的玻璃上，像一排排没有寄出的句子。\n\n"
                "　　林澄把信压在掌心里，没有立刻拆开。她知道这封信不是答案，"
                "只是把故事从停滞处向前推了一寸。"
            ),
            tags=[SAMPLE_TAG, "长篇示例", "第一章"],
        )
        created_entry_ids.append(article_one.id)
        article_two = container.entry_repository.create(
            title="示例｜第二章：河岸清单",
            body=(
                "　　第二天清晨，镇上的河雾还没有散。林澄在笔记本上写下三件事："
                "找到寄信人、查清旧邮局的火灾、不要再把往事当作梦。\n\n"
                "　　她写完最后一行，才发现墨水已经洇过纸背。"
            ),
            tags=[SAMPLE_TAG, "长篇示例", "第二章"],
        )
        created_entry_ids.append(article_two.id)

        note = container.entry_writing_note_repository.create(
            entry_id=article_one.id,
            body="示例便签：这一章的目标是让主角主动进入谜团，而不是只被事件推动。",
            pinned=True,
        )
        created_note_ids.append(note.id)

        collection = container.collection_repository.create(
            "示例项目｜雨夜来信",
            "一个可删除的长篇写作示例，用来演示文章、作品集、大纲、文脉和 AI Cards 如何协同。",
        )
        created_collection_id = collection.id
        container.collection_repository.add_entry(collection.id, article_one.id)
        container.collection_repository.add_entry(collection.id, article_two.id)

        outline_one = container.collection_outline_repository.create(
            collection.id,
            title="第一部：信件抵达",
            item_type="part",
            status="drafting",
            summary="主角收到旧友来信，故事从日常转向追索。",
            tags=[SAMPLE_TAG, "结构"],
            target_word_count=8000,
        )
        container.collection_outline_repository.create(
            collection.id,
            title="雨夜来信",
            item_type="chapter",
            status="drafting",
            summary="用一封迟来的信打开悬念，并建立主角的主动选择。",
            parent_id=outline_one.id if outline_one else None,
            entry_id=article_one.id,
            pov="林澄",
            setting="旧邮局",
            timeline="现在时第一晚",
            tags=[SAMPLE_TAG, "悬念", "开端"],
            target_word_count=3500,
        )
        container.collection_outline_repository.create(
            collection.id,
            title="河岸清单",
            item_type="chapter",
            status="idea",
            summary="主角整理线索，把谜团拆成可行动的三个目标。",
            parent_id=outline_one.id if outline_one else None,
            entry_id=article_two.id,
            pov="林澄",
            setting="河岸",
            timeline="次日清晨",
            tags=[SAMPLE_TAG, "行动", "线索"],
            target_word_count=4200,
        )

        reference = container.reference_repository.create(
            source_title="示例文脉｜雨与信",
            source_author="Living to Tell",
            content="雨声、信纸、旧邮局构成了一个低声的召唤场景：外部世界用一件小物推动人物行动。",
            tags=SAMPLE_TAG,
            usage_kind="scene",
            personal_note="可以把它作为场景气氛和叙事功能的拆解样本。",
        )
        created_reference_ids.append(reference.id)

        scene_card = container.ai_card_repository.create(
            kind="scene",
            name="示例｜迟来的信件",
            body=(
                "【场景原型】\n"
                "人物在生活停滞处收到一封迟来的信，信件迫使她重新面对过去。\n\n"
                "【触发条件】\n"
                "关系或谜团停滞；需要一个低成本但有重量的外部触发物。\n\n"
                "【核心冲突】\n"
                "我是否愿意重新进入一段已经被自己封存的往事？\n\n"
                "【关键动作】\n"
                "收到信\n+\n犹豫\n+\n阅读\n+\n列出行动目标\n+\n离开安全区\n\n"
                "【情绪曲线】\n"
                "平静\n+\n不安\n+\n迟疑\n+\n被迫确认\n+\n主动行动\n\n"
                "【叙事功能】\n"
                "打破停滞；启动主线；让主角从被动等待转为主动追索。\n\n"
                "【场景DNA】\n"
                "迟来的信息\n+\n被封存的关系\n+\n小物件触发\n+\n主动离开安全区\n\n"
                "【可替换元素】\n"
                "信件 -> 录音 / 旧照片 / 离线硬盘\n旧邮局 -> 医院档案室 / 废弃车站 / 家族阁楼\n\n"
                "【参考原文（可选）】\n"
                "雨落在旧邮局的玻璃上，像一排排没有寄出的句子。"
            ),
            tags=[SAMPLE_TAG, "场景模块"],
        )
        created_ai_card_ids.append(scene_card.id)

        marker = {
            "created_at": _now_iso(),
            "collection_id": collection.id,
            "entry_ids": [article_one.id, article_two.id],
            "reference_ids": [reference.id],
            "ai_card_ids": [scene_card.id],
            "note_ids": [note.id],
        }
        _save_marker(container, marker)
        state = _marker_to_state(container, marker)
        return SampleProjectActionOut(**state.model_dump(), action="created")
    except Exception as exc:  # noqa: BLE001
        _rollback_created_sample_project(
            container,
            note_ids=created_note_ids,
            ai_card_ids=created_ai_card_ids,
            reference_ids=created_reference_ids,
            collection_id=created_collection_id,
            entry_ids=created_entry_ids,
        )
        raise HTTPException(500, "示例项目创建失败，已回滚已创建的示例内容。") from exc


def _rollback_created_sample_project(
    container: AppContainer,
    *,
    note_ids: list[str],
    ai_card_ids: list[str],
    reference_ids: list[str],
    collection_id: str | None,
    entry_ids: list[str],
) -> None:
    for note_id in note_ids:
        container.entry_writing_note_repository.delete(note_id)
    for card_id in ai_card_ids:
        container.ai_card_repository.delete(card_id)
    for ref_id in reference_ids:
        container.reference_repository.delete(ref_id)
    if collection_id:
        container.collection_repository.delete(collection_id)
    if entry_ids:
        container.entry_repository.delete_many(entry_ids)


@router.delete("/sample-project", response_model=SampleProjectActionOut)
def delete_sample_project(
    container: AppContainer = Depends(get_container),
) -> SampleProjectActionOut:
    """Remove only the sample entities recorded in the marker."""
    marker = _load_marker(container)
    state = _marker_to_state(container, marker)
    if not marker:
        return SampleProjectActionOut(**state.model_dump(), action="not_installed")

    for note_id in _string_list(marker.get("note_ids")):
        container.entry_writing_note_repository.delete(note_id)
    for card_id in _string_list(marker.get("ai_card_ids")):
        container.ai_card_repository.delete(card_id)
    for ref_id in _string_list(marker.get("reference_ids")):
        container.reference_repository.delete(ref_id)
    collection_id = _string_or_none(marker.get("collection_id"))
    if collection_id:
        container.collection_repository.delete(collection_id)
    container.entry_repository.delete_many(_string_list(marker.get("entry_ids")))

    container.settings_repository.delete(SAMPLE_MARKER_KEY)
    return SampleProjectActionOut(installed=False, action="removed")
