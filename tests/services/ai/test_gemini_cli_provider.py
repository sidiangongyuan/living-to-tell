from __future__ import annotations

import subprocess

import pytest

from writer.domain.enums import RewriteAction
from writer.domain.models.ai_config import AiConfig
import writer.services.ai.gemini_cli_provider as gemini_cli_mod
from writer.services.ai.gemini_cli_provider import (
    GEMINI_CLI_DEFAULT_MODEL,
    GEMINI_CLI_PROXY_ENV,
    GEMINI_CLI_TIMEOUT_ENV,
    GeminiCliProvider,
)
from writer.services.ai.interfaces import AiError, RewriteRequest
from writer.services.ai.prompt_builder import PromptBuilder


@pytest.fixture(autouse=True)
def _disable_real_oauth_refresh(monkeypatch):
    monkeypatch.setattr(
        gemini_cli_mod,
        "_refresh_gemini_cli_access_token",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        gemini_cli_mod,
        "_try_run_code_assist_prompt",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(gemini_cli_mod, "_windows_system_proxy_url", lambda: None)


def test_chat_invokes_gemini_cli_and_returns_clean_text():
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="Ripgrep is not available. Falling back to GrepTool.\n\npong\n",
            stderr="",
        )

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli", model=GEMINI_CLI_DEFAULT_MODEL),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    response = provider.chat([{"role": "user", "content": "ping"}])

    assert response.content == "pong"
    assert response.provider == "gemini_cli"
    assert response.model == GEMINI_CLI_DEFAULT_MODEL
    cmd = calls[0][0]
    kwargs = calls[0][1]
    assert cmd[:2] == ["gemini.cmd", "--skip-trust"]
    assert "--model" not in cmd
    assert "--prompt" in cmd
    assert "User:" in cmd[-1]
    assert kwargs["input"] == ""
    assert kwargs["env"]["GEMINI_CLI_TRUST_WORKSPACE"] == "true"


def test_chat_passes_explicit_model_to_gemini_cli():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli", model="gemini-2.5-pro"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    response = provider.chat([{"role": "user", "content": "ping"}])

    assert response.model == "gemini-2.5-pro"
    assert "--model" in calls[0]
    assert calls[0][calls[0].index("--model") + 1] == "gemini-2.5-pro"


def test_openai_default_model_is_not_passed_to_gemini_cli():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli", model="gpt-4o-mini"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    response = provider.chat([{"role": "user", "content": "ping"}])

    assert response.model == GEMINI_CLI_DEFAULT_MODEL
    assert "--model" not in calls[0]


def test_proxy_env_is_injected_from_config():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    provider = GeminiCliProvider(
        AiConfig(
            provider_name="gemini_cli",
            model=GEMINI_CLI_DEFAULT_MODEL,
            gemini_cli_proxy="127.0.0.1:9999",
        ),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    provider.chat([{"role": "user", "content": "ping"}])

    env = calls[0]["env"]
    assert env[GEMINI_CLI_PROXY_ENV] == "http://127.0.0.1:9999"
    assert env["HTTPS_PROXY"] == "http://127.0.0.1:9999"
    assert env["HTTP_PROXY"] == "http://127.0.0.1:9999"


def test_direct_code_assist_output_is_used_before_cli(monkeypatch):
    def runner(cmd, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("CLI fallback should not run")

    monkeypatch.setattr(
        gemini_cli_mod,
        "_try_run_code_assist_prompt",
        lambda *args, **kwargs: gemini_cli_mod._GeminiCliRunResult(
            text="pong",
            model="gemini-2.5-pro",
            input_tokens=1,
            output_tokens=1,
        ),
    )
    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli", model=GEMINI_CLI_DEFAULT_MODEL),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    response = provider.chat([{"role": "user", "content": "ping"}])

    assert response.content == "pong"
    assert response.model == "gemini-2.5-pro"
    assert response.input_tokens == 1
    assert response.output_tokens == 1


def test_extract_code_assist_text():
    payload = {
        "response": {
            "candidates": [
                {"content": {"parts": [{"text": "po"}, {"text": "ng"}]}}
            ]
        }
    }

    assert gemini_cli_mod._extract_code_assist_text(payload) == "pong"


def test_extract_code_assist_model_and_usage():
    payload = {
        "response": {
            "modelVersion": "gemini-2.5-pro",
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 3,
            },
        }
    }

    assert gemini_cli_mod._extract_code_assist_model(payload) == "gemini-2.5-pro"
    assert gemini_cli_mod._extract_code_assist_usage(payload) == (12, 3)


def test_quota_status_from_load_response():
    payload = {
        "currentTier": {"name": "Gemini Code Assist"},
        "paidTier": {"name": "Google One AI Pro"},
        "cloudaicompanionProject": "project-123",
    }

    status = gemini_cli_mod._quota_status_from_load_response(
        payload, account="a@example.com"
    )

    assert status.available is True
    assert status.account == "a@example.com"
    assert status.project_id == "project-123"
    assert status.current_tier == "Gemini Code Assist"
    assert status.paid_tier == "Google One AI Pro"
    assert status.credits == "included / not itemized"


def test_rewrite_uses_prompt_builder_messages():
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="polished", stderr="")

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    response = provider.rewrite(
        RewriteRequest(action=RewriteAction.POLISH, text="hello")
    )

    assert response.content == "polished"
    assert response.provider == "gemini_cli"


def test_nonzero_exit_raises_ai_error():
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="auth failed")

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    with pytest.raises(AiError, match="auth failed"):
        provider.chat([{"role": "user", "content": "ping"}])


def test_auth_prompt_output_raises_helpful_ai_error():
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="Opening authentication page in your browser. Do you want to continue? [Y/n]: ",
            stderr="",
        )

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    with pytest.raises(AiError, match="OAuth authentication"):
        provider.chat([{"role": "user", "content": "ping"}])


def test_auth_prompt_noise_is_ignored_when_text_output_exists():
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=(
                "Opening authentication page in your browser. Do you want to continue? [Y/n]: y\n"
                "Ripgrep is not available. Falling back to GrepTool.\n"
                "pong\n"
            ),
            stderr="",
        )

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    response = provider.chat([{"role": "user", "content": "ping"}])

    assert response.content == "pong"


def test_timeout_raises_ai_error():
    def runner(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, timeout=1)

    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
        timeout_seconds=1,
    )

    with pytest.raises(AiError, match="timed out"):
        provider.chat([{"role": "user", "content": "ping"}])


def test_timeout_after_oauth_injection_mentions_code_assist(monkeypatch):
    def runner(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, timeout=1)

    monkeypatch.setattr(
        gemini_cli_mod,
        "_refresh_gemini_cli_access_token",
        lambda *args, **kwargs: "access-token",
    )
    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
        timeout_seconds=1,
    )

    with pytest.raises(AiError, match="cloudcode-pa.googleapis.com"):
        provider.chat([{"role": "user", "content": "ping"}])


def test_timeout_can_be_configured_by_environment(monkeypatch):
    calls = []

    def runner(cmd, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setenv(GEMINI_CLI_TIMEOUT_ENV, "7")
    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    provider.chat([{"role": "user", "content": "ping"}])

    assert calls[0]["timeout"] == 7


def test_default_timeout_allows_longer_writer_prompts(monkeypatch):
    calls = []

    def runner(cmd, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.delenv(GEMINI_CLI_TIMEOUT_ENV, raising=False)
    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    provider.chat([{"role": "user", "content": "ping"}])

    assert calls[0]["timeout"] == 120


def test_oauth_access_token_is_injected_when_refresh_available(monkeypatch):
    calls = []

    def runner(cmd, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(
        gemini_cli_mod,
        "_refresh_gemini_cli_access_token",
        lambda *args, **kwargs: "access-token",
    )
    provider = GeminiCliProvider(
        AiConfig(provider_name="gemini_cli"),
        PromptBuilder(),
        command="gemini.cmd",
        runner=runner,
    )

    provider.chat([{"role": "user", "content": "ping"}])

    env = calls[0]["env"]
    assert env["GOOGLE_GENAI_USE_GCA"] == "true"
    assert env["GOOGLE_CLOUD_ACCESS_TOKEN"] == "access-token"
