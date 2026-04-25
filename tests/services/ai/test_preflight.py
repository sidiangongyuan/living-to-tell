"""Tests for the synchronous AI preflight checks (M7B)."""
from __future__ import annotations

from writer.domain.models.ai_config import AiConfig
from writer.services.ai.preflight import format_issues, preflight_rewrite


def _config(**overrides) -> AiConfig:
    base = dict(
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        wire_api="responses",
        api_key_source="env:OPENAI_API_KEY",
    )
    base.update(overrides)
    return AiConfig(**base)


def test_valid_config_passes() -> None:
    issues = preflight_rewrite(
        _config(),
        "hello world",
        has_entry=True,
        environ={"OPENAI_API_KEY": "sk-test"},
    )
    assert issues == []


def test_no_entry_blocks() -> None:
    issues = preflight_rewrite(
        _config(),
        "hello",
        has_entry=False,
        environ={"OPENAI_API_KEY": "sk"},
    )
    assert any(i.code == "no_entry" for i in issues)


def test_empty_text_blocks() -> None:
    issues = preflight_rewrite(
        _config(), "   ", environ={"OPENAI_API_KEY": "sk"}
    )
    assert any(i.code == "empty_text" for i in issues)


def test_missing_model_blocks() -> None:
    issues = preflight_rewrite(
        _config(model=""), "text", environ={"OPENAI_API_KEY": "sk"}
    )
    assert any(i.code == "no_model" for i in issues)


def test_bad_wire_api_blocks() -> None:
    issues = preflight_rewrite(
        _config(wire_api="rest-v99"), "text",
        environ={"OPENAI_API_KEY": "sk"},
    )
    assert any(i.code == "bad_wire_api" for i in issues)


def test_literal_key_source_blocks() -> None:
    issues = preflight_rewrite(
        _config(api_key_source="literal:sk-abc"), "text", environ={},
    )
    assert any(i.code == "bad_key_source" for i in issues)


def test_missing_env_var_blocks() -> None:
    issues = preflight_rewrite(
        _config(api_key_source="env:MY_MISSING_VAR"),
        "text",
        environ={},
    )
    assert any(i.code == "missing_env_var" for i in issues)


def test_format_issues_single_returns_message() -> None:
    [issue] = preflight_rewrite(
        _config(model=""), "text", environ={"OPENAI_API_KEY": "sk"}
    )
    assert format_issues([issue]) == issue.message


def test_format_issues_multi_uses_bullets() -> None:
    issues = preflight_rewrite(
        _config(model="", api_key_source="literal:x"), "", environ={},
    )
    rendered = format_issues(issues)
    assert rendered.count("•") >= 2


def test_codex_source_blocks_when_auth_missing(tmp_path) -> None:
    from writer.services.ai.codex_auth import CodexAuthResolver

    resolver = CodexAuthResolver(path=tmp_path / "no-such.json")
    issues = preflight_rewrite(
        _config(api_key_source="codex"),
        "hello",
        has_entry=True,
        environ={},
        codex_auth=resolver,
    )
    assert any(i.code == "missing_codex_auth" for i in issues)


def test_codex_source_passes_when_auth_available(tmp_path) -> None:
    import json

    from writer.services.ai.codex_auth import CodexAuthResolver

    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"OPENAI_API_KEY": "sk-x"}), encoding="utf-8")
    resolver = CodexAuthResolver(path=auth)
    issues = preflight_rewrite(
        _config(api_key_source="codex"),
        "hello",
        has_entry=True,
        environ={},
        codex_auth=resolver,
    )
    assert issues == []
