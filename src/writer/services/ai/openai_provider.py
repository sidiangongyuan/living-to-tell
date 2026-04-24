"""OpenAI-compatible provider adapter.

Uses the ``responses`` API shape recommended in
``docs/codex-style-integration.md`` so the same configuration that powers a
local Codex setup can drive the writer app. Only ``responses`` is implemented
in M3; other wire APIs raise :class:`AiError`.
"""
from __future__ import annotations

import os
from typing import Optional

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.interfaces import (
    AiError,
    AiProvider,
    RewriteRequest,
    RewriteResponse,
)
from writer.services.ai.prompt_builder import PromptBuilder


class OpenAiProvider(AiProvider):
    """Adapter around the official ``openai`` Python SDK."""

    name = "openai"

    def __init__(
        self,
        config: AiConfig,
        prompt_builder: PromptBuilder,
        *,
        client=None,
    ) -> None:
        self._config = config
        self._prompts = prompt_builder
        self._client = client  # injectable for tests

    def _resolve_api_key(self) -> str:
        env_var = self._config.env_var_name()
        if not env_var:
            raise AiError(
                "API key source is not configured. Set api_key_source to "
                "env:OPENAI_API_KEY (or similar) and export the variable."
            )
        api_key = os.environ.get(env_var, "").strip()
        if not api_key:
            raise AiError(
                f"Environment variable {env_var} is empty. "
                "Set it before invoking AI rewrite."
            )
        return api_key

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise AiError("openai package is not installed") from exc
        kwargs = {"api_key": self._resolve_api_key()}
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def rewrite(self, request: RewriteRequest) -> RewriteResponse:
        if self._config.wire_api != "responses":
            raise AiError(
                f"Unsupported wire_api '{self._config.wire_api}'. "
                "M3 only supports 'responses'."
            )
        client = self._ensure_client()
        messages = self._prompts.build_messages(request)
        try:
            response = client.responses.create(
                model=self._config.model,
                input=messages,
            )
        except AiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AiError(f"AI request failed: {exc}") from exc

        text = _extract_output_text(response)
        if not text:
            raise AiError("AI response contained no text output.")

        usage = getattr(response, "usage", None)
        return RewriteResponse(
            content=text,
            model=self._config.model,
            provider=self.name,
            input_tokens=_safe_int(usage, "input_tokens"),
            output_tokens=_safe_int(usage, "output_tokens"),
            finish_reason=_safe_str(response, "finish_reason"),
        )


def _safe_int(obj, name: str) -> Optional[int]:
    if obj is None:
        return None
    value = getattr(obj, name, None)
    if isinstance(value, int):
        return value
    return None


def _safe_str(obj, name: str) -> Optional[str]:
    if obj is None:
        return None
    value = getattr(obj, name, None)
    return value if isinstance(value, str) else None


def _extract_output_text(response) -> str:
    """Pull text from a Responses-API result, tolerating SDK shape variance."""
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    output = getattr(response, "output", None) or []
    parts: list[str] = []
    for item in output:
        content = getattr(item, "content", None) or []
        for block in content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str):
                parts.append(block_text)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
    return "".join(parts).strip()
