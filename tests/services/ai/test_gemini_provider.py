import io
import json
from urllib.error import HTTPError

import pytest

from writer.app.container import build_container
from writer.domain.enums import RewriteAction
from writer.domain.models.ai_config import AiConfig
from writer.services.ai.gemini_auth import GeminiAuthResolver
from writer.services.ai.gemini_provider import GeminiProvider
from writer.services.ai.interfaces import AiError, RewriteRequest
from writer.services.ai.prompt_builder import PromptBuilder


class _FakeHttpResponse:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _RecordingOpener:
    def __init__(self, payload: dict | None = None, error_to_raise=None):
        self._payload = payload or {}
        self._error = error_to_raise
        self.requests = []

    def __call__(self, req, timeout=60):
        self.requests.append((req, timeout))
        if self._error is not None:
            raise self._error
        return _FakeHttpResponse(self._payload)


def _headers(req) -> dict[str, str]:
    return {key.lower(): value for key, value in req.header_items()}


def test_chat_uses_native_gemini_route_and_headers(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=gm-test\n", encoding="utf-8")
    opener = _RecordingOpener(
        {
            "candidates": [
                {
                    "content": {"parts": [{"text": "pong"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 3,
            },
        }
    )
    provider = GeminiProvider(
        AiConfig(
            base_url="https://example.test/gemini",
            model="gemini-3.1-pro",
            api_key_source="gemini",
        ),
        PromptBuilder(),
        gemini_auth=GeminiAuthResolver(path=env_file),
        opener=opener,
    )

    response = provider.chat(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "pong"},
        ]
    )

    assert response.content == "pong"
    assert response.provider == "gemini"
    assert response.input_tokens == 12
    assert response.output_tokens == 3

    req, timeout = opener.requests[0]
    assert timeout == 60
    assert req.full_url == (
        "https://example.test/gemini/v1beta/models/"
        "gemini-3.1-pro:generateContent"
    )
    headers = _headers(req)
    assert headers["x-goog-api-key"] == "gm-test"

    body = json.loads(req.data.decode("utf-8"))
    assert body["systemInstruction"]["parts"][0]["text"] == "sys"
    assert body["contents"][0]["role"] == "user"
    assert body["contents"][0]["parts"][0]["text"] == "hi"
    assert body["contents"][1]["role"] == "model"


def test_rewrite_strips_openai_suffix_from_base_url(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=gm-test\n", encoding="utf-8")
    opener = _RecordingOpener(
        {
            "candidates": [{"content": {"parts": [{"text": "done"}]}}],
        }
    )
    provider = GeminiProvider(
        AiConfig(
            base_url="https://example.test/v1beta/openai",
            model="gemini-3.1-pro",
            api_key_source="gemini",
        ),
        PromptBuilder(),
        gemini_auth=GeminiAuthResolver(path=env_file),
        opener=opener,
    )

    response = provider.rewrite(
        RewriteRequest(action=RewriteAction.POLISH, text="hi")
    )

    assert response.content == "done"
    req, _ = opener.requests[0]
    assert req.full_url == (
        "https://example.test/v1beta/models/"
        "gemini-3.1-pro:generateContent"
    )


def test_http_error_surfaces_provider_message(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=gm-test\n", encoding="utf-8")
    err = HTTPError(
        url="https://example.test",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(
            json.dumps({"error": {"message": "401 授权信息无效，请检查"}}).encode(
                "utf-8"
            )
        ),
    )
    provider = GeminiProvider(
        AiConfig(
            base_url="https://example.test/gemini",
            model="gemini-3.1-pro",
            api_key_source="gemini",
        ),
        PromptBuilder(),
        gemini_auth=GeminiAuthResolver(path=env_file),
        opener=_RecordingOpener(error_to_raise=err),
    )

    with pytest.raises(AiError, match="401 授权信息无效，请检查"):
        provider.chat([{"role": "user", "content": "hi"}])


def test_container_uses_gemini_provider_for_gemini_source(isolated_data_dir):
    container = build_container()
    try:
        container.settings.save_ai_config(
            AiConfig(
                provider_name="gemini",
                base_url="https://example.test/gemini",
                model="gemini-3.1-pro",
                api_key_source="gemini",
            )
        )
        provider = container.ai_task_service._provider_factory()  # noqa: SLF001
        assert isinstance(provider, GeminiProvider)
    finally:
        container.close()


def test_container_uses_gemini_provider_for_explicit_provider_name(isolated_data_dir):
    container = build_container()
    try:
        container.settings.save_ai_config(
            AiConfig(
                provider_name="gemini",
                base_url="https://example.test/gemini",
                model="gemini-3.1-pro",
                api_key_source="env:GEMINI_API_KEY",
            )
        )
        provider = container.ai_task_service._provider_factory()  # noqa: SLF001
        assert isinstance(provider, GeminiProvider)
    finally:
        container.close()