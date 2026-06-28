"""Persistence for motif nodes, excerpts, and star-map graph data."""
from __future__ import annotations

import sqlite3
import uuid
from typing import Iterable, Optional

from writer.domain.models.motif import (
    MOTIF_SOURCE_ARTICLE,
    MOTIF_SOURCE_KINDS,
    MOTIF_SOURCE_REFERENCE,
    MotifExcerpt,
    MotifGraphEdge,
    MotifGraphNode,
    MotifNode,
)


def _split_text(value: object) -> list[str]:
    if value is None:
        return []
    return [part.strip() for part in str(value).split("\n") if part.strip()]


def _join_text(values: Iterable[str]) -> str:
    return "\n".join(part.strip() for part in values if part.strip())


def _optional_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _all_exact_ranges(source_text: str, excerpt_text: str) -> list[tuple[int, int]]:
    clean_excerpt = excerpt_text.strip()
    if not source_text or not clean_excerpt:
        return []
    ranges: list[tuple[int, int]] = []
    start = 0
    while True:
        found = source_text.find(clean_excerpt, start)
        if found < 0:
            break
        ranges.append((found, found + len(clean_excerpt)))
        start = found + max(1, len(clean_excerpt))
    return ranges


def _common_suffix_length(left: str, right: str, limit: int = 90) -> int:
    left_tail = left[-limit:]
    right_tail = right[-limit:]
    total = min(len(left_tail), len(right_tail))
    for size in range(total, 0, -1):
        if left_tail[-size:] == right_tail[-size:]:
            return size
    return 0


def _common_prefix_length(left: str, right: str, limit: int = 90) -> int:
    left_head = left[:limit]
    right_head = right[:limit]
    total = min(len(left_head), len(right_head))
    for size in range(total, 0, -1):
        if left_head[:size] == right_head[:size]:
            return size
    return 0


def _merge_note_values(values: Iterable[object]) -> str:
    notes: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in notes:
            notes.append(text)
    return "\n\n".join(notes)


def _row_to_node(row: sqlite3.Row) -> MotifNode:
    return MotifNode(
        id=row["id"],
        name=row["name"],
        aliases=_split_text(row["aliases_text"]),
        note=row["note"] or "",
        tags=_split_text(row["tags_text"]),
        pinned=bool(row["pinned"]),
        excerpt_count=int(row["excerpt_count"] if "excerpt_count" in row.keys() else 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_excerpt(
    row: sqlite3.Row,
    *,
    motif_ids: list[str],
    motif_names: list[str],
    source_exists: bool,
    source_current_title: str,
) -> MotifExcerpt:
    return MotifExcerpt(
        id=row["id"],
        source_kind=row["source_kind"],
        source_id=row["source_id"],
        source_title_snapshot=row["source_title_snapshot"] or "",
        excerpt_text=row["excerpt_text"] or "",
        note=row["note"] or "",
        selection_start=_optional_int(row["selection_start"]),
        selection_end=_optional_int(row["selection_end"]),
        before_context=row["before_context"] or "",
        after_context=row["after_context"] or "",
        motif_ids=motif_ids,
        motif_names=motif_names,
        source_exists=source_exists,
        source_current_title=source_current_title,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class MotifRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # nodes -------------------------------------------------------------
    def create_node(
        self,
        *,
        name: str,
        aliases: Optional[list[str]] = None,
        note: str = "",
        tags: Optional[list[str]] = None,
        pinned: bool = False,
    ) -> MotifNode:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Motif name is required")
        if self.find_node_by_name(clean_name) is not None:
            raise ValueError("Motif name already exists")
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO motif_nodes
                (id, name, aliases_text, note, tags_text, pinned)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                clean_name,
                _join_text(aliases or []),
                note,
                _join_text(tags or []),
                1 if pinned else 0,
            ),
        )
        loaded = self.get_node(new_id)
        assert loaded is not None
        return loaded

    def get_or_create_node(self, name: str) -> MotifNode:
        existing = self.find_node_by_name(name)
        if existing is not None:
            return existing
        return self.create_node(name=name)

    def update_node(
        self,
        node_id: str,
        *,
        name: str,
        aliases: Optional[list[str]] = None,
        note: str = "",
        tags: Optional[list[str]] = None,
        pinned: bool = False,
    ) -> Optional[MotifNode]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Motif name is required")
        existing = self.find_node_by_name(clean_name)
        if existing is not None and existing.id != node_id:
            raise ValueError("Motif name already exists")
        cur = self._conn.execute(
            """
            UPDATE motif_nodes
               SET name = ?,
                   aliases_text = ?,
                   note = ?,
                   tags_text = ?,
                   pinned = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
                clean_name,
                _join_text(aliases or []),
                note,
                _join_text(tags or []),
                1 if pinned else 0,
                node_id,
            ),
        )
        if cur.rowcount == 0:
            return None
        return self.get_node(node_id)

    def delete_node(self, node_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM motif_nodes WHERE id = ?", (node_id,))
        self._delete_orphan_excerpts()
        return cur.rowcount > 0

    def get_node(self, node_id: str) -> Optional[MotifNode]:
        row = self._conn.execute(
            """
            SELECT m.*, COUNT(DISTINCT l.excerpt_id) AS excerpt_count
              FROM motif_nodes m
              LEFT JOIN motif_excerpt_links l ON l.motif_id = m.id
             WHERE m.id = ?
             GROUP BY m.id
            """,
            (node_id,),
        ).fetchone()
        return _row_to_node(row) if row else None

    def find_node_by_name(self, name: str) -> Optional[MotifNode]:
        clean_name = name.strip()
        if not clean_name:
            return None
        row = self._conn.execute(
            """
            SELECT m.*, COUNT(DISTINCT l.excerpt_id) AS excerpt_count
              FROM motif_nodes m
              LEFT JOIN motif_excerpt_links l ON l.motif_id = m.id
             WHERE lower(m.name) = lower(?)
             GROUP BY m.id
            """,
            (clean_name,),
        ).fetchone()
        return _row_to_node(row) if row else None

    def list_nodes(self, query: str = "", limit: int = 500) -> list[MotifNode]:
        clean_query = query.strip()
        params: list[object] = []
        where = ""
        if clean_query:
            where = (
                "WHERE m.name LIKE ? OR m.aliases_text LIKE ? "
                "OR m.tags_text LIKE ? OR m.note LIKE ?"
            )
            like = f"%{clean_query}%"
            params.extend([like, like, like, like])
        params.append(max(1, int(limit)))
        rows = self._conn.execute(
            f"""
            SELECT m.*, COUNT(DISTINCT l.excerpt_id) AS excerpt_count
              FROM motif_nodes m
              LEFT JOIN motif_excerpt_links l ON l.motif_id = m.id
              {where}
             GROUP BY m.id
             ORDER BY m.pinned DESC,
                      excerpt_count DESC,
                      m.updated_at DESC,
                      m.created_at DESC
             LIMIT ?
            """,
            tuple(params),
        ).fetchall()
        return [_row_to_node(row) for row in rows]

    # excerpts ----------------------------------------------------------
    def create_excerpt(
        self,
        *,
        source_kind: str,
        source_id: str,
        excerpt_text: str,
        motif_ids: Optional[list[str]] = None,
        motif_names: Optional[list[str]] = None,
        source_title_snapshot: str = "",
        note: str = "",
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None,
        before_context: str = "",
        after_context: str = "",
    ) -> MotifExcerpt:
        clean_source_kind = source_kind.strip()
        if clean_source_kind not in MOTIF_SOURCE_KINDS:
            raise ValueError("Unsupported motif source kind")
        clean_source_id = source_id.strip()
        if not clean_source_id:
            raise ValueError("Source id is required")
        clean_excerpt = excerpt_text.strip()
        if not clean_excerpt:
            raise ValueError("Excerpt text is required")

        source_exists, current_title = self._source_info(
            clean_source_kind, clean_source_id
        )
        if not source_exists:
            raise ValueError("Source not found")

        started_transaction = not self._conn.in_transaction
        if started_transaction:
            self._conn.execute("BEGIN")
        try:
            nodes = self._resolve_nodes(motif_ids or [], motif_names or [])
            if not nodes:
                raise ValueError("At least one motif is required")
            existing = self.resolve_excerpt_for_selection(
                source_kind=clean_source_kind,
                source_id=clean_source_id,
                selection_start=selection_start,
                selection_end=selection_end,
                excerpt_text=clean_excerpt,
                before_context=before_context,
                after_context=after_context,
            )
            if existing is not None:
                existing_row = self._excerpt_row(existing.id)
                assert existing_row is not None
                existing_id = existing.id
                update_parts = [
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
                ]
                params: list[object] = []
                if note.strip():
                    update_parts.append("note = ?")
                    params.append(_merge_note_values([existing_row["note"], note]))
                if source_title_snapshot.strip() and not (existing_row["source_title_snapshot"] or "").strip():
                    update_parts.append("source_title_snapshot = ?")
                    params.append(source_title_snapshot.strip())
                if before_context:
                    update_parts.append("before_context = ?")
                    params.append(before_context)
                if after_context:
                    update_parts.append("after_context = ?")
                    params.append(after_context)
                if selection_start is not None and selection_end is not None:
                    update_parts.append("selection_start = ?")
                    update_parts.append("selection_end = ?")
                    params.extend([selection_start, selection_end])
                params.append(existing_id)
                self._conn.execute(
                    f"UPDATE motif_excerpts SET {', '.join(update_parts)} WHERE id = ?",
                    tuple(params),
                )
                for node in nodes:
                    self._link_excerpt(node.id, existing_id)
                self._touch_nodes([node.id for node in nodes])
                if started_transaction:
                    self._conn.execute("COMMIT")
                loaded_existing = self.get_excerpt(existing_id)
                assert loaded_existing is not None
                return loaded_existing

            new_id = str(uuid.uuid4())
            self._conn.execute(
                """
                INSERT INTO motif_excerpts
                    (
                        id,
                        source_kind,
                        source_id,
                        source_title_snapshot,
                        excerpt_text,
                        note,
                        selection_start,
                        selection_end,
                        before_context,
                        after_context
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id,
                    clean_source_kind,
                    clean_source_id,
                    source_title_snapshot.strip() or current_title,
                    clean_excerpt,
                    note,
                    selection_start,
                    selection_end,
                    before_context,
                    after_context,
                ),
            )
            for node in nodes:
                self._link_excerpt(node.id, new_id)
            self._touch_nodes([node.id for node in nodes])
            if started_transaction:
                self._conn.execute("COMMIT")
        except Exception:
            if started_transaction:
                self._conn.execute("ROLLBACK")
            raise
        loaded = self.get_excerpt(new_id)
        assert loaded is not None
        return loaded

    def find_excerpt_for_selection(
        self,
        *,
        source_kind: str,
        source_id: str,
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None,
        excerpt_text: str = "",
        before_context: str = "",
        after_context: str = "",
    ) -> Optional[MotifExcerpt]:
        return self.resolve_excerpt_for_selection(
            source_kind=source_kind,
            source_id=source_id,
            selection_start=selection_start,
            selection_end=selection_end,
            excerpt_text=excerpt_text,
            before_context=before_context,
            after_context=after_context,
        )

    def resolve_excerpt_for_selection(
        self,
        *,
        source_kind: str,
        source_id: str,
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None,
        excerpt_text: str = "",
        before_context: str = "",
        after_context: str = "",
    ) -> Optional[MotifExcerpt]:
        clean_source_kind = source_kind.strip()
        clean_source_id = source_id.strip()
        clean_excerpt = excerpt_text.strip()
        if clean_source_kind not in MOTIF_SOURCE_KINDS or not clean_source_id or not clean_excerpt:
            return None

        source_text = self._source_text(clean_source_kind, clean_source_id)
        requested_range = self._resolve_current_text_range(
            source_text,
            clean_excerpt,
            selection_start=selection_start,
            selection_end=selection_end,
            before_context=before_context,
            after_context=after_context,
            fallback_start=selection_start,
        )

        exact_rows = self._find_excerpt_rows_for_exact_range(
            source_kind=clean_source_kind,
            source_id=clean_source_id,
            selection_start=selection_start,
            selection_end=selection_end,
        )
        text_rows = self._find_excerpt_rows_for_text(
            source_kind=clean_source_kind,
            source_id=clean_source_id,
            excerpt_text=clean_excerpt,
        )
        if not text_rows and not exact_rows:
            return None

        row_ranges = {
            row["id"]: self._resolve_current_text_range(
                source_text,
                row["excerpt_text"] or "",
                selection_start=_optional_int(row["selection_start"]),
                selection_end=_optional_int(row["selection_end"]),
                before_context=row["before_context"] or "",
                after_context=row["after_context"] or "",
                fallback_start=_optional_int(row["selection_start"]),
            )
            for row in text_rows
        }
        matching_exact_rows = [
            row
            for row in exact_rows
            if (row["excerpt_text"] or "").strip() == clean_excerpt
        ]
        candidates: list[sqlite3.Row] = []
        if requested_range is not None:
            candidates = [
                row for row in text_rows if row_ranges.get(row["id"]) == requested_range
            ]
            seen_ids = {row["id"] for row in candidates}
            candidates.extend(
                row for row in matching_exact_rows if row["id"] not in seen_ids
            )
            if (
                not candidates
                and len(text_rows) == 1
                and len(_all_exact_ranges(source_text, clean_excerpt)) <= 1
            ):
                candidates = text_rows
        elif matching_exact_rows:
            candidates = matching_exact_rows
        elif len(text_rows) == 1 and len(_all_exact_ranges(source_text, clean_excerpt)) <= 1:
            candidates = text_rows

        if not candidates:
            return None
        return self._merge_and_update_rows(
            candidates,
            selection_range=requested_range or row_ranges.get(candidates[0]["id"]),
            before_context=before_context,
            after_context=after_context,
        )

    def add_motifs_to_excerpt(
        self,
        excerpt_id: str,
        *,
        motif_ids: Optional[list[str]] = None,
        motif_names: Optional[list[str]] = None,
        note: Optional[str] = None,
    ) -> Optional[MotifExcerpt]:
        if self.get_excerpt(excerpt_id) is None:
            return None
        started_transaction = not self._conn.in_transaction
        if started_transaction:
            self._conn.execute("BEGIN")
        try:
            nodes = self._resolve_nodes(motif_ids or [], motif_names or [])
            if not nodes:
                raise ValueError("At least one motif is required")
            for node in nodes:
                self._link_excerpt(node.id, excerpt_id)
            update_parts = [
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
            ]
            params: list[object] = []
            if note is not None and note.strip():
                update_parts.append("note = ?")
                params.append(note)
            params.append(excerpt_id)
            self._conn.execute(
                f"UPDATE motif_excerpts SET {', '.join(update_parts)} WHERE id = ?",
                tuple(params),
            )
            self._touch_nodes([node.id for node in nodes])
            if started_transaction:
                self._conn.execute("COMMIT")
        except Exception:
            if started_transaction:
                self._conn.execute("ROLLBACK")
            raise
        return self.get_excerpt(excerpt_id)

    def set_motifs_for_excerpt(
        self,
        excerpt_id: str,
        *,
        motif_ids: Optional[list[str]] = None,
        motif_names: Optional[list[str]] = None,
        note: Optional[str] = None,
    ) -> tuple[bool, Optional[MotifExcerpt]]:
        if self.get_excerpt(excerpt_id) is None:
            return False, None
        started_transaction = not self._conn.in_transaction
        if started_transaction:
            self._conn.execute("BEGIN")
        try:
            existing_motif_ids = [
                row["motif_id"]
                for row in self._conn.execute(
                    "SELECT motif_id FROM motif_excerpt_links WHERE excerpt_id = ?",
                    (excerpt_id,),
                ).fetchall()
            ]
            nodes = self._resolve_nodes(motif_ids or [], motif_names or [])
            target_ids = {node.id for node in nodes}
            for motif_id in existing_motif_ids:
                if motif_id not in target_ids:
                    self._conn.execute(
                        """
                        DELETE FROM motif_excerpt_links
                         WHERE excerpt_id = ? AND motif_id = ?
                        """,
                        (excerpt_id, motif_id),
                    )
            for node in nodes:
                self._link_excerpt(node.id, excerpt_id)

            touched_ids = list({*existing_motif_ids, *target_ids})
            if not target_ids:
                self._conn.execute(
                    "DELETE FROM motif_excerpts WHERE id = ?", (excerpt_id,)
                )
                self._touch_nodes(touched_ids)
                if started_transaction:
                    self._conn.execute("COMMIT")
                return True, None

            update_parts = [
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
            ]
            params: list[object] = []
            if note is not None:
                update_parts.append("note = ?")
                params.append(note)
            params.append(excerpt_id)
            self._conn.execute(
                f"UPDATE motif_excerpts SET {', '.join(update_parts)} WHERE id = ?",
                tuple(params),
            )
            self._touch_nodes(touched_ids)
            if started_transaction:
                self._conn.execute("COMMIT")
        except Exception:
            if started_transaction:
                self._conn.execute("ROLLBACK")
            raise
        return True, self.get_excerpt(excerpt_id)

    def get_excerpt(self, excerpt_id: str) -> Optional[MotifExcerpt]:
        row = self._conn.execute(
            "SELECT * FROM motif_excerpts WHERE id = ?", (excerpt_id,)
        ).fetchone()
        if row is None:
            return None
        motif_ids, motif_names = self._motifs_for_excerpt(excerpt_id)
        source_exists, current_title = self._source_info(
            row["source_kind"], row["source_id"]
        )
        return _row_to_excerpt(
            row,
            motif_ids=motif_ids,
            motif_names=motif_names,
            source_exists=source_exists,
            source_current_title=current_title,
        )

    def list_excerpts_for_node(
        self, node_id: str, *, limit: int = 200
    ) -> list[MotifExcerpt]:
        rows = self._conn.execute(
            """
            SELECT e.*
              FROM motif_excerpts e
              JOIN motif_excerpt_links l ON l.excerpt_id = e.id
             WHERE l.motif_id = ?
             ORDER BY e.updated_at DESC, e.created_at DESC
             LIMIT ?
            """,
            (node_id, max(1, int(limit))),
        ).fetchall()
        return [self._excerpt_from_row(row) for row in rows]

    def list_excerpts_for_source(
        self,
        source_kind: str,
        source_id: str,
        *,
        limit: int = 500,
    ) -> list[MotifExcerpt]:
        clean_source_kind = source_kind.strip()
        if clean_source_kind not in MOTIF_SOURCE_KINDS:
            raise ValueError("Unsupported motif source kind")
        clean_source_id = source_id.strip()
        if not clean_source_id:
            raise ValueError("Source id is required")
        self.repair_source_excerpt_positions(clean_source_kind, clean_source_id)
        rows = self._conn.execute(
            """
            SELECT e.*
              FROM motif_excerpts e
             WHERE e.source_kind = ?
               AND e.source_id = ?
             ORDER BY
               CASE WHEN e.selection_start IS NULL THEN 1 ELSE 0 END,
               e.selection_start ASC,
               e.updated_at DESC,
               e.created_at DESC
             LIMIT ?
            """,
            (clean_source_kind, clean_source_id, max(1, int(limit))),
        ).fetchall()
        return [self._excerpt_from_row(row) for row in rows]

    def repair_source_excerpt_positions(
        self,
        source_kind: str,
        source_id: str,
    ) -> int:
        clean_source_kind = source_kind.strip()
        if clean_source_kind not in MOTIF_SOURCE_KINDS:
            raise ValueError("Unsupported motif source kind")
        clean_source_id = source_id.strip()
        if not clean_source_id:
            raise ValueError("Source id is required")
        source_text = self._source_text(clean_source_kind, clean_source_id)
        if not source_text:
            return 0
        rows = self._conn.execute(
            """
            SELECT *
              FROM motif_excerpts
             WHERE source_kind = ?
               AND source_id = ?
            """,
            (clean_source_kind, clean_source_id),
        ).fetchall()
        groups: dict[tuple[int, int, str], list[sqlite3.Row]] = {}
        repaired = 0
        for row in rows:
            excerpt_text = (row["excerpt_text"] or "").strip()
            if not excerpt_text:
                continue
            current_range = self._resolve_current_text_range(
                source_text,
                excerpt_text,
                selection_start=_optional_int(row["selection_start"]),
                selection_end=_optional_int(row["selection_end"]),
                before_context=row["before_context"] or "",
                after_context=row["after_context"] or "",
                fallback_start=_optional_int(row["selection_start"]),
            )
            if current_range is None:
                continue
            start, end = current_range
            groups.setdefault((start, end, excerpt_text), []).append(row)
            if row["selection_start"] != start or row["selection_end"] != end:
                before, after = self._contexts_for_range(source_text, start, end)
                self._update_excerpt_range(
                    row["id"],
                    start,
                    end,
                    before_context=before,
                    after_context=after,
                )
                repaired += 1
        for (start, end, _excerpt_text), duplicate_rows in groups.items():
            if len(duplicate_rows) <= 1:
                continue
            before, after = self._contexts_for_range(source_text, start, end)
            canonical = self._canonical_excerpt_row(
                duplicate_rows,
                selection_range=(start, end),
            )
            duplicate_ids = [row["id"] for row in duplicate_rows if row["id"] != canonical["id"]]
            self.merge_duplicate_excerpts(
                canonical["id"],
                duplicate_ids,
                selection_start=start,
                selection_end=end,
                before_context=before,
                after_context=after,
            )
            repaired += len(duplicate_ids)
        return repaired

    def delete_excerpt(self, excerpt_id: str) -> bool:
        motif_ids = [
            row["motif_id"]
            for row in self._conn.execute(
                "SELECT motif_id FROM motif_excerpt_links WHERE excerpt_id = ?",
                (excerpt_id,),
            ).fetchall()
        ]
        cur = self._conn.execute(
            "DELETE FROM motif_excerpts WHERE id = ?", (excerpt_id,)
        )
        if motif_ids:
            self._touch_nodes(motif_ids)
        return cur.rowcount > 0

    def unlink_motif_from_excerpt(self, excerpt_id: str, motif_id: str) -> bool:
        motif_ids = [
            row["motif_id"]
            for row in self._conn.execute(
                "SELECT motif_id FROM motif_excerpt_links WHERE excerpt_id = ?",
                (excerpt_id,),
            ).fetchall()
        ]
        if motif_id not in motif_ids:
            return False
        started_transaction = not self._conn.in_transaction
        if started_transaction:
            self._conn.execute("BEGIN")
        try:
            cur = self._conn.execute(
                """
                DELETE FROM motif_excerpt_links
                 WHERE excerpt_id = ? AND motif_id = ?
                """,
                (excerpt_id, motif_id),
            )
            if cur.rowcount <= 0:
                if started_transaction:
                    self._conn.execute("COMMIT")
                return False
            remaining_count = self._conn.execute(
                "SELECT COUNT(*) AS n FROM motif_excerpt_links WHERE excerpt_id = ?",
                (excerpt_id,),
            ).fetchone()["n"]
            if int(remaining_count) <= 0:
                self._conn.execute(
                    "DELETE FROM motif_excerpts WHERE id = ?", (excerpt_id,)
                )
            else:
                self._conn.execute(
                    """
                    UPDATE motif_excerpts
                       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                     WHERE id = ?
                    """,
                    (excerpt_id,),
                )
            self._touch_nodes(motif_ids)
            if started_transaction:
                self._conn.execute("COMMIT")
        except Exception:
            if started_transaction:
                self._conn.execute("ROLLBACK")
            raise
        return True

    def merge_duplicate_excerpts(
        self,
        canonical_id: str,
        duplicate_ids: list[str],
        *,
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None,
        before_context: Optional[str] = None,
        after_context: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Optional[MotifExcerpt]:
        unique_duplicate_ids = [
            duplicate_id
            for duplicate_id in dict.fromkeys(duplicate_ids)
            if duplicate_id and duplicate_id != canonical_id
        ]
        canonical = self._excerpt_row(canonical_id)
        if canonical is None:
            return None

        started_transaction = not self._conn.in_transaction
        if started_transaction:
            self._conn.execute("BEGIN")
        try:
            duplicate_rows = [
                row
                for row in (
                    self._excerpt_row(duplicate_id)
                    for duplicate_id in unique_duplicate_ids
                )
                if row is not None
            ]
            touched_ids = [
                row["motif_id"]
                for row in self._conn.execute(
                    """
                    SELECT DISTINCT motif_id
                      FROM motif_excerpt_links
                     WHERE excerpt_id IN ({})
                    """.format(",".join("?" for _ in [canonical_id, *unique_duplicate_ids])),
                    tuple([canonical_id, *unique_duplicate_ids]),
                ).fetchall()
            ]
            for duplicate_id in unique_duplicate_ids:
                for row in self._conn.execute(
                    """
                    SELECT motif_id
                      FROM motif_excerpt_links
                     WHERE excerpt_id = ?
                    """,
                    (duplicate_id,),
                ).fetchall():
                    self._link_excerpt(row["motif_id"], canonical_id)
            update_parts = [
                "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
            ]
            params: list[object] = []
            merged_note = _merge_note_values(
                [canonical["note"], *[row["note"] for row in duplicate_rows], note]
            )
            update_parts.append("note = ?")
            params.append(merged_note)
            if selection_start is not None and selection_end is not None:
                update_parts.append("selection_start = ?")
                update_parts.append("selection_end = ?")
                params.extend([selection_start, selection_end])
            if before_context is not None:
                update_parts.append("before_context = ?")
                params.append(before_context)
            if after_context is not None:
                update_parts.append("after_context = ?")
                params.append(after_context)
            source_title = canonical["source_title_snapshot"] or next(
                (
                    row["source_title_snapshot"]
                    for row in duplicate_rows
                    if (row["source_title_snapshot"] or "").strip()
                ),
                "",
            )
            if source_title != (canonical["source_title_snapshot"] or ""):
                update_parts.append("source_title_snapshot = ?")
                params.append(source_title)
            params.append(canonical_id)
            self._conn.execute(
                f"UPDATE motif_excerpts SET {', '.join(update_parts)} WHERE id = ?",
                tuple(params),
            )
            if unique_duplicate_ids:
                placeholders = ",".join("?" for _ in unique_duplicate_ids)
                self._conn.execute(
                    f"DELETE FROM motif_excerpts WHERE id IN ({placeholders})",
                    tuple(unique_duplicate_ids),
                )
            self._touch_nodes(touched_ids)
            if started_transaction:
                self._conn.execute("COMMIT")
        except Exception:
            if started_transaction:
                self._conn.execute("ROLLBACK")
            raise
        return self.get_excerpt(canonical_id)

    # graph -------------------------------------------------------------
    def graph(self, *, query: str = "", limit: int = 80) -> tuple[list[MotifGraphNode], list[MotifGraphEdge]]:
        nodes = self.list_nodes(query=query, limit=limit)
        return self._graph_for_node_set(nodes)

    def local_graph(
        self, node_id: str, *, limit: int = 32
    ) -> tuple[list[MotifGraphNode], list[MotifGraphEdge]]:
        center = self.get_node(node_id)
        if center is None:
            return [], []
        related_rows = self._conn.execute(
            """
            WITH center_excerpts AS (
                SELECT excerpt_id FROM motif_excerpt_links WHERE motif_id = ?
            ),
            center_sources AS (
                SELECT DISTINCT e.source_kind, e.source_id
                  FROM motif_excerpts e
                  JOIN center_excerpts ce ON ce.excerpt_id = e.id
            ),
            shared_excerpts AS (
                SELECT l.motif_id, COUNT(DISTINCT l.excerpt_id) AS n
                  FROM motif_excerpt_links l
                  JOIN center_excerpts ce ON ce.excerpt_id = l.excerpt_id
                 WHERE l.motif_id != ?
                 GROUP BY l.motif_id
            ),
            shared_sources AS (
                SELECT l.motif_id,
                       COUNT(DISTINCT e.source_kind || ':' || e.source_id) AS n
                  FROM motif_excerpt_links l
                  JOIN motif_excerpts e ON e.id = l.excerpt_id
                  JOIN center_sources cs
                    ON cs.source_kind = e.source_kind AND cs.source_id = e.source_id
                 WHERE l.motif_id != ?
                 GROUP BY l.motif_id
            )
            SELECT m.*,
                   COUNT(DISTINCT all_l.excerpt_id) AS excerpt_count,
                   COALESCE(se.n, 0) AS shared_excerpts,
                   COALESCE(ss.n, 0) AS shared_sources,
                   COALESCE(se.n, 0) * 2 + COALESCE(ss.n, 0) AS weight
              FROM motif_nodes m
              LEFT JOIN motif_excerpt_links all_l ON all_l.motif_id = m.id
              LEFT JOIN shared_excerpts se ON se.motif_id = m.id
              LEFT JOIN shared_sources ss ON ss.motif_id = m.id
             WHERE m.id != ?
               AND (COALESCE(se.n, 0) > 0 OR COALESCE(ss.n, 0) > 0)
             GROUP BY m.id
             ORDER BY weight DESC, excerpt_count DESC, m.updated_at DESC
             LIMIT ?
            """,
            (node_id, node_id, node_id, node_id, max(1, int(limit))),
        ).fetchall()
        related = [_row_to_node(row) for row in related_rows]
        graph_nodes = [
            MotifGraphNode(
                id=center.id,
                name=center.name,
                excerpt_count=center.excerpt_count,
                pinned=center.pinned,
                is_center=True,
            )
        ]
        graph_nodes.extend(
            MotifGraphNode(
                id=node.id,
                name=node.name,
                excerpt_count=node.excerpt_count,
                pinned=node.pinned,
                is_center=False,
            )
            for node in related
        )
        edges = [
            MotifGraphEdge(
                source_id=center.id,
                target_id=row["id"],
                weight=int(row["weight"]),
                shared_excerpts=int(row["shared_excerpts"]),
                shared_sources=int(row["shared_sources"]),
            )
            for row in related_rows
        ]
        return graph_nodes, edges

    # internals ---------------------------------------------------------
    def _resolve_nodes(
        self, motif_ids: list[str], motif_names: list[str]
    ) -> list[MotifNode]:
        by_id: dict[str, MotifNode] = {}
        for motif_id in motif_ids:
            node = self.get_node(motif_id)
            if node is not None:
                by_id[node.id] = node
        for name in motif_names:
            clean_name = name.strip()
            if not clean_name:
                continue
            node = self.get_or_create_node(clean_name)
            by_id[node.id] = node
        return list(by_id.values())

    def _link_excerpt(self, motif_id: str, excerpt_id: str) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO motif_excerpt_links
                (id, motif_id, excerpt_id)
            VALUES (?, ?, ?)
            """,
            (str(uuid.uuid4()), motif_id, excerpt_id),
        )

    def _excerpt_row(self, excerpt_id: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM motif_excerpts WHERE id = ?", (excerpt_id,)
        ).fetchone()

    def _find_excerpt_rows_for_exact_range(
        self,
        *,
        source_kind: str,
        source_id: str,
        selection_start: Optional[int],
        selection_end: Optional[int],
    ) -> list[sqlite3.Row]:
        if selection_start is None or selection_end is None:
            return []
        return self._conn.execute(
            """
            SELECT *
              FROM motif_excerpts
             WHERE source_kind = ?
               AND source_id = ?
               AND selection_start = ?
               AND selection_end = ?
             ORDER BY updated_at DESC, created_at DESC
            """,
            (source_kind, source_id, selection_start, selection_end),
        ).fetchall()

    def _find_excerpt_rows_for_text(
        self,
        *,
        source_kind: str,
        source_id: str,
        excerpt_text: str,
    ) -> list[sqlite3.Row]:
        clean_excerpt = excerpt_text.strip()
        if not clean_excerpt:
            return []
        rows = self._conn.execute(
            """
            SELECT *
              FROM motif_excerpts
             WHERE source_kind = ?
               AND source_id = ?
             ORDER BY created_at ASC, updated_at ASC, id ASC
            """,
            (source_kind, source_id),
        ).fetchall()
        return [
            row
            for row in rows
            if (row["excerpt_text"] or "").strip() == clean_excerpt
        ]

    def _canonical_excerpt_row(
        self,
        rows: list[sqlite3.Row],
        *,
        selection_range: Optional[tuple[Optional[int], Optional[int]]] = None,
    ) -> sqlite3.Row:
        expected_start: Optional[int] = None
        expected_end: Optional[int] = None
        if selection_range is not None:
            start, end = selection_range
            if start is not None and end is not None:
                expected_start = int(start)
                expected_end = int(end)

        return sorted(
            rows,
            key=lambda row: (
                0
                if expected_start is not None
                and _optional_int(row["selection_start"]) == expected_start
                and _optional_int(row["selection_end"]) == expected_end
                else 1,
                str(row["created_at"] or ""),
                str(row["updated_at"] or ""),
                str(row["id"] or ""),
            ),
        )[0]

    def _contexts_for_range(
        self,
        source_text: str,
        start: int,
        end: int,
        context_size: int = 90,
    ) -> tuple[str, str]:
        return (
            source_text[max(0, start - context_size):start],
            source_text[end:min(len(source_text), end + context_size)],
        )

    def _update_excerpt_range(
        self,
        excerpt_id: str,
        start: int,
        end: int,
        *,
        before_context: Optional[str] = None,
        after_context: Optional[str] = None,
    ) -> None:
        update_parts = [
            "selection_start = ?",
            "selection_end = ?",
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')",
        ]
        params: list[object] = [start, end]
        if before_context is not None:
            update_parts.append("before_context = ?")
            params.append(before_context)
        if after_context is not None:
            update_parts.append("after_context = ?")
            params.append(after_context)
        params.append(excerpt_id)
        self._conn.execute(
            f"UPDATE motif_excerpts SET {', '.join(update_parts)} WHERE id = ?",
            tuple(params),
        )

    def _merge_and_update_rows(
        self,
        rows: list[sqlite3.Row],
        *,
        selection_range: Optional[tuple[Optional[int], Optional[int]]],
        before_context: Optional[str] = None,
        after_context: Optional[str] = None,
    ) -> Optional[MotifExcerpt]:
        if not rows:
            return None
        canonical = self._canonical_excerpt_row(rows, selection_range=selection_range)
        duplicate_ids = [row["id"] for row in rows if row["id"] != canonical["id"]]
        start: Optional[int] = None
        end: Optional[int] = None
        if selection_range is not None:
            start_candidate, end_candidate = selection_range
            if start_candidate is not None and end_candidate is not None:
                start = int(start_candidate)
                end = int(end_candidate)
        return self.merge_duplicate_excerpts(
            canonical["id"],
            duplicate_ids,
            selection_start=start,
            selection_end=end,
            before_context=before_context if before_context else None,
            after_context=after_context if after_context else None,
        )

    def _resolve_current_text_range(
        self,
        source_text: str,
        excerpt_text: str,
        *,
        selection_start: Optional[int],
        selection_end: Optional[int],
        before_context: str = "",
        after_context: str = "",
        fallback_start: Optional[int] = None,
    ) -> Optional[tuple[int, int]]:
        clean_excerpt = excerpt_text.strip()
        if not source_text or not clean_excerpt:
            return None
        if selection_start is not None and selection_end is not None:
            safe_start = max(0, min(int(selection_start), len(source_text)))
            safe_end = max(safe_start, min(int(selection_end), len(source_text)))
            if source_text[safe_start:safe_end].strip() == clean_excerpt:
                return safe_start, safe_end

        ranges = _all_exact_ranges(source_text, clean_excerpt)
        if not ranges:
            return None
        if len(ranges) == 1:
            return ranges[0]

        scored: list[tuple[int, int, int]] = []
        for start, end in ranges:
            actual_before, actual_after = self._contexts_for_range(
                source_text, start, end
            )
            context_score = 0
            if before_context:
                context_score += _common_suffix_length(actual_before, before_context)
            if after_context:
                context_score += _common_prefix_length(actual_after, after_context)
            score = context_score * 1000
            if fallback_start is not None:
                distance = abs(start - int(fallback_start))
                score -= min(distance, 1000)
            scored.append((score, start, end))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored or scored[0][0] <= 0:
            return None
        if len(scored) > 1 and scored[0][0] == scored[1][0]:
            return None
        return scored[0][1], scored[0][2]

    def _touch_nodes(self, motif_ids: list[str]) -> None:
        if not motif_ids:
            return
        placeholders = ",".join("?" for _ in motif_ids)
        self._conn.execute(
            f"""
            UPDATE motif_nodes
               SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id IN ({placeholders})
            """,
            tuple(motif_ids),
        )

    def _delete_orphan_excerpts(self) -> None:
        self._conn.execute(
            """
            DELETE FROM motif_excerpts
             WHERE id NOT IN (
                SELECT DISTINCT excerpt_id FROM motif_excerpt_links
             )
            """
        )

    def _source_info(self, source_kind: str, source_id: str) -> tuple[bool, str]:
        if source_kind == MOTIF_SOURCE_ARTICLE:
            row = self._conn.execute(
                "SELECT title FROM entries WHERE id = ?", (source_id,)
            ).fetchone()
            return (row is not None, row["title"] if row else "")
        if source_kind == MOTIF_SOURCE_REFERENCE:
            row = self._conn.execute(
                "SELECT source_title, content FROM reference_passages WHERE id = ?",
                (source_id,),
            ).fetchone()
            if row is None:
                return False, ""
            title = row["source_title"] or (row["content"] or "")[:24]
            return True, title
        return False, ""

    def _source_text(self, source_kind: str, source_id: str) -> str:
        if source_kind == MOTIF_SOURCE_ARTICLE:
            row = self._conn.execute(
                "SELECT body FROM entries WHERE id = ?", (source_id,)
            ).fetchone()
            return (row["body"] or "") if row else ""
        if source_kind == MOTIF_SOURCE_REFERENCE:
            row = self._conn.execute(
                "SELECT content FROM reference_passages WHERE id = ?", (source_id,)
            ).fetchone()
            return (row["content"] or "") if row else ""
        return ""

    def _motifs_for_excerpt(self, excerpt_id: str) -> tuple[list[str], list[str]]:
        rows = self._conn.execute(
            """
            SELECT m.id, m.name
              FROM motif_nodes m
              JOIN motif_excerpt_links l ON l.motif_id = m.id
             WHERE l.excerpt_id = ?
             ORDER BY m.name COLLATE NOCASE
            """,
            (excerpt_id,),
        ).fetchall()
        return [row["id"] for row in rows], [row["name"] for row in rows]

    def _excerpt_from_row(self, row: sqlite3.Row) -> MotifExcerpt:
        motif_ids, motif_names = self._motifs_for_excerpt(row["id"])
        source_exists, current_title = self._source_info(
            row["source_kind"], row["source_id"]
        )
        return _row_to_excerpt(
            row,
            motif_ids=motif_ids,
            motif_names=motif_names,
            source_exists=source_exists,
            source_current_title=current_title,
        )

    def _graph_for_node_set(
        self, nodes: list[MotifNode]
    ) -> tuple[list[MotifGraphNode], list[MotifGraphEdge]]:
        if not nodes:
            return [], []
        node_ids = [node.id for node in nodes]
        placeholders = ",".join("?" for _ in node_ids)
        shared_excerpts: dict[tuple[str, str], int] = {}
        for row in self._conn.execute(
            f"""
            SELECT a.motif_id AS source_id,
                   b.motif_id AS target_id,
                   COUNT(DISTINCT a.excerpt_id) AS n
              FROM motif_excerpt_links a
              JOIN motif_excerpt_links b
                ON a.excerpt_id = b.excerpt_id AND a.motif_id < b.motif_id
             WHERE a.motif_id IN ({placeholders})
               AND b.motif_id IN ({placeholders})
             GROUP BY a.motif_id, b.motif_id
            """,
            tuple(node_ids + node_ids),
        ).fetchall():
            shared_excerpts[(row["source_id"], row["target_id"])] = int(row["n"])

        shared_sources: dict[tuple[str, str], int] = {}
        for row in self._conn.execute(
            f"""
            SELECT a.motif_id AS source_id,
                   b.motif_id AS target_id,
                   COUNT(DISTINCT ea.source_kind || ':' || ea.source_id) AS n
              FROM motif_excerpt_links a
              JOIN motif_excerpt_links b ON a.motif_id < b.motif_id
              JOIN motif_excerpts ea ON ea.id = a.excerpt_id
              JOIN motif_excerpts eb
                ON eb.id = b.excerpt_id
               AND eb.source_kind = ea.source_kind
               AND eb.source_id = ea.source_id
             WHERE a.motif_id IN ({placeholders})
               AND b.motif_id IN ({placeholders})
             GROUP BY a.motif_id, b.motif_id
            """,
            tuple(node_ids + node_ids),
        ).fetchall():
            shared_sources[(row["source_id"], row["target_id"])] = int(row["n"])

        keys = set(shared_excerpts) | set(shared_sources)
        edges = [
            MotifGraphEdge(
                source_id=source_id,
                target_id=target_id,
                weight=shared_excerpts.get((source_id, target_id), 0) * 2
                + shared_sources.get((source_id, target_id), 0),
                shared_excerpts=shared_excerpts.get((source_id, target_id), 0),
                shared_sources=shared_sources.get((source_id, target_id), 0),
            )
            for source_id, target_id in keys
        ]
        edges.sort(key=lambda edge: edge.weight, reverse=True)
        graph_nodes = [
            MotifGraphNode(
                id=node.id,
                name=node.name,
                excerpt_count=node.excerpt_count,
                pinned=node.pinned,
                is_center=False,
            )
            for node in nodes
        ]
        return graph_nodes, edges
