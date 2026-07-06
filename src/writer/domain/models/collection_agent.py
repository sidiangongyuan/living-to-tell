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

COLLECTION_AGENT_ACTION_TYPES = {
    "update_memory",
    "create_outline_item",
    "update_outline_item",
    "create_article_note",
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


@dataclass(frozen=True)
class CollectionAgentSettings:
    collection_id: str
    profile_id: str = "default"
    enabled: bool = True
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
