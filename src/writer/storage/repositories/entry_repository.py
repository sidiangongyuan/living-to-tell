"""CRUD and recent-list queries for entries.

UI code talks to this repository, never to ``sqlite3`` directly. All writes
update ``updated_at`` so the recent list ordering reflects the latest edit.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.enums import EntryType
from writer.domain.models.entry import Entry


# ---------------------------------------------------------------------------
# Tag serialization helpers (module-level so tests can import them directly)
# ---------------------------------------------------------------------------

def parse_tags(tags_text: str) -> list[str]:
    """Parse a comma-separated ``tags_text`` string into a normalised list.

    Rules:
    * Split on comma.
    * Strip whitespace from each part.
    * Drop empty parts.
    * Case-insensitive deduplication preserving first-occurrence order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for part in tags_text.split(","):
        tag = part.strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            result.append(tag)
    return result


def serialize_tags(tags: list[str]) -> str:
    """Serialise a tag list to the canonical ``tags_text`` storage format."""
    return ", ".join(tags)


def _row_to_entry(row: sqlite3.Row) -> Entry:
    keys = row.keys()
    raw_tags = row["tags_text"] if "tags_text" in keys else ""
    return Entry(
        id=row["id"],
        title=row["title"],
        body=row["body"],
        entry_type=row["entry_type"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        project_id=row["project_id"] if "project_id" in keys else None,
        chapter_id=row["chapter_id"] if "chapter_id" in keys else None,
        sequence_order=(
            row["sequence_order"] if "sequence_order" in keys else None
        ),
        tags=parse_tags(raw_tags),
    )


class EntryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # writes ------------------------------------------------------------
    def create(
        self,
        title: str = "",
        body: str = "",
        entry_type: str = EntryType.FRAGMENT.value,
        tags: list[str] | None = None,
    ) -> Entry:
        new_id = str(uuid.uuid4())
        tags_text = serialize_tags(tags) if tags else ""
        self._conn.execute(
            "INSERT INTO entries (id, title, body, entry_type, tags_text)"
            " VALUES (?, ?, ?, ?, ?)",
            (new_id, title, body, entry_type, tags_text),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def update(
        self,
        entry_id: str,
        *,
        title: str,
        body: str,
        tags: list[str] | None = None,
    ) -> Optional[Entry]:
        """Update title and body.  When *tags* is provided it is also saved;
        ``None`` (default) means "leave existing tags unchanged"."""
        if tags is not None:
            cur = self._conn.execute(
                """
                UPDATE entries
                   SET title = ?,
                       body = ?,
                       tags_text = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (title, body, serialize_tags(tags), entry_id),
            )
        else:
            cur = self._conn.execute(
                """
                UPDATE entries
                   SET title = ?,
                       body = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (title, body, entry_id),
            )
        if cur.rowcount == 0:
            return None
        return self.get(entry_id)

    def delete(self, entry_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        return cur.rowcount > 0

    # reads -------------------------------------------------------------
    def get(self, entry_id: str) -> Optional[Entry]:
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def list_recent(self, limit: int = 100) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()
        return int(row["n"])

    # tag queries -------------------------------------------------------
    def list_all_tags(self) -> list[str]:
        """Return a sorted, distinct list of all tags across all entries."""
        rows = self._conn.execute(
            "SELECT tags_text FROM entries WHERE tags_text != ''"
        ).fetchall()
        seen: set[str] = set()
        result: list[str] = []
        for row in rows:
            for tag in parse_tags(row["tags_text"]):
                if tag.lower() not in seen:
                    seen.add(tag.lower())
                    result.append(tag)
        return sorted(result, key=lambda t: t.lower())

    def list_recent_by_tag(self, tag: str, limit: int = 100) -> list[Entry]:
        """Return recent entries that carry *tag* (case-insensitive)."""
        tag_lower = tag.lower()
        rows = self._conn.execute(
            """
            SELECT * FROM entries
            WHERE tags_text != ''
            ORDER BY updated_at DESC, created_at DESC
            """,
        ).fetchall()
        result: list[Entry] = []
        for row in rows:
            entry = _row_to_entry(row)
            if any(t.lower() == tag_lower for t in entry.tags):
                result.append(entry)
                if len(result) >= limit:
                    break
        return result

    # project / chapter assignment (M5) ---------------------------------
    def assign_to_project(
        self, entry_id: str, project_id: Optional[str]
    ) -> Optional[Entry]:
        """Assign (or unassign) an entry to a project.

        Guarantees:
        * Clearing the project also clears ``chapter_id`` and
          ``sequence_order``.
        * Moving an entry to a *different* project detaches the chapter
          and appends the entry to the new project's unchaptered bucket.
        * Re-assigning to the *same* project is a no-op for ordering —
          the entry keeps its existing ``chapter_id`` /
          ``sequence_order`` so the user's tidying is not lost.
        """
        entry = self.get(entry_id)
        if entry is None:
            return None

        if project_id is None:
            self._conn.execute(
                """
                UPDATE entries
                   SET project_id = NULL,
                       chapter_id = NULL,
                       sequence_order = NULL,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (entry_id,),
            )
            return self.get(entry_id)

        if entry.project_id == project_id:
            return entry  # no-op: preserve ordering

        new_seq = self._next_sequence(project_id, None)
        self._conn.execute(
            """
            UPDATE entries
               SET project_id = ?,
                   chapter_id = NULL,
                   sequence_order = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (project_id, new_seq, entry_id),
        )
        return self.get(entry_id)

    def assign_to_chapter(
        self, entry_id: str, chapter_id: Optional[str]
    ) -> Optional[Entry]:
        """Move the entry between chapters / the unchaptered bucket.

        * ``chapter_id is None`` moves the entry back to the current
          project's unchaptered bucket and appends it to the end. If the
          entry was already unchaptered the call is a no-op.
        * Otherwise validates that ``chapter_id`` belongs to the entry's
          current project; mismatches raise :class:`ValueError` rather
          than silently re-parenting the entry.
        * Re-assigning to the same chapter is a no-op.
        """
        entry = self.get(entry_id)
        if entry is None:
            return None

        if chapter_id is None:
            if entry.chapter_id is None:
                return entry
            if entry.project_id is None:
                # Nothing meaningful to do; just ensure state is clean.
                return entry
            new_seq = self._next_sequence(entry.project_id, None)
            self._conn.execute(
                """
                UPDATE entries
                   SET chapter_id = NULL,
                       sequence_order = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (new_seq, entry_id),
            )
            return self.get(entry_id)

        row = self._conn.execute(
            "SELECT project_id FROM chapters WHERE id = ?", (chapter_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"chapter {chapter_id!r} does not exist")
        chapter_project_id = row["project_id"]
        if entry.project_id is None:
            raise ValueError(
                "cannot assign a chapter to an entry without a project"
            )
        if entry.project_id != chapter_project_id:
            raise ValueError(
                "chapter belongs to a different project than the entry"
            )

        if entry.chapter_id == chapter_id:
            return entry  # no-op

        new_seq = self._next_sequence(entry.project_id, chapter_id)
        self._conn.execute(
            """
            UPDATE entries
               SET chapter_id = ?,
                   sequence_order = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (chapter_id, new_seq, entry_id),
        )
        return self.get(entry_id)

    def reorder_container(
        self,
        project_id: str,
        chapter_id: Optional[str],
        ordered_ids: List[str],
    ) -> None:
        """Rewrite ``sequence_order`` for every entry in a container.

        ``chapter_id`` may be ``None`` to target the unchaptered bucket of
        ``project_id``. Raises :class:`ValueError` if any id does not
        belong to this container — the repository never silently moves
        entries between containers on behalf of the caller.
        """
        if chapter_id is None:
            existing = self.list_unchaptered_for_project(project_id)
        else:
            # Ensure the chapter actually belongs to the project.
            owner = self._conn.execute(
                "SELECT project_id FROM chapters WHERE id = ?", (chapter_id,)
            ).fetchone()
            if owner is None or owner["project_id"] != project_id:
                raise ValueError(
                    f"chapter {chapter_id!r} is not in project {project_id!r}"
                )
            existing = self.list_for_chapter(chapter_id)

        existing_ids = {e.id for e in existing}
        if set(ordered_ids) != existing_ids:
            raise ValueError(
                "reorder_container requires exactly the entries of the "
                "target container"
            )
        for index, eid in enumerate(ordered_ids):
            self._conn.execute(
                "UPDATE entries SET sequence_order = ? WHERE id = ?",
                (index, eid),
            )

    def _next_sequence(
        self, project_id: str, chapter_id: Optional[str]
    ) -> int:
        if chapter_id is None:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(sequence_order), -1) AS mx
                  FROM entries
                 WHERE project_id = ? AND chapter_id IS NULL
                """,
                (project_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(sequence_order), -1) AS mx
                  FROM entries
                 WHERE chapter_id = ?
                """,
                (chapter_id,),
            ).fetchone()
        return int(row["mx"]) + 1

    def list_for_project(self, project_id: str) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
             WHERE project_id = ?
             ORDER BY updated_at DESC, created_at DESC
            """,
            (project_id,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def list_for_chapter(self, chapter_id: str) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
             WHERE chapter_id = ?
             ORDER BY CASE WHEN sequence_order IS NULL THEN 1 ELSE 0 END,
                      sequence_order ASC,
                      created_at ASC
            """,
            (chapter_id,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def list_unchaptered_for_project(self, project_id: str) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
             WHERE project_id = ? AND chapter_id IS NULL
             ORDER BY CASE WHEN sequence_order IS NULL THEN 1 ELSE 0 END,
                      sequence_order ASC,
                      created_at ASC
            """,
            (project_id,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def delete(self, entry_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        return cur.rowcount > 0

    # reads -------------------------------------------------------------
    def get(self, entry_id: str) -> Optional[Entry]:
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def list_recent(self, limit: int = 100) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()
        return int(row["n"])

    # project / chapter assignment (M5) ---------------------------------
    def assign_to_project(
        self, entry_id: str, project_id: Optional[str]
    ) -> Optional[Entry]:
        """Assign (or unassign) an entry to a project.

        Guarantees:
        * Clearing the project also clears ``chapter_id`` and
          ``sequence_order``.
        * Moving an entry to a *different* project detaches the chapter
          and appends the entry to the new project's unchaptered bucket.
        * Re-assigning to the *same* project is a no-op for ordering —
          the entry keeps its existing ``chapter_id`` /
          ``sequence_order`` so the user's tidying is not lost.
        """
        entry = self.get(entry_id)
        if entry is None:
            return None

        if project_id is None:
            self._conn.execute(
                """
                UPDATE entries
                   SET project_id = NULL,
                       chapter_id = NULL,
                       sequence_order = NULL,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (entry_id,),
            )
            return self.get(entry_id)

        if entry.project_id == project_id:
            return entry  # no-op: preserve ordering

        new_seq = self._next_sequence(project_id, None)
        self._conn.execute(
            """
            UPDATE entries
               SET project_id = ?,
                   chapter_id = NULL,
                   sequence_order = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (project_id, new_seq, entry_id),
        )
        return self.get(entry_id)

    def assign_to_chapter(
        self, entry_id: str, chapter_id: Optional[str]
    ) -> Optional[Entry]:
        """Move the entry between chapters / the unchaptered bucket.

        * ``chapter_id is None`` moves the entry back to the current
          project's unchaptered bucket and appends it to the end. If the
          entry was already unchaptered the call is a no-op.
        * Otherwise validates that ``chapter_id`` belongs to the entry's
          current project; mismatches raise :class:`ValueError` rather
          than silently re-parenting the entry.
        * Re-assigning to the same chapter is a no-op.
        """
        entry = self.get(entry_id)
        if entry is None:
            return None

        if chapter_id is None:
            if entry.chapter_id is None:
                return entry
            if entry.project_id is None:
                # Nothing meaningful to do; just ensure state is clean.
                return entry
            new_seq = self._next_sequence(entry.project_id, None)
            self._conn.execute(
                """
                UPDATE entries
                   SET chapter_id = NULL,
                       sequence_order = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (new_seq, entry_id),
            )
            return self.get(entry_id)

        row = self._conn.execute(
            "SELECT project_id FROM chapters WHERE id = ?", (chapter_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"chapter {chapter_id!r} does not exist")
        chapter_project_id = row["project_id"]
        if entry.project_id is None:
            raise ValueError(
                "cannot assign a chapter to an entry without a project"
            )
        if entry.project_id != chapter_project_id:
            raise ValueError(
                "chapter belongs to a different project than the entry"
            )

        if entry.chapter_id == chapter_id:
            return entry  # no-op

        new_seq = self._next_sequence(entry.project_id, chapter_id)
        self._conn.execute(
            """
            UPDATE entries
               SET chapter_id = ?,
                   sequence_order = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (chapter_id, new_seq, entry_id),
        )
        return self.get(entry_id)

    def reorder_container(
        self,
        project_id: str,
        chapter_id: Optional[str],
        ordered_ids: List[str],
    ) -> None:
        """Rewrite ``sequence_order`` for every entry in a container.

        ``chapter_id`` may be ``None`` to target the unchaptered bucket of
        ``project_id``. Raises :class:`ValueError` if any id does not
        belong to this container — the repository never silently moves
        entries between containers on behalf of the caller.
        """
        if chapter_id is None:
            existing = self.list_unchaptered_for_project(project_id)
        else:
            # Ensure the chapter actually belongs to the project.
            owner = self._conn.execute(
                "SELECT project_id FROM chapters WHERE id = ?", (chapter_id,)
            ).fetchone()
            if owner is None or owner["project_id"] != project_id:
                raise ValueError(
                    f"chapter {chapter_id!r} is not in project {project_id!r}"
                )
            existing = self.list_for_chapter(chapter_id)

        existing_ids = {e.id for e in existing}
        if set(ordered_ids) != existing_ids:
            raise ValueError(
                "reorder_container requires exactly the entries of the "
                "target container"
            )
        for index, eid in enumerate(ordered_ids):
            self._conn.execute(
                "UPDATE entries SET sequence_order = ? WHERE id = ?",
                (index, eid),
            )

    def _next_sequence(
        self, project_id: str, chapter_id: Optional[str]
    ) -> int:
        if chapter_id is None:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(sequence_order), -1) AS mx
                  FROM entries
                 WHERE project_id = ? AND chapter_id IS NULL
                """,
                (project_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(sequence_order), -1) AS mx
                  FROM entries
                 WHERE chapter_id = ?
                """,
                (chapter_id,),
            ).fetchone()
        return int(row["mx"]) + 1

    def list_for_project(self, project_id: str) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
             WHERE project_id = ?
             ORDER BY updated_at DESC, created_at DESC
            """,
            (project_id,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def list_for_chapter(self, chapter_id: str) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
             WHERE chapter_id = ?
             ORDER BY CASE WHEN sequence_order IS NULL THEN 1 ELSE 0 END,
                      sequence_order ASC,
                      created_at ASC
            """,
            (chapter_id,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def list_unchaptered_for_project(self, project_id: str) -> List[Entry]:
        rows = self._conn.execute(
            """
            SELECT * FROM entries
             WHERE project_id = ? AND chapter_id IS NULL
             ORDER BY CASE WHEN sequence_order IS NULL THEN 1 ELSE 0 END,
                      sequence_order ASC,
                      created_at ASC
            """,
            (project_id,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]
