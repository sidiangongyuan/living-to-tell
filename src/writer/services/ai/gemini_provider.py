"""Native Gemini API provider adapter.

Uses the Gemini generateContent API directly instead of the OpenAI-compatible
Responses API. This matches the configuration shape used by the official
Gemini CLI, where ``GOOGLE_GEMINI_BASE_URL`` points at the service root and
the client appends the API version and native model routes.
"""
from __future__ import annotations

import json
import os
from typing import List, Optional
from urllib import error, request

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.gemini_auth import GeminiAuthError, GeminiAuthResolver
from writer.services.ai.interfaces import (
    AiError,
    AiProvider,
    ChatResponse,
    RewriteRequest,
    RewriteResponse,
)
from writer.services.ai.prompt_builder import PromptBuilder

GEMINI_TIMEOUT_ENV = "WRITER_GEMINI_TIMEOUT_SECONDS"
GEMINI_DEFAULT_TIMEOUT_SECONDS = 120


class GeminiProvider(AiProvider):
    """Adapter around the native Gemini generateContent HTTP API."""

    name = "gemini"

    def __init__(
        self,
        config: AiConfig,
        prompt_builder: PromptBuilder,
        *,
        gemini_auth: Optional[GeminiAuthResolver] = None,
        opener=None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self._config = config
        self._prompts = prompt_builder
        self._gemini_auth = gemini_auth
        self._opener = opener or request.urlopen
        self._timeout_seconds = _resolve_timeout_seconds(timeout_seconds)

    def rewrite(self, request_obj: RewriteRequest) -> RewriteResponse:
        messages = self._prompts.build_messages(request_obj)
        payload = self._build_payload(messages)
        result = self._send_request(self._config.model, payload)
        return RewriteResponse(
            content=result.content,
            model=self._config.model,
            provider=self.name,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            finish_reason=result.finish_reason,
        )

    def chat(self, messages, *, model=None) -> ChatResponse:
        used_model = model or self._config.model
        payload = self._build_payload(list(messages))
        result = self._send_request(used_model, payload)
        return ChatResponse(
            content=result.content,
            model=used_model,
            provider=self.name,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            finish_reason=result.finish_reason,
        )

    def _send_request(self, model: str, payload: dict) -> ChatResponse:
        api_key = self._resolve_api_key()
        url = self._request_url(model)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Writer/0.2",
        }
        mechanism = os.environ.get("GEMINI_API_KEY_AUTH_MECHANISM", "").strip().lower()
        if mechanism == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers["x-goog-api-key"] = api_key

        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with self._opener(req, timeout=self._timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            message = _extract_http_error(exc)
            raise AiError(f"AI request failed: {message}") from exc
        except error.URLError as exc:
            raise AiError(f"AI request failed: {exc.reason}") from exc
        except Exception as exc:  # noqa: BLE001
            raise AiError(f"AI request failed: {exc}") from exc

        parsed = _parse_response_json(raw)
        text = _extract_text(parsed)
        if not text:
            raise AiError("AI response contained no text output.")
        usage = parsed.get("usageMetadata") if isinstance(parsed, dict) else None
        candidate = _first_candidate(parsed)
        return ChatResponse(
            content=text,
            model=model,
            provider=self.name,
            input_tokens=_as_int(usage, "promptTokenCount"),
            output_tokens=_as_int(usage, "candidatesTokenCount"),
            finish_reason=_as_str(candidate, "finishReason"),
        )

    def _resolve_api_key(self) -> str:
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
                "env:GEMINI_API_KEY (or similar), or to 'gemini' to reuse "
                "~/.gemini/.env."
            )
        api_key = os.environ.get(env_var, "").strip()
        if not api_key:
            raise AiError(
                f"Environment variable {env_var} is empty. "
                "Set it before invoking Gemini."
            )
        return api_key

    def _request_url(self, model: str) -> str:
        base_url = _normalize_base_url(self._config.base_url)
        return f"{base_url}/models/{model}:generateContent"

    def _build_payload(self, messages: List[dict]) -> dict:
        system_text, contents = _split_messages(messages)
        payload = {"contents": contents}
        if system_text:
            payload["systemInstruction"] = {
                "parts": [{"text": system_text}],
            }
        return payload


def _normalize_base_url(base_url: Optional[str]) -> str:
    base = (base_url or "https://generativelanguage.googleapis.com").strip().rstrip("/")
    if base.endswith("/openai"):
        base = base[: -len("/openai")]
    if base.endswith("/v1") or base.endswith("/v1beta") or base.endswith("/v1beta1"):
        return base
    return base + "/v1beta"


def _resolve_timeout_seconds(explicit: Optional[int]) -> int:
    if explicit is not None:
        return max(1, int(explicit))
    raw = os.environ.get(GEMINI_TIMEOUT_ENV, "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return GEMINI_DEFAULT_TIMEOUT_SECONDS


def _split_messages(messages: List[dict]) -> tuple[str, List[dict]]:
    system_parts: List[str] = []
    contents: List[dict] = []
    for message in messages:
        role = str(message.get("role", "user") or "user").strip().lower()
        text = _message_text(message.get("content"))
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )
    if not contents:
        contents.append({"role": "user", "parts": [{"text": ""}]})
    return "\n\n".join(system_parts).strip(), contents


def _message_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(part for part in parts if part).strip()
    if isinstance(content, dict) and isinstance(content.get("text"), str):
        return content["text"].strip()
    return ""


def _extract_http_error(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:  # noqa: BLE001
        body = ""
    if body:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return body.strip() or f"HTTP {exc.code}"
        err = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(err, dict) and isinstance(err.get("message"), str):
            return err["message"]
        return body.strip()
    return f"HTTP {exc.code}"


def _parse_response_json(raw: str) -> dict:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AiError(f"AI response was not valid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise AiError("AI response JSON was not an object.")
    return loaded


def _first_candidate(data: dict) -> dict:
    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        return candidates[0]
    return {}


def _extract_text(data: dict) -> str:
    candidate = _first_candidate(data)
    content = candidate.get("content") if isinstance(candidate, dict) else None
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    out: List[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            out.append(part["text"])
    return "".join(out).strip()


def _as_int(obj, name: str) -> Optional[int]:
    if not isinstance(obj, dict):
        return None
    value = obj.get(name)
    return value if isinstance(value, int) else None


def _as_str(obj, name: str) -> Optional[str]:
    if not isinstance(obj, dict):
        return None
    value = obj.get(name)
    return value if isinstance(value, str) else None
