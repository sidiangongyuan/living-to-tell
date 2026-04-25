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
    """Parse a comma-separated ``tags_text`` string into a normalised list."""
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
        archived_at=row["archived_at"] if "archived_at" in keys else None,
        curation_status=(
            row["curation_status"]
            if "curation_status" in keys and row["curation_status"]
            else "unsorted"
        ),
    )


# Sort modes for ``list_recent`` (M7B).
SORT_UPDATED = "updated"
SORT_CREATED = "created"
SORT_TITLE = "title"
SUPPORTED_SORT_MODES = (SORT_UPDATED, SORT_CREATED, SORT_TITLE)


def _order_by_clause(sort: str) -> str:
    if sort == SORT_CREATED:
        return "ORDER BY created_at DESC, updated_at DESC"
    if sort == SORT_TITLE:
        return (
            "ORDER BY CASE WHEN title IS NULL OR title = '' THEN 1 ELSE 0 END, "
            "LOWER(title) ASC, updated_at DESC"
        )
    return "ORDER BY updated_at DESC, created_at DESC"


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

    def insert_restored(
        self,
        *,
        title: str,
        body: str,
        tags: list[str] | None = None,
        project_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        sequence_order: Optional[int] = None,
        archived_at: Optional[str] = None,
        entry_type: str = EntryType.FRAGMENT.value,
    ) -> Entry:
        """Re-create an entry whose content was recovered from trash.

        Preserves the original project/chapter/sequence assignment and the
        archived state where possible. If the requested ``sequence_order``
        is already taken (or invalid) inside the target project/chapter,
        the restored entry is appended to the end.
        """
        # Validate that chapter (if provided) actually belongs to the given
        # project. If not, drop the chapter assignment rather than writing
        # an inconsistent row.
        resolved_chapter: Optional[str] = chapter_id
        if project_id is not None and chapter_id is not None:
            row = self._conn.execute(
                "SELECT project_id FROM chapters WHERE id = ?",
                (chapter_id,),
            ).fetchone()
            if row is None or row["project_id"] != project_id:
                resolved_chapter = None

        # Resolve sequence_order: None stays None (unassigned); a conflicting
        # value is bumped to the next free slot.
        resolved_seq: Optional[int] = None
        if project_id is not None:
            if sequence_order is None:
                resolved_seq = self._next_sequence(project_id, resolved_chapter)
            else:
                if resolved_chapter is None:
                    existing = self._conn.execute(
                        """
                        SELECT 1 FROM entries
                         WHERE project_id = ? AND chapter_id IS NULL
                           AND sequence_order = ?
                        """,
                        (project_id, sequence_order),
                    ).fetchone()
                else:
                    existing = self._conn.execute(
                        """
                        SELECT 1 FROM entries
                         WHERE chapter_id = ? AND sequence_order = ?
                        """,
                        (resolved_chapter, sequence_order),
                    ).fetchone()
                if existing is None:
                    resolved_seq = int(sequence_order)
                else:
                    resolved_seq = self._next_sequence(
                        project_id, resolved_chapter
                    )

        new_id = str(uuid.uuid4())
        tags_text = serialize_tags(tags) if tags else ""
        self._conn.execute(
            """
            INSERT INTO entries (
                id, title, body, entry_type, tags_text,
                project_id, chapter_id, sequence_order, archived_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                title,
                body,
                entry_type,
                tags_text,
                project_id,
                resolved_chapter,
                resolved_seq,
                archived_at,
            ),
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

    def delete_many(self, entry_ids: list[str]) -> int:
        """Delete a batch of entries and return how many rows were removed."""
        unique = list({eid for eid in entry_ids if eid})
        if not unique:
            return 0
        placeholders = ",".join("?" for _ in unique)
        cur = self._conn.execute(
            f"DELETE FROM entries WHERE id IN ({placeholders})", unique
        )
        return cur.rowcount or 0

    def set_archived(self, entry_id: str, archived: bool) -> Optional[Entry]:
        """Archive or un-archive an entry.

        Archived entries are hidden from the default recent list but
        keep every other property (project/chapter, tags, body,
        version history).
        """
        if archived:
            self._conn.execute(
                """
                UPDATE entries
                   SET archived_at = COALESCE(
                           archived_at,
                           strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                       )
                 WHERE id = ?
                """,
                (entry_id,),
            )
        else:
            self._conn.execute(
                "UPDATE entries SET archived_at = NULL WHERE id = ?",
                (entry_id,),
            )
        return self.get(entry_id)

    def set_curation_status(
        self, entry_id: str, status: str
    ) -> Optional[Entry]:
        """Update the M8 curation tag (unsorted/included/parking/discarded)."""
        from writer.domain.enums import CurationStatus

        if status not in CurationStatus.values():
            raise ValueError(f"unknown curation status: {status!r}")
        self._conn.execute(
            "UPDATE entries SET curation_status = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
            "WHERE id = ?",
            (status, entry_id),
        )
        return self.get(entry_id)

    # reads -------------------------------------------------------------
    def get(self, entry_id: str) -> Optional[Entry]:
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def list_recent(
        self,
        limit: int = 100,
        *,
        sort: str = SORT_UPDATED,
        include_archived: bool = False,
        archived_only: bool = False,
    ) -> List[Entry]:
        """Return recent entries.

        By default archived entries are excluded so the main list stays
        clean. Pass ``include_archived=True`` to see everything or
        ``archived_only=True`` to see only archived rows.
        """
        where = ""
        if archived_only:
            where = "WHERE archived_at IS NOT NULL"
        elif not include_archived:
            where = "WHERE archived_at IS NULL"
        order = _order_by_clause(sort)
        rows = self._conn.execute(
            f"SELECT * FROM entries {where} {order} LIMIT ?",
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

    def list_recent_by_tag(
        self,
        tag: str,
        limit: int = 100,
        *,
        sort: str = SORT_UPDATED,
        include_archived: bool = False,
        archived_only: bool = False,
    ) -> list[Entry]:
        """Return recent entries that carry *tag* (case-insensitive)."""
        tag_lower = tag.lower()
        where = "WHERE tags_text != ''"
        if archived_only:
            where += " AND archived_at IS NOT NULL"
        elif not include_archived:
            where += " AND archived_at IS NULL"
        order = _order_by_clause(sort)
        rows = self._conn.execute(
            f"SELECT * FROM entries {where} {order}",
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
            return entry

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
        entry = self.get(entry_id)
        if entry is None:
            return None

        if chapter_id is None:
            if entry.chapter_id is None:
                return entry
            if entry.project_id is None:
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
            return entry

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
        if chapter_id is None:
            existing = self.list_unchaptered_for_project(project_id)
        else:
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
