"""Persistence for ``WorkSection`` blocks (M8).

A section is a single ordered prose block inside a work. The repository
keeps ``sort_order`` dense (0, 1, 2, …) on every reorder so up/down
arithmetic and drag-drop both stay simple.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.enums import SectionType
from writer.domain.models.work_section import WorkSection
from writer.storage.repositories.work_repository import rebuild_works_fts


def _row_to_section(row: sqlite3.Row) -> WorkSection:
    return WorkSection(
        id=row["id"],
        work_id=row["work_id"],
        section_type=row["section_type"],
        content=row["content"],
        sort_order=int(row["sort_order"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class WorkSectionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # writes ------------------------------------------------------------
    def create(
        self,
        work_id: str,
        *,
        section_type: str = SectionType.BODY.value,
        content: str = "",
        position: Optional[int] = None,
    ) -> WorkSection:
        """Create a section. ``position=None`` appends at end."""
        if section_type not in (SectionType.BODY.value, SectionType.HEADING.value):
            raise ValueError(f"unknown section type: {section_type!r}")
        new_id = str(uuid.uuid4())

        if position is None:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next "
                "FROM work_sections WHERE work_id = ?",
                (work_id,),
            ).fetchone()
            sort_order = int(row["next"])
        else:
            # Make room at the requested position.
            self._conn.execute(
                "UPDATE work_sections "
                "   SET sort_order = sort_order + 1 "
                " WHERE work_id = ? AND sort_order >= ?",
                (work_id, position),
            )
            sort_order = position

        self._conn.execute(
            "INSERT INTO work_sections (id, work_id, section_type, "
            "content, sort_order) VALUES (?, ?, ?, ?, ?)",
            (new_id, work_id, section_type, content, sort_order),
        )
        self._touch_work(work_id)
        rebuild_works_fts(self._conn, work_id)
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def update_content(
        self, section_id: str, content: str
    ) -> Optional[WorkSection]:
        cur = self._conn.execute(
            "UPDATE work_sections "
            "   SET content = ?, "
            "       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
            " WHERE id = ?",
            (content, section_id),
        )
        if cur.rowcount == 0:
            return None
        section = self.get(section_id)
        if section is not None:
            self._touch_work(section.work_id)
            rebuild_works_fts(self._conn, section.work_id)
        return section

    def set_section_type(
        self, section_id: str, section_type: str
    ) -> Optional[WorkSection]:
        if section_type not in (SectionType.BODY.value, SectionType.HEADING.value):
            raise ValueError(f"unknown section type: {section_type!r}")
        cur = self._conn.execute(
            "UPDATE work_sections "
            "   SET section_type = ?, "
            "       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
            " WHERE id = ?",
            (section_type, section_id),
        )
        if cur.rowcount == 0:
            return None
        section = self.get(section_id)
        if section is not None:
            self._touch_work(section.work_id)
        return section

    def insert_text_at(
        self, section_id: str, position: int, text: str
    ) -> Optional[WorkSection]:
        """Insert ``text`` into the section's content at ``position``.

        ``position`` is clamped to [0, len(content)]. Returns the updated
        section, or None if the section does not exist.
        """
        section = self.get(section_id)
        if section is None:
            return None
        body = section.content or ""
        pos = max(0, min(int(position), len(body)))
        new_body = body[:pos] + text + body[pos:]
        return self.update_content(section_id, new_body)

    def delete(self, section_id: str) -> bool:
        section = self.get(section_id)
        if section is None:
            return False
        cur = self._conn.execute(
            "DELETE FROM work_sections WHERE id = ?", (section_id,)
        )
        # Compact sort_order to keep it dense.
        self._compact(section.work_id)
        self._touch_work(section.work_id)
        rebuild_works_fts(self._conn, section.work_id)
        return cur.rowcount > 0

    def reorder(self, work_id: str, ordered_ids: List[str]) -> None:
        """Rewrite sort_order to exactly ``ordered_ids``.

        IDs not belonging to ``work_id`` are silently ignored. Sections
        belonging to the work that are missing from ``ordered_ids`` are
        appended after, preserving their current relative order — this
        keeps drag-drop reorder safe even when the UI passes a partial
        list.
        """
        existing = self.list_for_work(work_id)
        valid_ids = {s.id for s in existing}
        seen: set[str] = set()
        slot = 0
        for sid in ordered_ids:
            if sid in valid_ids and sid not in seen:
                self._conn.execute(
                    "UPDATE work_sections SET sort_order = ? WHERE id = ?",
                    (slot, sid),
                )
                seen.add(sid)
                slot += 1
        for s in existing:
            if s.id in seen:
                continue
            self._conn.execute(
                "UPDATE work_sections SET sort_order = ? WHERE id = ?",
                (slot, s.id),
            )
            slot += 1
        self._touch_work(work_id)

    def move(self, section_id: str, delta: int) -> Optional[WorkSection]:
        """Move a section ``delta`` slots up (negative) or down (positive)."""
        section = self.get(section_id)
        if section is None or delta == 0:
            return section
        siblings = self.list_for_work(section.work_id)
        ids = [s.id for s in siblings]
        try:
            idx = ids.index(section_id)
        except ValueError:
            return section
        new_idx = max(0, min(len(ids) - 1, idx + delta))
        if new_idx == idx:
            return section
        ids.pop(idx)
        ids.insert(new_idx, section_id)
        self.reorder(section.work_id, ids)
        return self.get(section_id)

    # reads -------------------------------------------------------------
    def get(self, section_id: str) -> Optional[WorkSection]:
        row = self._conn.execute(
            "SELECT * FROM work_sections WHERE id = ?", (section_id,)
        ).fetchone()
        return _row_to_section(row) if row is not None else None

    def list_for_work(self, work_id: str) -> List[WorkSection]:
        rows = self._conn.execute(
            "SELECT * FROM work_sections WHERE work_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (work_id,),
        ).fetchall()
        return [_row_to_section(r) for r in rows]

    def count_for_work(self, work_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM work_sections WHERE work_id = ?",
            (work_id,),
        ).fetchone()
        return int(row["n"])

    # private -----------------------------------------------------------
    def _touch_work(self, work_id: str) -> None:
        self._conn.execute(
            "UPDATE works SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
            " WHERE id = ?",
            (work_id,),
        )

    def _compact(self, work_id: str) -> None:
        rows = self._conn.execute(
            "SELECT id FROM work_sections WHERE work_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (work_id,),
        ).fetchall()
        for slot, r in enumerate(rows):
            self._conn.execute(
                "UPDATE work_sections SET sort_order = ? WHERE id = ?",
                (slot, r["id"]),
            )
