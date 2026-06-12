"""Entry repository for CRUD operations."""
from __future__ import annotations

import sqlite3
import uuid
from typing import Optional

from models import Entry, EntryType


def parse_tags(tags_text: str) -> list[str]:
    """Parse a comma-separated tags_text string into a normalised list."""
    seen: set[str] = set()
    result: list[str] = []
    for part in tags_text.split(","):
        tag = part.strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            result.append(tag)
    return result


def serialize_tags(tags: list[str]) -> str:
    """Serialise a tag list to the canonical tags_text storage format."""
    return ", ".join(tags)


def _row_to_entry(row: sqlite3.Row) -> Entry:
    """Convert a database row to an Entry model."""
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
        sequence_order=row["sequence_order"] if "sequence_order" in keys else None,
        tags=parse_tags(raw_tags),
        archived_at=row["archived_at"] if "archived_at" in keys else None,
        curation_status=(
            row["curation_status"]
            if "curation_status" in keys and row["curation_status"]
            else "unsorted"
        ),
    )


class EntryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        title: str = "",
        body: str = "",
        entry_type: str = EntryType.FRAGMENT.value,
        tags: list[str] | None = None,
    ) -> Entry:
        """Create a new entry."""
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
        """Update an existing entry."""
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
        """Delete an entry."""
        cur = self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        return cur.rowcount > 0

    def get(self, entry_id: str) -> Optional[Entry]:
        """Get a single entry by ID."""
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def list_recent(
        self,
        limit: int = 100,
        *,
        include_archived: bool = False,
    ) -> list[Entry]:
        """Return recent entries ordered by updated_at."""
        where = ""
        if not include_archived:
            where = "WHERE archived_at IS NULL"
        rows = self._conn.execute(
            f"SELECT * FROM entries {where} ORDER BY updated_at DESC, created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def count(self) -> int:
        """Count total entries."""
        row = self._conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()
        return int(row["n"])
