"""Persistence for AI threads and messages (M10A)."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.ai_thread import AiMessage, AiThread


def _row_to_thread(row: sqlite3.Row) -> AiThread:
    return AiThread(
        id=row["id"],
        scope_kind=row["scope_kind"],
        scope_id=row["scope_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_message(row: sqlite3.Row) -> AiMessage:
    return AiMessage(
        id=row["id"],
        thread_id=row["thread_id"],
        role=row["role"],
        content=row["content"],
        meta_json=row["meta_json"] or "{}",
        created_at=row["created_at"],
    )


class AiThreadRepository:
    """Threads are scoped to a fragment / work / collection (or 'global').

    Per scope (scope_kind, scope_id) the app uses the most recently updated
    thread by default. Older threads are kept for history but the UI only
    has to surface one 'current' thread per scope.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ---- threads ------------------------------------------------------
    def create(
        self,
        *,
        scope_kind: str,
        scope_id: Optional[str],
        title: str = "",
    ) -> AiThread:
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO ai_threads (id, scope_kind, scope_id, title)
            VALUES (?, ?, ?, ?)
            """,
            (new_id, scope_kind, scope_id, title),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def get(self, thread_id: str) -> Optional[AiThread]:
        row = self._conn.execute(
            "SELECT * FROM ai_threads WHERE id = ?", (thread_id,)
        ).fetchone()
        return _row_to_thread(row) if row else None

    def latest_for_scope(
        self, scope_kind: str, scope_id: Optional[str]
    ) -> Optional[AiThread]:
        if scope_id is None:
            row = self._conn.execute(
                """
                SELECT * FROM ai_threads
                 WHERE scope_kind = ? AND scope_id IS NULL
                 ORDER BY updated_at DESC LIMIT 1
                """,
                (scope_kind,),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT * FROM ai_threads
                 WHERE scope_kind = ? AND scope_id = ?
                 ORDER BY updated_at DESC LIMIT 1
                """,
                (scope_kind, scope_id),
            ).fetchone()
        return _row_to_thread(row) if row else None

    def get_or_create_for_scope(
        self, scope_kind: str, scope_id: Optional[str], *, title: str = ""
    ) -> AiThread:
        existing = self.latest_for_scope(scope_kind, scope_id)
        if existing is not None:
            return existing
        return self.create(scope_kind=scope_kind, scope_id=scope_id, title=title)

    def touch(self, thread_id: str) -> None:
        self._conn.execute(
            """
            UPDATE ai_threads
               SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (thread_id,),
        )

    def delete(self, thread_id: str) -> None:
        self._conn.execute("DELETE FROM ai_threads WHERE id = ?", (thread_id,))

    def list_for_scope(
        self, scope_kind: str, scope_id: Optional[str]
    ) -> List[AiThread]:
        if scope_id is None:
            rows = self._conn.execute(
                """
                SELECT * FROM ai_threads
                 WHERE scope_kind = ? AND scope_id IS NULL
                 ORDER BY updated_at DESC
                """,
                (scope_kind,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM ai_threads
                 WHERE scope_kind = ? AND scope_id = ?
                 ORDER BY updated_at DESC
                """,
                (scope_kind, scope_id),
            ).fetchall()
        return [_row_to_thread(r) for r in rows]

    # ---- messages -----------------------------------------------------
    def add_message(
        self,
        *,
        thread_id: str,
        role: str,
        content: str,
        meta_json: str = "{}",
    ) -> AiMessage:
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO ai_messages (id, thread_id, role, content, meta_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (new_id, thread_id, role, content, meta_json),
        )
        self.touch(thread_id)
        row = self._conn.execute(
            "SELECT * FROM ai_messages WHERE id = ?", (new_id,)
        ).fetchone()
        assert row is not None
        return _row_to_message(row)

    def list_messages(self, thread_id: str, *, limit: Optional[int] = None) -> List[AiMessage]:
        if limit is None:
            rows = self._conn.execute(
                """
                SELECT * FROM ai_messages
                 WHERE thread_id = ?
                 ORDER BY created_at ASC, rowid ASC
                """,
                (thread_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM ai_messages
                 WHERE thread_id = ?
                 ORDER BY created_at ASC, rowid ASC
                 LIMIT ?
                """,
                (thread_id, limit),
            ).fetchall()
        return [_row_to_message(r) for r in rows]

    def recent_messages(self, thread_id: str, *, limit: int) -> List[AiMessage]:
        """Most recent ``limit`` messages, returned in chronological order."""
        rows = self._conn.execute(
            """
            SELECT * FROM ai_messages
             WHERE thread_id = ?
             ORDER BY created_at DESC, rowid DESC
             LIMIT ?
            """,
            (thread_id, limit),
        ).fetchall()
        return list(reversed([_row_to_message(r) for r in rows]))

    def clear_messages(self, thread_id: str) -> int:
        cur = self._conn.execute(
            "DELETE FROM ai_messages WHERE thread_id = ?",
            (thread_id,),
        )
        self.touch(thread_id)
        return cur.rowcount or 0
