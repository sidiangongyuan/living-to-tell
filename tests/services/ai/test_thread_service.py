"""Tests for the M10A AI thread service.

Stub provider; verify thread persistence, history windowing, attachment
inlining, and tier model selection.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container
from writer.domain.enums import AiCostTier, AiThreadScope
from writer.services.ai.interfaces import (
    AiProvider,
    ChatResponse,
    RewriteResponse,
)
from writer.services.ai.task_prompt_builder import TaskPromptBuilder
from writer.services.ai.task_service import AiTaskService
from writer.services.ai.task_types import AiContextAttachment
from writer.services.ai.thread_service import (
    AiThreadService,
    DEFAULT_HISTORY_WINDOW,
)


class _StubProvider(AiProvider):
    name = "stub"

    def __init__(self, content: str = "ASSIST"):
        self._content = content
        self.calls: list[dict] = []

    def rewrite(self, request):  # pragma: no cover
        return RewriteResponse(content=self._content, model="stub", provider=self.name)

    def chat(self, messages, *, model=None):
        self.calls.append({"messages": list(messages), "model": model})
        return ChatResponse(
            content=self._content,
            model=model or "stub-default",
            provider=self.name,
            input_tokens=3,
            output_tokens=4,
        )


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


def _wire_thread_service(container, provider: AiProvider) -> AiThreadService:
    task_service = AiTaskService(
        provider_factory=lambda: provider,
        settings=container.settings,
        prompt_builder=TaskPromptBuilder(),
    )
    return AiThreadService(
        container.ai_thread_repository,
        provider_factory=lambda: provider,
        task_service=task_service,
    )


def test_get_or_create_for_scope_returns_same_thread_per_scope(container) -> None:
    provider = _StubProvider()
    svc = _wire_thread_service(container, provider)

    a1 = svc.get_or_create_for_scope(AiThreadScope.FRAGMENT, "frag-1", title="Frag 1")
    a2 = svc.get_or_create_for_scope(AiThreadScope.FRAGMENT, "frag-1", title="Frag 1")
    b1 = svc.get_or_create_for_scope(AiThreadScope.FRAGMENT, "frag-2", title="Frag 2")

    assert a1.id == a2.id
    assert a1.id != b1.id


def test_send_persists_user_and_assistant_messages(container) -> None:
    provider = _StubProvider("hello back")
    svc = _wire_thread_service(container, provider)
    thread = svc.get_or_create_for_scope(AiThreadScope.GLOBAL, None, title="Global")

    turn = svc.send(thread.id, "hello there")
    assert turn.user_message.content == "hello there"
    assert turn.assistant_message.content == "hello back"

    history = svc.history(thread.id)
    assert [m.role for m in history] == ["user", "assistant"]
    assert provider.calls, "provider should have been called"


def test_send_inlines_scope_and_explicit_attachments(container) -> None:
    provider = _StubProvider()
    svc = _wire_thread_service(container, provider)
    thread = svc.get_or_create_for_scope(AiThreadScope.FRAGMENT, "f-1", title="Frag")

    svc.send(
        thread.id,
        "what next?",
        scope_attachment=AiContextAttachment(
            kind="fragment", ref_id="f-1", name="Frag", body="SCOPE-BODY",
        ),
        attachments=[
            AiContextAttachment(kind="fragment", ref_id="f-2", name="Lore", body="LORE-BODY"),
        ],
    )

    sent_messages = provider.calls[-1]["messages"]
    final_user = sent_messages[-1]["content"]
    assert "SCOPE-BODY" in final_user
    assert "LORE-BODY" in final_user
    assert "Lore" in final_user


def test_history_windowing_caps_messages_sent_to_provider(container) -> None:
    provider = _StubProvider()
    svc = _wire_thread_service(container, provider)
    thread = svc.get_or_create_for_scope(AiThreadScope.GLOBAL, None, title="g")

    # Pump in many turns.
    for i in range(DEFAULT_HISTORY_WINDOW + 5):
        svc.send(thread.id, f"q{i}")

    last_call_msgs = provider.calls[-1]["messages"]
    # 1 system + (history_window historical) + 1 final user
    assert len(last_call_msgs) <= DEFAULT_HISTORY_WINDOW + 2


def test_context_budget_omits_older_history_without_deleting_it(container) -> None:
    provider = _StubProvider()
    svc = _wire_thread_service(container, provider)
    thread = svc.get_or_create_for_scope(AiThreadScope.GLOBAL, None, title="g")

    svc.send(thread.id, "older-message-" + ("x" * 80), context_budget_chars=500)
    svc.send(thread.id, "newer-message", context_budget_chars=500)
    turn = svc.send(thread.id, "final", context_budget_chars=80)

    sent = "\n".join(msg["content"] for msg in provider.calls[-1]["messages"])
    assert "older-message" not in sent
    assert "newer-message" in sent
    assert turn.context_breakdown.omitted_history_count > 0
    assert len(svc.history(thread.id)) == 6


def test_send_uses_tier_model_when_set(container) -> None:
    from writer.services.ai.task_service import KEY_AI_MODEL_STRONG
    container.settings.set(KEY_AI_MODEL_STRONG, "big-model")

    provider = _StubProvider()
    svc = _wire_thread_service(container, provider)
    thread = svc.get_or_create_for_scope(AiThreadScope.GLOBAL, None, title="g")

    svc.send(thread.id, "hi", cost_tier=AiCostTier.STRONG)
    assert provider.calls[-1]["model"] == "big-model"
