"""AI Card API for reusable style / character / scene context cards."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.enums import AiCostTier
from writer.domain.models.ai_card import AiCard as DomainCard
from writer.storage.repositories.entry_repository import parse_tags

router = APIRouter(prefix="/api/ai-cards", tags=["ai-cards"])
SETTING_CLEANUP_KEY = "tauri.ai_cards.deleted_setting_cards_v1"
VALID_CARD_TYPES = {"style", "character", "scene"}
MAX_DRAFT_SOURCE_CHARS = 12000


CARD_TEMPLATES = {
    "style": """【语言质感】

【句法节奏】

【叙述距离】

【意象偏好】

【情绪温度】

【适用场景】

【禁忌】

【可迁移写法】

【参考原文（可选）】
""",
    "character": """【角色核心】

【外在身份】

【核心欲望】

【核心恐惧】

【行动模式】

【说话方式】

【关系张力】

【成长/崩塌方向】

【可替换元素】

【参考原文（可选）】
""",
    "scene": """【场景原型】

【触发条件】

【核心冲突】

【关键动作】

【情绪曲线】

【叙事功能】

【场景DNA】

【可替换元素】

【参考原文（可选）】
""",
}


class AiCardOut(BaseModel):
    id: str
    title: str
    content: str
    card_type: str
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[str]
    updated_at: Optional[str]


class AiCardCreate(BaseModel):
    title: str
    content: str = ""
    card_type: str = "style"
    tags: list[str] = Field(default_factory=list)


class AiCardUpdate(BaseModel):
    title: str
    content: str
    card_type: str = "style"
    tags: list[str] = Field(default_factory=list)


class AiCardDraftRequest(BaseModel):
    card_type: str
    source_text: str
    keep_source_quotes: bool = False
    cost_tier: str = "strong"


class AiCardDraftOut(BaseModel):
    title: str
    card_type: str
    content: str
    tags: list[str] = Field(default_factory=list)


def _card_to_dto(card: DomainCard) -> AiCardOut:
    return AiCardOut(
        id=card.id,
        title=card.name or "",
        content=card.body or "",
        card_type=card.kind or "style",
        tags=card.tags,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


def _clean_tags(values: list[str] | None) -> list[str]:
    return parse_tags(", ".join(values or []))


def _clean_card_type(value: str | None, *, reject_setting: bool = True) -> str:
    normalized = (value or "style").strip().lower()
    if normalized == "setting" and reject_setting:
        raise HTTPException(400, "设定卡已移除，请使用风格、人物或场景卡。")
    if normalized not in VALID_CARD_TYPES:
        raise HTTPException(400, f"Unsupported AI card type: {value}")
    return normalized


def _cleanup_setting_cards(container: AppContainer) -> None:
    if container.settings_repository.get(SETTING_CLEANUP_KEY) == "1":
        return
    container.connection.execute("DELETE FROM ai_cards WHERE kind = ?", ("setting",))
    container.settings_repository.set(SETTING_CLEANUP_KEY, "1")


def _draft_template_for(card_type: str) -> str:
    return CARD_TEMPLATES[_clean_card_type(card_type)]


def _draft_system_prompt() -> str:
    return (
        "你是一个写作工具里的 AI 卡片生成器，不是聊天助手。"
        "你的任务是把输入材料提炼成可引用、可作为 AI 提示词上下文、也方便作者阅读的写作卡片。"
        "输出必须具体、克制、可迁移，避免空泛评价。"
        "只输出一个 JSON 对象，不要 Markdown，不要代码块，不要解释。"
        "JSON schema: {\"title\": string, \"card_type\": string, \"content\": string, \"tags\": string[]}。"
    )


def _draft_user_prompt(card_type: str, source_text: str, keep_source_quotes: bool) -> str:
    type_name = {"style": "风格卡", "character": "人物卡", "scene": "场景卡"}[card_type]
    quote_policy = (
        "允许在【参考原文（可选）】中保留 1-3 句最有代表性的原文锚点。"
        if keep_source_quotes
        else "不要保留原文摘录；【参考原文（可选）】留空或写“无”。"
    )
    return f"""请根据下面材料生成一张{type_name}草稿。

要求：
- title 控制在 40 个中文字符以内。
- card_type 必须严格等于 "{card_type}"。
- content 必须使用下方模板标题，标题不可改名、不可遗漏。
- 内容要像“可引用的写作工作卡”：既方便作者扫读，也能直接作为 AI 上下文使用。
- 每个栏目写短句或要点，优先给可执行约束、观察、禁忌和可迁移写法，不写百科长文。
- tags 返回 2-6 个短标签，便于检索和引用。
- {quote_policy}
- 如果材料不足，也要给出谨慎、可编辑的草稿，不要编造具体事实。

固定模板：
{_draft_template_for(card_type)}

输入材料：
{source_text[:MAX_DRAFT_SOURCE_CHARS].strip()}
"""


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    match = _JSON_FENCE.search(text or "")
    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed if isinstance(parsed, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    start = (text or "").find("{")
    end = (text or "").rfind("}")
    if 0 <= start < end:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    return None


def _coerce_draft(payload: dict[str, Any], expected_type: str) -> AiCardDraftOut:
    title = str(payload.get("title", "")).strip()
    content = str(payload.get("content", "")).strip()
    returned_type = _clean_card_type(str(payload.get("card_type", "")).strip())
    raw_tags = payload.get("tags", [])
    if isinstance(raw_tags, str):
        tags = parse_tags(raw_tags)
    elif isinstance(raw_tags, list):
        tags = _clean_tags([str(tag) for tag in raw_tags])
    else:
        tags = []
    if returned_type != expected_type:
        raise HTTPException(502, "AI 返回的卡片类型与请求不一致。")
    if not title or not content:
        raise HTTPException(502, "AI 返回的卡片草稿缺少标题或内容。")
    return AiCardDraftOut(title=title[:80], card_type=returned_type, content=content, tags=tags[:8])


def _cost_tier(value: str) -> AiCostTier:
    try:
        return AiCostTier((value or AiCostTier.STRONG.value).strip().lower())
    except ValueError as exc:
        raise HTTPException(400, f"Unknown cost_tier: {value}") from exc


def _friendly_ai_card_error(exc: Exception) -> str:
    raw = str(exc).strip()
    if "HTTP 403" in raw:
        return (
            "AI 服务拒绝了当前请求。可能是中转接口协议不匹配、"
            "模型无权限或密钥无效。"
        )
    if "<html" in raw.lower() or "<!doctype html" in raw.lower():
        return "AI 服务返回了网页错误页，请检查中转地址、模型权限和密钥。"
    return raw or exc.__class__.__name__


def _generate_draft(
    *,
    request: AiCardDraftRequest,
    container: AppContainer,
    fallback_source: str = "",
) -> AiCardDraftOut:
    card_type = _clean_card_type(request.card_type)
    source = (request.source_text or fallback_source or "").strip()
    if not source:
        raise HTTPException(400, "请先提供用于生成卡片的材料。")
    try:
        response = container.ai_task_service.generate_from_messages(
            [
                {"role": "system", "content": _draft_system_prompt()},
                {
                    "role": "user",
                    "content": _draft_user_prompt(
                        card_type,
                        source,
                        request.keep_source_quotes,
                    ),
                },
            ],
            cost_tier=_cost_tier(request.cost_tier),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"AI 卡片生成失败：{_friendly_ai_card_error(exc)}") from exc
    parsed = _parse_json_object(response.content)
    if parsed is None:
        raise HTTPException(502, "AI 没有返回可解析的卡片 JSON。")
    return _coerce_draft(parsed, card_type)


@router.get("", response_model=list[AiCardOut])
def list_cards(
    limit: int = Query(200, ge=1, le=1000),
    card_type: Optional[str] = None,
    container: AppContainer = Depends(get_container),
) -> list[AiCardOut]:
    _cleanup_setting_cards(container)
    if card_type:
        cards = container.ai_card_repository.list_by_kind(_clean_card_type(card_type))
    else:
        cards = container.ai_card_repository.list_all()
    return [_card_to_dto(card) for card in cards[:limit]]


@router.get("/search", response_model=list[AiCardOut])
def search_cards(
    q: str,
    limit: int = Query(100, ge=1, le=500),
    card_type: Optional[str] = None,
    container: AppContainer = Depends(get_container),
) -> list[AiCardOut]:
    _cleanup_setting_cards(container)
    needle = q.strip().lower()
    if not needle:
        return []
    source_cards = (
        container.ai_card_repository.list_by_kind(_clean_card_type(card_type))
        if card_type
        else container.ai_card_repository.list_all()
    )
    cards = [
        card
        for card in source_cards
        if needle in (card.name or "").lower()
        or needle in (card.body or "").lower()
        or needle in (card.kind or "").lower()
        or any(needle in tag.lower() for tag in card.tags)
    ]
    return [_card_to_dto(card) for card in cards[:limit]]


@router.get("/presets/list", response_model=list[dict])
def list_presets() -> list[dict]:
    return []


@router.post("/presets/generate", status_code=410)
def generate_from_presets(
    container: AppContainer = Depends(get_container),
) -> dict:
    _cleanup_setting_cards(container)
    raise HTTPException(410, "内置样例已移除。请新建自己的风格、人物或场景卡。")


@router.post("/generate-draft", response_model=AiCardDraftOut)
def generate_card_draft(
    request: AiCardDraftRequest,
    container: AppContainer = Depends(get_container),
) -> AiCardDraftOut:
    return _generate_draft(request=request, container=container)


@router.post("/{card_id}/upgrade-draft", response_model=AiCardDraftOut)
def upgrade_card_draft(
    card_id: str,
    request: AiCardDraftRequest,
    container: AppContainer = Depends(get_container),
) -> AiCardDraftOut:
    _cleanup_setting_cards(container)
    card = container.ai_card_repository.get(card_id)
    if not card:
        raise HTTPException(404, "AI Card not found")
    return _generate_draft(
        request=request,
        container=container,
        fallback_source=f"{card.name}\n\n{card.body}",
    )


@router.get("/{card_id}", response_model=AiCardOut)
def get_card(
    card_id: str,
    container: AppContainer = Depends(get_container),
) -> AiCardOut:
    _cleanup_setting_cards(container)
    card = container.ai_card_repository.get(card_id)
    if not card:
        raise HTTPException(404, "AI Card not found")
    return _card_to_dto(card)


@router.post("", response_model=AiCardOut, status_code=201)
def create_card(
    data: AiCardCreate,
    container: AppContainer = Depends(get_container),
) -> AiCardOut:
    _cleanup_setting_cards(container)
    card_type = _clean_card_type(data.card_type)
    card = container.ai_card_repository.create(
        kind=card_type,
        name=data.title,
        body=data.content,
        tags=_clean_tags(data.tags),
    )
    return _card_to_dto(card)


@router.put("/{card_id}", response_model=AiCardOut)
def update_card(
    card_id: str,
    data: AiCardUpdate,
    container: AppContainer = Depends(get_container),
) -> AiCardOut:
    _cleanup_setting_cards(container)
    existing = container.ai_card_repository.get(card_id)
    if not existing:
        raise HTTPException(404, "AI Card not found")
    card_type = _clean_card_type(data.card_type or existing.kind)
    card = container.ai_card_repository.update(
        card_id,
        kind=card_type,
        name=data.title,
        body=data.content,
        tags=_clean_tags(data.tags),
    )
    if not card:
        raise HTTPException(404, "AI Card not found")
    return _card_to_dto(card)


@router.delete("/{card_id}", status_code=204, response_class=Response)
def delete_card(
    card_id: str,
    container: AppContainer = Depends(get_container),
):
    _cleanup_setting_cards(container)
    if not container.ai_card_repository.get(card_id):
        raise HTTPException(404, "AI Card not found")
    container.ai_card_repository.delete(card_id)
