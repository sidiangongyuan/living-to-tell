"""OpenAI-compatible provider adapter.

Uses the ``responses`` API shape recommended in
``docs/codex-style-integration.md`` by default so the same configuration that
powers a local Codex setup can drive the writer app. ``chat_completions`` is
also supported for OpenAI-compatible relays such as DeepSeek-style gateways.
"""
from __future__ import annotations

import os
from typing import Optional

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.codex_auth import CodexAuthError, CodexAuthResolver
from writer.services.ai.gemini_auth import GeminiAuthError, GeminiAuthResolver
from writer.services.ai.interfaces import (
    AiError,
    AiProvider,
    ChatResponse,
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
        codex_auth: Optional[CodexAuthResolver] = None,
        gemini_auth: Optional[GeminiAuthResolver] = None,
    ) -> None:
        self._config = config
        self._prompts = prompt_builder
        self._client = client  # injectable for tests
        self._codex_auth = codex_auth  # injectable for tests; lazy default
        self._gemini_auth = gemini_auth  # injectable for tests; lazy default

    def _resolve_api_key(self) -> str:
        if self._config.uses_codex_auth():
            resolver = self._codex_auth or CodexAuthResolver()
            try:
                return resolver.read_api_key()
            except CodexAuthError as exc:
                # Re-raise as AiError. The message already avoids leaking
                # the key value (see codex_auth._extract_key).
                raise AiError(str(exc)) from exc

        if self._config.uses_gemini_auth():
            resolver = self._gemini_auth or GeminiAuthResolver()
            try:
                return resolver.read_api_key()
            except GeminiAuthError as exc:
                raise AiError(str(exc)) from exc

        env_var = self._config.env_var_name()
        if not env_var:
            raise AiError(
                "API key source is not configured. Set api_key_source to "
                "env:OPENAI_API_KEY (or similar), or to 'codex' to reuse "
                "~/.codex/auth.json, or to 'gemini' to reuse ~/.gemini/.env."
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
        if self._config.wire_api not in {"responses", "chat_completions"}:
            raise AiError(
                f"Unsupported wire_api '{self._config.wire_api}'. "
                "Supported values: responses, chat_completions."
            )
        client = self._ensure_client()
        messages = self._prompts.build_messages(request)
        if self._config.wire_api == "chat_completions":
            return self._chat_completions(messages, self._config.model)
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
            provider=self._provider_name(),
            transport="openai_responses",
            input_tokens=_safe_int(usage, "input_tokens"),
            output_tokens=_safe_int(usage, "output_tokens"),
            finish_reason=_safe_str(response, "finish_reason"),
        )

    # ------------------------------------------------------------------
    # M10A: generic chat — used by AiTaskService for the new task engine.
    # ------------------------------------------------------------------
    def chat(self, messages, *, model=None) -> ChatResponse:
        if self._config.wire_api not in {"responses", "chat_completions"}:
            raise AiError(
                f"Unsupported wire_api '{self._config.wire_api}'. "
                "Supported values: responses, chat_completions."
            )
        client = self._ensure_client()
        used_model = model or self._config.model
        if self._config.wire_api == "chat_completions":
            return self._chat_completions(list(messages), used_model)
        try:
            response = client.responses.create(
                model=used_model,
                input=list(messages),
            )
        except AiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AiError(f"AI request failed: {exc}") from exc

        text = _extract_output_text(response)
        if not text:
            raise AiError("AI response contained no text output.")

        usage = getattr(response, "usage", None)
        return ChatResponse(
            content=text,
            model=used_model,
            provider=self._provider_name(),
            transport="openai_responses",
            input_tokens=_safe_int(usage, "input_tokens"),
            output_tokens=_safe_int(usage, "output_tokens"),
            finish_reason=_safe_str(response, "finish_reason"),
        )

    def _provider_name(self) -> str:
        return self._config.provider_key()

    def _chat_completions(self, messages, model: str) -> ChatResponse:
        client = self._ensure_client()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=list(messages),
            )
        except AiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AiError(f"AI request failed: {exc}") from exc

        text = _extract_chat_completion_text(response)
        if not text:
            raise AiError("AI response contained no text output.")

        usage = getattr(response, "usage", None)
        return ChatResponse(
            content=text,
            model=model,
            provider=self._provider_name(),
            transport="openai_chat_completions",
            input_tokens=_safe_int(usage, "prompt_tokens"),
            output_tokens=_safe_int(usage, "completion_tokens"),
            finish_reason=_chat_finish_reason(response),
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


def _extract_chat_completion_text(response) -> str:
    choices = getattr(response, "choices", None) or []
    parts: list[str] = []
    for choice in choices:
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(message, dict) and isinstance(message.get("content"), str):
            parts.append(message["content"])
        elif isinstance(choice, dict):
            raw_message = choice.get("message")
            if isinstance(raw_message, dict) and isinstance(raw_message.get("content"), str):
                parts.append(raw_message["content"])
    return "".join(parts).strip()


def _chat_finish_reason(response) -> Optional[str]:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return None
    first = choices[0]
    value = getattr(first, "finish_reason", None)
    if isinstance(value, str):
        return value
    if isinstance(first, dict):
        raw = first.get("finish_reason")
        if isinstance(raw, str):
            return raw
    return None
