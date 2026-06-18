"""Chat thread orchestration (M10A).

The chat tab on the AI workspace operates over scope-bound threads.
Sending a message:
  1. Persists the user message.
  2. Builds a windowed history (recent N) plus the current scope target
     and any user-attached context.
  3. Calls the provider's ``chat()`` method.
  4. Persists the assistant response.

The service does NOT auto-inject the reference library or other content;
the UI must hand in attachments explicitly. This matches the M10A
default-context rule.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, List, Optional

from writer.app.locale import LOCALE_ZH_CN, current_locale
from writer.domain.enums import AiCostTier
from writer.domain.models.ai_thread import AiMessage, AiThread
from writer.services.ai.interfaces import AiProvider
from writer.services.ai.context_budget import (
    DEFAULT_CHAT_CONTEXT_BUDGET_CHARS,
    ContextBudgetBreakdown,
    select_history_for_budget,
)
from writer.services.ai.task_service import AiTaskService
from writer.services.ai.task_types import AiContextAttachment
from writer.storage.repositories.ai_thread_repository import AiThreadRepository


# How many recent messages are considered before character-budget fitting.
DEFAULT_HISTORY_WINDOW = 80


_EN_SYSTEM = (
    "You are a writing assistant working alongside the author of a personal "
    "writer's library. Stay focused on the writing object the user is "
    "currently editing. Keep responses concrete and actionable. If the user "
    "asks for substantial rewrites, you may suggest running a structured "
    "tool task instead of producing the rewrite inline."
)
_ZH_SYSTEM = (
    "你是一位写作助手，正在协助作者打理个人写作库。请聚焦用户当前编辑的对象，"
    "回答简洁、具体、可执行。如果用户希望大段改写，可以建议改用结构化工具任务，"
    "而不是直接在聊天里给出全部改写。"
)


@dataclass
class ChatTurn:
    user_message: AiMessage
    assistant_message: AiMessage
    context_breakdown: ContextBudgetBreakdown


class AiThreadService:
    def __init__(
        self,
        thread_repo: AiThreadRepository,
        provider_factory: Callable[[], AiProvider],
        task_service: AiTaskService,
    ) -> None:
        self._threads = thread_repo
        self._provider_factory = provider_factory
        self._tasks = task_service

    # ------------------------------------------------------------------
    def get_or_create_for_scope(
        self, scope_kind: str, scope_id: Optional[str], *, title: str = ""
    ) -> AiThread:
        return self._threads.get_or_create_for_scope(
            scope_kind, scope_id, title=title
        )

    def history(self, thread_id: str) -> List[AiMessage]:
        return self._threads.list_messages(thread_id)

    def send(
        self,
        thread_id: str,
        user_text: str,
        *,
        scope_attachment: Optional[AiContextAttachment] = None,
        attachments: Optional[List[AiContextAttachment]] = None,
        system_prompt: str = "",
        cost_tier: AiCostTier = AiCostTier.BALANCED,
        history_window: int = DEFAULT_HISTORY_WINDOW,
        context_budget_chars: int = DEFAULT_CHAT_CONTEXT_BUDGET_CHARS,
    ) -> ChatTurn:
        """Persist user message, run the provider, persist assistant message."""
        if not user_text.strip():
            raise ValueError("user_text must not be empty")

        attachments_list: List[AiContextAttachment] = list(attachments or [])
        if scope_attachment is not None:
            # Scope object always takes precedence and goes first so the
            # model knows which object the conversation is about.
            attachments_list.insert(0, scope_attachment)

        meta = json.dumps(
            {
                "attachments": [
                    {"kind": a.kind, "ref_id": a.ref_id, "name": a.name}
                    for a in attachments_list
                ]
            },
            ensure_ascii=False,
        )
        user_msg = self._threads.add_message(
            thread_id=thread_id, role="user", content=user_text, meta_json=meta
        )

        # Build the request to the provider.
        recent = self._threads.recent_messages(thread_id, limit=history_window)
        # The just-inserted user message is included in `recent`; we
        # re-render it from the live request so attachments are visible.
        # Drop the trailing user msg from history to avoid duplication.
        raw_history = [m for m in recent if m.id != user_msg.id]
        history, context_breakdown = select_history_for_budget(
            raw_history,
            user_text=user_text,
            attachments=attachments_list,
            budget_chars=context_budget_chars,
        )

        messages = _build_chat_messages(
            history=history,
            user_text=user_text,
            attachments=attachments_list,
            system_prompt=system_prompt,
        )
        provider = self._provider_factory()
        model = self._tasks.model_for_tier(cost_tier)
        response = provider.chat(messages, model=model)

        meta_assistant = json.dumps(
            {
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
            ensure_ascii=False,
        )
        assistant_msg = self._threads.add_message(
            thread_id=thread_id,
            role="assistant",
            content=response.content,
            meta_json=meta_assistant,
        )
        return ChatTurn(
            user_message=user_msg,
            assistant_message=assistant_msg,
            context_breakdown=context_breakdown,
        )


# ---------------------------------------------------------------------------
def _build_chat_messages(
    *,
    history: List[AiMessage],
    user_text: str,
    attachments: List[AiContextAttachment],
    system_prompt: str = "",
) -> List[dict]:
    system = _ZH_SYSTEM if current_locale() == LOCALE_ZH_CN else _EN_SYSTEM
    if system_prompt.strip():
        system = f"{system}\n\nUser standing instruction:\n{system_prompt.strip()}"
    messages: List[dict] = [{"role": "system", "content": system}]
    for m in history:
        if m.role in ("user", "assistant"):
            messages.append({"role": m.role, "content": m.content})

    user_blocks: List[str] = []
    if attachments:
        user_blocks.append(_format_attachments(attachments))
    user_blocks.append(user_text)
    messages.append({"role": "user", "content": "\n\n".join(user_blocks)})
    return messages


def _format_attachments(attachments: List[AiContextAttachment]) -> str:
    blocks = ["Context attachments (cite by name when relevant):"]
    for att in attachments:
        if not att.body.strip():
            continue
        blocks.append(f"--- [{att.kind}] {att.name} ---\n{att.body.strip()}")
    return "\n\n".join(blocks)
