"""Persistence for fragment-bound writing notes."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.entry_writing_note import (
    NOTE_STATUS_DONE,
    NOTE_STATUS_OPEN,
    EntryWritingNote,
)


def _row_to_note(row: sqlite3.Row) -> EntryWritingNote:
    return EntryWritingNote(
        id=row["id"],
        entry_id=row["entry_id"],
        body=row["body"],
        status=row["status"],
        pinned=bool(row["pinned"]),
        sort_order=int(row["sort_order"] or 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


class EntryWritingNoteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        *,
        entry_id: str,
        body: str,
        pinned: bool = False,
    ) -> EntryWritingNote:
        clean_body = body.strip()
        if not clean_body:
            raise ValueError("Writing note body cannot be empty")
        new_id = str(uuid.uuid4())
        sort_order = self._next_sort_order(entry_id)
        self._conn.execute(
            """
            INSERT INTO entry_writing_notes
                (id, entry_id, body, pinned, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (new_id, entry_id, clean_body, 1 if pinned else 0, sort_order),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def get(self, note_id: str) -> Optional[EntryWritingNote]:
        row = self._conn.execute(
            "SELECT * FROM entry_writing_notes WHERE id = ?", (note_id,)
        ).fetchone()
        return _row_to_note(row) if row else None

    def list_for_entry(
        self, entry_id: str, *, include_done: bool = False
    ) -> List[EntryWritingNote]:
        where = "entry_id = ?"
        params: list[object] = [entry_id]
        if not include_done:
            where += " AND status = ?"
            params.append(NOTE_STATUS_OPEN)
        rows = self._conn.execute(
            f"""
            SELECT * FROM entry_writing_notes
             WHERE {where}
             ORDER BY
                CASE status WHEN ? THEN 0 ELSE 1 END,
                pinned DESC,
                sort_order ASC,
                updated_at DESC
            """,
            (*params, NOTE_STATUS_OPEN),
        ).fetchall()
        return [_row_to_note(row) for row in rows]

    def count_open_for_entry(self, entry_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS count
              FROM entry_writing_notes
             WHERE entry_id = ? AND status = ?
            """,
            (entry_id, NOTE_STATUS_OPEN),
        ).fetchone()
        return int(row["count"] if row else 0)

    def update_body(self, note_id: str, body: str) -> Optional[EntryWritingNote]:
        clean_body = body.strip()
        if not clean_body:
            raise ValueError("Writing note body cannot be empty")
        self._conn.execute(
            """
            UPDATE entry_writing_notes
               SET body = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (clean_body, note_id),
        )
        return self.get(note_id)

    def set_pinned(self, note_id: str, pinned: bool) -> Optional[EntryWritingNote]:
        self._conn.execute(
            """
            UPDATE entry_writing_notes
               SET pinned = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (1 if pinned else 0, note_id),
        )
        return self.get(note_id)

    def set_done(self, note_id: str, done: bool = True) -> Optional[EntryWritingNote]:
        if done:
            status = NOTE_STATUS_DONE
            completed_expr = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
        else:
            status = NOTE_STATUS_OPEN
            completed_expr = "NULL"
        self._conn.execute(
            f"""
            UPDATE entry_writing_notes
               SET status = ?,
                   completed_at = {completed_expr},
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (status, note_id),
        )
        return self.get(note_id)

    def delete(self, note_id: str) -> None:
        self._conn.execute(
            "DELETE FROM entry_writing_notes WHERE id = ?", (note_id,)
        )

    def _next_sort_order(self, entry_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order
              FROM entry_writing_notes
             WHERE entry_id = ?
            """,
            (entry_id,),
        ).fetchone()
        return int(row["next_order"] if row else 0)
