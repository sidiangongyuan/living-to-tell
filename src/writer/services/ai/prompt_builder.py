"""Prompt construction for rewrite actions.

Kept independent from any SDK so prompts can be unit-tested without touching
the network. The system prompts deliberately encourage a restrained,
voice-preserving rewrite — see docs/cloud-ai-strategy.md §5.
"""
from __future__ import annotations

from typing import Dict, List

from writer.domain.enums import RewriteAction
from writer.services.ai.interfaces import RewriteRequest


_SYSTEM_PROMPTS: Dict[RewriteAction, str] = {
    RewriteAction.POLISH: (
        "You are a restrained prose polishing assistant for a personal writer. "
        "Lightly improve rhythm, clarity, and word choice while preserving the "
        "author's original meaning, emotional tone, and first-person voice. "
        "Do not add new facts, do not expand the scope, and do not over-write. "
        "Return only the rewritten text, with no preface or explanation."
    ),
    RewriteAction.EXPAND: (
        "You are a careful writing assistant. Expand the given passage with "
        "additional sensory detail, reflection, or context that is consistent "
        "with the author's voice and the existing content. Do not invent facts "
        "that contradict the passage. Return only the expanded text."
    ),
    RewriteAction.CONTINUE: (
        "You are a careful writing assistant. Continue the given passage in "
        "the same voice, register, and tense. Pick up exactly where the text "
        "leaves off; do not repeat the existing content. Return only the new "
        "continuation text."
    ),
}


class PromptBuilder:
    """Builds the message list for a rewrite request."""

    def system_prompt(self, action: RewriteAction) -> str:
        try:
            return _SYSTEM_PROMPTS[action]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unknown rewrite action: {action}") from exc

    def build_messages(self, request: RewriteRequest) -> List[Dict[str, str]]:
        system = self.system_prompt(request.action)
        if request.preserve_voice:
            system += " Strictly preserve the author's voice."

        user_parts: List[str] = []
        if request.references:
            joined = "\n\n---\n\n".join(request.references)
            user_parts.append(
                "Reference passages (for tonal inspiration only, do not copy):\n"
                f"{joined}"
            )
        user_parts.append("Text to rewrite:\n" + request.text)

        if request.max_output_chars:
            user_parts.append(
                f"Keep the output within about {request.max_output_chars} characters."
            )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]
