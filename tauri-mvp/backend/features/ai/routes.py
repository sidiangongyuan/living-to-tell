"""AI workspace: task services (rewrite, continue, summarize) + thread chat.

Exposes AiTaskService, AiThreadService, and RewriteService from the container.
Long-running AI calls are synchronous with extended timeout (handled by frontend).
"""
from __future__ import annotations

import json
import uuid
from typing import Any
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.enums import AiCostTier, AiTargetKind, AiTaskType
from writer.domain.models.ai_thread import AiThread as DomainThread
from writer.domain.models.ai_thread import AiMessage as DomainMessage
from writer.services.ai.task_types import (
    AiContextAttachment as DomainContextAttachment,
)
from writer.services.ai.task_types import AiTaskRequest as DomainAiTaskRequest

router = APIRouter(prefix="/api/ai", tags=["ai"])

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
    task_enum = TASK_TYPE_MAP.get(request.task_type)
    if not task_enum:
        raise HTTPException(400, f"Unknown task_type: {request.task_type}")

    try:
        result = container.ai_task_service.generate(
            DomainAiTaskRequest(
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
        )
        return AiTaskResponse(result=result.content, task_type=request.task_type)
    except Exception as e:
        raise HTTPException(500, f"AI task failed: {str(e)}")


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

        # Call AI service (this is where the long blocking call happens)
        turn = container.ai_thread_service.send(
            thread_id=thread.id,
            user_text=request.message,
            scope_attachment=scope_attachment,
            system_prompt=_chat_system_prompt(container),
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
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")
