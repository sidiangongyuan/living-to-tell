"""SQLite database connection and initialization."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    """Return the default database path."""
    return Path(__file__).parent / "writer.db"


def open_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a SQLite connection with project-wide pragmas applied."""
    target = Path(db_path) if db_path is not None else get_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Apply schema to the given connection (idempotent)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL DEFAULT '',
            entry_type TEXT NOT NULL DEFAULT 'fragment',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            tags_text TEXT NOT NULL DEFAULT '',
            project_id TEXT,
            chapter_id TEXT,
            sequence_order INTEGER,
            archived_at TEXT,
            curation_status TEXT NOT NULL DEFAULT 'unsorted'
        );

        CREATE INDEX IF NOT EXISTS idx_entries_updated ON entries (updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_entries_created ON entries (created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_entries_project ON entries (project_id);
        CREATE INDEX IF NOT EXISTS idx_entries_chapter ON entries (chapter_id);
    """)


def open_and_initialize(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Convenience helper to open and initialize database."""
    conn = open_connection(db_path)
    initialize_schema(conn)
    return conn
