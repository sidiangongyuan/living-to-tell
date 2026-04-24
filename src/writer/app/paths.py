"""Filesystem locations for user data, settings and the SQLite database.

All persistent paths flow through this module so UI / storage code never has
to hard-code locations. Tests can redirect storage by setting the
``WRITER_DATA_DIR`` environment variable before importing this module's
helpers (the helpers re-read the env var on every call).
"""
from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "Writer"
APP_AUTHOR = "Writer"
ENV_DATA_DIR = "WRITER_DATA_DIR"

DATABASE_FILENAME = "writer.sqlite3"


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
    return user_data_directory() / DATABASE_FILENAME
