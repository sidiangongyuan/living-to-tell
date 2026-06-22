"""Gemini provider adapter.

Native Gemini API keys use the ``generateContent`` route. Gemini proxy keys
that look like ``sk-...`` usually expose Gemini models through the familiar
``/v1/chat/completions`` wire protocol, even though the provider and model are
still Gemini. The adapter chooses the transport from the key shape and base
URL, so user-facing configuration can stay provider-oriented.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
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
GEMINI_CLI_GATEWAY_USER_AGENT_ENV = "WRITER_GEMINI_GATEWAY_USER_AGENT"
GEMINI_CLI_GATEWAY_API_CLIENT = "google-genai-sdk/1.30.0 gl-node/v25.7.0"
GEMINI_CLI_GATEWAY_VERSION = "0.47.0"


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
        result = self._send_request(self._config.model, messages)
        return RewriteResponse(
            content=result.content,
            model=self._config.model,
            provider=self.name,
            transport=result.transport,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            finish_reason=result.finish_reason,
        )

    def chat(self, messages, *, model=None) -> ChatResponse:
        used_model = model or self._config.model
        result = self._send_request(used_model, list(messages))
        return ChatResponse(
            content=result.content,
            model=used_model,
            provider=self.name,
            transport=result.transport,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            finish_reason=result.finish_reason,
        )

    def _send_request(self, model: str, messages: List[dict]) -> ChatResponse:
        api_key = self._resolve_api_key()
        if _should_use_openai_compatible_transport(api_key, self._config.base_url):
            return self._send_openai_compatible_request(model, messages, api_key)

        if _should_use_gemini_cli_gateway_transport(self._config):
            return self._send_gemini_cli_gateway_request(model, messages, api_key)

        url = self._request_url(model)
        payload = self._build_payload(messages)
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
            transport="gemini_native",
            input_tokens=_as_int(usage, "promptTokenCount"),
            output_tokens=_as_int(usage, "candidatesTokenCount"),
            finish_reason=_as_str(candidate, "finishReason"),
        )

    def _send_gemini_cli_gateway_request(
        self,
        model: str,
        messages: List[dict],
        api_key: str,
    ) -> ChatResponse:
        url = _gemini_cli_gateway_stream_url(self._config.base_url, model)
        payload = self._build_payload(messages)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": _gemini_cli_gateway_user_agent(model),
                "x-goog-api-client": GEMINI_CLI_GATEWAY_API_CLIENT,
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
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

        chunks = _parse_sse_json_objects(raw)
        text = "".join(_extract_text(chunk) for chunk in chunks).strip()
        if not text:
            raise AiError("AI response contained no text output.")
        last = chunks[-1] if chunks else {}
        usage = last.get("usageMetadata") if isinstance(last, dict) else None
        candidate = _first_candidate(last) if isinstance(last, dict) else {}
        return ChatResponse(
            content=text,
            model=model,
            provider=self.name,
            transport="gemini_stream_gateway",
            input_tokens=_as_int(usage, "promptTokenCount"),
            output_tokens=_as_int(usage, "candidatesTokenCount"),
            finish_reason=_as_str(candidate, "finishReason"),
        )

    def _send_openai_compatible_request(
        self,
        model: str,
        messages: List[dict],
        api_key: str,
    ) -> ChatResponse:
        url = _openai_compatible_chat_url(self._config.base_url)
        payload = {
            "model": model,
            "messages": _gateway_compatible_messages(messages),
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _gemini_cli_gateway_user_agent(model),
        }
        if self._opener is request.urlopen:
            raw = _post_json_with_curl(
                url,
                headers=headers,
                payload=payload,
                timeout_seconds=self._timeout_seconds,
            )
        else:
            raw = self._post_json_with_urllib(url, headers=headers, payload=payload)

        parsed = _parse_response_json(raw)
        text = _extract_openai_compatible_text(parsed)
        if not text:
            raise AiError("AI response contained no text output.")
        usage = parsed.get("usage") if isinstance(parsed, dict) else None
        choice = _first_openai_choice(parsed)
        return ChatResponse(
            content=text,
            model=model,
            provider=self.name,
            transport="gateway_compatible",
            input_tokens=_as_int(usage, "prompt_tokens"),
            output_tokens=_as_int(usage, "completion_tokens"),
            finish_reason=_as_str(choice, "finish_reason"),
        )

    def _post_json_with_urllib(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict,
    ) -> str:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with self._opener(req, timeout=self._timeout_seconds) as resp:
                return resp.read().decode("utf-8")
        except error.HTTPError as exc:
            message = _extract_http_error(exc)
            raise AiError(f"AI request failed: {message}") from exc
        except error.URLError as exc:
            raise AiError(f"AI request failed: {exc.reason}") from exc
        except Exception as exc:  # noqa: BLE001
            raise AiError(f"AI request failed: {exc}") from exc

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


def _openai_compatible_chat_url(base_url: Optional[str]) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise AiError(
            "OpenAI-compatible Gemini transport requires a custom API base URL."
        )
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1") or base.endswith("/v1beta") or base.endswith("/openai"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def _gemini_cli_gateway_stream_url(base_url: Optional[str], model: str) -> str:
    base = _normalize_base_url(base_url)
    return f"{base}/models/{model}:streamGenerateContent?alt=sse"


def _should_use_gemini_cli_gateway_transport(config: AiConfig) -> bool:
    if not config.uses_gemini_auth():
        return False
    base = (config.base_url or "").strip().lower()
    if not base:
        return False
    return "generativelanguage.googleapis.com" not in base


def _should_use_openai_compatible_transport(
    api_key: str,
    base_url: Optional[str],
) -> bool:
    key = (api_key or "").strip()
    if not key.lower().startswith("sk-"):
        return False
    base = (base_url or "").strip().lower()
    # Google-native endpoints do not use sk-style keys. When a local Gemini
    # config contains one, it is almost always an OpenAI-compatible proxy.
    return bool(base and "generativelanguage.googleapis.com" not in base)


def _gemini_cli_gateway_user_agent(model: str) -> str:
    override = os.environ.get(GEMINI_CLI_GATEWAY_USER_AGENT_ENV, "").strip()
    if override:
        return override
    platform = "win32" if sys.platform.startswith("win") else sys.platform
    arch = "x64" if sys.maxsize > 2**32 else "ia32"
    return (
        f"GeminiCLI-tui/{GEMINI_CLI_GATEWAY_VERSION}/{model} "
        f"({platform}; {arch}; terminal)"
    )


def _post_json_with_curl(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict,
    timeout_seconds: int,
) -> str:
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise AiError(
            "Gateway-compatible Gemini transport requires curl on this system. "
            "Install curl or use a Google-native Gemini key."
        )
    payload_text = json.dumps(payload, ensure_ascii=False)
    config_lines = [
        "silent",
        "show-error",
        f"max-time = {max(1, int(timeout_seconds))}",
        f"url = {json.dumps(url, ensure_ascii=False)}",
        "request = POST",
        f"data-binary = {json.dumps(payload_text, ensure_ascii=False)}",
        f"write-out = {json.dumps(chr(10) + '__WRITER_HTTP_STATUS__:%{http_code}')}",
    ]
    config_lines.extend(
        f"header = {json.dumps(f'{key}: {value}', ensure_ascii=False)}"
        for key, value in headers.items()
    )
    config = "\n".join(config_lines)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [curl, "--config", "-"],
            input=config,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, int(timeout_seconds)) + 5,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as exc:
        raise AiError(f"AI request failed: timed out after {timeout_seconds} seconds") from exc
    except Exception as exc:  # noqa: BLE001
        raise AiError(f"AI request failed: curl could not start: {exc}") from exc

    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or f"curl exit {completed.returncode}").strip()
        raise AiError(f"AI request failed: {message}")
    return _extract_curl_body_or_raise(completed.stdout)


def _extract_curl_body_or_raise(raw: str) -> str:
    marker = "\n__WRITER_HTTP_STATUS__:"
    if marker not in raw:
        return raw
    body, status_text = raw.rsplit(marker, 1)
    try:
        status = int(status_text.strip()[:3])
    except ValueError:
        return body
    if status >= 400:
        raise AiError(f"AI request failed: {_extract_error_body(body, status, '')}")
    if status == 0:
        raise AiError("AI request failed: network connection failed")
    return body


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


def _gateway_compatible_messages(messages: List[dict]) -> List[dict]:
    """Build messages for Gemini models behind OpenAI-compatible gateways.

    Some Gemini relay services expose /v1/chat/completions but reject OpenAI's
    system role when forwarding to the upstream Gemini API. Folding system
    instructions into the first user message keeps one wire protocol for the
    user-facing Gemini provider while avoiding that gateway-specific failure.
    """
    system_parts: List[str] = []
    out: List[dict] = []
    first_user_index: Optional[int] = None
    for message in messages:
        role = str(message.get("role", "user") or "user").strip().lower()
        text = _message_text(message.get("content"))
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        if role == "user" and first_user_index is None:
            first_user_index = len(out)
        out.append({"role": role, "content": text})

    system_text = "\n\n".join(system_parts).strip()
    if system_text:
        folded = f"系统指令：\n{system_text}"
        if first_user_index is None:
            out.insert(0, {"role": "user", "content": folded})
        else:
            original = out[first_user_index]["content"]
            out[first_user_index]["content"] = f"{folded}\n\n用户输入：\n{original}"

    if not out:
        out.append({"role": "user", "content": ""})
    return out


def _extract_http_error(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:  # noqa: BLE001
        body = ""
    if body:
        return _extract_error_body(body, exc.code, exc.reason)
    return f"HTTP {exc.code}"


def _extract_error_body(body: str, code: int, reason: str) -> str:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return _clean_http_error_body(body, code, reason)
    err = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(err, dict):
        message = err.get("message")
        code_text = err.get("code")
        err_type = err.get("type")
        if code >= 500 and (
            message == "openai_error"
            or code_text == "bad_response_status_code"
            or err_type == "bad_response_status_code"
        ):
            return (
                f"HTTP {code}: 中转接口返回了上游错误，请检查模型名、"
                "模型权限或请求格式。"
            )
        if isinstance(message, str) and message.strip():
            if isinstance(code_text, str) and code_text.strip() and code_text not in message:
                return f"HTTP {code}: {code_text}: {message}"
            return f"HTTP {code}: {message}"
    return _clean_http_error_body(body, code, reason)


def _clean_http_error_body(body: str, code: int, reason: str) -> str:
    text = body.strip()
    if not text:
        return f"HTTP {code} {reason}".strip()
    if "<html" in text[:500].lower() or "<!doctype html" in text[:500].lower():
        if code == 403:
            return (
                "HTTP 403: AI 服务拒绝了当前请求。可能是中转接口协议不匹配、"
                "模型无权限或密钥无效。"
            )
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL
        )
        if title_match:
            title = html.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip()
            return f"HTTP {code}: {title}"
        text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    if len(text) > 500:
        text = text[:500].rstrip() + "..."
    return text or f"HTTP {code} {reason}".strip()


def _parse_response_json(raw: str) -> dict:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AiError(f"AI response was not valid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise AiError("AI response JSON was not an object.")
    return loaded


def _parse_sse_json_objects(raw: str) -> List[dict]:
    events: List[dict] = []
    data_lines: List[str] = []

    def flush() -> None:
        if not data_lines:
            return
        data = "\n".join(data_lines).strip()
        data_lines.clear()
        if not data or data == "[DONE]":
            return
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise AiError(f"AI stream response was not valid JSON: {exc}") from exc
        if isinstance(parsed, dict):
            if isinstance(parsed.get("error"), dict):
                message = parsed["error"].get("message")
                raise AiError(str(message or parsed["error"]))
            events.append(parsed)

    for raw_line in raw.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            flush()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    flush()
    if events:
        return events

    # Some gateways return one JSON object instead of a formal SSE stream even
    # on the streaming route.
    return [_parse_response_json(raw)]


def _first_candidate(data: dict) -> dict:
    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        return candidates[0]
    return {}


def _first_openai_choice(data: dict) -> dict:
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return choices[0]
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


def _extract_openai_compatible_text(data: dict) -> str:
    choice = _first_openai_choice(data)
    message = choice.get("message") if isinstance(choice, dict) else None
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    elif isinstance(item.get("content"), str):
                        parts.append(item["content"])
            return "".join(parts).strip()
    text = choice.get("text") if isinstance(choice, dict) else None
    return text.strip() if isinstance(text, str) else ""


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
