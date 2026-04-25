"""Tests for the Codex auth-file resolver.

Hard rule under test: no error message or status field may contain the
secret or a prefix of it — only structural facts (path, missing field).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from writer.services.ai.codex_auth import (
    CODEX_AUTH_SOURCE,
    CodexAuthError,
    CodexAuthResolver,
    status_text,
)


SECRET = "sk-supersecrettestvalue-should-never-leak"


def _write_auth(dir_: Path, payload) -> Path:
    path = dir_ / "auth.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_source_constant_is_literal_codex():
    assert CODEX_AUTH_SOURCE == "codex"


def test_missing_file_reports_missing_file(tmp_path):
    r = CodexAuthResolver(path=tmp_path / "nope.json")
    status = r.status()
    assert status.available is False
    assert status.reason == "missing_file"


def test_root_key_is_available(tmp_path):
    path = _write_auth(tmp_path, {"OPENAI_API_KEY": SECRET})
    r = CodexAuthResolver(path=path)
    assert r.status().available is True
    assert r.read_api_key() == SECRET


def test_nested_tokens_key_is_available(tmp_path):
    path = _write_auth(tmp_path, {"tokens": {"OPENAI_API_KEY": SECRET}})
    r = CodexAuthResolver(path=path)
    assert r.status().available is True
    assert r.read_api_key() == SECRET


def test_empty_key_reports_missing_key(tmp_path):
    path = _write_auth(tmp_path, {"OPENAI_API_KEY": "   "})
    r = CodexAuthResolver(path=path)
    status = r.status()
    assert status.available is False
    assert status.reason == "missing_key"
    with pytest.raises(CodexAuthError) as exc:
        r.read_api_key()
    assert SECRET not in str(exc.value)


def test_unreadable_file_reports_unreadable(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text("this is not json", encoding="utf-8")
    r = CodexAuthResolver(path=path)
    status = r.status()
    assert status.available is False
    assert status.reason == "unreadable"


def test_status_text_is_secret_free(tmp_path):
    path = _write_auth(tmp_path, {"OPENAI_API_KEY": SECRET})
    r = CodexAuthResolver(path=path)
    assert status_text(r.status()) == "available"


def test_errors_never_contain_the_secret(tmp_path):
    # Missing file
    r = CodexAuthResolver(path=tmp_path / "nope.json")
    with pytest.raises(CodexAuthError) as exc:
        r.read_api_key()
    assert SECRET not in str(exc.value)

    # No key field
    path = _write_auth(tmp_path, {"something_else": "x"})
    r = CodexAuthResolver(path=path)
    with pytest.raises(CodexAuthError) as exc:
        r.read_api_key()
    assert SECRET not in str(exc.value)
