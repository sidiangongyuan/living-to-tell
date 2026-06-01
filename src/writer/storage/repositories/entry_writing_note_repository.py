"""Persistence for fragment-bound writing notes."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.entry_writing_note import (
    NOTE_BOARD_WIDTH_DEFAULT,
    NOTE_COLOR_KEY_DEFAULT,
    NOTE_STATUS_DONE,
    NOTE_STATUS_OPEN,
    NOTE_Z_INDEX_DEFAULT,
    EntryWritingNote,
)

NOTE_COLOR_KEYS = {"cream", "amber", "mist", "blue", "rose", "paper"}
NOTE_WIDTH_MIN = 220
NOTE_WIDTH_MAX = 340


def _row_to_note(row: sqlite3.Row) -> EntryWritingNote:
    return EntryWritingNote(
        id=row["id"],
        entry_id=row["entry_id"],
        body=row["body"],
        status=row["status"],
        pinned=bool(row["pinned"]),
        sort_order=int(row["sort_order"] or 0),
        board_x=_optional_int(row["board_x"]),
        board_y=_optional_int(row["board_y"]),
        board_width=_bounded_width(row["board_width"]),
        color_key=_normalize_color_key(row["color_key"]),
        z_index=_int_or_default(row["z_index"], NOTE_Z_INDEX_DEFAULT),
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
                CASE WHEN board_y IS NULL THEN 1 ELSE 0 END,
                board_y ASC,
                CASE WHEN board_x IS NULL THEN 1 ELSE 0 END,
                board_x ASC,
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

    def update_layout(
        self,
        note_id: str,
        *,
        x: int,
        y: int,
        width: int,
        color_key: str,
        z_index: int,
    ) -> Optional[EntryWritingNote]:
        self._conn.execute(
            """
            UPDATE entry_writing_notes
               SET board_x = ?,
                   board_y = ?,
                   board_width = ?,
                   color_key = ?,
                   z_index = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
                int(x),
                int(y),
                _bounded_width(width),
                _normalize_color_key(color_key),
                max(0, int(z_index)),
                note_id,
            ),
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


def _optional_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_or_default(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _bounded_width(value: object) -> int:
    width = _int_or_default(value, NOTE_BOARD_WIDTH_DEFAULT)
    return max(NOTE_WIDTH_MIN, min(NOTE_WIDTH_MAX, width))


def _normalize_color_key(value: object) -> str:
    key = str(value or "").strip().lower()
    return key if key in NOTE_COLOR_KEYS else NOTE_COLOR_KEY_DEFAULT
