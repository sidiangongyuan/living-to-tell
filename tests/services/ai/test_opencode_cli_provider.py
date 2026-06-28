from __future__ import annotations

import json
import subprocess

import pytest

from writer.domain.enums import RewriteAction
from writer.domain.models.ai_config import AiConfig
from writer.services.ai.interfaces import AiError, RewriteRequest
from writer.services.ai.opencode_cli_provider import (
    OPENCODE_DEFAULT_MODEL,
    OpenCodeCliProvider,
    list_opencode_models,
    opencode_auth_status,
    parse_opencode_models,
)
from writer.services.ai.prompt_builder import PromptBuilder


def _json_event(event_type: str, part: dict) -> str:
    return json.dumps(
        {
            "type": event_type,
            "timestamp": 1,
            "sessionID": "ses_test",
            "part": part,
        },
        ensure_ascii=False,
    )


def test_chat_invokes_opencode_in_temp_dir_and_parses_json_events():
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="\n".join(
                [
                    _json_event(
                        "text",
                        {
                            "type": "text",
                            "text": "po",
                            "messageID": "m",
                            "sessionID": "s",
                        },
                    ),
                    _json_event(
                        "text",
                        {
                            "type": "text",
                            "text": "ng",
                            "messageID": "m",
                            "sessionID": "s",
                        },
                    ),
                    _json_event(
                        "step_finish",
                        {
                            "type": "step-finish",
                            "reason": "stop",
                            "tokens": {"input": 12, "output": 2},
                            "cost": 0,
                        },
                    ),
                ]
            ),
            stderr="",
        )

    provider = OpenCodeCliProvider(
        AiConfig(provider_name="opencode", model=OPENCODE_DEFAULT_MODEL),
        PromptBuilder(),
        command="opencode",
        runner=runner,
    )

    response = provider.chat([{"role": "user", "content": "ping"}])

    assert response.content == "pong"
    assert response.provider == "opencode"
    assert response.model == OPENCODE_DEFAULT_MODEL
    assert response.transport == "opencode_cli"
    assert response.input_tokens == 12
    assert response.output_tokens == 2
    assert response.finish_reason == "stop"
    assert response.cost == 0
    cmd, kwargs = calls[0]
    assert cmd[:6] == [
        "opencode",
        "run",
        "--model",
        OPENCODE_DEFAULT_MODEL,
        "--format",
        "json",
    ]
    assert "--dir" in cmd
    workdir = cmd[cmd.index("--dir") + 1]
    assert workdir
    assert kwargs["input"] == ""
    prompt = cmd[-1]
    assert "Do not use tools" in prompt
    assert "User:" in prompt


def test_rewrite_uses_prompt_builder_messages():
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=_json_event(
                "text",
                {
                    "type": "text",
                    "text": "polished",
                    "messageID": "m",
                    "sessionID": "s",
                },
            ),
            stderr="",
        )

    provider = OpenCodeCliProvider(
        AiConfig(provider_name="opencode"),
        PromptBuilder(),
        command="opencode",
        runner=runner,
    )

    response = provider.rewrite(
        RewriteRequest(action=RewriteAction.POLISH, text="hello")
    )

    assert response.content == "polished"
    assert response.provider == "opencode"


def test_nonzero_exit_maps_model_errors_to_chinese_message():
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            1,
            stdout="",
            stderr="Model not found: opencode/missing",
        )

    provider = OpenCodeCliProvider(
        AiConfig(provider_name="opencode", model="opencode/missing"),
        PromptBuilder(),
        command="opencode",
        runner=runner,
    )

    with pytest.raises(AiError, match="模型不存在"):
        provider.chat([{"role": "user", "content": "ping"}])


def test_invalid_json_output_raises_helpful_error():
    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="not-json", stderr="")

    provider = OpenCodeCliProvider(
        AiConfig(provider_name="opencode"),
        PromptBuilder(),
        command="opencode",
        runner=runner,
    )

    with pytest.raises(AiError, match="无法解析"):
        provider.chat([{"role": "user", "content": "ping"}])


def test_timeout_raises_helpful_error():
    def runner(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, timeout=1)

    provider = OpenCodeCliProvider(
        AiConfig(provider_name="opencode"),
        PromptBuilder(),
        command="opencode",
        runner=runner,
        timeout_seconds=1,
    )

    with pytest.raises(AiError, match="请求超时"):
        provider.chat([{"role": "user", "content": "ping"}])


def test_parse_opencode_models_filters_noise_and_duplicates():
    assert parse_opencode_models(
        "opencode/deepseek-v4-flash-free\n"
        "noise\n"
        "opencode/deepseek-v4-flash-free\n"
        "opencode/mimo-v2.5-free\n"
    ) == [
        "opencode/deepseek-v4-flash-free",
        "opencode/mimo-v2.5-free",
    ]


def test_list_opencode_models_invokes_refresh_flag():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="opencode/deepseek-v4-flash-free\nopencode/mimo-v2.5-free\n",
            stderr="",
        )

    models = list_opencode_models(command="opencode", runner=runner, refresh=True)

    assert models == [
        "opencode/deepseek-v4-flash-free",
        "opencode/mimo-v2.5-free",
    ]
    assert calls[0] == ["opencode", "models", "opencode", "--refresh"]


def test_opencode_auth_status_uses_auth_list_without_reading_key_file(tmp_path):
    def runner(cmd, **kwargs):
        assert cmd == ["opencode", "auth", "list"]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="Credentials are loaded from ~/.local/share/opencode/auth.json\nOpenCode Go api\n",
            stderr="",
        )

    status = opencode_auth_status(command="opencode", runner=runner)

    assert status.available is True
    assert status.command == "opencode"


def test_opencode_auth_status_warns_but_allows_existing_auth_file(monkeypatch, tmp_path):
    auth_dir = tmp_path / "opencode"
    auth_dir.mkdir()
    (auth_dir / "auth.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    def runner(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="auth list failed")

    status = opencode_auth_status(command="opencode", runner=runner)

    assert status.available is True
    assert status.reason == "auth_list_failed"
    assert status.path == auth_dir / "auth.json"
