"""Full-text search for entries via SQLite FTS5.

Hides SQL details from the UI. Accepts a free-form user query and returns
entries ordered by FTS5 rank. The query string is wrapped as a single
phrase (with prefix matching on the last token) so users can type natural
words without learning FTS5 syntax.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from writer.domain.models.entry import Entry
from writer.domain.models.work import Work
from writer.storage.repositories.entry_repository import _row_to_entry
from writer.storage.repositories.work_repository import _row_to_work


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


@dataclass
class SearchHit:
    """One hit from the global search (M8).

    ``kind`` is ``"fragment"`` or ``"work"``. For works, ``section_id``
    points at the section that matched (best-effort, may be ``None`` if
    only header fields matched).
    """

    kind: str  # "fragment" | "work"
    id: str
    title: str
    snippet: str
    section_id: Optional[str] = None


class SearchService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Backwards-compatible fragment-only search (used by the existing
    # fragment list panel).
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # M8: works-only search.
    # ------------------------------------------------------------------
    def search_works(self, raw_query: str, limit: int = 50) -> List[Work]:
        match = _build_match_expression(raw_query)
        if not match:
            return []
        rows = self._conn.execute(
            """
            SELECT w.*
              FROM works_fts
              JOIN works w ON w.id = works_fts.work_id
             WHERE works_fts MATCH ?
             ORDER BY rank
             LIMIT ?
            """,
            (match, limit),
        ).fetchall()
        return [_row_to_work(r) for r in rows]

    # ------------------------------------------------------------------
    # M8: unified global search returning a mixed result list.
    # ------------------------------------------------------------------
    def search_all(self, raw_query: str, limit: int = 50) -> List[SearchHit]:
        results: List[SearchHit] = []
        match = _build_match_expression(raw_query)
        if not match:
            return results

        # --- Fragments ---
        fragment_rows = self._conn.execute(
            """
            SELECT e.id AS id,
                   e.title AS title,
                   snippet(entries_fts, 1, '[', ']', '…', 12) AS snip
              FROM entries_fts
              JOIN entries e ON e.rowid = entries_fts.rowid
             WHERE entries_fts MATCH ?
             ORDER BY rank
             LIMIT ?
            """,
            (match, limit),
        ).fetchall()
        for r in fragment_rows:
            results.append(
                SearchHit(
                    kind="fragment",
                    id=r["id"],
                    title=r["title"] or "",
                    snippet=r["snip"] or "",
                )
            )

        # --- Works (may be capped by `limit` per kind for fairness). ---
        work_rows = self._conn.execute(
            """
            SELECT works_fts.work_id AS id,
                   works_fts.title AS title,
                   snippet(works_fts, 3, '[', ']', '…', 12) AS snip
              FROM works_fts
             WHERE works_fts MATCH ?
             ORDER BY rank
             LIMIT ?
            """,
            (match, limit),
        ).fetchall()
        for r in work_rows:
            section_id = self._best_section_for_work(r["id"], match)
            results.append(
                SearchHit(
                    kind="work",
                    id=r["id"],
                    title=r["title"] or "",
                    snippet=r["snip"] or "",
                    section_id=section_id,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Locate the section whose content most likely caused a work hit.
    # Works on plain LIKE matching against the cleaned tokens — close
    # enough for "open the work and scroll to the matching section".
    # ------------------------------------------------------------------
    def _best_section_for_work(
        self, work_id: str, match_expr: str
    ) -> Optional[str]:
        # Pull the original tokens out of the match expression: they
        # look like `"foo" "bar"*` — strip quotes and trailing stars.
        tokens: List[str] = []
        for raw in match_expr.split():
            t = raw.strip().strip('"').rstrip("*").strip('"')
            if t:
                tokens.append(t)
        if not tokens:
            return None
        sections = self._conn.execute(
            "SELECT id, content FROM work_sections WHERE work_id = ? "
            "ORDER BY sort_order ASC",
            (work_id,),
        ).fetchall()
        for r in sections:
            content = (r["content"] or "").lower()
            if all(t.lower() in content for t in tokens):
                return r["id"]
        # Fallback: section that contains the *last* token (prefix-most).
        last = tokens[-1].lower()
        for r in sections:
            if last in (r["content"] or "").lower():
                return r["id"]
        return None

