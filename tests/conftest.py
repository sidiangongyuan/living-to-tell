"""Shared pytest fixtures.

Tests must never write into the real platformdirs user data directory. We
redirect storage to a per-test temp directory by setting ``WRITER_DATA_DIR``
before any writer module reads it.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from writer.app import paths as paths_module


@pytest.fixture()
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(paths_module.ENV_DATA_DIR, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def _safety_net_data_dir(tmp_path_factory: pytest.TempPathFactory,
                         monkeypatch: pytest.MonkeyPatch) -> None:
    """Even if a test forgets ``isolated_data_dir`` we still redirect storage
    out of the real user-data folder."""
    if os.environ.get(paths_module.ENV_DATA_DIR):
        return
    safe_dir = tmp_path_factory.mktemp("writer-data")
    monkeypatch.setenv(paths_module.ENV_DATA_DIR, str(safe_dir))
