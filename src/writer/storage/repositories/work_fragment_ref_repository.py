"""Persistence for ``WorkFragmentRef`` rows (M8).

Each row records "fragment X was *included* into work Y at section Z".
Powers the reverse lookup "which works use this fragment". Never enforces
content sync — see :mod:`writer.domain.models.work_fragment_ref`.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.work import Work
from writer.domain.models.work_fragment_ref import WorkFragmentRef
from writer.storage.repositories.work_repository import _row_to_work


def _row_to_ref(row: sqlite3.Row) -> WorkFragmentRef:
    return WorkFragmentRef(
        id=row["id"],
        work_id=row["work_id"],
        section_id=row["section_id"],
        entry_id=row["entry_id"],
        included_text=row["included_text"] or "",
        created_at=row["created_at"],
    )


class WorkFragmentRefRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(
        self,
        *,
        work_id: str,
        section_id: Optional[str],
        entry_id: str,
        included_text: str,
    ) -> WorkFragmentRef:
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO work_fragment_refs "
            "(id, work_id, section_id, entry_id, included_text) "
            "VALUES (?, ?, ?, ?, ?)",
            (new_id, work_id, section_id, entry_id, included_text or ""),
        )
        row = self._conn.execute(
            "SELECT * FROM work_fragment_refs WHERE id = ?", (new_id,)
        ).fetchone()
        assert row is not None
        return _row_to_ref(row)

    def delete(self, ref_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM work_fragment_refs WHERE id = ?", (ref_id,)
        )
        return cur.rowcount > 0

    def list_for_work(self, work_id: str) -> List[WorkFragmentRef]:
        rows = self._conn.execute(
            "SELECT * FROM work_fragment_refs WHERE work_id = ? "
            "ORDER BY created_at ASC",
            (work_id,),
        ).fetchall()
        return [_row_to_ref(r) for r in rows]

    def list_for_entry(self, entry_id: str) -> List[WorkFragmentRef]:
        rows = self._conn.execute(
            "SELECT * FROM work_fragment_refs WHERE entry_id = ? "
            "ORDER BY created_at DESC",
            (entry_id,),
        ).fetchall()
        return [_row_to_ref(r) for r in rows]

    def list_works_using_entry(self, entry_id: str) -> List[Work]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT works.* FROM work_fragment_refs
            JOIN works ON works.id = work_fragment_refs.work_id
            WHERE work_fragment_refs.entry_id = ?
            ORDER BY works.updated_at DESC, works.created_at DESC
            """,
            (entry_id,),
        ).fetchall()
        return [_row_to_work(r) for r in rows]
