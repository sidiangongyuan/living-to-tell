"""Shared AI provider construction helpers."""
from __future__ import annotations

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.gemini_cli_provider import GeminiCliProvider
from writer.services.ai.gemini_provider import GeminiProvider
from writer.services.ai.interfaces import AiProvider
from writer.services.ai.opencode_cli_provider import OpenCodeCliProvider
from writer.services.ai.openai_provider import OpenAiProvider
from writer.services.ai.prompt_builder import PromptBuilder


def provider_for_config(
    config: AiConfig,
    prompt_builder: PromptBuilder | None = None,
) -> AiProvider:
    """Build the provider implementation matching a stored AI config."""

    builder = prompt_builder or PromptBuilder()
    if config.provider_key() == "opencode" or config.uses_opencode_auth():
        return OpenCodeCliProvider(config, builder)
    if config.provider_key() == "gemini_cli":
        return GeminiCliProvider(config, builder)
    if config.provider_key() == "gemini" or config.uses_gemini_auth():
        return GeminiProvider(config, builder)
    return OpenAiProvider(config, builder)
