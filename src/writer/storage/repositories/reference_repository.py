"""CRUD + search for reference passages.

Uses the same unicode61 FTS5 / sanitised token-quoting approach as
:class:`writer.services.search_service.SearchService`: strip non-alnum
characters from each whitespace-separated token, double-quote them, and
prefix-match the last token so users can search as they type.
"""
from __future__ import annotations

import re
import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.reference_passage import ReferencePassage


def _row_to_reference(row: sqlite3.Row) -> ReferencePassage:
    return ReferencePassage(
        id=row["id"],
        source_title=row["source_title"],
        source_author=row["source_author"],
        content=row["content"],
        tags=row["tags"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


_TOKEN_RE = re.compile(r"[^\w]+", flags=re.UNICODE)


def _build_match_expression(query: str) -> Optional[str]:
    tokens: list[str] = []
    for raw in query.split():
        cleaned = _TOKEN_RE.sub("", raw)
        if cleaned:
            tokens.append(cleaned)
    if not tokens:
        return None
    quoted = [f'"{t}"' for t in tokens[:-1]]
    quoted.append(f'"{tokens[-1]}"*')
    return " ".join(quoted)


class ReferenceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # writes ------------------------------------------------------------
    def create(
        self,
        *,
        source_title: str,
        content: str,
        source_author: str = "",
        tags: str = "",
    ) -> ReferencePassage:
        if not source_title.strip():
            raise ValueError("source_title is required")
        if not content.strip():
            raise ValueError("content is required")
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO reference_passages
                (id, source_title, source_author, content, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (new_id, source_title.strip(), source_author.strip(), content, tags.strip()),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def update(
        self,
        ref_id: str,
        *,
        source_title: str,
        content: str,
        source_author: str = "",
        tags: str = "",
    ) -> Optional[ReferencePassage]:
        if not source_title.strip():
            raise ValueError("source_title is required")
        if not content.strip():
            raise ValueError("content is required")
        cur = self._conn.execute(
            """
            UPDATE reference_passages
               SET source_title = ?,
                   source_author = ?,
                   content = ?,
                   tags = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
                source_title.strip(),
                source_author.strip(),
                content,
                tags.strip(),
                ref_id,
            ),
        )
        if cur.rowcount == 0:
            return None
        return self.get(ref_id)

    def delete(self, ref_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM reference_passages WHERE id = ?", (ref_id,)
        )
        return cur.rowcount > 0

    # reads -------------------------------------------------------------
    def get(self, ref_id: str) -> Optional[ReferencePassage]:
        row = self._conn.execute(
            "SELECT * FROM reference_passages WHERE id = ?", (ref_id,)
        ).fetchone()
        return _row_to_reference(row) if row else None

    def list_recent(self, limit: int = 200) -> List[ReferencePassage]:
        rows = self._conn.execute(
            """
            SELECT * FROM reference_passages
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_reference(r) for r in rows]

    def get_many(self, ids: list[str]) -> List[ReferencePassage]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT * FROM reference_passages WHERE id IN ({placeholders})",
            tuple(ids),
        ).fetchall()
        by_id = {row["id"]: _row_to_reference(row) for row in rows}
        return [by_id[i] for i in ids if i in by_id]

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM reference_passages"
        ).fetchone()
        return int(row["n"])

    def search(self, query: str, limit: int = 200) -> List[ReferencePassage]:
        expr = _build_match_expression(query)
        if expr is None:
            return []
        rows = self._conn.execute(
            """
            SELECT r.*
              FROM reference_passages_fts f
              JOIN reference_passages r ON r.rowid = f.rowid
             WHERE reference_passages_fts MATCH ?
             ORDER BY r.updated_at DESC
             LIMIT ?
            """,
            (expr, limit),
        ).fetchall()
        return [_row_to_reference(r) for r in rows]
