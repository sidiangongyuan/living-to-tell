"""Prompt construction for rewrite actions.

Kept independent from any SDK so prompts can be unit-tested without touching
the network. The system prompts deliberately encourage a restrained,
voice-preserving rewrite — see docs/cloud-ai-strategy.md §5.

System prompts are available in English and Simplified Chinese. The active
locale is read from ``writer.app.locale`` at call time so the language
follows the setting chosen at startup.
"""
from __future__ import annotations

from typing import Dict, List

from writer.app.locale import LOCALE_ZH_CN, current_locale
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

_SYSTEM_PROMPTS_ZH_CN: Dict[RewriteAction, str] = {
    RewriteAction.POLISH: (
        "你是一位为个人写作者服务的克制散文润色助手。"
        "在保留作者原意、情感基调和第一人称叙述风格的前提下，"
        "轻微改善文章的节奏、清晰度和用词选择。"
        "不要添加新事实，不要扩展范围，不要过度改写。"
        "只返回改写后的文本，不要添加任何前言或说明。"
    ),
    RewriteAction.EXPAND: (
        "你是一位细心的写作助手。"
        "在与作者声音和现有内容保持一致的前提下，"
        "用更多感官细节、反思或背景来扩展给定的段落。"
        "不要虚构与文章相矛盾的事实。"
        "只返回扩展后的文本。"
    ),
    RewriteAction.CONTINUE: (
        "你是一位细心的写作助手。"
        "以相同的声音、语气和时态续写给定的段落。"
        "从文本结尾处接着写，不要重复现有内容。"
        "只返回新续写的文本。"
    ),
}


class PromptBuilder:
    """Builds the message list for a rewrite request."""

    def system_prompt(self, action: RewriteAction) -> str:
        prompts = (
            _SYSTEM_PROMPTS_ZH_CN
            if current_locale() == LOCALE_ZH_CN
            else _SYSTEM_PROMPTS
        )
        try:
            return prompts[action]
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
