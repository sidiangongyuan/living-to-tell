"""Project repository (M5).

Pure CRUD over the ``projects`` table. Cascading deletes clear chapters;
entry FK is left as ``SET NULL`` semantics — the repository simply detaches
entries from the deleted project so orphaned fragments remain visible.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.project import Project


def _row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ProjectRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # writes ------------------------------------------------------------
    def create(self, name: str, description: str = "") -> Project:
        if not name.strip():
            raise ValueError("name is required")
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
            (new_id, name.strip(), description),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def rename(self, project_id: str, name: str) -> Optional[Project]:
        if not name.strip():
            raise ValueError("name is required")
        cur = self._conn.execute(
            """
            UPDATE projects
               SET name = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (name.strip(), project_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get(project_id)

    def update_description(
        self, project_id: str, description: str
    ) -> Optional[Project]:
        cur = self._conn.execute(
            """
            UPDATE projects
               SET description = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (description, project_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get(project_id)

    def delete(self, project_id: str) -> bool:
        # Detach entries so they stay visible as orphan fragments after the
        # project is removed. Clear sequence_order too — the old value is
        # meaningless outside a project container.
        self._conn.execute(
            "UPDATE entries "
            "   SET project_id = NULL, "
            "       chapter_id = NULL, "
            "       sequence_order = NULL "
            " WHERE project_id = ?",
            (project_id,),
        )
        cur = self._conn.execute(
            "DELETE FROM projects WHERE id = ?", (project_id,)
        )
        return cur.rowcount > 0

    # reads -------------------------------------------------------------
    def get(self, project_id: str) -> Optional[Project]:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return _row_to_project(row) if row else None

    def list_all(self) -> List[Project]:
        rows = self._conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
        return [_row_to_project(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM projects"
        ).fetchone()
        return int(row["n"])
