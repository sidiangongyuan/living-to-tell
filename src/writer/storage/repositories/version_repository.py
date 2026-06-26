"""Storage for AI-generated and original versions of an entry.

Used in M2 only as a thin scaffold; M3 will populate it from the rewrite
service. Defined now so the storage layer is complete enough for entries to
own their version history.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.entry_version import EntryVersion


def _word_count(body: str) -> int:
    if not body:
        return 0
    total = 0
    buffer: list[str] = []
    for ch in body:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            if buffer:
                if "".join(buffer).strip():
                    total += 1
                buffer = []
            total += 1
        else:
            buffer.append(ch)
    if buffer:
        total += len([token for token in "".join(buffer).split() if token.strip()])
    return total


def _row_to_version(row: sqlite3.Row) -> EntryVersion:
    keys = row.keys()
    return EntryVersion(
        id=row["id"],
        entry_id=row["entry_id"],
        version_type=row["version_type"],
        content=row["content"],
        title_snapshot=row["title_snapshot"] if "title_snapshot" in keys else "",
        tags_snapshot=row["tags_snapshot"] if "tags_snapshot" in keys else "",
        label=row["label"] if "label" in keys else "",
        reason=row["reason"] if "reason" in keys else "",
        word_count=int(row["word_count"]) if "word_count" in keys else _word_count(row["content"] or ""),
        char_count=int(row["char_count"]) if "char_count" in keys else len(row["content"] or ""),
        created_at=row["created_at"],
        provider=row["provider"],
        model=row["model"],
    )


class VersionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        *,
        entry_id: str,
        version_type: str,
        content: str,
        title_snapshot: str = "",
        tags_snapshot: str = "",
        label: str = "",
        reason: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> EntryVersion:
        new_id = str(uuid.uuid4())
        word_count = _word_count(content)
        char_count = len(content or "")
        self._conn.execute(
            """
            INSERT INTO entry_versions
                (
                    id, entry_id, version_type, content,
                    title_snapshot, tags_snapshot, label, reason,
                    word_count, char_count, provider, model
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                entry_id,
                version_type,
                content,
                title_snapshot,
                tags_snapshot,
                label,
                reason,
                word_count,
                char_count,
                provider,
                model,
            ),
        )
        row = self._conn.execute(
            "SELECT * FROM entry_versions WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_version(row)

    def list_for_entry(self, entry_id: str) -> List[EntryVersion]:
        rows = self._conn.execute(
            """
            SELECT * FROM entry_versions
            WHERE entry_id = ?
            ORDER BY created_at DESC
            """,
            (entry_id,),
        ).fetchall()
        return [_row_to_version(r) for r in rows]

    def get(self, version_id: str) -> Optional[EntryVersion]:
        row = self._conn.execute(
            "SELECT * FROM entry_versions WHERE id = ?", (version_id,)
        ).fetchone()
        return _row_to_version(row) if row else None

    def delete(self, version_id: str, *, entry_id: Optional[str] = None) -> bool:
        if entry_id is None:
            cur = self._conn.execute(
                "DELETE FROM entry_versions WHERE id = ?",
                (version_id,),
            )
        else:
            cur = self._conn.execute(
                "DELETE FROM entry_versions WHERE id = ? AND entry_id = ?",
                (version_id, entry_id),
            )
        return cur.rowcount > 0
