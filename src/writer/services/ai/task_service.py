"""High-level AI task engine (M10A).

Acts as the single entry point the UI uses to run any AI task. Wraps the
provider, builds prompts via :class:`TaskPromptBuilder`, parses structured
output, and resolves citations.

This service intentionally does NOT mutate fragments or works. The UI
remains responsible for the safe write-back step (preview → accept →
version snapshot), exactly as M3's :class:`RewriteService` already does
for fragments. ``AiTaskService.generate`` only produces text; UI helpers
or :class:`RewriteService.apply_acceptance` do the persistence.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

from writer.app.settings import Settings
from writer.domain.enums import AiCostTier, AiTaskType
from writer.services.ai.interfaces import AiError, AiProvider
from writer.services.ai.task_prompt_builder import (
    STRUCTURED_TASKS,
    TaskPromptBuilder,
)
from writer.services.ai.task_types import (
    AiCitation,
    AiContextAttachment,
    AiTaskRequest,
    AiTaskResponse,
)


# Settings keys for cost-tier model overrides. Falling back to the global
# default model when an override is unset is intentional.
KEY_AI_MODEL_THRIFTY = "ai.model.thrifty"
KEY_AI_MODEL_BALANCED = "ai.model.balanced"
KEY_AI_MODEL_STRONG = "ai.model.strong"

_TIER_KEYS = {
    AiCostTier.THRIFTY: KEY_AI_MODEL_THRIFTY,
    AiCostTier.BALANCED: KEY_AI_MODEL_BALANCED,
    AiCostTier.STRONG: KEY_AI_MODEL_STRONG,
}


# Soft warning when the rendered prompt grows beyond this many chars; UI
# uses it to show "context heavy" hints.
SOFT_CONTEXT_BUDGET_CHARS = 32_000


class AiTaskService:
    def __init__(
        self,
        provider_factory: Callable[[], AiProvider],
        settings: Settings,
        prompt_builder: Optional[TaskPromptBuilder] = None,
        *,
        library_search: Optional[Callable[[str, int], List[AiContextAttachment]]] = None,
    ) -> None:
        self._provider_factory = provider_factory
        self._settings = settings
        self._prompts = prompt_builder or TaskPromptBuilder()
        self._library_search = library_search

    # ---- helpers ------------------------------------------------------
    def model_for_tier(self, tier: AiCostTier) -> Optional[str]:
        key = _TIER_KEYS.get(tier)
        if key is None:
            return None
        override = self._settings.get(key)
        return override.strip() if override and override.strip() else None

    def estimate_context_chars(self, request: AiTaskRequest) -> int:
        return request.estimated_context_chars()

    def is_context_heavy(self, request: AiTaskRequest) -> bool:
        return self.estimate_context_chars(request) > SOFT_CONTEXT_BUDGET_CHARS

    # ---- public API ---------------------------------------------------
    def generate(self, request: AiTaskRequest) -> AiTaskResponse:
        """Run a task and return a structured response.

        Library QA: if no attachments were provided AND a library search
        callable is wired, the service performs ONE controlled search and
        attaches the top candidates. This is the only auto-attachment path
        — every other task only sees what the user explicitly attached.
        """
        if (
            request.task_type is AiTaskType.LIBRARY_QA
            and not request.attachments
            and self._library_search is not None
        ):
            request = _with_library_attachments(
                request, self._library_search(request.text, 5)
            )

        provider = self._provider_factory()
        messages = self._prompts.build_messages(request)
        model = self.model_for_tier(request.cost_tier)
        response = provider.chat(messages, model=model)

        structured: Optional[Dict[str, Any]] = None
        citations: List[AiCitation] = []
        if request.task_type in STRUCTURED_TASKS or request.expect_structured:
            structured = _parse_json_lenient(response.content)
            if structured is None:
                raise AiError(
                    "AI did not return parseable JSON for a structured task. "
                    "Raw output: " + response.content[:500]
                )
            if request.task_type is AiTaskType.LIBRARY_QA:
                citations = _resolve_citations(
                    structured.get("citations", []), request.attachments
                )

        return AiTaskResponse(
            content=response.content,
            structured=structured,
            citations=citations,
            model=response.model,
            provider=response.provider,
            transport=response.transport,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            finish_reason=response.finish_reason,
            cost=response.cost,
        )

    def generate_from_messages(
        self,
        messages: List[dict],
        *,
        cost_tier: AiCostTier = AiCostTier.BALANCED,
    ) -> AiTaskResponse:
        """Run a fixed prompt that is not part of the task taxonomy.

        This is used by narrow generators such as AI card drafting where the
        UI needs a strict artifact instead of a general writing task.
        """
        provider = self._provider_factory()
        model = self.model_for_tier(cost_tier)
        response = provider.chat(messages, model=model)
        return AiTaskResponse(
            content=response.content,
            model=response.model,
            provider=response.provider,
            transport=response.transport,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            finish_reason=response.finish_reason,
            cost=response.cost,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _with_library_attachments(
    request: AiTaskRequest, attachments: List[AiContextAttachment]
) -> AiTaskRequest:
    if not attachments:
        return request
    new = AiTaskRequest(
        task_type=request.task_type,
        target_kind=request.target_kind,
        text=request.text,
        target_ref_id=request.target_ref_id,
        style=request.style,
        intensity=request.intensity,
        extra_instructions=request.extra_instructions,
        max_output_chars=request.max_output_chars,
        preserve_meaning=request.preserve_meaning,
        preserve_voice=request.preserve_voice,
        forbid_terms=list(request.forbid_terms),
        must_keep_terms=list(request.must_keep_terms),
        attachments=list(request.attachments) + list(attachments),
        cost_tier=request.cost_tier,
        desired_output=request.desired_output,
        expect_structured=request.expect_structured,
    )
    return new


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _parse_json_lenient(text: str) -> Optional[Dict[str, Any]]:
    """Try hard to extract a JSON object from a model response."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = _JSON_FENCE.search(text)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    # Last resort: take the first {...} block.
    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _resolve_citations(
    raw: Any, attachments: List[AiContextAttachment]
) -> List[AiCitation]:
    """Resolve model-provided ``citations[*].name`` back to attachment objects."""
    if not isinstance(raw, list):
        return []
    by_name = {att.name: att for att in attachments}
    out: List[AiCitation] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        excerpt = str(item.get("excerpt", "")).strip()
        att = by_name.get(name)
        if att is None:
            # Citation references a name we never sent — keep it but mark
            # the source as unresolved so the UI can show it dimmed.
            out.append(AiCitation(kind="unresolved", ref_id="", name=name, excerpt=excerpt))
            continue
        out.append(
            AiCitation(kind=att.kind, ref_id=att.ref_id, name=att.name, excerpt=excerpt)
        )
    return out
