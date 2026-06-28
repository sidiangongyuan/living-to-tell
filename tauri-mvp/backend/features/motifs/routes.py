"""Motif star-map feature routes."""
from __future__ import annotations

import json
import re
import time
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.settings import SUPPORTED_AI_PROVIDERS, SUPPORTED_WIRE_APIS
from writer.app.container import AppContainer
from writer.domain.enums import AiCostTier
from writer.domain.models.ai_config import AiConfig
from writer.domain.models.motif import (
    MOTIF_SOURCE_ARTICLE,
    MOTIF_SOURCE_REFERENCE,
    MotifExcerpt,
    MotifGraphEdge,
    MotifGraphNode,
    MotifNode,
)
from writer.services.ai.provider_factory import provider_for_config
from writer.services.ai.prompt_builder import PromptBuilder
from writer.services.ai.task_service import AiTaskService

router = APIRouter(prefix="/api/motifs", tags=["motifs"])

SourceKind = Literal["article", "reference"]
DraftCostTier = Literal["balanced", "strong"]

MAX_ENRICH_NOTE_CHARS = 6000
MAX_ENRICH_EXCERPTS = 8
MAX_ENRICH_EXCERPT_CHARS = 260


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


class MotifEnrichmentRequest(BaseModel):
    motif_id: Optional[str] = None
    concept: str = ""
    direction: str = ""
    include_excerpts: bool = True
    request_web_context: bool = False
    profile_id: str = "default"
    cost_tier: DraftCostTier = "strong"


class MotifSourceHintOut(BaseModel):
    title: str
    url: Optional[str] = None
    note: str = ""


class MotifEnrichmentDraftOut(BaseModel):
    title: str
    concept: str
    aliases: list[str]
    tags: list[str]
    note: str
    related_suggestions: list[str]
    source_hints: list[MotifSourceHintOut]
    provider: Optional[str] = None
    model: Optional[str] = None
    transport: Optional[str] = None
    elapsed_ms: int


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


def _friendly_ai_error(exc: Exception) -> str:
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
    if len(raw) > 240:
        return raw[:240].rstrip() + "..."
    return raw


def _cost_tier(value: str) -> AiCostTier:
    try:
        return AiCostTier((value or AiCostTier.STRONG.value).strip().lower())
    except ValueError as exc:
        raise HTTPException(400, f"Unknown cost_tier: {value}") from exc


def _unique_clean(values: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value[:48])
        if len(result) >= limit:
            break
    return result


def _source_hints_from(values: Any, *, request_web_context: bool) -> list[MotifSourceHintOut]:
    hints: list[MotifSourceHintOut] = []
    if isinstance(values, list):
        for raw in values:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()
            note = str(raw.get("note") or "").strip()
            url = str(raw.get("url") or "").strip() or None
            if not title and not note:
                continue
            hints.append(
                MotifSourceHintOut(
                    title=(title or "来源线索")[:120],
                    url=url[:500] if url else None,
                    note=note[:240],
                )
            )
            if len(hints) >= 5:
                break
    if request_web_context and not hints:
        hints.append(
            MotifSourceHintOut(
                title="未能联网核对",
                note="模型未返回可核对来源；请把本草稿当作写作联想材料继续核对。",
            )
        )
    return hints


def _ensure_source_section(note: str, hints: list[MotifSourceHintOut], *, request_web_context: bool) -> str:
    heading = "【来源线索（需核对）】"
    if heading in note:
        return note
    if request_web_context and hints:
        lines = [
            f"- {hint.title}" + (f"：{hint.note}" if hint.note else "")
            for hint in hints[:5]
        ]
    elif request_web_context:
        lines = ["- 未能联网核对；请把本草稿当作写作联想材料继续核对。"]
    else:
        lines = ["- 未请求联网补充。"]
    return f"{note.rstrip()}\n\n{heading}\n" + "\n".join(lines)


def _coerce_enrichment_draft(
    payload: dict[str, Any],
    *,
    concept: str,
    request_web_context: bool,
    provider: Optional[str],
    model: Optional[str],
    transport: Optional[str],
    elapsed_ms: int,
) -> MotifEnrichmentDraftOut:
    title = str(payload.get("title") or concept).strip()
    note = str(payload.get("note") or "").strip()
    if not note:
        raise HTTPException(502, "AI 返回的意象草稿缺少概念或笔记。")
    required_headings = [
        "【一句话定义】",
        "【核心张力】",
        "【写作功能】",
        "【场景触发】",
        "【人物表现】",
        "【意象转译】",
        "【短例子】",
        "【关联建议】",
        "【误用提醒】",
        "【微练习】",
    ]
    missing = [heading for heading in required_headings if heading not in note]
    if missing:
        raise HTTPException(502, f"AI 返回的意象草稿缺少模板标题：{missing[0]}")
    hints = _source_hints_from(payload.get("source_hints"), request_web_context=request_web_context)
    note = _ensure_source_section(note[:MAX_ENRICH_NOTE_CHARS], hints, request_web_context=request_web_context)
    return MotifEnrichmentDraftOut(
        title=title[:80],
        concept=concept[:80],
        aliases=_unique_clean(payload.get("aliases"), limit=10),
        tags=_unique_clean(payload.get("tags"), limit=10),
        note=note,
        related_suggestions=_unique_clean(payload.get("related_suggestions"), limit=12),
        source_hints=hints,
        provider=provider,
        model=model,
        transport=transport,
        elapsed_ms=elapsed_ms,
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


def _enrichment_system_prompt() -> str:
    return (
        "你是写作工具里的意象/概念短卡生成器，不是百科问答助手。"
        "你的目标是把概念转成可记忆、可迁移、可写作调用的短卡。"
        "输出必须凝练、具体、克制，避免长篇思想史和空泛赞美。"
        "不要编造引文、页码、版本、作者原话或看似精确的出处。"
        "只输出一个 JSON 对象，不要 Markdown，不要代码块，不要解释。"
        "JSON schema: {"
        "\"title\": string, \"concept\": string, \"aliases\": string[], "
        "\"tags\": string[], \"note\": string, "
        "\"related_suggestions\": string[], "
        "\"source_hints\": [{\"title\": string, \"url\": string|null, \"note\": string}]"
        "}。"
    )


def _format_enrichment_excerpts(excerpts: list[MotifExcerpt]) -> str:
    if not excerpts:
        return "无"
    blocks: list[str] = []
    for index, excerpt in enumerate(excerpts[:MAX_ENRICH_EXCERPTS], start=1):
        text = (excerpt.excerpt_text or "").strip().replace("\n", " ")
        note = (excerpt.note or "").strip().replace("\n", " ")
        source = excerpt.source_current_title or excerpt.source_title_snapshot or "未知来源"
        block = f"{index}. 来源：{source}\n摘录：{text[:MAX_ENRICH_EXCERPT_CHARS]}"
        if note:
            block += f"\n备注：{note[:160]}"
        blocks.append(block)
    return "\n\n".join(blocks)


def _enrichment_user_prompt(
    *,
    concept: str,
    direction: str,
    request_web_context: bool,
    node: Optional[MotifNode],
    excerpts: list[MotifExcerpt],
) -> str:
    web_policy = (
        "本次用户请求“联网补充”。如果当前模型/供应商具备联网或检索能力，请使用它核对概念线索，"
        "并在 source_hints 中给出 3-5 条标题/链接/用途；note 的【来源线索（需核对）】也要简要列出。"
        "如果你无法联网或无法确认来源，必须明确写“未能联网核对”，不要假装查过。"
        if request_web_context
        else "本次未请求联网补充。source_hints 返回空数组；note 的【来源线索（需核对）】写“未请求联网补充”。"
    )
    aliases = "、".join(node.aliases) if node and node.aliases else "无"
    tags = "、".join(node.tags) if node and node.tags else "无"
    existing_note = (node.note if node else "").strip() or "无"
    return f"""请为写作者生成一张“意象/概念短卡”草稿。

概念：{concept}
生成方向：{direction.strip() or "概念理解 + 写作转译"}

当前意象资料：
- 已有别名：{aliases}
- 已有标签：{tags}
- 已有笔记：
{existing_note[:1800]}

相关摘录：
{_format_enrichment_excerpts(excerpts)}

生成要求：
- note 必须控制在约 800-1200 中文字，不要写成百科长文。
- note 必须完整使用这些标题，标题不可改名、不可遗漏：
【一句话定义】
【核心张力】
【写作功能】
【场景触发】
【人物表现】
【意象转译】
【短例子】
【关联建议】
【误用提醒】
【微练习】
【来源线索（需核对）】
- 【短例子】写 3-5 句，展示概念如何变成一个场景、人物瞬间或叙事动作。
- 【关联建议】列出可联想的概念/意象，但不要假设软件会自动建节点或连边。
- aliases 给出少量别名、译名、近义称呼；tags 给出少量分类标签。
- related_suggestions 只给概念名，不写解释。
- {web_policy}
- 不要生成页码、伪原文、伪精确引用；没有把握时写“需核对”。
"""


def _generate_with_profile(
    messages: list[dict[str, str]],
    *,
    request: MotifEnrichmentRequest,
    container: AppContainer,
) -> tuple[Any, Optional[AiConfig]]:
    profile_id = (request.profile_id or "default").strip() or "default"
    _profile_name, config, error = _profile_config(profile_id, container)
    if config is None:
        raise HTTPException(400, error or "这个 AI 配置档案不可用。")
    if profile_id == "default":
        return container.ai_task_service.generate_from_messages(
            messages,
            cost_tier=_cost_tier(request.cost_tier),
        ), config
    prompt_builder = PromptBuilder()
    task_service = AiTaskService(
        provider_factory=lambda: provider_for_config(config, prompt_builder),
        settings=container.settings,
    )
    return task_service.generate_from_messages(
        messages,
        cost_tier=_cost_tier(request.cost_tier),
        model_override=config.model,
    ), config


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


@router.post("/enrich-draft", response_model=MotifEnrichmentDraftOut)
def generate_motif_enrichment_draft(
    request: MotifEnrichmentRequest,
    container: AppContainer = Depends(get_container),
) -> MotifEnrichmentDraftOut:
    node: Optional[MotifNode] = None
    if request.motif_id:
        node = container.motif_repository.get_node(request.motif_id)
        if node is None:
            raise HTTPException(404, "这个意象已经不存在，已刷新列表。")

    concept = (request.concept or node.name if node else request.concept).strip()
    if not concept:
        raise HTTPException(400, "请先输入要丰富的概念或意象。")

    excerpts: list[MotifExcerpt] = []
    if node is not None and request.include_excerpts:
        excerpts = container.motif_repository.list_excerpts_for_node(
            node.id,
            limit=MAX_ENRICH_EXCERPTS,
        )

    messages = [
        {"role": "system", "content": _enrichment_system_prompt()},
        {
            "role": "user",
            "content": _enrichment_user_prompt(
                concept=concept,
                direction=request.direction,
                request_web_context=request.request_web_context,
                node=node,
                excerpts=excerpts,
            ),
        },
    ]
    started = time.perf_counter()
    try:
        response, config = _generate_with_profile(
            messages,
            request=request,
            container=container,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"AI 丰富意象失败：{_friendly_ai_error(exc)}") from exc

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    parsed = _parse_json_object(response.content)
    if parsed is None:
        raise HTTPException(502, "AI 没有返回可解析的意象草稿 JSON。")
    return _coerce_enrichment_draft(
        parsed,
        concept=concept,
        request_web_context=request.request_web_context,
        provider=getattr(response, "provider", None) or config.provider_key(),
        model=getattr(response, "model", None) or config.model,
        transport=getattr(response, "transport", None),
        elapsed_ms=elapsed_ms,
    )


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
