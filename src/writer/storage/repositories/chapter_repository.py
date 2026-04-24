"""Chapter repository (M5).

A chapter belongs to exactly one project and carries a ``sort_order``
integer that gives the stable output order inside that project. New
chapters land at ``max(sort_order) + 1``; the repo exposes a ``reorder``
helper that rewrites a project's chapter order in one call.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.chapter import Chapter


def _row_to_chapter(row: sqlite3.Row) -> Chapter:
    return Chapter(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        sort_order=row["sort_order"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ChapterRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # writes ------------------------------------------------------------
    def create(self, project_id: str, title: str = "") -> Chapter:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS mx FROM chapters WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        next_order = int(row["mx"]) + 1
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO chapters (id, project_id, title, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (new_id, project_id, title, next_order),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def rename(self, chapter_id: str, title: str) -> Optional[Chapter]:
        cur = self._conn.execute(
            """
            UPDATE chapters
               SET title = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (title, chapter_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get(chapter_id)

    def delete(self, chapter_id: str) -> bool:
        # Preserve relative order when entries become unchaptered: read
        # them in current order, then append each one to the project's
        # unchaptered bucket. Using UPDATE + explicit sequence_order
        # avoids a silent dependency on the ALTER TABLE migration order.
        chapter_row = self._conn.execute(
            "SELECT project_id FROM chapters WHERE id = ?", (chapter_id,)
        ).fetchone()
        if chapter_row is not None:
            project_id = chapter_row["project_id"]
            entries = self._conn.execute(
                """
                SELECT id FROM entries
                 WHERE chapter_id = ?
                 ORDER BY CASE WHEN sequence_order IS NULL THEN 1 ELSE 0 END,
                          sequence_order ASC,
                          created_at ASC
                """,
                (chapter_id,),
            ).fetchall()
            max_row = self._conn.execute(
                """
                SELECT COALESCE(MAX(sequence_order), -1) AS mx
                  FROM entries
                 WHERE project_id = ? AND chapter_id IS NULL
                """,
                (project_id,),
            ).fetchone()
            next_seq = int(max_row["mx"]) + 1
            for erow in entries:
                self._conn.execute(
                    """
                    UPDATE entries
                       SET chapter_id = NULL,
                           sequence_order = ?
                     WHERE id = ?
                    """,
                    (next_seq, erow["id"]),
                )
                next_seq += 1
        cur = self._conn.execute(
            "DELETE FROM chapters WHERE id = ?", (chapter_id,)
        )
        return cur.rowcount > 0

    def reorder(self, project_id: str, ordered_ids: List[str]) -> None:
        """Rewrite chapter ordering inside a project.

        Chapters not listed are left untouched. Raises ``ValueError`` if an
        id is not a chapter of this project.
        """
        existing = {
            c.id for c in self.list_for_project(project_id)
        }
        for cid in ordered_ids:
            if cid not in existing:
                raise ValueError(f"chapter {cid!r} is not in project {project_id!r}")
        for index, cid in enumerate(ordered_ids):
            self._conn.execute(
                "UPDATE chapters SET sort_order = ? WHERE id = ?",
                (index, cid),
            )

    # reads -------------------------------------------------------------
    def get(self, chapter_id: str) -> Optional[Chapter]:
        row = self._conn.execute(
            "SELECT * FROM chapters WHERE id = ?", (chapter_id,)
        ).fetchone()
        return _row_to_chapter(row) if row else None

    def list_for_project(self, project_id: str) -> List[Chapter]:
        rows = self._conn.execute(
            """
            SELECT * FROM chapters
             WHERE project_id = ?
             ORDER BY sort_order ASC, created_at ASC
            """,
            (project_id,),
        ).fetchall()
        return [_row_to_chapter(r) for r in rows]
