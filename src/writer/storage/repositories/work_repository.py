"""Persistence for ``Work`` entities (M8).

A *work* is a finished-piece writing unit kept separately from the
free-form ``entries`` (fragments) table. Section bodies live in
``work_sections``; this repository owns only the work header.

The works full-text search index (``works_fts``) is rebuilt by
:func:`rebuild_works_fts` whenever a header or any section changes —
both this module and :mod:`writer.storage.repositories.work_section_repository`
call it.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.enums import WorkStatus
from writer.domain.models.work import Work
from writer.storage.repositories.entry_repository import (
    parse_tags,
    serialize_tags,
)


# ---------------------------------------------------------------------------
# FTS sync helper (shared across work_repository + work_section_repository).
# ---------------------------------------------------------------------------


def rebuild_works_fts(conn: sqlite3.Connection, work_id: str) -> None:
    """Recompute the works_fts row for ``work_id`` from current data.

    Called after any change that affects searchable text (title, summary,
    tags, or section content). Idempotent.
    """
    head = conn.execute(
        "SELECT title, summary, tags_text FROM works WHERE id = ?",
        (work_id,),
    ).fetchone()
    if head is None:
        conn.execute("DELETE FROM works_fts WHERE work_id = ?", (work_id,))
        return
    section_rows = conn.execute(
        "SELECT content FROM work_sections WHERE work_id = ? "
        "ORDER BY sort_order ASC, created_at ASC",
        (work_id,),
    ).fetchall()
    body = "\n\n".join(r["content"] or "" for r in section_rows)
    conn.execute("DELETE FROM works_fts WHERE work_id = ?", (work_id,))
    conn.execute(
        "INSERT INTO works_fts (work_id, title, summary, body, tags) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            work_id,
            head["title"] or "",
            head["summary"] or "",
            body,
            head["tags_text"] or "",
        ),
    )


def _row_to_work(row: sqlite3.Row) -> Work:
    return Work(
        id=row["id"],
        title=row["title"],
        summary=row["summary"],
        status=row["status"],
        tags=parse_tags(row["tags_text"] or ""),
        target_word_count=row["target_word_count"],
        archived_at=row["archived_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class WorkRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # writes ------------------------------------------------------------
    def create(
        self,
        *,
        title: str = "",
        summary: str = "",
        status: str = WorkStatus.IDEA.value,
        tags: Optional[list[str]] = None,
        target_word_count: Optional[int] = None,
    ) -> Work:
        if status not in WorkStatus.values():
            raise ValueError(f"unknown work status: {status!r}")
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO works (id, title, summary, status, tags_text, "
            "target_word_count) VALUES (?, ?, ?, ?, ?, ?)",
            (
                new_id,
                title,
                summary,
                status,
                serialize_tags(tags) if tags else "",
                target_word_count,
            ),
        )
        rebuild_works_fts(self._conn, new_id)
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def update(
        self,
        work_id: str,
        *,
        title: str,
        summary: str,
        tags: Optional[list[str]] = None,
    ) -> Optional[Work]:
        if tags is not None:
            self._conn.execute(
                """
                UPDATE works
                   SET title = ?,
                       summary = ?,
                       tags_text = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (title, summary, serialize_tags(tags), work_id),
            )
        else:
            self._conn.execute(
                """
                UPDATE works
                   SET title = ?,
                       summary = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (title, summary, work_id),
            )
        rebuild_works_fts(self._conn, work_id)
        return self.get(work_id)

    def set_status(self, work_id: str, status: str) -> Optional[Work]:
        if status not in WorkStatus.values():
            raise ValueError(f"unknown work status: {status!r}")
        self._conn.execute(
            "UPDATE works SET status = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
            "WHERE id = ?",
            (status, work_id),
        )
        # Note: archived_at is the *hard* archive flag (analogous to
        # entries.archived_at). The FINAL/ARCHIVED status enum is a
        # softer label the user sets in the workflow; archived_at lets
        # the work disappear from the default list independent of label.
        return self.get(work_id)

    def set_archived(self, work_id: str, archived: bool) -> Optional[Work]:
        if archived:
            self._conn.execute(
                """
                UPDATE works
                   SET archived_at = COALESCE(
                           archived_at,
                           strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                       )
                 WHERE id = ?
                """,
                (work_id,),
            )
        else:
            self._conn.execute(
                "UPDATE works SET archived_at = NULL WHERE id = ?",
                (work_id,),
            )
        return self.get(work_id)

    def set_target_word_count(
        self, work_id: str, count: Optional[int]
    ) -> Optional[Work]:
        if count is not None and count < 0:
            raise ValueError("target_word_count must be >= 0")
        self._conn.execute(
            "UPDATE works SET target_word_count = ? WHERE id = ?",
            (count, work_id),
        )
        return self.get(work_id)

    def delete(self, work_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM works WHERE id = ?", (work_id,))
        self._conn.execute(
            "DELETE FROM works_fts WHERE work_id = ?", (work_id,)
        )
        return cur.rowcount > 0

    # reads -------------------------------------------------------------
    def get(self, work_id: str) -> Optional[Work]:
        row = self._conn.execute(
            "SELECT * FROM works WHERE id = ?", (work_id,)
        ).fetchone()
        return _row_to_work(row) if row is not None else None

    def get_many(self, work_ids: list[str]) -> List[Work]:
        if not work_ids:
            return []
        placeholders = ",".join("?" for _ in work_ids)
        rows = self._conn.execute(
            f"SELECT * FROM works WHERE id IN ({placeholders})", list(work_ids)
        ).fetchall()
        by_id = {r["id"]: _row_to_work(r) for r in rows}
        return [by_id[i] for i in work_ids if i in by_id]

    def list_recent(
        self,
        limit: int = 200,
        *,
        include_archived: bool = False,
        archived_only: bool = False,
    ) -> List[Work]:
        if archived_only:
            where = "WHERE archived_at IS NOT NULL"
        elif include_archived:
            where = ""
        else:
            where = "WHERE archived_at IS NULL"
        rows = self._conn.execute(
            f"""
            SELECT * FROM works
            {where}
             ORDER BY updated_at DESC, created_at DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_work(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM works").fetchone()
        return int(row["n"])
