"""Persistence for application settings (key/value)."""
from __future__ import annotations

import sqlite3
from typing import Dict, Optional


class SettingsRepository:
    """Reads and writes rows in the ``app_settings`` table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return row["value"]

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (key, value),
        )
        self._conn.commit()

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        self._conn.commit()

    def get_all(self) -> Dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {row["key"]: row["value"] for row in rows}
