from pathlib import Path

import pytest

from writer.services.ai.codex_config_importer import CodexConfigImporter


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_imports_safe_fields_from_codex_layout(tmp_path):
    cfg = _write(
        tmp_path,
        """
        model = "gpt-5"
        model_provider = "openai"

        [model_providers.openai]
        name = "OpenAI"
        base_url = "https://example.test/v1"
        wire_api = "responses"
        api_key = "should-not-be-imported"
        """,
    )
    result = CodexConfigImporter().import_from(cfg)
    assert result.base_url == "https://example.test/v1"
    assert result.model == "gpt-5"
    assert result.wire_api == "responses"


def test_credentials_are_not_exposed(tmp_path):
    cfg = _write(
        tmp_path,
        """
        model = "gpt-5"
        model_provider = "openai"

        [model_providers.openai]
        base_url = "https://example.test/v1"
        wire_api = "responses"
        api_key = "secret"

        [auth]
        token = "should-be-ignored"
        """,
    )
    result = CodexConfigImporter().import_from(cfg)
    # Result is a frozen dataclass with only safe, non-credential fields.
    assert set(result.__dataclass_fields__.keys()) == {
        "base_url",
        "model",
        "wire_api",
        "requires_openai_auth",
    }


def test_flat_layout_fallback(tmp_path):
    cfg = _write(
        tmp_path,
        """
        base_url = "https://flat.example/v1"
        model = "gpt-test"
        wire_api = "responses"
        """,
    )
    result = CodexConfigImporter().import_from(cfg)
    assert result.base_url == "https://flat.example/v1"
    assert result.model == "gpt-test"
    assert result.wire_api == "responses"


def test_missing_provider_block_yields_partial(tmp_path):
    cfg = _write(tmp_path, 'model = "only-model"\n')
    result = CodexConfigImporter().import_from(cfg)
    assert result.model == "only-model"
    assert result.base_url is None
    assert result.wire_api is None
    assert not result.is_empty()


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        CodexConfigImporter().import_from(tmp_path / "nope.toml")
