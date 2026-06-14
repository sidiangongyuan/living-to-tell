"""Backend configuration: data directory and database location.

The Tauri MVP defaults to **sharing** the production Qt app's database at
``%APPDATA%\\Writer\\Writer``, so both versions access the same data.

To use an **isolated** dev database instead (for testing), set
``WRITER_USE_DEV_DB=1`` in the environment before launching the backend.
"""
from __future__ import annotations

import os
from pathlib import Path

# Repo-root-relative dev data dir: tauri-mvp/backend/.data/
_BACKEND_DIR = Path(__file__).resolve().parent
_DEV_DATA_DIR = _BACKEND_DIR / ".data"


def configure_data_dir() -> Path:
    """Decide which data dir the ``writer`` package will use, and set the env.

    MUST be called before importing ``writer.app.paths`` (transitively, before
    building the container). Returns the resolved data directory.
    """
    if os.environ.get("WRITER_USE_DEV_DB") == "1":
        # Isolated dev database under the backend folder.
        target = Path(_DEV_DATA_DIR).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        os.environ["WRITER_DATA_DIR"] = str(target)
        return target

    # Default: shared Qt database (production location).
    # Leave WRITER_DATA_DIR unset → writer.app.paths falls back to the
    # platformdirs production location (the real Qt database).
    os.environ.pop("WRITER_DATA_DIR", None)
    # Import lazily so this module has no import-time writer dependency.
    from writer.app.paths import user_data_directory

    return user_data_directory()
