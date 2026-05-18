"""Lightweight character-budget helpers for AI context assembly."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from writer.domain.models.ai_thread import AiMessage
from writer.services.ai.task_service import SOFT_CONTEXT_BUDGET_CHARS
from writer.services.ai.task_types import AiContextAttachment


DEFAULT_CHAT_CONTEXT_BUDGET_CHARS = SOFT_CONTEXT_BUDGET_CHARS


@dataclass(frozen=True)
class ContextBudgetBreakdown:
    budget_chars: int
    user_chars: int
    attachment_chars: int
    history_chars: int
    selected_history_count: int
    omitted_history_count: int

    @property
    def total_chars(self) -> int:
        return self.user_chars + self.attachment_chars + self.history_chars

    @property
    def over_budget(self) -> bool:
        return self.total_chars > self.budget_chars


def estimate_attachment_chars(attachments: Iterable[AiContextAttachment]) -> int:
    return sum(len(a.body or "") + len(a.name or "") + len(a.kind or "") for a in attachments)


def select_history_for_budget(
    history: Sequence[AiMessage],
    *,
    user_text: str,
    attachments: Sequence[AiContextAttachment],
    budget_chars: int = DEFAULT_CHAT_CONTEXT_BUDGET_CHARS,
) -> tuple[list[AiMessage], ContextBudgetBreakdown]:
    """Return recent history that fits the remaining character budget.

    The database history is not modified. We walk from newest to oldest so the
    most recent conversational turns survive when context is tight.
    """
    budget = max(0, int(budget_chars))
    user_chars = len(user_text or "")
    attachment_chars = estimate_attachment_chars(attachments)
    remaining = max(0, budget - user_chars - attachment_chars)
    selected_reversed: list[AiMessage] = []
    history_chars = 0

    for message in reversed(history):
        size = len(message.content or "")
        if size > remaining and selected_reversed:
            continue
        if size > remaining:
            continue
        selected_reversed.append(message)
        history_chars += size
        remaining -= size

    selected = list(reversed(selected_reversed))
    breakdown = ContextBudgetBreakdown(
        budget_chars=budget,
        user_chars=user_chars,
        attachment_chars=attachment_chars,
        history_chars=history_chars,
        selected_history_count=len(selected),
        omitted_history_count=max(0, len(history) - len(selected)),
    )
    return selected, breakdown
