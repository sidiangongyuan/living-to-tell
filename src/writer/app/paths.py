"""Filesystem locations for user data, settings and the SQLite database.

All persistent paths flow through this module so UI / storage code never has
to hard-code locations. Tests can redirect storage by setting the
``WRITER_DATA_DIR`` environment variable before importing this module's
helpers (the helpers re-read the env var on every call).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "LivingToTell"
APP_AUTHOR = "LivingToTell"
DISPLAY_NAME = "活着为了讲述"
ENGLISH_NAME = "Living to Tell"
LEGACY_APP_NAME = "Writer"
LEGACY_APP_AUTHOR = "Writer"
ENV_DATA_DIR = "WRITER_DATA_DIR"

DATABASE_FILENAME = "living-to-tell.sqlite3"
LEGACY_DATABASE_FILENAME = "writer.sqlite3"
_SQLITE_SUFFIXES = ("", "-journal", "-wal", "-shm")


def user_data_directory() -> Path:
    """Return the directory holding user data, creating it if needed."""
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        path = Path(override).expanduser()
    else:
        path = Path(user_data_dir(APP_NAME, APP_AUTHOR, roaming=True))
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    """Return the SQLite database file path."""
    data_dir = user_data_directory()
    _copy_legacy_data_if_needed(data_dir)
    return data_dir / DATABASE_FILENAME


def legacy_user_data_directory() -> Path:
    """Return the old Writer data directory without creating it."""
    return Path(user_data_dir(LEGACY_APP_NAME, LEGACY_APP_AUTHOR, roaming=True))


def legacy_database_path() -> Path:
    """Return the old Writer SQLite database path."""
    return legacy_user_data_directory() / LEGACY_DATABASE_FILENAME


def _copy_legacy_data_if_needed(data_dir: Path) -> None:
    """Copy the old Writer database into the new LivingToTell directory once.

    The migration is intentionally copy-only. The old Writer directory remains
    intact as a rollback point, and tests/dev environments that set
    ``WRITER_DATA_DIR`` are isolated from production migration behavior.
    """
    if os.environ.get(ENV_DATA_DIR):
        return

    target = data_dir / DATABASE_FILENAME
    source = legacy_database_path()
    if target.exists() or not source.exists():
        return

    data_dir.mkdir(parents=True, exist_ok=True)
    for suffix in _SQLITE_SUFFIXES:
        source_file = Path(f"{source}{suffix}")
        target_file = Path(f"{target}{suffix}")
        if source_file.exists() and not target_file.exists():
            shutil.copy2(source_file, target_file)

    _copy_legacy_auxiliary_dirs(data_dir)


def _copy_legacy_auxiliary_dirs(data_dir: Path) -> None:
    legacy_dir = legacy_user_data_directory()
    for name in ("backups", "checkpoints"):
        source = legacy_dir / name
        target = data_dir / name
        if source.exists() and source.is_dir() and not target.exists():
            shutil.copytree(source, target)
