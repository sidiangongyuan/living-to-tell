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
