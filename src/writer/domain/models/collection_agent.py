"""Domain models for collection-bound writing agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


COLLECTION_AGENT_SCOPE = "collection_agent"

COLLECTION_AGENT_MEMORY_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("project_core", "项目核心", "题材、核心命题、主要冲突、叙事承诺。"),
    ("characters", "人物与关系", "主要人物、欲望、矛盾、关系变化。"),
    ("timeline", "时间线", "关键事件顺序、断点、未确认时间。"),
    ("world", "地点与世界", "空间、制度、规则、重要环境。"),
    ("style", "主题与风格", "叙事口吻、审美约束、禁用方向。"),
    ("foreshadowing", "伏笔与线索", "已埋线索、待回收线索、风险提示。"),
    ("decisions", "决策记录", "用户确认过的 canon 事实和结构决定。"),
    ("open_questions", "未解决问题", "还没定下来的设定、人物、结构问题。"),
)

_COLLECTION_AGENT_MEMORY_SECTION_ALIASES = {
    "project_core": "project_core",
    "project": "project_core",
    "core_theme": "project_core",
    "central_theme": "project_core",
    "premise": "project_core",
    "项目核心": "project_core",
    "核心命题": "project_core",
    "核心冲突": "project_core",
    "哲学基调": "project_core",
    "characters": "characters",
    "character": "characters",
    "character_relationships": "characters",
    "relationships": "characters",
    "人物与关系": "characters",
    "人物": "characters",
    "角色": "characters",
    "timeline": "timeline",
    "chronology": "timeline",
    "时间线": "timeline",
    "事件顺序": "timeline",
    "world": "world",
    "worldbuilding": "world",
    "setting": "world",
    "places": "world",
    "地点与世界": "world",
    "世界观": "world",
    "地点": "world",
    "style": "style",
    "themes": "style",
    "themes_and_style": "style",
    "tone": "style",
    "voice": "style",
    "主题与风格": "style",
    "主题": "style",
    "风格": "style",
    "foreshadowing": "foreshadowing",
    "clues": "foreshadowing",
    "setup_payoff": "foreshadowing",
    "伏笔与线索": "foreshadowing",
    "伏笔": "foreshadowing",
    "线索": "foreshadowing",
    "decisions": "decisions",
    "decision_log": "decisions",
    "canon": "decisions",
    "决策记录": "decisions",
    "决策": "decisions",
    "open_questions": "open_questions",
    "unresolved_questions": "open_questions",
    "unknowns": "open_questions",
    "未解决问题": "open_questions",
    "待确认问题": "open_questions",
}


def normalize_collection_agent_memory_section_id(
    value: str,
    *hints: str,
) -> Optional[str]:
    """Map provider-friendly section labels back to the fixed Project Bible schema."""

    def normalized_key(raw: str) -> str:
        chunks: list[str] = []
        previous_separator = False
        for character in (raw or "").strip().casefold():
            if character.isalnum():
                chunks.append(character)
                previous_separator = False
            elif chunks and not previous_separator:
                chunks.append("_")
                previous_separator = True
        return "".join(chunks).strip("_")

    candidates = [value, *hints]
    normalized_candidates = [normalized_key(item) for item in candidates if (item or "").strip()]
    for candidate in normalized_candidates:
        direct = _COLLECTION_AGENT_MEMORY_SECTION_ALIASES.get(candidate)
        if direct:
            return direct
        for section_id, _title, _help in COLLECTION_AGENT_MEMORY_SECTIONS:
            if candidate.startswith(f"{section_id}_") or candidate.endswith(f"_{section_id}"):
                return section_id

    markers: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("project_core", ("projectcore", "coretheme", "centraltheme", "premise", "项目核心", "核心命题", "核心冲突", "哲学基调", "叙事承诺")),
        ("characters", ("character", "relationship", "人物", "角色", "关系")),
        ("timeline", ("timeline", "chronology", "时间线", "事件顺序")),
        ("world", ("world", "setting", "location", "place", "世界", "地点", "设定")),
        ("style", ("theme", "style", "tone", "voice", "主题", "风格", "口吻", "审美")),
        ("foreshadowing", ("foreshadow", "clue", "setup", "payoff", "伏笔", "线索")),
        ("decisions", ("decision", "canon", "决策", "已确认")),
        ("open_questions", ("openquestion", "unresolved", "unknown", "未解决", "待确认", "未定")),
    )
    for candidate in normalized_candidates:
        compact = candidate.replace("_", "")
        for section_id, section_markers in markers:
            if any(marker in compact for marker in section_markers):
                return section_id
    return None

COLLECTION_AGENT_ACTION_TYPES = {
    "update_memory",
    "create_outline_item",
    "update_outline_item",
    "create_article_note",
    "update_author_portrait",
}
COLLECTION_AGENT_ACTION_STATUSES = {"pending", "applied", "rejected", "deferred"}
COLLECTION_AGENT_RUN_STATUSES = {
    "queued",
    "preparing_context",
    "sending_request",
    "waiting_model",
    "parsing_response",
    "building_proposals",
    "succeeded",
    "failed",
    "cancelled",
}

COLLECTION_AGENT_STAGE_LABELS = {
    "queued": "排队中",
    "preparing_context": "整理作品集上下文",
    "sending_request": "发送请求",
    "waiting_model": "已发送请求，等待模型返回",
    "parsing_response": "解析 Agent 回答",
    "building_proposals": "整理可确认提案",
    "succeeded": "已完成",
    "failed": "失败",
    "cancelled": "已中断",
}

COLLECTION_AGENT_MODES = {"discuss", "plan", "draft", "review"}
COLLECTION_AGENT_DRAFT_STATUSES = {"draft", "applied"}
COLLECTION_AGENT_STYLE_SAMPLE_STATUSES = {"active", "completed"}


@dataclass(frozen=True)
class CollectionAgentSettings:
    collection_id: str
    profile_id: str = "default"
    enabled: bool = True
    active_session_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class CollectionAgentMemory:
    collection_id: str
    sections: dict[str, str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass(frozen=True)
class CollectionAgentRun:
    id: str
    collection_id: str
    thread_id: Optional[str]
    user_message_id: Optional[str]
    assistant_message_id: Optional[str]
    status: str
    stage: str
    stage_label: str
    request: dict[str, Any]
    result: dict[str, Any]
    error: str
    profile_id: str
    provider: Optional[str]
    model: Optional[str]
    transport: Optional[str]
    session_id: Optional[str]
    mode: str
    draft_id: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]


@dataclass(frozen=True)
class CollectionAgentAction:
    id: str
    collection_id: str
    run_id: Optional[str]
    action_type: str
    status: str
    title: str
    summary: str
    payload: dict[str, Any]
    preview: dict[str, Any]
    reason: str
    risk: str
    applied_ref_id: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    applied_at: Optional[str]


@dataclass(frozen=True)
class CollectionAgentSession:
    id: str
    collection_id: str
    thread_id: str
    title: str
    mode: str
    summary: str
    archived: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    last_message_at: Optional[str]


@dataclass(frozen=True)
class CollectionAgentDraft:
    id: str
    collection_id: str
    session_id: str
    run_id: Optional[str]
    parent_draft_id: Optional[str]
    title: str
    content: str
    brief: dict[str, Any]
    variant_label: str
    status: str
    target_entry_id: Optional[str]
    applied_ref_id: Optional[str]
    content_hash: str
    created_at: Optional[str]
    updated_at: Optional[str]
    applied_at: Optional[str]


@dataclass(frozen=True)
class CollectionAgentStyleSample:
    id: str
    collection_id: str
    entry_id: str
    original_body: str
    final_body: str
    status: str
    created_at: Optional[str]
    completed_at: Optional[str]


@dataclass(frozen=True)
class AuthorPortrait:
    id: str
    tags: list[str]
    summary: str
    evidence_count: int
    created_at: Optional[str]
    updated_at: Optional[str]


@dataclass(frozen=True)
class AuthorPortraitVersion:
    id: str
    portrait_id: str
    tags: list[str]
    summary: str
    evidence_count: int
    reason: str
    created_at: Optional[str]
