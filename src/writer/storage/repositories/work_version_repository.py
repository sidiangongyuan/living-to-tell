"""Persistence for ``WorkVersion`` rows (M8 work version history)."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.work_version import WorkVersion


def _row_to_version(row: sqlite3.Row) -> WorkVersion:
    return WorkVersion(
        id=row["id"],
        work_id=row["work_id"],
        version_type=row["version_type"],
        content_json=row["content_json"],
        label=row["label"] or "",
        created_at=row["created_at"],
    )


class WorkVersionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        *,
        work_id: str,
        version_type: str,
        content_json: str,
        label: str = "",
    ) -> WorkVersion:
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO work_versions "
            "(id, work_id, version_type, content_json, label) "
            "VALUES (?, ?, ?, ?, ?)",
            (new_id, work_id, version_type, content_json, label),
        )
        row = self._conn.execute(
            "SELECT * FROM work_versions WHERE id = ?", (new_id,)
        ).fetchone()
        assert row is not None
        return _row_to_version(row)

    def list_for_work(self, work_id: str) -> List[WorkVersion]:
        rows = self._conn.execute(
            "SELECT * FROM work_versions WHERE work_id = ? "
            "ORDER BY created_at DESC, id DESC",
            (work_id,),
        ).fetchall()
        return [_row_to_version(r) for r in rows]

    def get(self, version_id: str) -> Optional[WorkVersion]:
        row = self._conn.execute(
            "SELECT * FROM work_versions WHERE id = ?", (version_id,)
        ).fetchone()
        return _row_to_version(row) if row is not None else None
