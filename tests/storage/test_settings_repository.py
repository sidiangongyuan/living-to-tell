"""Tests for SettingsRepository."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.storage.database import open_and_initialize
from writer.storage.repositories.settings_repository import SettingsRepository


@pytest.fixture()
def repo(tmp_path: Path):
    conn = open_and_initialize(tmp_path / "test.sqlite3")
    try:
        yield SettingsRepository(conn)
    finally:
        conn.close()


def test_get_missing_returns_default(repo: SettingsRepository) -> None:
    assert repo.get("nope") is None
    assert repo.get("nope", "fallback") == "fallback"


def test_set_then_get(repo: SettingsRepository) -> None:
    repo.set("ai.model", "gpt-4o-mini")
    assert repo.get("ai.model") == "gpt-4o-mini"


def test_set_overwrites_existing_value(repo: SettingsRepository) -> None:
    repo.set("ai.base_url", "https://api.example.com/v1")
    repo.set("ai.base_url", "https://api.openai.com/v1")
    assert repo.get("ai.base_url") == "https://api.openai.com/v1"


def test_get_all_returns_all_pairs(repo: SettingsRepository) -> None:
    repo.set("a", "1")
    repo.set("b", "2")
    assert repo.get_all() == {"a": "1", "b": "2"}


def test_delete_removes_key(repo: SettingsRepository) -> None:
    repo.set("tmp", "x")
    repo.delete("tmp")
    assert repo.get("tmp") is None
