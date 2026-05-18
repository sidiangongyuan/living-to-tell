"""CRUD + search for reference passages.

Uses the same unicode61 FTS5 / sanitised token-quoting approach as
:class:`writer.services.search_service.SearchService`: strip non-alnum
characters from each whitespace-separated token, double-quote them, and
prefix-match the last token so users can search as they type.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.reference_passage import (
    REFERENCE_KIND_EXCERPT,
    USAGE_KIND_STYLE,
    ReferencePassage,
    normalise_kind,
    normalise_usage_kind,
)


def _row_to_reference(row: sqlite3.Row) -> ReferencePassage:
    keys = row.keys()
    return ReferencePassage(
        id=row["id"],
        source_title=row["source_title"],
        source_author=row["source_author"],
        content=row["content"],
        tags=row["tags"],
        kind=normalise_kind(row["kind"] if "kind" in keys else None),
        usage_kind=normalise_usage_kind(row["usage_kind"] if "usage_kind" in keys else None),
        personal_note=row["personal_note"] if "personal_note" in keys else "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


_TOKEN_RE = re.compile(r"[^\w]+", flags=re.UNICODE)


@dataclass(frozen=True)
class ReferenceLibraryStats:
    total: int
    total_chars: int
    recent_7d: int
    duplicate_risk_count: int
    by_kind: dict[str, int] = field(default_factory=dict)
    by_usage_kind: dict[str, int] = field(default_factory=dict)
    top_tags: list[tuple[str, int]] = field(default_factory=list)


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
        kind: str = REFERENCE_KIND_EXCERPT,
        usage_kind: str = USAGE_KIND_STYLE,
        personal_note: str = "",
    ) -> ReferencePassage:
        if not source_title.strip():
            raise ValueError("source_title is required")
        if not content.strip():
            raise ValueError("content is required")
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO reference_passages
                (id, source_title, source_author, content, tags, kind, usage_kind, personal_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                source_title.strip(),
                source_author.strip(),
                content,
                tags.strip(),
                normalise_kind(kind),
                normalise_usage_kind(usage_kind),
                personal_note,
            ),
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
        kind: str = REFERENCE_KIND_EXCERPT,
        usage_kind: str = USAGE_KIND_STYLE,
        personal_note: str = "",
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
                   kind = ?,
                   usage_kind = ?,
                   personal_note = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
                source_title.strip(),
                source_author.strip(),
                content,
                tags.strip(),
                normalise_kind(kind),
                normalise_usage_kind(usage_kind),
                personal_note,
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

    def list_recent(
        self, limit: int = 200, *, kind: Optional[str] = None, usage_kind: Optional[str] = None
    ) -> List[ReferencePassage]:
        conditions = []
        params: list = []
        if kind is not None:
            conditions.append("kind = ?")
            params.append(kind)
        if usage_kind is not None:
            conditions.append("usage_kind = ?")
            params.append(usage_kind)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT * FROM reference_passages
            {where}
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [_row_to_reference(r) for r in rows]

    def list_by_kind(
        self, kind: str, limit: int = 200
    ) -> List[ReferencePassage]:
        return self.list_recent(limit=limit, kind=normalise_kind(kind))

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

    def find_exact_duplicate(self, content: str) -> Optional[ReferencePassage]:
        normalized = normalize_reference_content(content)
        if not normalized:
            return None
        rows = self._conn.execute(
            "SELECT * FROM reference_passages ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
        for row in rows:
            passage = _row_to_reference(row)
            if normalize_reference_content(passage.content) == normalized:
                return passage
        return None

    def stats(self) -> ReferenceLibraryStats:
        rows = self._conn.execute("SELECT * FROM reference_passages").fetchall()
        passages = [_row_to_reference(r) for r in rows]
        by_kind = Counter(p.kind for p in passages)
        by_usage_kind = Counter(p.usage_kind for p in passages)
        tags: Counter[str] = Counter()
        duplicate_keys: Counter[str] = Counter()
        total_chars = 0
        for passage in passages:
            total_chars += len(passage.content or "")
            normalized = normalize_reference_content(passage.content)
            if normalized:
                duplicate_keys[normalized] += 1
            for tag in (passage.tags or "").split(","):
                value = tag.strip()
                if value:
                    tags[value] += 1
        recent_row = self._conn.execute(
            """
            SELECT COUNT(*) AS n
              FROM reference_passages
             WHERE created_at >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-7 days')
            """
        ).fetchone()
        duplicate_risk_count = sum(count for count in duplicate_keys.values() if count > 1)
        return ReferenceLibraryStats(
            total=len(passages),
            total_chars=total_chars,
            recent_7d=int(recent_row["n"] if recent_row else 0),
            duplicate_risk_count=duplicate_risk_count,
            by_kind=dict(by_kind),
            by_usage_kind=dict(by_usage_kind),
            top_tags=tags.most_common(5),
        )

    def search(
        self, query: str, limit: int = 200, *, kind: Optional[str] = None, usage_kind: Optional[str] = None
    ) -> List[ReferencePassage]:
        expr = _build_match_expression(query)
        if expr is None:
            return []
        conditions = ["reference_passages_fts MATCH ?"]
        params: list = [expr]
        if kind is not None:
            conditions.append("r.kind = ?")
            params.append(kind)
        if usage_kind is not None:
            conditions.append("r.usage_kind = ?")
            params.append(usage_kind)
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT r.*
              FROM reference_passages_fts f
              JOIN reference_passages r ON r.rowid = f.rowid
             WHERE {" AND ".join(conditions)}
             ORDER BY r.updated_at DESC
             LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [_row_to_reference(r) for r in rows]


def normalize_reference_content(content: str) -> str:
    return " ".join((content or "").split()).casefold()
