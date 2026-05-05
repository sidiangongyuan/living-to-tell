import pytest

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.interfaces import (
    AiError,
    RewriteRequest,
)
from writer.services.ai.openai_provider import OpenAiProvider
from writer.services.ai.prompt_builder import PromptBuilder
from writer.domain.enums import RewriteAction


class _FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.usage = type("U", (), {"input_tokens": 10, "output_tokens": 5})()


class _FakeResponses:
    def __init__(self, output_text: str = "result"):
        self._text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._text)


class _FakeClient:
    def __init__(self, output_text: str = "result"):
        self.responses = _FakeResponses(output_text)


def test_rewrite_uses_responses_api_and_returns_text():
    client = _FakeClient("polished output")
    config = AiConfig(model="m", base_url="https://x", api_key_source="env:NOPE")
    provider = OpenAiProvider(config, PromptBuilder(), client=client)

    response = provider.rewrite(
        RewriteRequest(action=RewriteAction.POLISH, text="hi")
    )

    assert response.content == "polished output"
    assert response.model == "m"
    assert response.provider == "openai"
    assert response.input_tokens == 10
    assert response.output_tokens == 5
    assert client.responses.calls[0]["model"] == "m"
    assert client.responses.calls[0]["input"][0]["role"] == "system"


def test_rewrite_rejects_unsupported_wire_api():
    client = _FakeClient()
    config = AiConfig(wire_api="chat", api_key_source="env:NOPE")
    provider = OpenAiProvider(config, PromptBuilder(), client=client)
    with pytest.raises(AiError):
        provider.rewrite(RewriteRequest(action=RewriteAction.POLISH, text="hi"))


def test_missing_env_var_raises(monkeypatch):
    monkeypatch.delenv("WRITER_TEST_KEY", raising=False)
    config = AiConfig(api_key_source="env:WRITER_TEST_KEY")
    provider = OpenAiProvider(config, PromptBuilder())  # no injected client
    with pytest.raises(AiError):
        provider.rewrite(RewriteRequest(action=RewriteAction.POLISH, text="hi"))


def test_codex_source_routes_to_resolver(tmp_path):
    import json

    from writer.services.ai.codex_auth import CodexAuthResolver

    auth = tmp_path / "auth.json"
    auth.write_text(
        json.dumps({"OPENAI_API_KEY": "sk-from-codex"}), encoding="utf-8"
    )
    resolver = CodexAuthResolver(path=auth)
    config = AiConfig(api_key_source="codex")
    provider = OpenAiProvider(config, PromptBuilder(), codex_auth=resolver)
    assert provider._resolve_api_key() == "sk-from-codex"


def test_codex_source_raises_ai_error_when_missing(tmp_path):
    from writer.services.ai.codex_auth import CodexAuthResolver

    resolver = CodexAuthResolver(path=tmp_path / "no-such.json")
    config = AiConfig(api_key_source="codex")
    provider = OpenAiProvider(config, PromptBuilder(), codex_auth=resolver)
    with pytest.raises(AiError):
        provider._resolve_api_key()


def test_gemini_source_routes_to_resolver(tmp_path):
    from writer.services.ai.gemini_auth import GeminiAuthResolver

    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=gm-test\n"
        "GOOGLE_GEMINI_BASE_URL=https://example.test/gemini\n",
        encoding="utf-8",
    )
    resolver = GeminiAuthResolver(path=env_file)
    config = AiConfig(api_key_source="gemini")
    provider = OpenAiProvider(config, PromptBuilder(), gemini_auth=resolver)
    assert provider._resolve_api_key() == "gm-test"


def test_explicit_gemini_provider_name_sets_provider_name():
    client = _FakeClient("gemini output")
    config = AiConfig(
        provider_name="gemini",
        model="gemini-3.1-pro",
        api_key_source="gemini",
    )
    provider = OpenAiProvider(config, PromptBuilder(), client=client)

    response = provider.rewrite(
        RewriteRequest(action=RewriteAction.POLISH, text="hi")
    )

    assert response.provider == "gemini"
