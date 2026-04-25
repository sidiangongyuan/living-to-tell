"""Tests for the one-shot env:OPENAI_API_KEY → codex auto-migration."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from writer.app.codex_auth_migration import (
    KEY_MIGRATION_FLAG,
    maybe_migrate_to_codex_auth,
)
from writer.app.settings import KEY_AI_API_KEY_SOURCE, Settings
from writer.services.ai.codex_auth import CodexAuthResolver
from writer.services.ai.codex_config_importer import CodexConfigImporter
from writer.storage.database import open_and_initialize
from writer.storage.repositories.settings_repository import SettingsRepository


SECRET = "sk-not-leaked-anywhere"


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    conn = open_and_initialize(tmp_path / "migrate.sqlite3")
    return Settings(SettingsRepository(conn))


def _seed_default_old_user(settings: Settings) -> None:
    """Mimic an existing install: env:OPENAI_API_KEY pointing at tokenflux."""
    settings.set("ai.base_url", "https://tokenflux.dev/v1")
    settings.set("ai.model", "gpt-5")
    settings.set("ai.wire_api", "responses")
    settings.set(KEY_AI_API_KEY_SOURCE, "env:OPENAI_API_KEY")


def _write_codex_config(
    dir_: Path,
    *,
    base_url: str = "https://tokenflux.dev/v1",
    requires_openai_auth: bool = True,
) -> Path:
    cfg = dir_ / "config.toml"
    cfg.write_text(
        f"""
model = "gpt-5"
model_provider = "tokenflux"

[model_providers.tokenflux]
base_url = "{base_url}"
wire_api = "responses"
requires_openai_auth = {str(requires_openai_auth).lower()}
""",
        encoding="utf-8",
    )
    return cfg


def _write_auth_json(dir_: Path, key: str = SECRET) -> Path:
    auth = dir_ / "auth.json"
    auth.write_text(json.dumps({"OPENAI_API_KEY": key}), encoding="utf-8")
    return auth


class _FixedPathImporter(CodexConfigImporter):
    """Importer whose default_path is overridden for tests."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def default_path(self) -> Path:  # type: ignore[override]
        return self._path


# ---------------------------------------------------------------------------
# Should migrate
# ---------------------------------------------------------------------------


def test_migrates_when_all_conditions_met(settings, tmp_path):
    _seed_default_old_user(settings)
    cfg = _write_codex_config(tmp_path)
    auth = _write_auth_json(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )

    assert outcome.migrated is True
    assert outcome.reason == "ok"
    assert settings.ai_api_key_source == "codex"
    assert settings.get(KEY_MIGRATION_FLAG) == "1"


def test_secret_is_never_persisted(settings, tmp_path):
    _seed_default_old_user(settings)
    cfg = _write_codex_config(tmp_path)
    auth = _write_auth_json(tmp_path)
    maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )
    # Walk every persisted value and assert the key never appears.
    all_values = settings._repo.get_all()  # type: ignore[attr-defined]
    for k, v in all_values.items():
        assert SECRET not in (v or ""), f"secret leaked into {k}"


# ---------------------------------------------------------------------------
# Should NOT migrate
# ---------------------------------------------------------------------------


def test_skipped_when_env_var_is_set(settings, tmp_path):
    _seed_default_old_user(settings)
    cfg = _write_codex_config(tmp_path)
    auth = _write_auth_json(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={"OPENAI_API_KEY": "user-already-exported"},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )

    assert outcome.migrated is False
    assert outcome.reason == "env_var_present"
    assert settings.ai_api_key_source == "env:OPENAI_API_KEY"


def test_skipped_when_codex_config_missing(settings, tmp_path):
    _seed_default_old_user(settings)
    auth = _write_auth_json(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(tmp_path / "no-config.toml"),
    )

    assert outcome.migrated is False
    assert outcome.reason == "no_codex_config"
    assert settings.ai_api_key_source == "env:OPENAI_API_KEY"


def test_skipped_when_requires_openai_auth_is_false(settings, tmp_path):
    _seed_default_old_user(settings)
    cfg = _write_codex_config(tmp_path, requires_openai_auth=False)
    auth = _write_auth_json(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )

    assert outcome.migrated is False
    assert outcome.reason == "auth_not_required"


def test_skipped_when_base_url_mismatch(settings, tmp_path):
    _seed_default_old_user(settings)
    # Codex config points elsewhere than the user's stored base_url.
    cfg = _write_codex_config(tmp_path, base_url="https://other-provider/v1")
    auth = _write_auth_json(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )

    assert outcome.migrated is False
    assert outcome.reason == "base_url_mismatch"
    assert settings.ai_api_key_source == "env:OPENAI_API_KEY"


def test_skipped_when_auth_file_missing(settings, tmp_path):
    _seed_default_old_user(settings)
    cfg = _write_codex_config(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=tmp_path / "no-such-auth.json"),
        importer=_FixedPathImporter(cfg),
    )

    assert outcome.migrated is False
    assert outcome.reason == "auth_file_unavailable"


def test_skipped_when_user_already_chose_codex(settings, tmp_path):
    _seed_default_old_user(settings)
    settings.set(KEY_AI_API_KEY_SOURCE, "codex")
    cfg = _write_codex_config(tmp_path)
    auth = _write_auth_json(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )

    assert outcome.migrated is False
    assert outcome.reason == "source_not_default"


def test_skipped_when_user_uses_different_env_var(settings, tmp_path):
    _seed_default_old_user(settings)
    settings.set(KEY_AI_API_KEY_SOURCE, "env:MY_OTHER_KEY")
    cfg = _write_codex_config(tmp_path)
    auth = _write_auth_json(tmp_path)

    outcome = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )

    assert outcome.migrated is False
    assert outcome.reason == "source_not_default"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_migration_is_idempotent(settings, tmp_path):
    _seed_default_old_user(settings)
    cfg = _write_codex_config(tmp_path)
    auth = _write_auth_json(tmp_path)

    first = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )
    assert first.migrated is True

    # User then reverts to env:VAR through the Settings dialog.
    settings.set(KEY_AI_API_KEY_SOURCE, "env:OPENAI_API_KEY")

    # Second startup must NOT re-flip the user's choice.
    second = maybe_migrate_to_codex_auth(
        settings,
        environ={},
        codex_auth=CodexAuthResolver(path=auth),
        importer=_FixedPathImporter(cfg),
    )
    assert second.migrated is False
    assert second.reason == "already_done"
    assert settings.ai_api_key_source == "env:OPENAI_API_KEY"
