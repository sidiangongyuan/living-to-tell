"""Full-text search for entries via SQLite FTS5.

Hides SQL details from the UI. Accepts a free-form user query and returns
entries ordered by FTS5 rank. The query string is wrapped as a single
phrase (with prefix matching on the last token) so users can type natural
words without learning FTS5 syntax.
"""
from __future__ import annotations

import sqlite3
from typing import List

from writer.domain.models.entry import Entry
from writer.storage.repositories.entry_repository import _row_to_entry


def _build_match_expression(raw: str) -> str:
    """Turn a free-form user query into a safe FTS5 MATCH expression.

    Strategy: split on whitespace, keep alphanumerics + CJK chars, drop
    everything else, quote each token (which neutralises FTS5 operators),
    and add a trailing ``*`` to the last token so as-you-type works.
    """
    tokens: List[str] = []
    for word in raw.split():
        cleaned = "".join(ch for ch in word if ch.isalnum())
        if cleaned:
            tokens.append(cleaned)
    if not tokens:
        return ""
    quoted = [f'"{t}"' for t in tokens]
    quoted[-1] = f'"{tokens[-1]}"*'
    return " ".join(quoted)


class SearchService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def search(self, raw_query: str, limit: int = 50) -> List[Entry]:
        match = _build_match_expression(raw_query)
        if not match:
            return []
        rows = self._conn.execute(
            """
            SELECT e.*
              FROM entries_fts
              JOIN entries e ON e.rowid = entries_fts.rowid
             WHERE entries_fts MATCH ?
             ORDER BY rank
             LIMIT ?
            """,
            (match, limit),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]
