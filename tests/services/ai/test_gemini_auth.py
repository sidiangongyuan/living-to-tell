from writer.services.ai.gemini_auth import (
    GEMINI_AUTH_SOURCE,
    GeminiAuthError,
    GeminiAuthResolver,
    GeminiConfigImporter,
)


def test_gemini_auth_source_constant():
    assert GEMINI_AUTH_SOURCE == "gemini"


def test_gemini_status_reports_missing_file(tmp_path):
    resolver = GeminiAuthResolver(path=tmp_path / "nope.env")
    status = resolver.status()
    assert not status.available
    assert status.reason == "missing_file"


def test_gemini_reads_api_key_and_imports_safe_fields(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GOOGLE_GEMINI_BASE_URL=https://example.test/gemini\n"
        "GEMINI_API_KEY=gm-test\n"
        "GEMINI_MODEL=gemini-3.1-pro\n",
        encoding="utf-8",
    )
    resolver = GeminiAuthResolver(path=env_file)
    importer = GeminiConfigImporter(path=env_file)

    assert resolver.read_api_key() == "gm-test"

    imported = importer.import_default()
    assert imported.base_url == "https://example.test/gemini"
    assert imported.model == "gemini-3.1-pro"
    assert imported.wire_api == "responses"


def test_gemini_read_raises_when_missing_key(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_MODEL=gemini-3.1-pro\n", encoding="utf-8")
    resolver = GeminiAuthResolver(path=env_file)

    try:
        resolver.read_api_key()
    except GeminiAuthError as exc:
        assert "GEMINI_API_KEY" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected GeminiAuthError")