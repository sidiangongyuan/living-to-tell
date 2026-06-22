"""Tests for the M10A AI task service.

Stub the AiProvider so no real network call is ever issued.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from writer.app.container import build_container
from writer.domain.enums import (
    AiCostTier,
    AiTargetKind,
    AiTaskType,
)
from writer.services.ai.interfaces import (
    AiError,
    AiProvider,
    ChatResponse,
    RewriteResponse,
)
from writer.services.ai.task_prompt_builder import (
    STRUCTURED_TASKS,
    TaskPromptBuilder,
)
from writer.services.ai.task_service import (
    AiTaskService,
    KEY_AI_MODEL_BALANCED,
    KEY_AI_MODEL_STRONG,
    KEY_AI_MODEL_THRIFTY,
    SOFT_CONTEXT_BUDGET_CHARS,
)
from writer.services.ai.task_types import (
    AiContextAttachment,
    AiTaskRequest,
)


class _StubProvider(AiProvider):
    """Records every chat call and returns a scripted response."""

    name = "stub"

    def __init__(self, content: str = "OK", model_seen: Optional[list] = None) -> None:
        self._content = content
        self.calls: list[dict] = []
        self.model_seen = model_seen if model_seen is not None else []

    def rewrite(self, request):  # pragma: no cover — not exercised here
        return RewriteResponse(content=self._content, model="stub", provider=self.name)

    def chat(self, messages, *, model=None):
        self.calls.append({"messages": list(messages), "model": model})
        self.model_seen.append(model)
        return ChatResponse(
            content=self._content,
            model=model or "stub-default",
            provider=self.name,
            input_tokens=10,
            output_tokens=20,
            finish_reason="stop",
        )


class _ScriptedProvider(_StubProvider):
    """Stub that returns whatever string is in self._next, on demand."""

    def __init__(self, scripted_content: str) -> None:
        super().__init__(content=scripted_content)


# ---------------------------------------------------------------------------
# Pure prompt-builder tests
# ---------------------------------------------------------------------------


def test_prompt_builder_emits_one_system_one_user_for_each_task() -> None:
    builder = TaskPromptBuilder()
    for task in AiTaskType:
        request = AiTaskRequest(
            task_type=task,
            target_kind=AiTargetKind.PASTE,
            text="hello",
        )
        msgs = builder.build_messages(request)
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"
        assert any("hello" in (m["content"] or "") for m in msgs)


def test_structured_tasks_include_json_schema_hint() -> None:
    builder = TaskPromptBuilder()
    for task in STRUCTURED_TASKS:
        sys_prompt = builder.system_prompt(task)
        assert "JSON" in sys_prompt or "json" in sys_prompt


def test_attachments_are_inlined_with_a_label() -> None:
    builder = TaskPromptBuilder()
    request = AiTaskRequest(
        task_type=AiTaskType.LIBRARY_QA,
        target_kind=AiTargetKind.PASTE,
        text="who is X?",
        attachments=[
            AiContextAttachment(kind="fragment", ref_id="f1", name="Lore A", body="A is a wizard."),
        ],
    )
    msgs = builder.build_messages(request)
    user_content = msgs[-1]["content"]
    assert "Lore A" in user_content
    assert "A is a wizard." in user_content


def test_polish_with_style_demands_single_direct_rewrite_only() -> None:
    builder = TaskPromptBuilder()
    request = AiTaskRequest(
        task_type=AiTaskType.POLISH,
        target_kind=AiTargetKind.PASTE,
        text="She had brown hair.",
        style="Camus style",
        intensity="medium",
        preserve_voice=True,
    )
    msgs = builder.build_messages(request)
    system_content = msgs[0]["content"]
    user_content = msgs[-1]["content"]
    assert "freeform rewriting prompt" in system_content
    assert "author-by-author variants" in system_content
    assert "No heading, no explanation" in user_content
    assert "multiple authors or traits" in user_content
    assert "Polish and expand return the full resulting text" in user_content


def test_medium_polish_with_style_does_not_turn_into_expansion() -> None:
    builder = TaskPromptBuilder()
    request = AiTaskRequest(
        task_type=AiTaskType.POLISH,
        target_kind=AiTargetKind.PASTE,
        text="She had brown hair.",
        style="Camus",
        intensity="medium",
        preserve_voice=True,
    )
    msgs = builder.build_messages(request)
    system_content = msgs[0]["content"]
    user_content = msgs[-1]["content"]
    assert "more than synonym substitution" in system_content
    assert "do not add new information points or later plot" in system_content
    assert "do not use polishing as expansion" in user_content
    assert "do not add characters, events, settings, or later action" in user_content


def test_task_control_labels_are_task_specific() -> None:
    builder = TaskPromptBuilder()
    cases = (
        (AiTaskType.EXPAND, "sensory detail", "Expansion direction: sensory detail"),
        (
            AiTaskType.CONTINUE,
            "one paragraph",
            "Continuation direction / length: one paragraph",
        ),
        (AiTaskType.SUMMARIZE, "editor memo", "Summary mode: editor memo"),
        (AiTaskType.OUTLINE, "by scene", "Outline mode: by scene"),
        (AiTaskType.TITLE, "restrained", "Title style: restrained"),
        (AiTaskType.STRUCTURE_DIAGNOSE, "pacing", "Diagnosis focus: pacing"),
        (AiTaskType.CONSISTENCY_CHECK, "timeline", "Consistency focus: timeline"),
        (AiTaskType.LIBRARY_QA, "cite each claim", "Answer focus: cite each claim"),
    )
    for task_type, style, expected in cases:
        request = AiTaskRequest(
            task_type=task_type,
            target_kind=AiTargetKind.PASTE,
            text="source text",
            style=style,
        )
        msgs = builder.build_messages(request)
        assert expected in msgs[-1]["content"]
        assert "Target style:" not in msgs[-1]["content"]


def test_intensity_prompt_labels_follow_task_semantics() -> None:
    builder = TaskPromptBuilder()
    cases = (
        (AiTaskType.POLISH, "medium", "Polish scope: medium"),
        (AiTaskType.EXPAND, "strong", "Detail density: strong"),
    )

    for task_type, intensity, expected in cases:
        request = AiTaskRequest(
            task_type=task_type,
            target_kind=AiTargetKind.PASTE,
            text="source text",
            intensity=intensity,
        )
        msgs = builder.build_messages(request)
        assert expected in msgs[-1]["content"]
        assert "Edit intensity:" not in msgs[-1]["content"]


def test_prompt_contracts_distinguish_polish_expand_continue() -> None:
    builder = TaskPromptBuilder()

    expand = builder.build_messages(
        AiTaskRequest(
            task_type=AiTaskType.EXPAND,
            target_kind=AiTargetKind.PASTE,
            text="source text",
            style="sensory detail",
        )
    )
    expand_user = expand[-1]["content"]
    assert "inside the current scene/argument only" in expand_user
    assert "do not continue beyond the ending" in expand_user

    expand_dense = builder.build_messages(
        AiTaskRequest(
            task_type=AiTaskType.EXPAND,
            target_kind=AiTargetKind.PASTE,
            text="source text",
            intensity="medium",
        )
    )
    expand_dense_user = expand_dense[-1]["content"]
    assert "noticeably increase the detail density" in expand_dense_user
    assert "do more than rephrase" in expand_dense_user

    cont = builder.build_messages(
        AiTaskRequest(
            task_type=AiTaskType.CONTINUE,
            target_kind=AiTargetKind.PASTE,
            text="source text",
            style="one paragraph",
        )
    )
    cont_user = cont[-1]["content"]
    assert "output only new content after the source text" in cont_user
    assert "do not include, rewrite, or summarize the source" in cont_user


def test_visible_structured_tasks_have_json_contracts() -> None:
    builder = TaskPromptBuilder()
    for task in (
        AiTaskType.SUMMARIZE,
        AiTaskType.OUTLINE,
        AiTaskType.TITLE,
        AiTaskType.STRUCTURE_DIAGNOSE,
        AiTaskType.CONSISTENCY_CHECK,
        AiTaskType.LIBRARY_QA,
    ):
        assert task in STRUCTURED_TASKS
        sys_prompt = builder.system_prompt(task)
        assert "STRICT JSON" in sys_prompt


# ---------------------------------------------------------------------------
# Task service tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


def _make_service(provider: AiProvider, settings, *, library_search=None) -> AiTaskService:
    return AiTaskService(
        provider_factory=lambda: provider,
        settings=settings,
        prompt_builder=TaskPromptBuilder(),
        library_search=library_search,
    )


def test_polish_task_passes_text_through_and_records_tokens(container) -> None:
    provider = _StubProvider("POLISHED")
    service = _make_service(provider, container.settings)
    response = service.generate(
        AiTaskRequest(
            task_type=AiTaskType.POLISH,
            target_kind=AiTargetKind.FRAGMENT,
            text="hello",
            cost_tier=AiCostTier.BALANCED,
        )
    )
    assert response.content == "POLISHED"
    assert response.input_tokens == 10
    assert response.output_tokens == 20
    assert provider.calls, "provider should have been invoked"


def test_tier_models_are_resolved_from_settings(container) -> None:
    container.settings.set(KEY_AI_MODEL_THRIFTY, "tiny")
    container.settings.set(KEY_AI_MODEL_BALANCED, "mid")
    container.settings.set(KEY_AI_MODEL_STRONG, "big")

    provider = _StubProvider("ok")
    service = _make_service(provider, container.settings)

    for tier, expected in (
        (AiCostTier.THRIFTY, "tiny"),
        (AiCostTier.BALANCED, "mid"),
        (AiCostTier.STRONG, "big"),
    ):
        service.generate(
            AiTaskRequest(
                task_type=AiTaskType.POLISH,
                target_kind=AiTargetKind.PASTE,
                text="x",
                cost_tier=tier,
            )
        )
    assert provider.model_seen[-3:] == ["tiny", "mid", "big"]


def test_fixed_message_generation_uses_requested_tier_model(container) -> None:
    container.settings.set(KEY_AI_MODEL_STRONG, "big")
    provider = _StubProvider("draft")
    service = _make_service(provider, container.settings)

    response = service.generate_from_messages(
        [{"role": "user", "content": "make a card"}],
        cost_tier=AiCostTier.STRONG,
    )

    assert response.content == "draft"
    assert provider.model_seen[-1] == "big"
    assert provider.calls[-1]["messages"][0]["content"] == "make a card"


def test_unset_tier_falls_back_to_provider_default(container) -> None:
    provider = _StubProvider("ok")
    service = _make_service(provider, container.settings)
    service.generate(
        AiTaskRequest(
            task_type=AiTaskType.POLISH,
            target_kind=AiTargetKind.PASTE,
            text="x",
            cost_tier=AiCostTier.STRONG,
        )
    )
    assert provider.model_seen[-1] is None  # provider's chat() applies default


def test_structure_diagnose_parses_json_strict(container) -> None:
    payload = {"issues": [{"severity": "high", "where": "p1", "what": "stub"}]}
    provider = _StubProvider(json.dumps(payload))
    service = _make_service(provider, container.settings)
    response = service.generate(
        AiTaskRequest(
            task_type=AiTaskType.STRUCTURE_DIAGNOSE,
            target_kind=AiTargetKind.PASTE,
            text="story body",
            expect_structured=True,
        )
    )
    assert response.structured == payload


def test_structure_diagnose_parses_fenced_json(container) -> None:
    payload = {"issues": []}
    provider = _StubProvider("```json\n" + json.dumps(payload) + "\n```")
    service = _make_service(provider, container.settings)
    response = service.generate(
        AiTaskRequest(
            task_type=AiTaskType.STRUCTURE_DIAGNOSE,
            target_kind=AiTargetKind.PASTE,
            text="story body",
            expect_structured=True,
        )
    )
    assert response.structured == payload


def test_structure_diagnose_raises_on_unparseable_output(container) -> None:
    provider = _StubProvider("not json at all")
    service = _make_service(provider, container.settings)
    with pytest.raises(AiError):
        service.generate(
            AiTaskRequest(
                task_type=AiTaskType.STRUCTURE_DIAGNOSE,
                target_kind=AiTargetKind.PASTE,
                text="story body",
                expect_structured=True,
            )
        )


def test_library_qa_resolves_citations_against_attachments(container) -> None:
    payload = {
        "answer": "X is the antagonist.",
        "citations": [{"name": "Lore A"}, {"name": "Lore B"}, {"name": "missing"}],
    }
    provider = _StubProvider(json.dumps(payload))
    service = _make_service(provider, container.settings)

    request = AiTaskRequest(
        task_type=AiTaskType.LIBRARY_QA,
        target_kind=AiTargetKind.PASTE,
        text="who is X?",
        attachments=[
            AiContextAttachment(kind="fragment", ref_id="f1", name="Lore A", body="..."),
            AiContextAttachment(kind="fragment", ref_id="f2", name="Lore B", body="..."),
        ],
    )
    response = service.generate(request)
    cite_names = [c.name for c in response.citations]
    assert "Lore A" in cite_names
    assert "Lore B" in cite_names
    # The 'missing' reference becomes an unresolved citation rather than vanishing.
    unresolved = [c for c in response.citations if c.kind == "unresolved"]
    assert len(unresolved) == 1


def test_library_qa_auto_attaches_via_library_search_when_empty(container) -> None:
    payload = {"answer": "yes", "citations": [{"name": "auto"}]}
    provider = _StubProvider(json.dumps(payload))

    def fake_search(query: str, limit: int):
        assert query == "who?"
        return [
            AiContextAttachment(kind="fragment", ref_id="f1", name="auto", body="auto body"),
        ]

    service = _make_service(provider, container.settings, library_search=fake_search)
    request = AiTaskRequest(
        task_type=AiTaskType.LIBRARY_QA,
        target_kind=AiTargetKind.PASTE,
        text="who?",
    )
    response = service.generate(request)
    assert response.citations and response.citations[0].name == "auto"


def test_estimate_context_chars_sums_text_extra_and_attachments() -> None:
    request = AiTaskRequest(
        task_type=AiTaskType.SUMMARIZE,
        target_kind=AiTargetKind.PASTE,
        text="x" * 100,
        extra_instructions="y" * 50,
        attachments=[
            AiContextAttachment(kind="fragment", ref_id="a", name="a", body="z" * 200),
        ],
    )
    assert request.estimated_context_chars() == 100 + 50 + 200


def test_is_context_heavy_uses_soft_budget(container) -> None:
    provider = _StubProvider("ok")
    service = _make_service(provider, container.settings)
    light = AiTaskRequest(task_type=AiTaskType.POLISH, target_kind=AiTargetKind.PASTE, text="x")
    heavy = AiTaskRequest(
        task_type=AiTaskType.POLISH,
        target_kind=AiTargetKind.PASTE,
        text="x" * (SOFT_CONTEXT_BUDGET_CHARS + 1),
    )
    assert service.is_context_heavy(light) is False
    assert service.is_context_heavy(heavy) is True
