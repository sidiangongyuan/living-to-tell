"""Article collection API for reading order, preview, and export."""
from __future__ import annotations

import json
import hashlib
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from deps import get_container
from writer.app.container import AppContainer
from writer.app.settings import SUPPORTED_AI_PROVIDERS, SUPPORTED_WIRE_APIS
from writer.domain.models.ai_config import AiConfig
from writer.domain.models.collection_agent import (
    COLLECTION_AGENT_MODES,
    COLLECTION_AGENT_MEMORY_SECTIONS,
    COLLECTION_AGENT_SCOPE,
    AuthorPortrait,
    AuthorPortraitVersion,
    CollectionAgentAction,
    CollectionAgentDraft,
    CollectionAgentMemory,
    CollectionAgentRun,
    CollectionAgentSession,
    CollectionAgentSettings,
    CollectionAgentStyleSample,
    normalize_collection_agent_memory_section_id,
)
from writer.domain.models.collection_outline import CollectionOutlineItem
from writer.domain.models.collection import Collection as DomainCollection
from writer.domain.models.entry import Entry as DomainEntry
from writer.services.ai.provider_factory import provider_for_config
from writer.services.ai.prompt_builder import PromptBuilder

router = APIRouter(prefix="/api/collections", tags=["collections"])
_AGENT_EXECUTOR = ThreadPoolExecutor(max_workers=3)
_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class CollectionOut(BaseModel):
    id: str
    title: str
    description: str
    project_type: str = "general"
    article_count: int = 0
    created_at: Optional[str]
    updated_at: Optional[str]


class CollectionCreate(BaseModel):
    title: str
    description: str = ""
    project_type: str = "general"


class CollectionUpdate(BaseModel):
    title: str
    description: str = ""
    project_type: str = "general"


class OutlineItemOut(BaseModel):
    id: str
    collection_id: str
    parent_id: Optional[str] = None
    entry_id: Optional[str] = None
    title: str
    item_type: str
    status: str
    summary: str
    notes: str
    pov: str
    setting: str
    timeline: str
    tags: list[str]
    target_word_count: Optional[int] = None
    sort_order: int
    created_at: Optional[str]
    updated_at: Optional[str]


class OutlineItemCreate(BaseModel):
    parent_id: Optional[str] = None
    entry_id: Optional[str] = None
    title: str = ""
    item_type: str = "scene"
    status: str = "idea"
    summary: str = ""
    notes: str = ""
    pov: str = ""
    setting: str = ""
    timeline: str = ""
    tags: list[str] = Field(default_factory=list)
    target_word_count: Optional[int] = None


class OutlineItemUpdate(OutlineItemCreate):
    title: str


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


class ReorderOutlineRequest(BaseModel):
    item_ids: list[str] = Field(default_factory=list)


class EntryCollectionsRequest(BaseModel):
    collection_ids: list[str] = Field(default_factory=list)


class CollectionAgentMemorySectionOut(BaseModel):
    id: str
    title: str
    help: str
    content: str = ""


class CollectionAgentMemoryOut(BaseModel):
    collection_id: str
    sections: list[CollectionAgentMemorySectionOut]
    updated_at: Optional[str] = None


class CollectionAgentMemoryUpdate(BaseModel):
    sections: dict[str, str] = Field(default_factory=dict)


class CollectionAgentSettingsOut(BaseModel):
    collection_id: str
    profile_id: str = "default"
    enabled: bool = True
    active_session_id: Optional[str] = None
    updated_at: Optional[str] = None


class CollectionAgentSettingsUpdate(BaseModel):
    profile_id: str = "default"
    enabled: bool = True


class CollectionAgentSessionOut(BaseModel):
    id: str
    collection_id: str
    thread_id: str
    title: str
    mode: str
    summary: str
    archived: bool
    message_count: int = 0
    run_count: int = 0
    draft_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_message_at: Optional[str] = None


class CollectionAgentSessionCreate(BaseModel):
    title: str = "新会话"
    mode: str = "discuss"


class CollectionAgentSessionUpdate(BaseModel):
    title: Optional[str] = None
    mode: Optional[str] = None
    archived: Optional[bool] = None


class CollectionAgentDraftBrief(BaseModel):
    target_scene: str = ""
    pov: str = ""
    tense: str = ""
    target_length: Optional[int] = Field(default=None, ge=100, le=20000)
    must_happen: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class CollectionAgentDraftOut(BaseModel):
    id: str
    collection_id: str
    session_id: str
    run_id: Optional[str] = None
    parent_draft_id: Optional[str] = None
    title: str
    content: str
    brief: dict[str, Any]
    variant_label: str
    status: str
    target_entry_id: Optional[str] = None
    applied_ref_id: Optional[str] = None
    content_hash: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    applied_at: Optional[str] = None


class CollectionAgentDraftUpdate(BaseModel):
    title: str
    content: str
    brief: dict[str, Any] = Field(default_factory=dict)


class CollectionAgentDraftApply(BaseModel):
    operation: str
    target_entry_id: Optional[str] = None
    article_title: str = ""
    expected_body_hash: str = ""
    selection_start: Optional[int] = Field(default=None, ge=0)
    selection_end: Optional[int] = Field(default=None, ge=0)
    expected_selected_text: str = ""


class CollectionAgentDraftApplyOut(BaseModel):
    draft: CollectionAgentDraftOut
    entry_id: str
    article_title: str
    operation: str
    version_id: Optional[str] = None


class CollectionAgentDraftDeleteMany(BaseModel):
    draft_ids: list[str] = Field(default_factory=list)
    clear_all: bool = False


class CollectionAgentStyleSampleOut(BaseModel):
    id: str
    collection_id: str
    entry_id: str
    original_body: str
    final_body: str
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class CollectionAgentStyleSampleCreate(BaseModel):
    entry_id: str


class AuthorPortraitOut(BaseModel):
    id: str
    tags: list[str]
    summary: str
    evidence_count: int
    completed_style_cycles: int = 0
    reminder_due: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AuthorPortraitUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)
    summary: str = ""


class AuthorPortraitVersionOut(BaseModel):
    id: str
    portrait_id: str
    tags: list[str]
    summary: str
    evidence_count: int
    reason: str
    created_at: Optional[str] = None


class CollectionAgentContextRef(BaseModel):
    kind: str
    ref_id: str


class CollectionAgentReferenceOut(BaseModel):
    kind: str
    ref_id: str
    name: str
    body_preview: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class CollectionAgentMessageOut(BaseModel):
    id: Optional[str] = None
    thread_id: Optional[str] = None
    role: str
    content: str
    timestamp: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CollectionAgentActionOut(BaseModel):
    id: str
    collection_id: str
    run_id: Optional[str] = None
    action_type: str
    status: str
    title: str
    summary: str
    payload: dict[str, Any]
    preview: dict[str, Any]
    reason: str
    risk: str
    applied_ref_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    applied_at: Optional[str] = None


class CollectionAgentRunOut(BaseModel):
    id: str
    collection_id: str
    thread_id: Optional[str] = None
    status: str
    stage: str
    stage_label: str
    request: dict[str, Any]
    result: dict[str, Any]
    error: str
    profile_id: str
    provider: Optional[str] = None
    model: Optional[str] = None
    transport: Optional[str] = None
    session_id: Optional[str] = None
    mode: str = "discuss"
    draft_id: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    actions: list[CollectionAgentActionOut] = Field(default_factory=list)


class CollectionAgentStateOut(BaseModel):
    settings: CollectionAgentSettingsOut
    memory: CollectionAgentMemoryOut
    thread_id: Optional[str] = None
    messages: list[CollectionAgentMessageOut] = Field(default_factory=list)
    runs: list[CollectionAgentRunOut] = Field(default_factory=list)
    actions: list[CollectionAgentActionOut] = Field(default_factory=list)
    profiles: list[dict[str, str]] = Field(default_factory=list)
    sessions: list[CollectionAgentSessionOut] = Field(default_factory=list)
    active_session_id: Optional[str] = None
    drafts: list[CollectionAgentDraftOut] = Field(default_factory=list)
    author_portrait: Optional[AuthorPortraitOut] = None
    style_samples: list[CollectionAgentStyleSampleOut] = Field(default_factory=list)
    active_run: Optional[CollectionAgentRunOut] = None


class CollectionAgentRunCreate(BaseModel):
    message: str
    task_type: str = "free_chat"
    context_refs: list[CollectionAgentContextRef] = Field(default_factory=list)
    request_web_context: bool = False
    profile_id: Optional[str] = None
    session_id: Optional[str] = None
    mode: str = "discuss"
    draft_brief: Optional[CollectionAgentDraftBrief] = None
    parent_draft_id: Optional[str] = None


class CollectionAgentChatCreate(CollectionAgentRunCreate):
    pass


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
        project_type=c.project_type or "general",
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


def _outline_to_dto(item: CollectionOutlineItem) -> OutlineItemOut:
    return OutlineItemOut(
        id=item.id,
        collection_id=item.collection_id,
        parent_id=item.parent_id,
        entry_id=item.entry_id,
        title=item.title,
        item_type=item.item_type,
        status=item.status,
        summary=item.summary,
        notes=item.notes,
        pov=item.pov,
        setting=item.setting,
        timeline=item.timeline,
        tags=item.tags,
        target_word_count=item.target_word_count,
        sort_order=item.sort_order,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _memory_to_dto(memory: CollectionAgentMemory) -> CollectionAgentMemoryOut:
    sections = [
        CollectionAgentMemorySectionOut(
            id=section_id,
            title=title,
            help=help_text,
            content=memory.sections.get(section_id, ""),
        )
        for section_id, title, help_text in COLLECTION_AGENT_MEMORY_SECTIONS
    ]
    return CollectionAgentMemoryOut(
        collection_id=memory.collection_id,
        sections=sections,
        updated_at=memory.updated_at,
    )


def _settings_to_dto(settings: CollectionAgentSettings) -> CollectionAgentSettingsOut:
    return CollectionAgentSettingsOut(
        collection_id=settings.collection_id,
        profile_id=settings.profile_id,
        enabled=settings.enabled,
        active_session_id=settings.active_session_id,
        updated_at=settings.updated_at,
    )


def _session_to_dto(
    session: CollectionAgentSession,
    container: AppContainer,
) -> CollectionAgentSessionOut:
    counts = container.collection_agent_repository.session_counts(session.id)
    return CollectionAgentSessionOut(
        id=session.id,
        collection_id=session.collection_id,
        thread_id=session.thread_id,
        title=session.title,
        mode=session.mode,
        summary=session.summary,
        archived=session.archived,
        message_count=counts["messages"],
        run_count=counts["runs"],
        draft_count=counts["drafts"],
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_message_at=session.last_message_at,
    )


def _draft_to_dto(draft: CollectionAgentDraft) -> CollectionAgentDraftOut:
    return CollectionAgentDraftOut(
        id=draft.id,
        collection_id=draft.collection_id,
        session_id=draft.session_id,
        run_id=draft.run_id,
        parent_draft_id=draft.parent_draft_id,
        title=draft.title,
        content=draft.content,
        brief=draft.brief,
        variant_label=draft.variant_label,
        status=draft.status,
        target_entry_id=draft.target_entry_id,
        applied_ref_id=draft.applied_ref_id,
        content_hash=draft.content_hash,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        applied_at=draft.applied_at,
    )


def _style_sample_to_dto(sample: CollectionAgentStyleSample) -> CollectionAgentStyleSampleOut:
    return CollectionAgentStyleSampleOut(
        id=sample.id,
        collection_id=sample.collection_id,
        entry_id=sample.entry_id,
        original_body=sample.original_body,
        final_body=sample.final_body,
        status=sample.status,
        created_at=sample.created_at,
        completed_at=sample.completed_at,
    )


def _portrait_to_dto(
    portrait: AuthorPortrait,
    *,
    completed_style_cycles: int = 0,
) -> AuthorPortraitOut:
    return AuthorPortraitOut(
        id=portrait.id,
        tags=portrait.tags,
        summary=portrait.summary,
        evidence_count=portrait.evidence_count,
        completed_style_cycles=completed_style_cycles,
        reminder_due=(completed_style_cycles - portrait.evidence_count) >= 3,
        created_at=portrait.created_at,
        updated_at=portrait.updated_at,
    )


def _portrait_version_to_dto(version: AuthorPortraitVersion) -> AuthorPortraitVersionOut:
    return AuthorPortraitVersionOut(
        id=version.id,
        portrait_id=version.portrait_id,
        tags=version.tags,
        summary=version.summary,
        evidence_count=version.evidence_count,
        reason=version.reason,
        created_at=version.created_at,
    )


def _message_to_dto(message: Any) -> CollectionAgentMessageOut:
    try:
        meta = json.loads(message.meta_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        meta = {}
    return CollectionAgentMessageOut(
        id=message.id,
        thread_id=message.thread_id,
        role=message.role,
        content=message.content,
        timestamp=message.created_at,
        meta=meta if isinstance(meta, dict) else {},
    )


def _action_to_dto(action: CollectionAgentAction) -> CollectionAgentActionOut:
    return CollectionAgentActionOut(
        id=action.id,
        collection_id=action.collection_id,
        run_id=action.run_id,
        action_type=action.action_type,
        status=action.status,
        title=action.title,
        summary=action.summary,
        payload=action.payload,
        preview=action.preview,
        reason=action.reason,
        risk=action.risk,
        applied_ref_id=action.applied_ref_id,
        created_at=action.created_at,
        updated_at=action.updated_at,
        applied_at=action.applied_at,
    )


def _run_to_dto(run: CollectionAgentRun, container: AppContainer) -> CollectionAgentRunOut:
    actions = container.collection_agent_repository.list_actions(
        run.collection_id,
        limit=100,
    )
    run_actions = [action for action in actions if action.run_id == run.id]
    return CollectionAgentRunOut(
        id=run.id,
        collection_id=run.collection_id,
        thread_id=run.thread_id,
        status=run.status,
        stage=run.stage,
        stage_label=run.stage_label,
        request=run.request,
        result=run.result,
        error=run.error,
        profile_id=run.profile_id,
        provider=run.provider,
        model=run.model,
        transport=run.transport,
        session_id=run.session_id,
        mode=run.mode,
        draft_id=run.draft_id,
        created_at=run.created_at,
        started_at=run.started_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
        actions=[_action_to_dto(action) for action in run_actions],
    )


def _collection_or_404(collection_id: str, container: AppContainer) -> DomainCollection:
    collection = container.collection_repository.get(collection_id)
    if collection is None:
        raise HTTPException(404, "Collection not found")
    return collection


def _friendly_ai_error(exc: Exception | str) -> str:
    raw = str(exc).strip()
    lowered = raw.lower()
    if not raw:
        return "AI 请求失败，请稍后重试。"
    if "<!doctype html" in lowered or "<html" in lowered:
        return "AI 服务返回了网页错误页，请检查接口协议、模型权限和密钥。"
    if "http 403" in lowered or "forbidden" in lowered:
        return "AI 服务拒绝了当前请求，可能是模型无权限、密钥无效或接口协议不匹配。"
    if "failed to fetch" in lowered:
        return "后台服务正在启动或连接中，请稍后重试；如果持续出现，请重启应用。"
    if "traceback" in lowered:
        return "AI 请求失败，后台返回了异常信息。请检查模型配置后重试。"
    raw = re.sub(r"sk-[A-Za-z0-9]{12,}", "sk-***", raw)
    return raw[:260].rstrip() + ("..." if len(raw) > 260 else "")


def _parse_json_lenient(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    fenced = _JSON_FENCE.search(text)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _profile_options(container: AppContainer) -> list[dict[str, str]]:
    options = [{"id": "default", "name": "默认配置"}]
    for raw in container.settings.load_ai_provider_profiles():
        profile_id = str(raw.get("id") or "").strip()
        name = str(raw.get("name") or "").strip()
        if profile_id and name and bool(raw.get("enabled", True)):
            options.append({"id": profile_id, "name": name})
    return options


def _ensure_agent_session(
    collection: DomainCollection,
    container: AppContainer,
    *,
    requested_session_id: Optional[str] = None,
) -> CollectionAgentSession:
    repo = container.collection_agent_repository
    sessions = repo.list_sessions(collection.id, include_archived=True)
    if not sessions:
        legacy_thread = container.ai_thread_repository.latest_for_scope(
            COLLECTION_AGENT_SCOPE,
            collection.id,
        )
        had_legacy = legacy_thread is not None
        thread = legacy_thread or container.ai_thread_repository.create(
            scope_kind=COLLECTION_AGENT_SCOPE,
            scope_id=collection.id,
            title=f"{collection.name or '作品集'} Agent",
        )
        session = repo.create_session(
            collection.id,
            thread_id=thread.id,
            title="旧 Agent 会话" if had_legacy else "共同构思",
            mode="discuss",
        )
        repo.backfill_session_for_thread(thread.id, session.id)
        repo.set_active_session(collection.id, session.id)
        return session

    by_id = {item.id: item for item in sessions}
    requested = by_id.get((requested_session_id or "").strip())
    if requested is not None and not requested.archived:
        repo.set_active_session(collection.id, requested.id)
        return requested
    settings = repo.get_settings(collection.id)
    active = by_id.get(settings.active_session_id or "")
    if active is not None and not active.archived:
        return active
    visible = [item for item in sessions if not item.archived]
    session = visible[0] if visible else sessions[0]
    if session.archived:
        session = repo.update_session(session.id, archived=False) or session
    repo.set_active_session(collection.id, session.id)
    return session


def _collection_agent_state(
    collection_id: str,
    container: AppContainer,
    *,
    session_id: Optional[str] = None,
) -> CollectionAgentStateOut:
    collection = _collection_or_404(collection_id, container)
    active_session = _ensure_agent_session(
        collection,
        container,
        requested_session_id=session_id,
    )
    settings = container.collection_agent_repository.get_settings(collection_id)
    memory = container.collection_agent_repository.get_memory(collection_id)
    thread = container.ai_thread_repository.get(active_session.thread_id)
    if thread is None:
        raise HTTPException(409, "当前 Agent 会话的数据已损坏，请新建会话。")
    runs = container.collection_agent_repository.list_runs(
        collection_id,
        session_id=active_session.id,
        limit=60,
    )
    actions = container.collection_agent_repository.list_actions(collection_id, limit=80)
    sessions = container.collection_agent_repository.list_sessions(
        collection_id,
        include_archived=True,
    )
    drafts = container.collection_agent_repository.list_drafts(collection_id, limit=120)
    samples = container.collection_agent_repository.list_style_samples(collection_id)
    completed_cycles = container.collection_agent_repository.count_completed_style_samples()
    portrait = container.collection_agent_repository.get_author_portrait()
    global_active_run = container.collection_agent_repository.get_active_run(collection_id)
    return CollectionAgentStateOut(
        settings=_settings_to_dto(settings),
        memory=_memory_to_dto(memory),
        thread_id=thread.id,
        messages=[
            _message_to_dto(message)
            for message in container.ai_thread_repository.list_messages(thread.id, limit=120)
        ],
        runs=[_run_to_dto(run, container) for run in runs],
        actions=[_action_to_dto(action) for action in actions],
        profiles=_profile_options(container),
        sessions=[_session_to_dto(item, container) for item in sessions],
        active_session_id=active_session.id,
        drafts=[_draft_to_dto(draft) for draft in drafts],
        author_portrait=_portrait_to_dto(
            portrait,
            completed_style_cycles=completed_cycles,
        ),
        style_samples=[_style_sample_to_dto(sample) for sample in samples],
        active_run=_run_to_dto(global_active_run, container) if global_active_run else None,
    )


def _profile_config(profile_id: str, container: AppContainer) -> tuple[str, Optional[AiConfig], str]:
    normalized_id = (profile_id or "default").strip() or "default"
    if normalized_id == "default":
        return "默认配置", container.settings.load_ai_config(), ""
    for raw in container.settings.load_ai_provider_profiles():
        raw_id = str(raw.get("id") or "").strip()
        if raw_id != normalized_id:
            continue
        name = str(raw.get("name") or "").strip() or "AI 配置档案"
        if not bool(raw.get("enabled", True)):
            return name, None, "这个 AI 配置档案已停用，请到设置页启用后再试。"
        provider = str(raw.get("provider_name") or "").strip().lower()
        wire_api = str(raw.get("wire_api") or "responses").strip().lower()
        if provider not in SUPPORTED_AI_PROVIDERS or wire_api not in SUPPORTED_WIRE_APIS:
            return name, None, "这个 AI 配置档案已失效，请到设置页重新保存。"
        model = str(raw.get("model") or "").strip()
        if not model:
            return name, None, "这个 AI 配置档案没有填写模型。"
        return name, AiConfig(
            provider_name=provider,
            base_url=str(raw.get("base_url") or "").strip() or None,
            wire_api=wire_api,
            model=model,
            api_key_source=str(raw.get("api_key_source") or "env:OPENAI_API_KEY").strip(),
            gemini_cli_proxy=str(raw.get("gemini_cli_proxy") or "").strip() or None,
        ), ""
    return "已删除的配置档案", None, "这个 AI 配置档案已不存在，请在设置页刷新配置。"


def _truncate(value: str, limit: int) -> str:
    text = (value or "").strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def _context_ref_key(ref: CollectionAgentContextRef) -> tuple[str, str]:
    return ((ref.kind or "").strip(), (ref.ref_id or "").strip())


def _agent_reference_to_attachment(
    ref: CollectionAgentContextRef,
    container: AppContainer,
) -> Optional[dict[str, str]]:
    kind, ref_id = _context_ref_key(ref)
    if not kind or not ref_id:
        return None
    if kind == "outline":
        item = container.collection_outline_repository.get(ref_id)
        if item is None:
            return None
        parts = [
            f"标题：{item.title}",
            f"类型：{item.item_type}",
            f"状态：{item.status}",
            f"摘要：{item.summary}",
            f"备注：{item.notes}",
            f"视角：{item.pov}",
            f"时间线：{item.timeline}",
            f"地点：{item.setting}",
            f"标签：{', '.join(item.tags)}",
        ]
        if item.entry_id:
            entry = container.entry_repository.get(item.entry_id)
            if entry is not None:
                parts.append(f"关联文章：{entry.title}\n{_truncate(entry.body, 6000)}")
        return {"kind": kind, "ref_id": ref_id, "name": item.title or "结构节点", "body": "\n".join(parts)}
    if kind == "article":
        entry = container.entry_repository.get(ref_id)
        if entry is None:
            return None
        return {"kind": kind, "ref_id": ref_id, "name": entry.title or "未命名文章", "body": _truncate(entry.body, 8000)}
    if kind == "ai_card":
        card = container.ai_card_repository.get(ref_id)
        if card is None:
            return None
        return {"kind": kind, "ref_id": ref_id, "name": card.name or "AI 卡片", "body": _truncate(card.body, 3000)}
    if kind == "motif":
        node = container.motif_repository.get_node(ref_id)
        if node is None:
            return None
        body = json.dumps(node.profile, ensure_ascii=False) if node.profile else node.note
        return {"kind": kind, "ref_id": ref_id, "name": node.name, "body": _truncate(body, 3000)}
    if kind == "reference":
        passage = container.reference_repository.get(ref_id)
        if passage is None:
            return None
        title = passage.source_title or "文脉标本"
        body = f"作者：{passage.source_author}\n标题：{passage.source_title}\n内容：{passage.content}\n个人备注：{passage.personal_note}"
        return {"kind": kind, "ref_id": ref_id, "name": title, "body": _truncate(body, 3000)}
    return None


def _outline_path_map(items: list[CollectionOutlineItem]) -> dict[str, str]:
    by_parent: dict[Optional[str], list[CollectionOutlineItem]] = {}
    for item in sorted(items, key=lambda row: (row.sort_order, row.created_at or "")):
        by_parent.setdefault(item.parent_id, []).append(item)
    paths: dict[str, str] = {}

    def visit(parent_id: Optional[str], prefix: list[int]) -> None:
        for index, item in enumerate(by_parent.get(parent_id, []), start=1):
            path = [*prefix, index]
            paths[item.id] = ".".join(str(part) for part in path)
            visit(item.id, path)

    visit(None, [])
    return paths


def _build_collection_context_pack(
    collection_id: str,
    *,
    refs: list[CollectionAgentContextRef],
    request_web_context: bool,
    include_style_evidence: bool = False,
    container: AppContainer,
) -> tuple[str, list[dict[str, str]]]:
    collection = _collection_or_404(collection_id, container)
    memory = container.collection_agent_repository.get_memory(collection_id)
    outline = container.collection_outline_repository.list_for_collection(collection_id)
    articles = container.collection_repository.list_entries(collection_id)
    article_by_id = {entry.id: entry for entry in articles}
    linked_article_ids = {item.entry_id for item in outline if item.entry_id}
    path_map = _outline_path_map(outline)

    blocks = [
        f"作品集：{collection.name or '未命名作品集'}",
        f"项目类型：{collection.project_type}",
        f"描述：{collection.description or '无'}",
        "",
        "项目圣经：",
    ]
    for section_id, title, _help in COLLECTION_AGENT_MEMORY_SECTIONS:
        blocks.append(f"- {title}：{memory.sections.get(section_id, '').strip() or '未记录'}")

    portrait = container.collection_agent_repository.get_author_portrait()
    blocks.append("\n作者画像（跨作品、由作者确认）：")
    blocks.append(f"- 标签：{', '.join(portrait.tags) if portrait.tags else '未建立'}")
    blocks.append(f"- 描述：{portrait.summary or '未建立'}")

    blocks.append("\n书稿结构索引：")
    if outline:
        for item in outline[:160]:
            linked = article_by_id.get(item.entry_id or "")
            linked_label = f"；关联文章：{linked.title}" if linked else ""
            bits = [
                f"{path_map.get(item.id, '?')} [{item.item_type}/{item.status}] {item.title}{linked_label}",
                f"摘要：{_truncate(item.summary, 240) or '无'}",
            ]
            if item.notes:
                bits.append(f"备注：{_truncate(item.notes, 180)}")
            if item.pov or item.timeline or item.setting:
                bits.append(f"视角/时间/地点：{item.pov or '-'} / {item.timeline or '-'} / {item.setting or '-'}")
            blocks.append("\n".join(bits))
    else:
        blocks.append("无结构节点。")

    unplanned = [entry for entry in articles if entry.id not in linked_article_ids]
    blocks.append("\n未编排文章：")
    if unplanned:
        for index, entry in enumerate(unplanned[:80], start=1):
            blocks.append(f"{index}. {entry.title or '未命名文章'}：{_truncate(entry.body, 180)}")
    else:
        blocks.append("无。")

    blocks.append("\n本轮显式引用：")
    attachments: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        key = _context_ref_key(ref)
        if key in seen:
            continue
        seen.add(key)
        attachment = _agent_reference_to_attachment(ref, container)
        if attachment is None:
            continue
        attachments.append(attachment)
        blocks.append(f"--- [{attachment['kind']}] {attachment['name']} ---\n{attachment['body']}")
    if not attachments:
        blocks.append("无。")

    if request_web_context:
        blocks.append(
            "\n用户本轮请求可能需要联网。若当前模型具备联网/检索能力，可以使用；"
            "必须标注来源需核对，不能假装软件已完成网页核验。"
        )
    if include_style_evidence:
        samples = container.collection_agent_repository.list_completed_style_samples(limit=6)
        blocks.append("\n已完成的写作闭环样本（仅用于作者画像证据）：")
        if not samples:
            blocks.append("无。")
        for index, sample in enumerate(samples, start=1):
            entry = container.entry_repository.get(sample.entry_id)
            blocks.append(
                f"样本 {index}：{entry.title if entry else '已删除文章'}\n"
                f"作者原稿：{_truncate(sample.original_body, 5000)}\n"
                f"最终确认稿：{_truncate(sample.final_body, 5000)}"
            )
    return "\n\n".join(blocks), attachments


def _agent_system_prompt(mode: str, task_type: str) -> str:
    mode_guidance = {
        "discuss": (
            "当前是讨论模式。和作者共同构思、追问、比较方案，不急着替作者定案。"
            "作品从零开始时一次只问一个关键问题；作者说‘先给方案’时，先给 2 到 4 个有差异的方向再追问。"
        ),
        "plan": (
            "当前是规划模式。把想法整理成可执行的分部、章节、场景、伏笔或下一步，"
            "区分已确认事实和待决定问题。"
        ),
        "draft": (
            "当前是草稿模式。根据本轮场景简报写一份可编辑的主要草稿。"
            "草稿只是候选稿，绝不能声称已写入文章；正文必须放在 draft.content。"
        ),
        "review": (
            "当前是审校模式。检查连续性、人物动机、节奏、叙事承诺和硬逻辑问题。"
            "不要把个人偏好包装成错误；优先指出可定位、有证据的问题。"
        ),
    }.get(mode, "")
    portrait_guidance = ""
    if task_type == "author_portrait":
        portrait_guidance = (
            "本轮是作者画像整理。只能依据作者原稿与最终确认稿之间反复保留的风格证据，"
            "生成 update_author_portrait 提案；不能把被拒绝的 Agent 文本或外部引用当成作者风格。"
        )
    return (
        "你是写作软件中的作品集共创 Agent，是书稿总编、共同构思者和连续性助手。"
        "你服务作者的意图与审美，可以讨论、规划、写候选草稿和审校，但不得擅自改正文或把建议当成 canon。"
        "除非出现明确的连续性、canon 或逻辑冲突，否则以跟随作者为主。"
        + mode_guidance
        + portrait_guidance
        + "所有长期记忆和结构写回都必须生成可确认提案。"
        "只输出一个 JSON 对象，不要 Markdown 代码块。"
        "JSON schema: {"
        "\"answer\": string, \"evidence\": string[], \"next_steps\": string[], "
        "\"conflicts\": [{\"title\":string,\"existing\":string,\"proposed\":string,\"reason\":string}], "
        "\"draft\": null|{\"title\":string,\"content\":string,\"variant_label\":string}, "
        "\"actions\": [{"
        "\"action_type\": \"update_memory\"|\"create_outline_item\"|\"update_outline_item\"|\"create_article_note\"|\"update_author_portrait\", "
        "\"title\": string, \"summary\": string, \"payload\": object, "
        "\"preview\": object, \"reason\": string, \"risk\": string"
        "}]}。"
        "动作限制：update_memory 只能包含 section_id, content, mode(append|replace)；"
        "其中 section_id 必须严格使用以下一个固定值："
        "project_core(项目核心)、characters(人物与关系)、timeline(时间线)、world(地点与世界)、"
        "style(主题与风格)、foreshadowing(伏笔与线索)、decisions(决策记录)、"
        "open_questions(未解决问题)；不要自行创造新的栏目名；"
        "create_outline_item 只能包含 title,item_type,status,summary,notes,parent_id,entry_id,pov,setting,timeline,tags,target_word_count；"
        "update_outline_item 必须包含 item_id，并只修改结构节点元数据；"
        "create_article_note 必须包含 entry_id, body, pinned；"
        "update_author_portrait 只能包含 tags, summary, evidence_count。"
        "禁止提出直接修改文章正文的 action。"
    )


def _agent_user_prompt(
    message: str,
    context_pack: str,
    *,
    draft_brief: Optional[dict[str, Any]] = None,
) -> str:
    brief_text = ""
    if draft_brief:
        brief_text = "\n本轮场景简报：\n" + json.dumps(draft_brief, ensure_ascii=False, indent=2)
    return f"""用户请求：
{message.strip()}
{brief_text}

作品集上下文包：
{context_pack}

请给出具体、可执行、克制的总编式回答。若需要写回数据，只放入 actions；不要假装已经写入。
"""


def _normalize_agent_actions(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    actions: list[dict[str, Any]] = []
    for item in raw[:12]:
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("action_type") or "").strip()
        payload = item.get("payload")
        preview = item.get("preview")
        title = str(item.get("title") or "Agent 提案").strip()[:120]
        summary = str(item.get("summary") or "").strip()[:800]
        if action_type not in {
            "update_memory",
            "create_outline_item",
            "update_outline_item",
            "create_article_note",
            "update_author_portrait",
        }:
            continue
        if not isinstance(payload, dict):
            continue
        if action_type == "update_memory":
            section_id = normalize_collection_agent_memory_section_id(
                str(payload.get("section_id") or ""),
                title,
                summary,
            )
            if section_id is None:
                continue
            payload = {**payload, "section_id": section_id}
        actions.append(
            {
                "action_type": action_type,
                "title": title,
                "summary": summary,
                "payload": payload,
                "preview": preview if isinstance(preview, dict) else payload,
                "reason": str(item.get("reason") or "").strip()[:800],
                "risk": str(item.get("risk") or "").strip()[:800],
            }
        )
    return actions


def _agent_result_from_response(
    content: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], Optional[dict[str, str]]]:
    parsed = _parse_json_lenient(content)
    if parsed is None:
        return {
            "answer": content.strip(),
            "evidence": [],
            "next_steps": [],
            "conflicts": [],
            "structured": False,
        }, [], None
    answer = str(parsed.get("answer") or "").strip() or content.strip()
    evidence = parsed.get("evidence")
    next_steps = parsed.get("next_steps")
    raw_conflicts = parsed.get("conflicts")
    conflicts: list[dict[str, str]] = []
    if isinstance(raw_conflicts, list):
        for item in raw_conflicts[:8]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "Canon 冲突").strip()
            existing = str(item.get("existing") or "").strip()
            proposed = str(item.get("proposed") or "").strip()
            reason = str(item.get("reason") or "").strip()
            if existing or proposed:
                conflicts.append(
                    {
                        "title": title[:160],
                        "existing": existing[:1200],
                        "proposed": proposed[:1200],
                        "reason": reason[:800],
                    }
                )
    result = {
        "answer": answer,
        "evidence": [str(item).strip() for item in evidence if str(item).strip()][:12] if isinstance(evidence, list) else [],
        "next_steps": [str(item).strip() for item in next_steps if str(item).strip()][:12] if isinstance(next_steps, list) else [],
        "conflicts": conflicts,
        "structured": True,
    }
    raw_draft = parsed.get("draft")
    draft: Optional[dict[str, str]] = None
    if isinstance(raw_draft, dict):
        draft_content = str(raw_draft.get("content") or "").strip()
        if draft_content:
            draft = {
                "title": str(raw_draft.get("title") or "未命名场景草稿").strip()[:160],
                "content": draft_content,
                "variant_label": str(raw_draft.get("variant_label") or "").strip()[:80],
            }
    return result, _normalize_agent_actions(parsed.get("actions")), draft


def _estimate_agent_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def _compact_session_locally(
    session: CollectionAgentSession,
    messages: list[Any],
    container: AppContainer,
    *,
    force: bool = False,
) -> tuple[str, bool]:
    total_tokens = sum(_estimate_agent_tokens(message.content) for message in messages)
    if total_tokens < 12000 and len(messages) <= 12 and not force:
        return session.summary, False
    older = messages[:-12]
    if not older:
        return session.summary, False
    lines: list[str] = []
    if session.summary.strip():
        lines.append(session.summary.strip())
    lines.append("较早会话的工作摘要：")
    for message in older[-30:]:
        role = "作者" if message.role == "user" else "Agent"
        clean = " ".join((message.content or "").split())
        if clean:
            lines.append(f"- {role}：{_truncate(clean, 240)}")
    summary = "\n".join(lines)[-6000:]
    container.collection_agent_repository.save_session_summary(session.id, summary)
    return summary, True


def _session_provider_history(
    session: CollectionAgentSession,
    container: AppContainer,
) -> tuple[str, list[dict[str, str]], bool]:
    messages = container.ai_thread_repository.list_messages(session.thread_id)
    summary, compacted = _compact_session_locally(session, messages, container)
    history = [
        {"role": message.role, "content": message.content}
        for message in messages[-12:]
        if message.role in {"user", "assistant"} and (message.content or "").strip()
    ]
    return summary, history, compacted


def _run_cancelled(run_id: str, container: AppContainer) -> bool:
    run = container.collection_agent_repository.get_run(run_id)
    return run is None or run.status == "cancelled"


def _run_collection_agent(run_id: str, container: AppContainer) -> None:
    run = container.collection_agent_repository.get_run(run_id)
    if run is None:
        return
    try:
        container.collection_agent_repository.mark_run_started(run_id)
        request = run.request
        message = str(request.get("message") or "").strip()
        context_refs = [
            CollectionAgentContextRef(**item)
            for item in request.get("context_refs", [])
            if isinstance(item, dict)
        ]
        profile_id = str(request.get("profile_id") or run.profile_id or "default").strip() or "default"
        request_web_context = bool(request.get("request_web_context", False))
        mode = str(request.get("mode") or run.mode or "discuss").strip()
        if mode not in COLLECTION_AGENT_MODES:
            mode = "discuss"
        task_type = str(request.get("task_type") or "free_chat").strip()
        draft_brief = request.get("draft_brief")
        if not isinstance(draft_brief, dict):
            draft_brief = None
        _profile_name, config, profile_error = _profile_config(profile_id, container)
        if config is None:
            raise RuntimeError(profile_error or "这个 AI 配置档案不可用。")

        if _run_cancelled(run_id, container):
            return
        container.collection_agent_repository.update_run_stage(run_id, "preparing_context")
        collection = _collection_or_404(run.collection_id, container)
        session = (
            container.collection_agent_repository.get_session(run.session_id or "")
            or _ensure_agent_session(collection, container)
        )
        session_summary, provider_history, compacted = _session_provider_history(
            session,
            container,
        )
        context_pack, attachments = _build_collection_context_pack(
            run.collection_id,
            refs=context_refs,
            request_web_context=request_web_context,
            include_style_evidence=task_type == "author_portrait",
            container=container,
        )
        context_pack = _truncate(context_pack, 42000)
        context_manifest = {
            "collection": collection.name or "未命名作品集",
            "session_id": session.id,
            "mode": mode,
            "memory": True,
            "outline_items": len(container.collection_outline_repository.list_for_collection(run.collection_id)),
            "explicit_refs": [
                {"kind": item["kind"], "ref_id": item["ref_id"], "name": item["name"]}
                for item in attachments
            ],
            "recent_turns": len(provider_history) // 2,
            "summary_used": bool(session_summary.strip()),
            "compacted_now": compacted,
            "whole_book_body": False,
        }
        meta = json.dumps(
            {
                "agent_run_id": run_id,
                "session_id": session.id,
                "mode": mode,
                "context_refs": request.get("context_refs", []),
                "attachments": [
                    {"kind": item["kind"], "ref_id": item["ref_id"], "name": item["name"]}
                    for item in attachments
                ],
            },
            ensure_ascii=False,
        )
        user_message = container.ai_thread_repository.add_message(
            thread_id=run.thread_id or "",
            role="user",
            content=message,
            meta_json=meta,
        )
        container.collection_agent_repository.attach_user_message(run_id, user_message.id)
        container.collection_agent_repository.touch_session(session.id)
        if session.title == "新会话":
            container.collection_agent_repository.update_session(
                session.id,
                title=_truncate(message.replace("\n", " "), 28) or "新会话",
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _agent_system_prompt(mode, task_type)},
        ]
        if session_summary.strip():
            messages.append(
                {
                    "role": "system",
                    "content": "当前会话的可见工作摘要（不是项目 canon）：\n" + session_summary,
                }
            )
        messages.extend(provider_history)
        messages.append(
            {
                "role": "user",
                "content": _agent_user_prompt(
                    message,
                    context_pack,
                    draft_brief=draft_brief,
                ),
            }
        )
        container.collection_agent_repository.update_run_stage(run_id, "sending_request")
        if _run_cancelled(run_id, container):
            return
        provider = provider_for_config(config, PromptBuilder())
        container.collection_agent_repository.update_run_stage(run_id, "waiting_model")
        started = time.perf_counter()
        response = provider.chat(messages, model=config.model)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if _run_cancelled(run_id, container):
            return

        container.collection_agent_repository.update_run_stage(run_id, "parsing_response")
        result, actions, draft_payload = _agent_result_from_response(response.content)
        if mode == "draft" and draft_payload is None and result.get("answer"):
            draft_payload = {
                "title": str((draft_brief or {}).get("target_scene") or "未命名场景草稿")[:160],
                "content": str(result["answer"]).strip(),
                "variant_label": "",
            }
        draft: Optional[CollectionAgentDraft] = None
        if draft_payload is not None:
            draft = container.collection_agent_repository.create_draft(
                run.collection_id,
                session_id=session.id,
                run_id=run_id,
                parent_draft_id=str(request.get("parent_draft_id") or "").strip() or None,
                title=draft_payload["title"],
                content=draft_payload["content"],
                brief=draft_brief or {},
                variant_label=draft_payload["variant_label"],
            )
            container.collection_agent_repository.attach_draft(run_id, draft.id)
        result.update(
            {
                "elapsed_ms": elapsed_ms,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost": response.cost,
                "mode": mode,
                "draft_id": draft.id if draft else None,
                "context_manifest": context_manifest,
            }
        )
        assistant_message = container.ai_thread_repository.add_message(
            thread_id=run.thread_id or "",
            role="assistant",
            content=result["answer"],
            meta_json=json.dumps(
                {
                    "agent_run_id": run_id,
                    "provider": response.provider,
                    "model": response.model,
                    "transport": response.transport,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost": response.cost,
                    "session_id": session.id,
                    "mode": mode,
                    "draft_id": draft.id if draft else None,
                },
                ensure_ascii=False,
            ),
        )
        container.collection_agent_repository.update_run_stage(run_id, "building_proposals")
        if _run_cancelled(run_id, container):
            return
        for action in actions:
            container.collection_agent_repository.create_action(
                run.collection_id,
                run_id=run_id,
                action_type=action["action_type"],
                title=action["title"],
                summary=action["summary"],
                payload=action["payload"],
                preview=action["preview"],
                reason=action["reason"],
                risk=action["risk"],
            )
        container.collection_agent_repository.complete_run(
            run_id,
            result=result,
            assistant_message_id=assistant_message.id,
            provider=response.provider,
            model=response.model,
            transport=response.transport,
        )
        container.collection_agent_repository.touch_session(session.id)
    except Exception as exc:  # noqa: BLE001
        container.collection_agent_repository.fail_run(run_id, _friendly_ai_error(exc))


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
    try:
        collection = container.collection_repository.create(
            name=data.title.strip() or "未命名作品集",
            description=data.description,
            project_type=data.project_type,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
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
    try:
        collection = container.collection_repository.update_project_type(
            collection_id,
            data.project_type,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
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


@router.get("/{collection_id}/outline", response_model=list[OutlineItemOut])
def list_collection_outline(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> list[OutlineItemOut]:
    _collection_or_404(collection_id, container)
    return [
        _outline_to_dto(item)
        for item in container.collection_outline_repository.list_for_collection(collection_id)
    ]


@router.post("/{collection_id}/outline", response_model=OutlineItemOut, status_code=201)
def create_collection_outline_item(
    collection_id: str,
    data: OutlineItemCreate,
    container: AppContainer = Depends(get_container),
) -> OutlineItemOut:
    _collection_or_404(collection_id, container)
    try:
        item = container.collection_outline_repository.create(
            collection_id,
            title=data.title,
            item_type=data.item_type,
            status=data.status,
            summary=data.summary,
            notes=data.notes,
            parent_id=data.parent_id,
            entry_id=data.entry_id,
            pov=data.pov,
            setting=data.setting,
            timeline=data.timeline,
            tags=data.tags,
            target_word_count=data.target_word_count,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if item is None:
        raise HTTPException(404, "Collection not found")
    return _outline_to_dto(item)


@router.put("/{collection_id}/outline/order", response_model=list[OutlineItemOut])
def reorder_collection_outline(
    collection_id: str,
    data: ReorderOutlineRequest,
    container: AppContainer = Depends(get_container),
) -> list[OutlineItemOut]:
    _collection_or_404(collection_id, container)
    return [
        _outline_to_dto(item)
        for item in container.collection_outline_repository.reorder(
            collection_id,
            data.item_ids,
        )
    ]


@router.put("/{collection_id}/outline/{item_id}", response_model=OutlineItemOut)
def update_collection_outline_item(
    collection_id: str,
    item_id: str,
    data: OutlineItemUpdate,
    container: AppContainer = Depends(get_container),
) -> OutlineItemOut:
    _collection_or_404(collection_id, container)
    try:
        item = container.collection_outline_repository.update(
            item_id,
            title=data.title,
            item_type=data.item_type,
            status=data.status,
            summary=data.summary,
            notes=data.notes,
            parent_id=data.parent_id,
            entry_id=data.entry_id,
            pov=data.pov,
            setting=data.setting,
            timeline=data.timeline,
            tags=data.tags,
            target_word_count=data.target_word_count,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if item is None or item.collection_id != collection_id:
        raise HTTPException(404, "Outline item not found")
    return _outline_to_dto(item)


@router.delete("/{collection_id}/outline/{item_id}", status_code=204)
def delete_collection_outline_item(
    collection_id: str,
    item_id: str,
    container: AppContainer = Depends(get_container),
):
    _collection_or_404(collection_id, container)
    if not container.collection_outline_repository.delete(
        item_id,
        collection_id=collection_id,
    ):
        raise HTTPException(404, "Outline item not found")


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
    try:
        output = container.collection_export_service.export_collection_docx(
            collection_id,
            tmp.name,
        )
    except Exception:
        _cleanup_temp_file(tmp.name)
        raise
    filename = f"{_collection_or_404(collection_id, container).name or 'collection'}.docx"
    return FileResponse(
        output,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        background=BackgroundTask(_cleanup_temp_file, output),
    )


@router.get("/{collection_id}/agent", response_model=CollectionAgentStateOut)
def get_collection_agent_state(
    collection_id: str,
    session_id: Optional[str] = Query(default=None),
    container: AppContainer = Depends(get_container),
) -> CollectionAgentStateOut:
    return _collection_agent_state(collection_id, container, session_id=session_id)


@router.get("/{collection_id}/agent/sessions", response_model=list[CollectionAgentSessionOut])
def list_collection_agent_sessions(
    collection_id: str,
    include_archived: bool = Query(False),
    container: AppContainer = Depends(get_container),
) -> list[CollectionAgentSessionOut]:
    collection = _collection_or_404(collection_id, container)
    _ensure_agent_session(collection, container)
    return [
        _session_to_dto(session, container)
        for session in container.collection_agent_repository.list_sessions(
            collection_id,
            include_archived=include_archived,
        )
    ]


@router.post(
    "/{collection_id}/agent/sessions",
    response_model=CollectionAgentSessionOut,
    status_code=201,
)
def create_collection_agent_session(
    collection_id: str,
    data: CollectionAgentSessionCreate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentSessionOut:
    collection = _collection_or_404(collection_id, container)
    mode = (data.mode or "discuss").strip()
    if mode not in COLLECTION_AGENT_MODES:
        raise HTTPException(400, "Agent 模式无效。")
    thread = container.ai_thread_repository.create(
        scope_kind=COLLECTION_AGENT_SCOPE,
        scope_id=collection_id,
        title=f"{collection.name or '作品集'} · {(data.title or '新会话').strip()[:80]}",
    )
    session = container.collection_agent_repository.create_session(
        collection_id,
        thread_id=thread.id,
        title=data.title,
        mode=mode,
    )
    container.collection_agent_repository.set_active_session(collection_id, session.id)
    return _session_to_dto(session, container)


@router.put(
    "/{collection_id}/agent/sessions/{session_id}",
    response_model=CollectionAgentSessionOut,
)
def update_collection_agent_session(
    collection_id: str,
    session_id: str,
    data: CollectionAgentSessionUpdate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentSessionOut:
    _collection_or_404(collection_id, container)
    session = container.collection_agent_repository.get_session(session_id)
    if session is None or session.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 会话已不存在。")
    if data.mode is not None and data.mode not in COLLECTION_AGENT_MODES:
        raise HTTPException(400, "Agent 模式无效。")
    if data.archived and container.collection_agent_repository.has_active_run_for_session(session_id):
        raise HTTPException(400, "会话正在运行，不能归档。")
    updated = container.collection_agent_repository.update_session(
        session_id,
        title=data.title,
        mode=data.mode,
        archived=data.archived,
    )
    assert updated is not None
    return _session_to_dto(updated, container)


@router.post(
    "/{collection_id}/agent/sessions/{session_id}/activate",
    response_model=CollectionAgentStateOut,
)
def activate_collection_agent_session(
    collection_id: str,
    session_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentStateOut:
    _collection_or_404(collection_id, container)
    session = container.collection_agent_repository.get_session(session_id)
    if session is None or session.collection_id != collection_id or session.archived:
        raise HTTPException(404, "这个 Agent 会话不可用。")
    return _collection_agent_state(collection_id, container, session_id=session_id)


@router.post(
    "/{collection_id}/agent/sessions/{session_id}/compact",
    response_model=CollectionAgentSessionOut,
)
def compact_collection_agent_session(
    collection_id: str,
    session_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentSessionOut:
    _collection_or_404(collection_id, container)
    session = container.collection_agent_repository.get_session(session_id)
    if session is None or session.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 会话已不存在。")
    messages = container.ai_thread_repository.list_messages(session.thread_id)
    _compact_session_locally(session, messages, container, force=True)
    updated = container.collection_agent_repository.get_session(session_id)
    assert updated is not None
    return _session_to_dto(updated, container)


@router.post(
    "/{collection_id}/agent/sessions/{session_id}/clear",
    response_model=CollectionAgentStateOut,
)
def clear_collection_agent_session(
    collection_id: str,
    session_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentStateOut:
    _collection_or_404(collection_id, container)
    session = container.collection_agent_repository.get_session(session_id)
    if session is None or session.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 会话已不存在。")
    if container.collection_agent_repository.has_active_run(collection_id):
        raise HTTPException(400, "Agent 正在工作，请等待完成或先中断本地等待。")
    container.collection_agent_repository.clear_session_history(collection_id, session_id)
    container.ai_thread_repository.clear_messages(session.thread_id)
    return _collection_agent_state(collection_id, container, session_id=session_id)


@router.delete("/{collection_id}/agent/sessions/{session_id}", status_code=204)
def delete_collection_agent_session(
    collection_id: str,
    session_id: str,
    container: AppContainer = Depends(get_container),
) -> Response:
    _collection_or_404(collection_id, container)
    session = container.collection_agent_repository.get_session(session_id)
    if session is None or session.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 会话已不存在。")
    if container.collection_agent_repository.has_active_run_for_session(session_id):
        raise HTTPException(400, "会话正在运行，不能删除。")
    run_ids = {
        run.id
        for run in container.collection_agent_repository.list_runs(
            collection_id,
            session_id=session_id,
            limit=1000,
        )
    }
    if any(
        action.status in {"pending", "deferred"} and action.run_id in run_ids
        for action in container.collection_agent_repository.list_actions(collection_id, limit=1000)
    ):
        raise HTTPException(400, "这个会话还有待确认提案，请先处理或归档会话。")
    container.collection_agent_repository.clear_session_history(collection_id, session_id)
    container.ai_thread_repository.delete(session.thread_id)
    _ensure_agent_session(_collection_or_404(collection_id, container), container)
    return Response(status_code=204)


@router.put("/{collection_id}/agent/settings", response_model=CollectionAgentSettingsOut)
def save_collection_agent_settings(
    collection_id: str,
    data: CollectionAgentSettingsUpdate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentSettingsOut:
    _collection_or_404(collection_id, container)
    _name, config, error = _profile_config(data.profile_id, container)
    if config is None:
        raise HTTPException(400, error or "这个 AI 配置档案不可用。")
    settings = container.collection_agent_repository.save_settings(
        collection_id,
        profile_id=data.profile_id,
        enabled=data.enabled,
    )
    return _settings_to_dto(settings)


@router.get("/{collection_id}/agent/memory", response_model=CollectionAgentMemoryOut)
def get_collection_agent_memory(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentMemoryOut:
    _collection_or_404(collection_id, container)
    return _memory_to_dto(container.collection_agent_repository.get_memory(collection_id))


@router.put("/{collection_id}/agent/memory", response_model=CollectionAgentMemoryOut)
def save_collection_agent_memory(
    collection_id: str,
    data: CollectionAgentMemoryUpdate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentMemoryOut:
    _collection_or_404(collection_id, container)
    return _memory_to_dto(
        container.collection_agent_repository.save_memory(collection_id, data.sections)
    )


@router.post("/{collection_id}/agent/clear", response_model=CollectionAgentStateOut)
def clear_collection_agent_conversation(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentStateOut:
    _collection_or_404(collection_id, container)
    if container.collection_agent_repository.has_active_run(collection_id):
        raise HTTPException(400, "Agent 正在工作，请等待完成或先中断本地等待。")
    collection = _collection_or_404(collection_id, container)
    session = _ensure_agent_session(collection, container)
    container.collection_agent_repository.clear_session_history(collection_id, session.id)
    container.ai_thread_repository.clear_messages(session.thread_id)
    return _collection_agent_state(collection_id, container, session_id=session.id)


@router.get("/{collection_id}/agent/references", response_model=list[CollectionAgentReferenceOut])
def search_collection_agent_references(
    collection_id: str,
    q: str = Query("", max_length=120),
    limit: int = Query(30, ge=1, le=80),
    container: AppContainer = Depends(get_container),
) -> list[CollectionAgentReferenceOut]:
    _collection_or_404(collection_id, container)
    query = (q or "").strip()
    query_lower = query.lower()
    results: list[CollectionAgentReferenceOut] = []

    def match(*values: str) -> bool:
        if not query_lower:
            return True
        return any(query_lower in (value or "").lower() for value in values)

    for item in container.collection_outline_repository.list_for_collection(collection_id):
        if len(results) >= limit:
            break
        if not match(item.title, item.summary, item.notes, item.pov, item.setting, item.timeline):
            continue
        results.append(
            CollectionAgentReferenceOut(
                kind="outline",
                ref_id=item.id,
                name=item.title or "结构节点",
                body_preview=_truncate(item.summary or item.notes, 160),
                meta={"type": item.item_type, "status": item.status},
            )
        )

    if len(results) < limit:
        for entry in container.collection_repository.list_entries(collection_id):
            if len(results) >= limit:
                break
            if not match(entry.title, entry.body, ", ".join(entry.tags)):
                continue
            results.append(
                CollectionAgentReferenceOut(
                    kind="article",
                    ref_id=entry.id,
                    name=entry.title or "未命名文章",
                    body_preview=_truncate(entry.body, 160),
                    meta={"tags": entry.tags},
                )
            )

    if len(results) < limit:
        for card in container.ai_card_repository.list_all():
            if len(results) >= limit:
                break
            if not match(card.name, card.body, ", ".join(card.tags), card.kind):
                continue
            results.append(
                CollectionAgentReferenceOut(
                    kind="ai_card",
                    ref_id=card.id,
                    name=card.name or "AI 卡片",
                    body_preview=_truncate(card.body, 160),
                    meta={"kind": card.kind, "tags": card.tags},
                )
            )

    if len(results) < limit:
        motifs = container.motif_repository.list_nodes(query=query, limit=limit)
        for node in motifs:
            if len(results) >= limit:
                break
            results.append(
                CollectionAgentReferenceOut(
                    kind="motif",
                    ref_id=node.id,
                    name=node.name,
                    body_preview=_truncate(node.note or json.dumps(node.profile, ensure_ascii=False), 160),
                    meta={"tags": node.tags, "aliases": node.aliases},
                )
            )

    if len(results) < limit:
        references = (
            container.reference_repository.search(query, limit=limit)
            if query
            else container.reference_repository.list_recent(limit=limit)
        )
        for passage in references:
            if len(results) >= limit:
                break
            results.append(
                CollectionAgentReferenceOut(
                    kind="reference",
                    ref_id=passage.id,
                    name=passage.source_title or "文脉标本",
                    body_preview=_truncate(passage.content, 160),
                    meta={"author": passage.source_author, "usage_kind": passage.usage_kind},
                )
            )
    return results[:limit]


def _start_collection_agent_run(
    collection_id: str,
    data: CollectionAgentRunCreate,
    container: AppContainer,
) -> CollectionAgentRunOut:
    collection = _collection_or_404(collection_id, container)
    message = (data.message or "").strip()
    if not message:
        raise HTTPException(400, "请输入要交给作品集 Agent 的问题或任务。")
    if container.collection_agent_repository.has_active_run(collection_id):
        raise HTTPException(400, "Agent 正在工作，请等待完成或先中断本地等待。")
    settings = container.collection_agent_repository.get_settings(collection_id)
    if not settings.enabled:
        raise HTTPException(400, "这个作品集的 Agent 已停用。")
    profile_id = (data.profile_id or settings.profile_id or "default").strip() or "default"
    _name, config, error = _profile_config(profile_id, container)
    if config is None:
        raise HTTPException(400, error or "这个 AI 配置档案不可用。")
    session = _ensure_agent_session(
        collection,
        container,
        requested_session_id=data.session_id,
    )
    if session.archived:
        raise HTTPException(400, "这个会话已归档，请先恢复后再继续。")
    mode = (data.mode or session.mode or "discuss").strip()
    if mode not in COLLECTION_AGENT_MODES:
        raise HTTPException(400, "Agent 模式无效。")
    parent_draft_id = (data.parent_draft_id or "").strip() or None
    if parent_draft_id:
        parent_draft = container.collection_agent_repository.get_draft(parent_draft_id)
        if parent_draft is None or parent_draft.collection_id != collection_id:
            raise HTTPException(400, "要参考的原草稿已不存在。")
    refs = [{"kind": ref.kind, "ref_id": ref.ref_id} for ref in data.context_refs]
    draft_brief = data.draft_brief.model_dump() if data.draft_brief is not None else None
    run = container.collection_agent_repository.create_run(
        collection_id,
        thread_id=session.thread_id,
        profile_id=profile_id,
        session_id=session.id,
        mode=mode,
        request={
            "message": message,
            "task_type": data.task_type,
            "context_refs": refs,
            "request_web_context": data.request_web_context,
            "profile_id": profile_id,
            "session_id": session.id,
            "mode": mode,
            "draft_brief": draft_brief,
            "parent_draft_id": parent_draft_id,
        },
    )
    container.collection_agent_repository.update_session(session.id, mode=mode)
    container.collection_agent_repository.set_active_session(collection_id, session.id)
    _AGENT_EXECUTOR.submit(_run_collection_agent, run.id, container)
    return _run_to_dto(run, container)


@router.post("/{collection_id}/agent/chat", response_model=CollectionAgentRunOut, status_code=202)
def create_collection_agent_chat_run(
    collection_id: str,
    data: CollectionAgentChatCreate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentRunOut:
    return _start_collection_agent_run(collection_id, data, container)


@router.post("/{collection_id}/agent/runs", response_model=CollectionAgentRunOut, status_code=202)
def create_collection_agent_run(
    collection_id: str,
    data: CollectionAgentRunCreate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentRunOut:
    return _start_collection_agent_run(collection_id, data, container)


@router.get("/{collection_id}/agent/runs/{run_id}", response_model=CollectionAgentRunOut)
def get_collection_agent_run(
    collection_id: str,
    run_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentRunOut:
    _collection_or_404(collection_id, container)
    run = container.collection_agent_repository.get_run(run_id)
    if run is None or run.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 任务已不存在。")
    return _run_to_dto(run, container)


@router.post("/{collection_id}/agent/runs/{run_id}/cancel", response_model=CollectionAgentRunOut)
def cancel_collection_agent_run(
    collection_id: str,
    run_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentRunOut:
    _collection_or_404(collection_id, container)
    run = container.collection_agent_repository.get_run(run_id)
    if run is None or run.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 任务已不存在。")
    cancelled = container.collection_agent_repository.cancel_run(run_id)
    assert cancelled is not None
    return _run_to_dto(cancelled, container)


@router.get("/{collection_id}/agent/drafts", response_model=list[CollectionAgentDraftOut])
def list_collection_agent_drafts(
    collection_id: str,
    session_id: Optional[str] = Query(default=None),
    include_applied: bool = Query(True),
    container: AppContainer = Depends(get_container),
) -> list[CollectionAgentDraftOut]:
    _collection_or_404(collection_id, container)
    if session_id:
        session = container.collection_agent_repository.get_session(session_id)
        if session is None or session.collection_id != collection_id:
            raise HTTPException(404, "这个 Agent 会话已不存在。")
    return [
        _draft_to_dto(draft)
        for draft in container.collection_agent_repository.list_drafts(
            collection_id,
            session_id=session_id,
            include_applied=include_applied,
            limit=200,
        )
    ]


@router.get("/{collection_id}/agent/drafts/{draft_id}", response_model=CollectionAgentDraftOut)
def get_collection_agent_draft(
    collection_id: str,
    draft_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentDraftOut:
    _collection_or_404(collection_id, container)
    draft = container.collection_agent_repository.get_draft(draft_id)
    if draft is None or draft.collection_id != collection_id:
        raise HTTPException(404, "这份 Agent 草稿已不存在。")
    return _draft_to_dto(draft)


@router.put("/{collection_id}/agent/drafts/{draft_id}", response_model=CollectionAgentDraftOut)
def update_collection_agent_draft(
    collection_id: str,
    draft_id: str,
    data: CollectionAgentDraftUpdate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentDraftOut:
    _collection_or_404(collection_id, container)
    draft = container.collection_agent_repository.get_draft(draft_id)
    if draft is None or draft.collection_id != collection_id:
        raise HTTPException(404, "这份 Agent 草稿已不存在。")
    try:
        updated = container.collection_agent_repository.update_draft(
            draft_id,
            title=data.title,
            content=data.content,
            brief=data.brief,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    assert updated is not None
    return _draft_to_dto(updated)


def _entry_body_hash(body: str) -> str:
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


@router.post(
    "/{collection_id}/agent/drafts/{draft_id}/apply",
    response_model=CollectionAgentDraftApplyOut,
)
def apply_collection_agent_draft(
    collection_id: str,
    draft_id: str,
    data: CollectionAgentDraftApply,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentDraftApplyOut:
    _collection_or_404(collection_id, container)
    draft = container.collection_agent_repository.get_draft(draft_id)
    if draft is None or draft.collection_id != collection_id:
        raise HTTPException(404, "这份 Agent 草稿已不存在。")
    operation = (data.operation or "").strip()
    if operation not in {"create_article", "append", "replace_selection"}:
        raise HTTPException(400, "草稿写回方式无效。")
    if draft.status == "applied":
        entry = container.entry_repository.get(draft.target_entry_id or "")
        if entry is None:
            raise HTTPException(409, "这份草稿已应用，但目标文章已不存在。")
        return CollectionAgentDraftApplyOut(
            draft=_draft_to_dto(draft),
            entry_id=entry.id,
            article_title=entry.title,
            operation=(draft.applied_ref_id or operation).split(":", 1)[0],
        )

    version_id: Optional[str] = None
    if operation == "create_article":
        entry = container.entry_repository.create(
            title=(data.article_title or draft.title).strip() or "Agent 场景草稿",
            body=draft.content,
        )
        container.collection_repository.add_entry(collection_id, entry.id)
    else:
        entry_id = (data.target_entry_id or "").strip()
        entry = container.entry_repository.get(entry_id)
        in_collection = any(
            item.id == entry_id
            for item in container.collection_repository.list_entries(collection_id)
        )
        if entry is None or not in_collection:
            raise HTTPException(400, "请选择当前作品集中的目标文章。")
        if not data.expected_body_hash or data.expected_body_hash != _entry_body_hash(entry.body):
            raise HTTPException(409, "文章正文已发生变化，请重新预览写回位置。")
        if operation == "append":
            body = entry.body.rstrip()
            new_body = f"{body}\n\n{draft.content}" if body else draft.content
        else:
            start = data.selection_start
            end = data.selection_end
            if start is None or end is None or start >= end or end > len(entry.body):
                raise HTTPException(400, "请选择一个明确的正文范围。")
            if start == 0 and end == len(entry.body):
                raise HTTPException(400, "不能用 Agent 草稿覆盖整篇文章，请选择局部文字或新建文章。")
            selected = entry.body[start:end]
            if selected != data.expected_selected_text:
                raise HTTPException(409, "选中的原文已发生变化，请重新选择后再应用。")
            new_body = entry.body[:start] + draft.content + entry.body[end:]
        run = container.collection_agent_repository.get_run(draft.run_id or "")
        version = container.version_history_service.save_ai_before_apply(
            entry.id,
            label=f"Agent 草稿：{draft.title}",
            provider=run.provider if run else None,
            model=run.model if run else None,
        )
        version_id = version.id
        updated_entry = container.entry_repository.update(
            entry.id,
            title=entry.title,
            body=new_body,
            tags=entry.tags,
        )
        assert updated_entry is not None
        entry = updated_entry

    applied = container.collection_agent_repository.mark_draft_applied(
        draft.id,
        target_entry_id=entry.id,
        applied_ref_id=f"{operation}:{entry.id}",
    )
    assert applied is not None
    return CollectionAgentDraftApplyOut(
        draft=_draft_to_dto(applied),
        entry_id=entry.id,
        article_title=entry.title,
        operation=operation,
        version_id=version_id,
    )


@router.post("/{collection_id}/agent/drafts/delete", response_model=dict[str, int])
def delete_collection_agent_drafts(
    collection_id: str,
    data: CollectionAgentDraftDeleteMany,
    container: AppContainer = Depends(get_container),
) -> dict[str, int]:
    _collection_or_404(collection_id, container)
    deleted = (
        container.collection_agent_repository.clear_unapplied_drafts(collection_id)
        if data.clear_all
        else container.collection_agent_repository.delete_drafts(collection_id, data.draft_ids)
    )
    return {"deleted": deleted}


@router.get(
    "/{collection_id}/agent/style-samples",
    response_model=list[CollectionAgentStyleSampleOut],
)
def list_collection_agent_style_samples(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> list[CollectionAgentStyleSampleOut]:
    _collection_or_404(collection_id, container)
    return [
        _style_sample_to_dto(item)
        for item in container.collection_agent_repository.list_style_samples(collection_id)
    ]


@router.post(
    "/{collection_id}/agent/style-samples",
    response_model=CollectionAgentStyleSampleOut,
    status_code=201,
)
def start_collection_agent_style_sample(
    collection_id: str,
    data: CollectionAgentStyleSampleCreate,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentStyleSampleOut:
    _collection_or_404(collection_id, container)
    entry = container.entry_repository.get(data.entry_id)
    if entry is None or not any(
        item.id == entry.id for item in container.collection_repository.list_entries(collection_id)
    ):
        raise HTTPException(400, "请选择当前作品集中的文章。")
    sample = container.collection_agent_repository.create_style_sample(
        collection_id,
        entry_id=entry.id,
        original_body=entry.body,
    )
    return _style_sample_to_dto(sample)


@router.post(
    "/{collection_id}/agent/style-samples/{sample_id}/complete",
    response_model=CollectionAgentStyleSampleOut,
)
def complete_collection_agent_style_sample(
    collection_id: str,
    sample_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentStyleSampleOut:
    _collection_or_404(collection_id, container)
    sample = container.collection_agent_repository.get_style_sample(sample_id)
    if sample is None or sample.collection_id != collection_id:
        raise HTTPException(404, "这个写作闭环样本已不存在。")
    if sample.status == "completed":
        return _style_sample_to_dto(sample)
    entry = container.entry_repository.get(sample.entry_id)
    if entry is None:
        raise HTTPException(400, "样本文章已不存在。")
    completed = container.collection_agent_repository.complete_style_sample(
        sample_id,
        final_body=entry.body,
    )
    assert completed is not None
    return _style_sample_to_dto(completed)


@router.get("/{collection_id}/agent/author-portrait", response_model=AuthorPortraitOut)
def get_collection_agent_author_portrait(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> AuthorPortraitOut:
    _collection_or_404(collection_id, container)
    completed = container.collection_agent_repository.count_completed_style_samples()
    return _portrait_to_dto(
        container.collection_agent_repository.get_author_portrait(),
        completed_style_cycles=completed,
    )


@router.put("/{collection_id}/agent/author-portrait", response_model=AuthorPortraitOut)
def save_collection_agent_author_portrait(
    collection_id: str,
    data: AuthorPortraitUpdate,
    container: AppContainer = Depends(get_container),
) -> AuthorPortraitOut:
    _collection_or_404(collection_id, container)
    completed = container.collection_agent_repository.count_completed_style_samples()
    portrait = container.collection_agent_repository.save_author_portrait(
        tags=data.tags,
        summary=data.summary,
        evidence_count=completed,
        reason="manual",
    )
    return _portrait_to_dto(portrait, completed_style_cycles=completed)


@router.get(
    "/{collection_id}/agent/author-portrait/versions",
    response_model=list[AuthorPortraitVersionOut],
)
def list_collection_agent_author_portrait_versions(
    collection_id: str,
    container: AppContainer = Depends(get_container),
) -> list[AuthorPortraitVersionOut]:
    _collection_or_404(collection_id, container)
    return [
        _portrait_version_to_dto(item)
        for item in container.collection_agent_repository.list_author_portrait_versions()
    ]


@router.post(
    "/{collection_id}/agent/author-portrait/versions/{version_id}/restore",
    response_model=AuthorPortraitOut,
)
def restore_collection_agent_author_portrait_version(
    collection_id: str,
    version_id: str,
    container: AppContainer = Depends(get_container),
) -> AuthorPortraitOut:
    _collection_or_404(collection_id, container)
    portrait = container.collection_agent_repository.restore_author_portrait_version(version_id)
    if portrait is None:
        raise HTTPException(404, "这个作者画像版本已不存在。")
    completed = container.collection_agent_repository.count_completed_style_samples()
    return _portrait_to_dto(portrait, completed_style_cycles=completed)


def _apply_collection_agent_action(
    action: CollectionAgentAction,
    container: AppContainer,
) -> str:
    payload = action.payload
    if action.action_type == "update_memory":
        section_id = normalize_collection_agent_memory_section_id(
            str(payload.get("section_id") or ""),
            action.title,
            action.summary,
        )
        if section_id is None:
            raise ValueError("无法识别这条提案要更新的项目圣经栏目，请拒绝后重新生成。")
        content = str(payload.get("content") or "").strip()
        mode = str(payload.get("mode") or "replace").strip()
        memory = container.collection_agent_repository.update_memory_section(
            action.collection_id,
            section_id,
            content,
            mode="append" if mode == "append" else "replace",
        )
        return f"memory:{memory.collection_id}:{section_id}"

    if action.action_type == "create_outline_item":
        item = container.collection_outline_repository.create(
            action.collection_id,
            title=str(payload.get("title") or "Agent 提案节点"),
            item_type=str(payload.get("item_type") or "scene"),
            status=str(payload.get("status") or "idea"),
            summary=str(payload.get("summary") or ""),
            notes=str(payload.get("notes") or ""),
            parent_id=str(payload.get("parent_id") or "").strip() or None,
            entry_id=str(payload.get("entry_id") or "").strip() or None,
            pov=str(payload.get("pov") or ""),
            setting=str(payload.get("setting") or ""),
            timeline=str(payload.get("timeline") or ""),
            tags=[str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()]
            if isinstance(payload.get("tags"), list)
            else [],
            target_word_count=payload.get("target_word_count") if isinstance(payload.get("target_word_count"), int) else None,
        )
        if item is None:
            raise ValueError("无法创建结构节点。")
        return item.id

    if action.action_type == "update_outline_item":
        item_id = str(payload.get("item_id") or "").strip()
        existing = container.collection_outline_repository.get(item_id)
        if existing is None or existing.collection_id != action.collection_id:
            raise ValueError("要修改的结构节点已不存在。")
        item = container.collection_outline_repository.update(
            item_id,
            title=str(payload.get("title") or existing.title),
            item_type=str(payload.get("item_type") or existing.item_type),
            status=str(payload.get("status") or existing.status),
            summary=str(payload.get("summary") if payload.get("summary") is not None else existing.summary),
            notes=str(payload.get("notes") if payload.get("notes") is not None else existing.notes),
            parent_id=str(payload.get("parent_id")).strip() if payload.get("parent_id") else existing.parent_id,
            entry_id=str(payload.get("entry_id")).strip() if payload.get("entry_id") else existing.entry_id,
            pov=str(payload.get("pov") if payload.get("pov") is not None else existing.pov),
            setting=str(payload.get("setting") if payload.get("setting") is not None else existing.setting),
            timeline=str(payload.get("timeline") if payload.get("timeline") is not None else existing.timeline),
            tags=[str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()]
            if isinstance(payload.get("tags"), list)
            else existing.tags,
            target_word_count=payload.get("target_word_count")
            if isinstance(payload.get("target_word_count"), int)
            else existing.target_word_count,
        )
        if item is None:
            raise ValueError("无法更新结构节点。")
        return item.id

    if action.action_type == "create_article_note":
        entry_id = str(payload.get("entry_id") or "").strip()
        body = str(payload.get("body") or "").strip()
        if not entry_id or container.entry_repository.get(entry_id) is None:
            raise ValueError("要添加便签的文章已不存在。")
        if not body:
            raise ValueError("便签内容不能为空。")
        for existing_note in container.entry_writing_note_repository.list_for_entry(entry_id, include_done=True):
            if existing_note.body.strip() == body:
                return existing_note.id
        note = container.entry_writing_note_repository.create(
            entry_id=entry_id,
            body=body,
            pinned=bool(payload.get("pinned", False)),
        )
        return note.id

    if action.action_type == "update_author_portrait":
        tags = payload.get("tags")
        summary = str(payload.get("summary") or "").strip()
        if not isinstance(tags, list) or not summary:
            raise ValueError("作者画像提案缺少标签或描述。")
        completed = container.collection_agent_repository.count_completed_style_samples()
        portrait = container.collection_agent_repository.save_author_portrait(
            tags=[str(tag).strip() for tag in tags if str(tag).strip()],
            summary=summary,
            evidence_count=completed,
            reason=f"agent_action:{action.id}",
        )
        return f"author_portrait:{portrait.id}"

    raise ValueError("不支持的 Agent 提案类型。")


@router.post("/{collection_id}/agent/actions/{action_id}/apply", response_model=CollectionAgentActionOut)
def apply_collection_agent_action(
    collection_id: str,
    action_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentActionOut:
    _collection_or_404(collection_id, container)
    action = container.collection_agent_repository.get_action(action_id)
    if action is None or action.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 提案已不存在。")
    if action.status == "applied":
        return _action_to_dto(action)
    if action.status not in {"pending", "deferred"}:
        raise HTTPException(400, "这个 Agent 提案已经处理过。")
    try:
        applied_ref_id = _apply_collection_agent_action(action, container)
        updated = container.collection_agent_repository.set_action_status(
            action_id,
            "applied",
            applied_ref_id=applied_ref_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    assert updated is not None
    return _action_to_dto(updated)


@router.post("/{collection_id}/agent/actions/{action_id}/reject", response_model=CollectionAgentActionOut)
def reject_collection_agent_action(
    collection_id: str,
    action_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentActionOut:
    _collection_or_404(collection_id, container)
    action = container.collection_agent_repository.get_action(action_id)
    if action is None or action.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 提案已不存在。")
    if action.status == "applied":
        raise HTTPException(400, "已应用的提案不能拒绝。")
    updated = container.collection_agent_repository.set_action_status(action_id, "rejected")
    assert updated is not None
    return _action_to_dto(updated)


@router.post("/{collection_id}/agent/actions/{action_id}/defer", response_model=CollectionAgentActionOut)
def defer_collection_agent_action(
    collection_id: str,
    action_id: str,
    container: AppContainer = Depends(get_container),
) -> CollectionAgentActionOut:
    _collection_or_404(collection_id, container)
    action = container.collection_agent_repository.get_action(action_id)
    if action is None or action.collection_id != collection_id:
        raise HTTPException(404, "这个 Agent 提案已不存在。")
    if action.status == "applied":
        raise HTTPException(400, "已应用的提案不能稍后处理。")
    updated = container.collection_agent_repository.set_action_status(action_id, "deferred")
    assert updated is not None
    return _action_to_dto(updated)


# Legacy work endpoints are intentionally not exposed in the Tauri MVP UI.
