"""Storage for AI-generated and original versions of an entry.

Used in M2 only as a thin scaffold; M3 will populate it from the rewrite
service. Defined now so the storage layer is complete enough for entries to
own their version history.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.entry_version import EntryVersion


def _row_to_version(row: sqlite3.Row) -> EntryVersion:
    return EntryVersion(
        id=row["id"],
        entry_id=row["entry_id"],
        version_type=row["version_type"],
        content=row["content"],
        created_at=row["created_at"],
        provider=row["provider"],
        model=row["model"],
    )


class VersionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        *,
        entry_id: str,
        version_type: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> EntryVersion:
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO entry_versions
                (id, entry_id, version_type, content, provider, model)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id, entry_id, version_type, content, provider, model),
        )
        row = self._conn.execute(
            "SELECT * FROM entry_versions WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_version(row)

    def list_for_entry(self, entry_id: str) -> List[EntryVersion]:
        rows = self._conn.execute(
            """
            SELECT * FROM entry_versions
            WHERE entry_id = ?
            ORDER BY created_at DESC
            """,
            (entry_id,),
        ).fetchall()
        return [_row_to_version(r) for r in rows]

    def get(self, version_id: str) -> Optional[EntryVersion]:
        row = self._conn.execute(
            "SELECT * FROM entry_versions WHERE id = ?", (version_id,)
        ).fetchone()
        return _row_to_version(row) if row else None
