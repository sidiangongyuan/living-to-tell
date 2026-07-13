"""AI workspace: task services (rewrite, continue, summarize) + thread chat.

Exposes AiTaskService, AiThreadService, and RewriteService from the container.
Long-running AI calls are synchronous with extended timeout (handled by frontend).
"""
from __future__ import annotations

import json
import hashlib
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from dataclasses import dataclass
from threading import Lock
from typing import Any, Iterable
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from deps import get_container
from features.ai.job_manager import AiJobRecord, ai_job_manager
from features.ai.article_task_runs import (
    ArticleTaskRunRecord,
    article_task_run_manager,
)
from features.ai.error_messages import friendly_ai_error as safe_friendly_ai_error
from features.ai_cards.routes import (
    AiCardDraftOut,
    AiCardDraftRequest,
    generate_ai_card_draft_core,
)
from features.motifs.routes import (
    MotifEnrichmentDraftOut,
    MotifEnrichmentRequest,
    MotifRelationDiscoveryDraftOut,
    MotifRelationDiscoveryRequest,
    generate_motif_enrichment_draft_core,
    generate_motif_relation_discovery_core,
)
from writer.app.settings import SUPPORTED_AI_PROVIDERS, SUPPORTED_WIRE_APIS
from writer.app.container import AppContainer
from writer.domain.enums import AiCostTier, AiTargetKind, AiTaskType
from writer.domain.models.ai_config import AiConfig
from writer.domain.models.ai_thread import AiThread as DomainThread
from writer.domain.models.ai_thread import AiMessage as DomainMessage
from writer.services.ai.interfaces import AiError
from writer.services.ai.preflight import format_issues, preflight_rewrite
from writer.services.ai.provider_factory import provider_for_config
from writer.services.ai.prompt_builder import PromptBuilder
from writer.services.ai.task_prompt_builder import TaskPromptBuilder
from writer.services.ai.task_service import AiTaskService
from writer.services.ai.task_types import (
    AiContextAttachment as DomainContextAttachment,
)
from writer.services.ai.task_types import AiTaskRequest as DomainAiTaskRequest

router = APIRouter(prefix="/api/ai", tags=["ai"])
_article_task_apply_lock = Lock()

KEY_TAURI_AI_TASK_PRESETS = "ai.tauri_task_presets"
KEY_TAURI_AI_CHAT_SYSTEM_PROMPT = "ai.tauri_chat_system_prompt"
MAX_PRESETS_PER_TASK = 50
MAX_ATTACHMENT_CHARS = 40_000
MAX_CHAT_SYSTEM_PROMPT_CHARS = 4_000

TASK_TYPE_MAP = {
    "polish": AiTaskType.POLISH,
    # The domain enum does not have a standalone rewrite task. The Tauri UI
    # exposes "rewrite" as a user-facing task, backed by style-transfer with
    # explicit rewrite controls.
    "rewrite": AiTaskType.STYLE_TRANSFER,
    "expand": AiTaskType.EXPAND,
    "continue": AiTaskType.CONTINUE,
    "style_transfer": AiTaskType.STYLE_TRANSFER,
    "summarize": AiTaskType.SUMMARIZE,
    "outline": AiTaskType.OUTLINE,
    "title": AiTaskType.TITLE,
    "structure_diagnose": AiTaskType.STRUCTURE_DIAGNOSE,
    "consistency_check": AiTaskType.CONSISTENCY_CHECK,
}
TARGET_KIND_MAP = {
    "selection": AiTargetKind.SELECTION,
    "article": AiTargetKind.FRAGMENT,
    "fragment": AiTargetKind.FRAGMENT,
    "collection": AiTargetKind.COLLECTION,
    "paste": AiTargetKind.PASTE,
}
SUPPORTED_TASK_PRESET_TYPES = set(TASK_TYPE_MAP)


# ---- DTOs ----
class AiAttachmentIn(BaseModel):
    kind: str
    ref_id: str
    name: str
    body: str


class AiTaskRequest(BaseModel):
    task_type: str  # 'rewrite', 'continue', 'summarize', etc.
    text: str
    instructions: Optional[str] = None
    context: Optional[str] = None
    target_kind: str = "paste"
    target_ref_id: Optional[str] = None
    style: Optional[str] = None
    intensity: Optional[str] = None
    extra_instructions: Optional[str] = None
    max_output_chars: Optional[int] = None
    preserve_meaning: bool = True
    preserve_voice: bool = True
    forbid_terms: list[str] = Field(default_factory=list)
    must_keep_terms: list[str] = Field(default_factory=list)
    attachments: list[AiAttachmentIn] = Field(default_factory=list)
    cost_tier: str = "balanced"


class AiTaskResponse(BaseModel):
    result: str
    task_type: str


class AiTaskCompareRequest(AiTaskRequest):
    profile_ids: list[str] = Field(default_factory=lambda: ["default"])


class AiTaskResultStats(BaseModel):
    input_chars: int
    output_chars: int
    delta_chars: int
    output_ratio: Optional[float] = None
    input_paragraphs: int
    output_paragraphs: int


class AiTaskCompareResult(BaseModel):
    profile_id: str
    profile_name: str
    provider: str
    model: str
    transport: Optional[str] = None
    status: str
    result: str = ""
    error: str = ""
    elapsed_ms: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost: Optional[float] = None
    finish_reason: Optional[str] = None
    stats: AiTaskResultStats


class AiTaskCompareResponse(BaseModel):
    task_type: str
    results: list[AiTaskCompareResult]


class ArticleTaskRunCreate(BaseModel):
    article_id: str
    task_type: str
    profile_ids: list[str]
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    instructions: Optional[str] = None
    context: Optional[str] = None
    style: Optional[str] = None
    intensity: Optional[str] = None
    extra_instructions: Optional[str] = None
    max_output_chars: Optional[int] = None
    preserve_meaning: bool = True
    preserve_voice: bool = True
    forbid_terms: list[str] = Field(default_factory=list)
    must_keep_terms: list[str] = Field(default_factory=list)
    attachments: list[AiAttachmentIn] = Field(default_factory=list)
    cost_tier: str = "balanced"


class ArticleTaskRunApply(BaseModel):
    profile_id: str


class AiTaskAttachmentSnapshotOut(BaseModel):
    kind: str
    ref_id: str
    name: str
    size_chars: int


class ArticleTaskRunOut(BaseModel):
    run_id: str
    article_id: str
    article_title: str
    task_type: str
    article_hash: str
    original_text: str
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    status: str
    stage: str
    stage_label: str
    error: str = ""
    profiles: list[dict[str, Any]]
    attachment_snapshots: list[AiTaskAttachmentSnapshotOut] = Field(default_factory=list)
    results: list[AiTaskCompareResult]
    created_at: str
    started_at: Optional[str] = None
    updated_at: str
    completed_at: Optional[str] = None
    elapsed_ms: int
    applied_profile_id: Optional[str] = None
    applied_at: Optional[str] = None
    applied_version_id: Optional[str] = None


class ArticleTaskApplyOut(BaseModel):
    run: ArticleTaskRunOut
    entry: dict[str, Any]
    version_id: str
    was_noop: bool = False


class AiJobSnapshot(BaseModel):
    job_id: str
    kind: str
    status: str
    stage: str
    stage_label: str
    concept: str
    motif_id: Optional[str] = None
    profile_id: str
    started_at: str
    updated_at: str
    elapsed_ms: int
    result: Optional[Any] = None
    error: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    transport: Optional[str] = None


class AiTaskCompareProfileSnapshot(BaseModel):
    profile_id: str
    profile_name: str
    provider: str
    model: str


class AiTaskCompareStartedEvent(BaseModel):
    event: str = "started"
    run_id: str
    profiles: list[AiTaskCompareProfileSnapshot]


class AiTaskCompareResultEvent(BaseModel):
    event: str
    result: AiTaskCompareResult


class AiTaskCompareDoneEvent(BaseModel):
    event: str = "done"
    run_id: str


class AiCardDraftJobRequest(AiCardDraftRequest):
    card_id: Optional[str] = None


@dataclass(frozen=True)
class _ProfileRuntime:
    profile_id: str
    profile_name: str
    config: Optional[AiConfig]
    error: str = ""


class ThreadOut(BaseModel):
    id: str
    scope_kind: str
    scope_id: Optional[str]
    title: str
    created_at: Optional[str]
    updated_at: Optional[str]


class ThreadCreate(BaseModel):
    title: str = "New Conversation"
    scope_kind: str = "global"
    scope_id: Optional[str] = None


class MessageOut(BaseModel):
    id: Optional[str] = None
    thread_id: Optional[str] = None
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str]
    meta: dict[str, Any] = Field(default_factory=dict)


class CurrentThreadOut(BaseModel):
    thread: ThreadOut
    messages: list[MessageOut] = Field(default_factory=list)


class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str
    scope_kind: Optional[str] = None
    scope_id: Optional[str] = None
    profile_id: Optional[str] = None


class ChatResponse(BaseModel):
    thread_id: str
    user_message: MessageOut
    assistant_message: MessageOut


class ChatSettings(BaseModel):
    system_prompt: str = ""


class AiTaskPreset(BaseModel):
    id: str = ""
    task_type: str
    name: str
    controls: dict[str, Any] = Field(default_factory=dict)


def _thread_to_dto(t: DomainThread) -> ThreadOut:
    scope_kind = "article" if t.scope_kind == "fragment" else t.scope_kind
    return ThreadOut(
        id=t.id,
        scope_kind=scope_kind,
        scope_id=t.scope_id,
        title=t.title,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _message_to_dto(message: DomainMessage) -> MessageOut:
    import json

    try:
        meta = json.loads(message.meta_json or "{}")
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    return MessageOut(
        id=message.id,
        thread_id=message.thread_id,
        role=message.role,
        content=message.content,
        timestamp=message.created_at,
        meta=meta,
    )


def _normalise_scope_kind(scope_kind: Optional[str]) -> str:
    normalized = (scope_kind or "global").strip().lower()
    if normalized == "fragment":
        normalized = "article"
    if normalized not in {"article", "work", "collection", "global"}:
        raise HTTPException(400, f"Unknown scope_kind: {scope_kind}")
    return normalized


def _storage_scope_kind(scope_kind: str) -> str:
    return "fragment" if scope_kind == "article" else scope_kind


def _clean_chat_system_prompt(value: str) -> str:
    return (value or "").strip()[:MAX_CHAT_SYSTEM_PROMPT_CHARS]


def _chat_system_prompt(container: AppContainer) -> str:
    return _clean_chat_system_prompt(
        str(container.settings.get(KEY_TAURI_AI_CHAT_SYSTEM_PROMPT) or "")
    )


def _target_kind(value: str) -> AiTargetKind:
    normalized = (value or "paste").strip().lower()
    try:
        return TARGET_KIND_MAP[normalized]
    except KeyError as exc:
        raise HTTPException(400, f"Unknown target_kind: {value}") from exc


def _cost_tier(value: str) -> AiCostTier:
    normalized = (value or AiCostTier.BALANCED.value).strip().lower()
    try:
        return AiCostTier(normalized)
    except ValueError as exc:
        raise HTTPException(400, f"Unknown cost_tier: {value}") from exc


def _clean_terms(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(value)
    return cleaned


def _task_extra_instructions(request: AiTaskRequest) -> Optional[str]:
    parts = [
        part.strip()
        for part in (request.instructions, request.extra_instructions)
        if part and part.strip()
    ]
    return "\n\n".join(parts) if parts else None


def _task_attachments(request: AiTaskRequest) -> list[DomainContextAttachment]:
    attachments: list[DomainContextAttachment] = []
    if request.context and request.context.strip():
        attachments.append(
            DomainContextAttachment(
                kind="context",
                ref_id="manual",
                name="Manual context",
                body=request.context.strip()[:MAX_ATTACHMENT_CHARS],
            )
        )
    for item in request.attachments:
        kind = item.kind.strip() or "context"
        ref_id = item.ref_id.strip() or "manual"
        name = item.name.strip() or kind
        body = item.body.strip()
        if not body:
            continue
        attachments.append(
            DomainContextAttachment(
                kind=kind[:80],
                ref_id=ref_id[:120],
                name=name[:160],
                body=body[:MAX_ATTACHMENT_CHARS],
            )
        )
    return attachments


def _domain_task_request(request: AiTaskRequest) -> DomainAiTaskRequest:
    task_enum = TASK_TYPE_MAP.get(request.task_type)
    if not task_enum:
        raise HTTPException(400, f"Unknown task_type: {request.task_type}")
    return DomainAiTaskRequest(
        task_type=task_enum,
        target_kind=_target_kind(request.target_kind),
        text=request.text,
        target_ref_id=request.target_ref_id,
        style=request.style,
        intensity=request.intensity,
        extra_instructions=_task_extra_instructions(request),
        max_output_chars=request.max_output_chars,
        preserve_meaning=request.preserve_meaning,
        preserve_voice=request.preserve_voice,
        forbid_terms=_clean_terms(request.forbid_terms),
        must_keep_terms=_clean_terms(request.must_keep_terms),
        attachments=_task_attachments(request),
        cost_tier=_cost_tier(request.cost_tier),
    )


def _paragraph_count(value: str) -> int:
    return len([part for part in (value or "").splitlines() if part.strip()])


def _task_stats(input_text: str, output_text: str) -> AiTaskResultStats:
    input_chars = len(input_text or "")
    output_chars = len(output_text or "")
    return AiTaskResultStats(
        input_chars=input_chars,
        output_chars=output_chars,
        delta_chars=output_chars - input_chars,
        output_ratio=round(output_chars / input_chars, 3) if input_chars else None,
        input_paragraphs=_paragraph_count(input_text),
        output_paragraphs=_paragraph_count(output_text),
    )


def _friendly_ai_error(exc: Exception) -> str:
    return safe_friendly_ai_error(exc)


def _profile_config_from_raw(raw: dict[str, Any]) -> Optional[_ProfileRuntime]:
    profile_id = str(raw.get("id") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not profile_id or not name or not bool(raw.get("enabled", True)):
        return None
    provider = str(raw.get("provider_name") or "").strip().lower()
    wire_api = str(raw.get("wire_api") or "responses").strip().lower()
    if provider not in SUPPORTED_AI_PROVIDERS or wire_api not in SUPPORTED_WIRE_APIS:
        return _ProfileRuntime(
            profile_id=profile_id,
            profile_name=name,
            config=None,
            error="这个 AI 配置档案已失效，请到设置页重新保存。",
        )
    model = str(raw.get("model") or "").strip()
    if not model:
        return _ProfileRuntime(
            profile_id=profile_id,
            profile_name=name,
            config=None,
            error="这个 AI 配置档案没有填写模型。",
        )
    config = AiConfig(
        provider_name=provider,
        base_url=str(raw.get("base_url") or "").strip() or None,
        wire_api=wire_api,
        model=model,
        api_key_source=str(raw.get("api_key_source") or "env:OPENAI_API_KEY").strip(),
        gemini_cli_proxy=str(raw.get("gemini_cli_proxy") or "").strip() or None,
    )
    return _ProfileRuntime(profile_id=profile_id, profile_name=name, config=config)


def _resolve_compare_profiles(
    profile_ids: list[str],
    container: AppContainer,
    *,
    allow_default_fallback: bool = True,
) -> list[_ProfileRuntime]:
    unique_ids: list[str] = []
    raw_profile_ids = profile_ids if profile_ids else (["default"] if allow_default_fallback else [])
    for raw in raw_profile_ids:
        value = str(raw or "").strip()
        if not value or value in unique_ids:
            continue
        unique_ids.append(value)
    if not unique_ids:
        raise HTTPException(400, "请选择至少一个 AI 配置。")

    raw_profiles, default_profile_id = container.settings.ensure_ai_profile_defaults()
    stored: dict[str, _ProfileRuntime] = {}
    for raw in raw_profiles:
        profile = _profile_config_from_raw(raw)
        if profile is not None:
            stored[profile.profile_id] = profile

    resolved: list[_ProfileRuntime] = []
    for profile_id in unique_ids:
        if profile_id == "default":
            default_profile = stored.get(default_profile_id or "")
            if default_profile is None or default_profile.config is None:
                # Compatibility for old direct API callers. The current UI
                # never advertises this implicit entry on a fresh install.
                default_profile = _ProfileRuntime(
                    profile_id="default",
                    profile_name="默认配置",
                    config=container.settings.load_ai_config(),
                )
            resolved.append(
                _ProfileRuntime(
                    profile_id="default",
                    profile_name=(
                        f"默认 · {default_profile.profile_name}"
                        if default_profile.profile_id != "default"
                        else "默认配置"
                    ),
                    config=default_profile.config,
                )
            )
            continue
        profile = stored.get(profile_id)
        if profile is None:
            resolved.append(
                _ProfileRuntime(
                    profile_id=profile_id,
                    profile_name="已删除的配置档案",
                    config=None,
                    error="这个 AI 配置档案已不存在，请在设置页刷新配置。",
                )
            )
        else:
            resolved.append(profile)
    return resolved


def _compare_profile_snapshot(runtime: _ProfileRuntime) -> AiTaskCompareProfileSnapshot:
    config = runtime.config
    return AiTaskCompareProfileSnapshot(
        profile_id=runtime.profile_id,
        profile_name=runtime.profile_name,
        provider=config.provider_key() if config is not None else "",
        model=config.model if config is not None else "",
    )


def _json_line(payload: BaseModel | dict[str, Any]) -> str:
    data = payload.model_dump() if isinstance(payload, BaseModel) else payload
    return json.dumps(data, ensure_ascii=False) + "\n"


def _job_snapshot(record: AiJobRecord) -> AiJobSnapshot:
    return AiJobSnapshot(
        job_id=record.job_id,
        kind=record.kind,
        status=record.status,
        stage=record.stage,
        stage_label=record.stage_label,
        concept=record.concept,
        motif_id=record.motif_id,
        profile_id=record.profile_id,
        started_at=record.started_at or record.created_at,
        updated_at=record.updated_at,
        elapsed_ms=record.elapsed_ms(),
        result=record.result,
        error=record.error,
        provider=record.provider,
        model=record.model,
        transport=record.transport,
    )


def _article_run_out(record: ArticleTaskRunRecord) -> ArticleTaskRunOut:
    attachment_snapshots = []
    for item in record.request.get("attachments", []):
        if not isinstance(item, dict):
            continue
        body = str(item.get("body") or "").strip()
        attachment_snapshots.append(
            AiTaskAttachmentSnapshotOut(
                kind=str(item.get("kind") or "context")[:80],
                ref_id=str(item.get("ref_id") or "")[:120],
                name=str(item.get("name") or item.get("kind") or "context")[:160],
                size_chars=min(len(body), MAX_ATTACHMENT_CHARS),
            )
        )
    return ArticleTaskRunOut(
        run_id=record.run_id,
        article_id=record.article_id,
        article_title=record.article_title,
        task_type=record.task_type,
        article_hash=record.article_hash,
        original_text=record.target_text,
        selection_start=record.selection_start,
        selection_end=record.selection_end,
        status=record.status,
        stage=record.stage,
        stage_label=record.stage_label,
        error=record.error,
        profiles=record.profiles,
        attachment_snapshots=attachment_snapshots,
        results=[AiTaskCompareResult(**item) for item in record.results],
        created_at=record.created_at,
        started_at=record.started_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
        elapsed_ms=record.elapsed_ms(),
        applied_profile_id=record.applied_profile_id,
        applied_at=record.applied_at,
        applied_version_id=record.applied_version_id,
    )


def _entry_payload(entry: Any) -> dict[str, Any]:
    return {
        "id": entry.id,
        "title": entry.title,
        "body": entry.body,
        "entry_type": entry.entry_type,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "tags": list(entry.tags),
        "archived_at": entry.archived_at,
        "curation_status": entry.curation_status,
    }


def _stream_compare_results(
    *,
    run_id: str,
    profiles: list[_ProfileRuntime],
    domain_request: DomainAiTaskRequest,
    input_text: str,
    container: AppContainer,
) -> Iterable[str]:
    yield _json_line(
        AiTaskCompareStartedEvent(
            run_id=run_id,
            profiles=[_compare_profile_snapshot(profile) for profile in profiles],
        )
    )
    with ThreadPoolExecutor(max_workers=len(profiles)) as executor:
        futures = [
            executor.submit(
                _run_compare_profile,
                profile,
                domain_request,
                input_text,
                container,
            )
            for profile in profiles
        ]
        for future in as_completed(futures):
            result = future.result()
            yield _json_line(
                AiTaskCompareResultEvent(
                    event="result" if result.status == "success" else "error",
                    result=result,
                )
            )
    yield _json_line(AiTaskCompareDoneEvent(run_id=run_id))


def _default_thread_title(
    scope_kind: str,
    scope_id: Optional[str],
    container: AppContainer,
) -> str:
    if scope_kind == "article" and scope_id:
        entry = container.entry_repository.get(scope_id)
        if entry is not None:
            return (entry.title or "").strip() or "Article"
    if scope_kind == "work" and scope_id:
        work = container.work_repository.get(scope_id)
        if work is not None:
            return (work.title or "").strip() or "Work"
    if scope_kind == "collection" and scope_id:
        collection = container.collection_repository.get(scope_id)
        if collection is not None:
            return (collection.name or "").strip() or "Collection"
    return "New Conversation"


def _scope_attachment_for(
    scope_kind: str,
    scope_id: Optional[str],
    container: AppContainer,
) -> Optional[DomainContextAttachment]:
    if scope_kind == "article" and scope_id:
        entry = container.entry_repository.get(scope_id)
        if entry is None:
            raise HTTPException(404, "Article not found")
        return DomainContextAttachment(
            kind="article",
            ref_id=entry.id,
            name=entry.title or "Untitled",
            body=entry.body or "",
        )
    if scope_kind == "work" and scope_id:
        work = container.work_repository.get(scope_id)
        if work is None:
            raise HTTPException(404, "Work not found")
        sections = container.work_section_repository.list_for_work(scope_id)
        parts = [work.summary.strip()] if work.summary.strip() else []
        parts.extend((section.content or "").strip() for section in sections if (section.content or "").strip())
        return DomainContextAttachment(
            kind="work",
            ref_id=work.id,
            name=work.title or "Untitled work",
            body="\n\n".join(parts).strip(),
        )
    if scope_kind == "collection" and scope_id:
        collection = container.collection_repository.get(scope_id)
        if collection is None:
            raise HTTPException(404, "Collection not found")
        entries = container.collection_repository.list_entries(scope_id)
        blocks = []
        if collection.description.strip():
            blocks.append(collection.description.strip())
        for index, entry in enumerate(entries, start=1):
            title = (entry.title or "").strip() or f"Article {index}"
            body = (entry.body or "").strip()
            blocks.append(f"{index}. {title}\n\n{body}".strip())
        return DomainContextAttachment(
            kind="collection",
            ref_id=collection.id,
            name=collection.name or "Untitled collection",
            body="\n\n".join(blocks).strip(),
        )
    return None


def _require_scope_id(scope_kind: str, scope_id: Optional[str]) -> None:
    if scope_kind in {"article", "collection"} and not scope_id:
        raise HTTPException(400, f"scope_id is required for {scope_kind} chat")


def _resolve_thread_for_chat(
    request: ChatRequest,
    container: AppContainer,
) -> tuple[DomainThread, Optional[DomainContextAttachment]]:
    if request.thread_id:
        thread = container.ai_thread_repository.get(request.thread_id)
        if thread is None:
            raise HTTPException(404, "Thread not found")
        scope_attachment = _scope_attachment_for(
            _normalise_scope_kind(thread.scope_kind),
            thread.scope_id,
            container,
        )
        return thread, scope_attachment

    scope_kind = _normalise_scope_kind(request.scope_kind)
    _require_scope_id(scope_kind, request.scope_id)
    scope_attachment = _scope_attachment_for(scope_kind, request.scope_id, container)
    thread = container.ai_thread_service.get_or_create_for_scope(
        _storage_scope_kind(scope_kind),
        request.scope_id,
        title=_default_thread_title(scope_kind, request.scope_id, container),
    )
    return thread, scope_attachment


# ---- Task endpoints (synchronous, long timeout) ----
@router.post("/task", response_model=AiTaskResponse)
def run_ai_task(
    request: AiTaskRequest,
    container: AppContainer = Depends(get_container),
) -> AiTaskResponse:
    """Run an AI task (rewrite, continue, summarize, etc).

    This is SYNCHRONOUS and may take 30-120s. The frontend must set a long
    timeout when calling this endpoint.
    """
    try:
        result = container.ai_task_service.generate(_domain_task_request(request))
        return AiTaskResponse(result=result.content, task_type=request.task_type)
    except Exception as e:
        raise HTTPException(500, f"AI task failed: {_friendly_ai_error(e)}")


@router.post("/jobs/motif-enrichment", response_model=AiJobSnapshot)
def create_motif_enrichment_job(
    request: MotifEnrichmentRequest,
    container: AppContainer = Depends(get_container),
) -> AiJobSnapshot:
    concept = (request.concept or "").strip()
    if not concept and request.motif_id:
        node = container.motif_repository.get_node(request.motif_id)
        concept = node.name if node is not None else ""
    if not concept:
        raise HTTPException(400, "请先输入要丰富的概念或意象。")

    record = ai_job_manager.create(
        kind="motif_enrichment",
        concept=concept,
        motif_id=request.motif_id,
        profile_id=(request.profile_id or "default").strip() or "default",
        worker=lambda update_stage: generate_motif_enrichment_draft_core(
            request,
            container,
            update_stage=update_stage,
        ),
    )
    return _job_snapshot(record)


@router.post("/jobs/motif-relation-discovery", response_model=AiJobSnapshot)
def create_motif_relation_discovery_job(
    request: MotifRelationDiscoveryRequest,
    container: AppContainer = Depends(get_container),
) -> AiJobSnapshot:
    node = container.motif_repository.get_node(request.motif_id)
    if node is None:
        raise HTTPException(404, "这个意象已经不存在，已刷新列表。")
    record = ai_job_manager.create(
        kind="motif_relation_discovery",
        concept=node.name,
        motif_id=node.id,
        profile_id=(request.profile_id or "default").strip() or "default",
        worker=lambda update_stage: generate_motif_relation_discovery_core(
            request,
            container,
            update_stage=update_stage,
        ),
    )
    return _job_snapshot(record)


@router.post("/jobs/ai-card-draft", response_model=AiJobSnapshot)
def create_ai_card_draft_job(
    request: AiCardDraftJobRequest,
    container: AppContainer = Depends(get_container),
) -> AiJobSnapshot:
    card_type = (request.card_type or "scene").strip()
    card_id = (request.card_id or "").strip() or None
    fallback_source = ""
    concept = {"style": "风格卡草稿", "character": "人物卡草稿", "scene": "场景卡草稿"}.get(card_type, "AI 卡片草稿")
    if card_id:
        card = container.ai_card_repository.get(card_id)
        if not card:
            raise HTTPException(404, "AI Card not found")
        fallback_source = f"{card.name}\n\n{card.body}"
        concept = (card.name or "").strip() or concept

    record = ai_job_manager.create(
        kind="ai_card_draft",
        concept=concept,
        motif_id=card_id,
        profile_id=(request.profile_id or "default").strip() or "default",
        worker=lambda update_stage: generate_ai_card_draft_core(
            request=request,
            container=container,
            fallback_source=fallback_source,
            update_stage=update_stage,
        ),
    )
    return _job_snapshot(record)


@router.get("/jobs/{job_id}", response_model=AiJobSnapshot)
def get_ai_job(job_id: str) -> AiJobSnapshot:
    return _job_snapshot(ai_job_manager.get(job_id))


@router.post("/jobs/{job_id}/cancel", response_model=AiJobSnapshot)
def cancel_ai_job(job_id: str) -> AiJobSnapshot:
    return _job_snapshot(ai_job_manager.cancel(job_id))


def _run_compare_profile(
    runtime: _ProfileRuntime,
    domain_request: DomainAiTaskRequest,
    input_text: str,
    container: AppContainer,
) -> AiTaskCompareResult:
    started = time.perf_counter()
    config = runtime.config
    if config is None:
        return AiTaskCompareResult(
            profile_id=runtime.profile_id,
            profile_name=runtime.profile_name,
            provider="",
            model="",
            status="error",
            error=runtime.error or "这个 AI 配置档案不可用。",
            elapsed_ms=0,
            stats=_task_stats(input_text, ""),
        )

    issues = preflight_rewrite(config, input_text, has_entry=True)
    if issues:
        return AiTaskCompareResult(
            profile_id=runtime.profile_id,
            profile_name=runtime.profile_name,
            provider=config.provider_key(),
            model=config.model,
            transport=None,
            status="error",
            error=safe_friendly_ai_error(format_issues(issues)),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            stats=_task_stats(input_text, ""),
        )

    prompt_builder = PromptBuilder()
    task_service = AiTaskService(
        provider_factory=lambda: provider_for_config(config, prompt_builder),
        settings=container.settings,
        prompt_builder=TaskPromptBuilder(),
    )
    try:
        response = task_service.generate(domain_request, model_override=config.model)
    except Exception as exc:  # noqa: BLE001
        return AiTaskCompareResult(
            profile_id=runtime.profile_id,
            profile_name=runtime.profile_name,
            provider=config.provider_key(),
            model=config.model,
            transport=None,
            status="error",
            error=_friendly_ai_error(exc),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            stats=_task_stats(input_text, ""),
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return AiTaskCompareResult(
        profile_id=runtime.profile_id,
        profile_name=runtime.profile_name,
        provider=response.provider or config.provider_key(),
        model=response.model or config.model,
        transport=response.transport,
        status="success",
        result=response.content,
        error="",
        elapsed_ms=elapsed_ms,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost=response.cost,
        finish_reason=response.finish_reason,
        stats=_task_stats(input_text, response.content),
    )


@router.post("/task/compare", response_model=AiTaskCompareResponse)
def compare_ai_task(
    request: AiTaskCompareRequest,
    container: AppContainer = Depends(get_container),
) -> AiTaskCompareResponse:
    """Run the same AI task against the selected AI profiles."""

    domain_request = _domain_task_request(request)
    profiles = _resolve_compare_profiles(
        request.profile_ids,
        container,
        allow_default_fallback="profile_ids" not in request.model_fields_set,
    )
    if len(profiles) == 1:
        results = [_run_compare_profile(profiles[0], domain_request, request.text, container)]
    else:
        with ThreadPoolExecutor(max_workers=len(profiles)) as executor:
            futures = [
                executor.submit(
                    _run_compare_profile,
                    profile,
                    domain_request,
                    request.text,
                    container,
                )
                for profile in profiles
            ]
            results = [future.result() for future in futures]
    return AiTaskCompareResponse(task_type=request.task_type, results=results)


@router.post("/task/compare/stream")
def compare_ai_task_stream(
    request: AiTaskCompareRequest,
    container: AppContainer = Depends(get_container),
) -> StreamingResponse:
    """Run an AI comparison and stream each model result as it completes."""

    domain_request = _domain_task_request(request)
    profiles = _resolve_compare_profiles(
        request.profile_ids,
        container,
        allow_default_fallback="profile_ids" not in request.model_fields_set,
    )
    run_id = uuid.uuid4().hex
    return StreamingResponse(
        _stream_compare_results(
            run_id=run_id,
            profiles=profiles,
            domain_request=domain_request,
            input_text=request.text,
            container=container,
        ),
        media_type="application/x-ndjson",
    )


@router.post("/task-runs", response_model=ArticleTaskRunOut, status_code=202)
def create_article_task_run(
    request: ArticleTaskRunCreate,
    container: AppContainer = Depends(get_container),
) -> ArticleTaskRunOut:
    if request.task_type not in {"polish", "rewrite", "expand", "continue"}:
        raise HTTPException(400, "文章 AI 修改只支持润色、改写、扩写和续写。")
    article = container.entry_repository.get((request.article_id or "").strip())
    if article is None:
        raise HTTPException(404, "文章不存在，可能已被删除。")

    body = article.body or ""
    start = request.selection_start
    end = request.selection_end
    if (start is None) != (end is None):
        raise HTTPException(400, "选区起止位置必须同时提供。")
    if start is not None and end is not None:
        if start < 0 or end < start or end > len(body):
            raise HTTPException(400, "文章选区已经失效，请回到文章页重新选择。")
        if start == end:
            start = None
            end = None
    target_text = body[start:end] if start is not None and end is not None else body
    if not target_text.strip():
        raise HTTPException(400, "文章或选区没有可处理的正文。")

    task_request = AiTaskRequest(
        task_type=request.task_type,
        text=target_text,
        instructions=request.instructions,
        context=request.context,
        target_kind="selection" if start is not None else "article",
        target_ref_id=article.id,
        style=request.style,
        intensity=request.intensity,
        extra_instructions=request.extra_instructions,
        max_output_chars=request.max_output_chars,
        preserve_meaning=request.preserve_meaning,
        preserve_voice=request.preserve_voice,
        forbid_terms=request.forbid_terms,
        must_keep_terms=request.must_keep_terms,
        attachments=request.attachments,
        cost_tier=request.cost_tier,
    )
    domain_request = _domain_task_request(task_request)
    profiles = _resolve_compare_profiles(
        request.profile_ids,
        container,
        allow_default_fallback=False,
    )
    profile_snapshots = [
        _compare_profile_snapshot(profile).model_dump()
        for profile in profiles
    ]
    pending_results = [
        AiTaskCompareResult(
            profile_id=profile.profile_id,
            profile_name=profile.profile_name,
            provider=profile.config.provider_key() if profile.config is not None else "",
            model=profile.config.model if profile.config is not None else "",
            status="pending",
            stats=_task_stats(target_text, ""),
        ).model_dump()
        for profile in profiles
    ]
    run_id = uuid.uuid4().hex
    record = ArticleTaskRunRecord(
        run_id=run_id,
        article_id=article.id,
        article_title=(article.title or "").strip() or "未命名文章",
        task_type=request.task_type,
        article_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        article_body=body,
        target_text=target_text,
        selection_start=start,
        selection_end=end,
        request=task_request.model_dump(),
        profiles=profile_snapshots,
        results=pending_results,
    )

    def worker(active_run_id: str) -> None:
        article_task_run_manager.set_stage(active_run_id, "sending_request")
        executor = ThreadPoolExecutor(max_workers=min(8, len(profiles)))
        cancelled = False
        try:
            future_profiles = {
                executor.submit(
                    _run_compare_profile,
                    profile,
                    domain_request,
                    target_text,
                    container,
                ): profile.profile_id
                for profile in profiles
            }
            article_task_run_manager.set_stage(active_run_id, "waiting_model")
            pending = set(future_profiles)
            while pending:
                if article_task_run_manager.is_cancelled(active_run_id):
                    cancelled = True
                    for future in pending:
                        future.cancel()
                    return
                done, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                for future in done:
                    result = future.result()
                    article_task_run_manager.set_result(
                        active_run_id,
                        result.profile_id,
                        result.model_dump(),
                    )
        finally:
            executor.shutdown(wait=not cancelled, cancel_futures=cancelled)
        article_task_run_manager.complete(active_run_id)

    return _article_run_out(article_task_run_manager.create(record, worker))


@router.get("/task-runs/active", response_model=Optional[ArticleTaskRunOut])
def get_latest_article_task_run() -> Optional[ArticleTaskRunOut]:
    record = article_task_run_manager.latest()
    return _article_run_out(record) if record is not None else None


@router.get("/task-runs/{run_id}", response_model=ArticleTaskRunOut)
def get_article_task_run(run_id: str) -> ArticleTaskRunOut:
    return _article_run_out(article_task_run_manager.get(run_id))


@router.post("/task-runs/{run_id}/cancel", response_model=ArticleTaskRunOut)
def cancel_article_task_run(run_id: str) -> ArticleTaskRunOut:
    return _article_run_out(article_task_run_manager.cancel(run_id))


def _apply_article_task_run(
    run_id: str,
    data: ArticleTaskRunApply,
    container: AppContainer,
) -> ArticleTaskApplyOut:
    record = article_task_run_manager.get(run_id)
    profile_id = (data.profile_id or "").strip()
    if record.applied_profile_id:
        if record.applied_profile_id != profile_id:
            raise HTTPException(409, "这轮结果已经写回文章，不能再写入另一个模型结果。")
        if record.applied_entry is None or not record.applied_version_id:
            raise HTTPException(409, "这轮结果已经写回，请刷新文章查看。")
        return ArticleTaskApplyOut(
            run=_article_run_out(record),
            entry=record.applied_entry,
            version_id=record.applied_version_id,
            was_noop=True,
        )
    if record.status != "succeeded":
        raise HTTPException(400, "任务尚未完成，暂时不能写回文章。")
    result = next(
        (
            item for item in record.results
            if str(item.get("profile_id") or "") == profile_id
            and item.get("status") == "success"
        ),
        None,
    )
    if result is None:
        raise HTTPException(400, "请选择一个已经成功返回的模型结果。")

    entry = container.entry_repository.get(record.article_id)
    if entry is None:
        raise HTTPException(404, "原文章已不存在，不能写回。")
    current_hash = hashlib.sha256((entry.body or "").encode("utf-8")).hexdigest()
    if current_hash != record.article_hash:
        raise HTTPException(
            409,
            "文章在 AI 运行后已经发生变化。为避免覆盖新内容，请重新运行；当前结果仍可复制。",
        )

    generated = str(result.get("result") or "")
    if not generated.strip():
        raise HTTPException(400, "这个模型没有返回可写入的内容。")
    start = record.selection_start
    end = record.selection_end
    if record.task_type == "continue":
        insert_at = end if start is not None and end is not None else len(entry.body)
        before = entry.body[:insert_at]
        after = entry.body[insert_at:]
        before_separator = "" if not before or before.endswith(("\n", " ")) else "\n\n"
        after_separator = (
            ""
            if not after or generated.endswith(("\n", " ")) or after.startswith(("\n", " "))
            else "\n\n"
        )
        next_body = before + before_separator + generated + after_separator + after
    elif start is not None and end is not None:
        next_body = entry.body[:start] + generated + entry.body[end:]
    else:
        next_body = generated

    version = container.version_history_service.save_ai_before_apply(
        entry.id,
        label=f"AI {record.task_type}",
        provider=str(result.get("provider") or "") or None,
        model=str(result.get("model") or "") or None,
    )
    updated = container.entry_repository.update(
        entry.id,
        title=entry.title,
        body=next_body,
        tags=entry.tags,
    )
    if updated is None:
        raise HTTPException(404, "原文章已不存在，不能写回。")
    payload = _entry_payload(updated)
    applied = article_task_run_manager.mark_applied(
        run_id,
        profile_id=profile_id,
        version_id=version.id,
        entry=payload,
    )
    return ArticleTaskApplyOut(
        run=_article_run_out(applied),
        entry=payload,
        version_id=version.id,
    )


@router.post("/task-runs/{run_id}/apply", response_model=ArticleTaskApplyOut)
def apply_article_task_run(
    run_id: str,
    data: ArticleTaskRunApply,
    container: AppContainer = Depends(get_container),
) -> ArticleTaskApplyOut:
    # A double-click, retry, or second window must observe the first apply
    # before it can create another version or mutate the article again.
    with _article_task_apply_lock:
        return _apply_article_task_run(run_id, data, container)


@router.delete("/task-runs/{run_id}", status_code=204)
def delete_article_task_run(run_id: str):
    article_task_run_manager.delete(run_id)


def _clean_task_presets(raw: Any) -> dict[str, list[AiTaskPreset]]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    if not isinstance(raw, dict):
        return {}

    cleaned: dict[str, list[AiTaskPreset]] = {}
    for task_type, values in raw.items():
        if task_type not in SUPPORTED_TASK_PRESET_TYPES or not isinstance(values, list):
            continue
        presets: list[AiTaskPreset] = []
        seen_names: set[str] = set()
        for value in values[:MAX_PRESETS_PER_TASK]:
            item = value.model_dump() if isinstance(value, AiTaskPreset) else value
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            lowered = name.lower()
            if lowered in seen_names:
                continue
            seen_names.add(lowered)
            controls = item.get("controls")
            if not isinstance(controls, dict):
                controls = {}
            preset_id = str(item.get("id", "")).strip() or uuid.uuid4().hex
            presets.append(
                AiTaskPreset(
                    id=preset_id[:80],
                    task_type=task_type,
                    name=name[:80],
                    controls=controls,
                )
            )
        if presets:
            cleaned[task_type] = presets
    return cleaned


@router.get("/task-presets", response_model=dict[str, list[AiTaskPreset]])
def list_task_presets(
    container: AppContainer = Depends(get_container),
) -> dict[str, list[AiTaskPreset]]:
    return _clean_task_presets(container.settings.get(KEY_TAURI_AI_TASK_PRESETS))


@router.put("/task-presets", response_model=dict[str, list[AiTaskPreset]])
def save_task_presets(
    presets: dict[str, list[AiTaskPreset]],
    container: AppContainer = Depends(get_container),
) -> dict[str, list[AiTaskPreset]]:
    cleaned = _clean_task_presets(presets)
    if cleaned:
        container.settings.set(
            KEY_TAURI_AI_TASK_PRESETS,
            json.dumps(
                {
                    task_type: [preset.model_dump() for preset in values]
                    for task_type, values in cleaned.items()
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
    else:
        container.settings_repository.delete(KEY_TAURI_AI_TASK_PRESETS)
    return cleaned


@router.get("/chat-settings", response_model=ChatSettings)
def get_chat_settings(
    container: AppContainer = Depends(get_container),
) -> ChatSettings:
    return ChatSettings(system_prompt=_chat_system_prompt(container))


@router.put("/chat-settings", response_model=ChatSettings)
def save_chat_settings(
    settings: ChatSettings,
    container: AppContainer = Depends(get_container),
) -> ChatSettings:
    cleaned = _clean_chat_system_prompt(settings.system_prompt)
    if cleaned:
        container.settings.set(KEY_TAURI_AI_CHAT_SYSTEM_PROMPT, cleaned)
    else:
        container.settings_repository.delete(KEY_TAURI_AI_CHAT_SYSTEM_PROMPT)
    return ChatSettings(system_prompt=cleaned)


# ---- Thread management ----
@router.get("/threads", response_model=list[ThreadOut])
def list_threads(
    container: AppContainer = Depends(get_container),
) -> list[ThreadOut]:
    rows = container.connection.execute(
        """
        SELECT * FROM ai_threads
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 50
        """
    ).fetchall()
    threads = [
        DomainThread(
            id=row["id"],
            scope_kind=row["scope_kind"],
            scope_id=row["scope_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
    return [_thread_to_dto(t) for t in threads]


@router.post("/threads", response_model=ThreadOut, status_code=201)
def create_thread(
    data: ThreadCreate,
    container: AppContainer = Depends(get_container),
) -> ThreadOut:
    scope_kind = _normalise_scope_kind(data.scope_kind)
    thread = container.ai_thread_repository.create(
        scope_kind=_storage_scope_kind(scope_kind),
        scope_id=data.scope_id,
        title=data.title,
    )
    return _thread_to_dto(thread)


@router.get("/threads/current", response_model=Optional[CurrentThreadOut])
def get_current_thread(
    scope_kind: str = Query("global"),
    scope_id: Optional[str] = Query(None),
    create: bool = Query(False),
    container: AppContainer = Depends(get_container),
) -> Optional[CurrentThreadOut]:
    normalized_scope = _normalise_scope_kind(scope_kind)
    _require_scope_id(normalized_scope, scope_id)
    storage_scope = _storage_scope_kind(normalized_scope)
    if create:
        thread = container.ai_thread_service.get_or_create_for_scope(
            storage_scope,
            scope_id,
            title=_default_thread_title(normalized_scope, scope_id, container),
        )
    else:
        thread = container.ai_thread_repository.latest_for_scope(storage_scope, scope_id)
    if thread is None:
        return None
    return CurrentThreadOut(
        thread=_thread_to_dto(thread),
        messages=[_message_to_dto(message) for message in container.ai_thread_service.history(thread.id)],
    )


@router.get("/threads/{thread_id}/messages", response_model=list[MessageOut])
def get_thread_messages(
    thread_id: str,
    container: AppContainer = Depends(get_container),
) -> list[MessageOut]:
    thread = container.ai_thread_repository.get(thread_id)
    if thread is None:
        raise HTTPException(404, "Thread not found")
    return [_message_to_dto(message) for message in container.ai_thread_service.history(thread_id)]


@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(
    thread_id: str,
    container: AppContainer = Depends(get_container),
):
    thread = container.ai_thread_repository.get(thread_id)
    if thread is None:
        raise HTTPException(404, "Thread not found")
    container.ai_thread_repository.delete(thread_id)


# ---- Chat (synchronous) ----
@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    container: AppContainer = Depends(get_container),
) -> ChatResponse:
    """Send a message to a thread and get the assistant's reply.

    Synchronous. May take 10-60s depending on the model.
    """
    try:
        thread, scope_attachment = _resolve_thread_for_chat(request, container)

        profile_id = (request.profile_id or "default").strip() or "default"
        runtime: Optional[_ProfileRuntime] = None
        provider = None
        if request.profile_id is not None and profile_id != "default":
            runtime = _resolve_compare_profiles(
                [profile_id],
                container,
                allow_default_fallback=False,
            )[0]
            if runtime.config is None:
                raise HTTPException(400, runtime.error or "这个 AI 配置档案不可用。")
            prompt_builder = PromptBuilder()
            provider = provider_for_config(runtime.config, prompt_builder)

        message_profile_id = (
            runtime.profile_id
            if runtime is not None
            else container.settings.load_ai_default_profile_id()
        )

        # Call AI service (this is where the long blocking call happens)
        turn = container.ai_thread_service.send(
            thread_id=thread.id,
            user_text=request.message,
            scope_attachment=scope_attachment,
            system_prompt=_chat_system_prompt(container),
            provider_override=provider,
            model_override=runtime.config.model if runtime and runtime.config else None,
            profile_id=message_profile_id,
        )

        return ChatResponse(
            thread_id=thread.id,
            user_message=MessageOut(
                id=turn.user_message.id,
                thread_id=turn.user_message.thread_id,
                role="user",
                content=turn.user_message.content,
                timestamp=turn.user_message.created_at,
            ),
            assistant_message=MessageOut(
                id=turn.assistant_message.id,
                thread_id=turn.assistant_message.thread_id,
                role="assistant",
                content=turn.assistant_message.content,
                timestamp=turn.assistant_message.created_at,
                meta=_message_to_dto(turn.assistant_message).meta,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, _friendly_ai_error(e))
