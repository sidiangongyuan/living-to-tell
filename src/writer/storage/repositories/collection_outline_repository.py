"""Persistence for collection-level project outlines."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.collection_outline import CollectionOutlineItem
from writer.storage.repositories.entry_repository import serialize_tags


VALID_OUTLINE_TYPES = {"part", "chapter", "scene", "note"}
VALID_OUTLINE_STATUSES = {"idea", "drafting", "revising", "done", "parked"}


def _row_to_outline_item(row: sqlite3.Row) -> CollectionOutlineItem:
    return CollectionOutlineItem(
        id=row["id"],
        collection_id=row["collection_id"],
        parent_id=row["parent_id"],
        entry_id=row["entry_id"],
        title=row["title"],
        item_type=row["item_type"],
        status=row["status"],
        summary=row["summary"],
        notes=row["notes"],
        pov=row["pov"],
        setting=row["setting"],
        timeline=row["timeline"],
        tags_text=row["tags_text"],
        target_word_count=row["target_word_count"],
        sort_order=int(row["sort_order"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class CollectionOutlineRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        collection_id: str,
        *,
        title: str = "",
        item_type: str = "scene",
        status: str = "idea",
        summary: str = "",
        notes: str = "",
        parent_id: Optional[str] = None,
        entry_id: Optional[str] = None,
        pov: str = "",
        setting: str = "",
        timeline: str = "",
        tags: list[str] | None = None,
        target_word_count: Optional[int] = None,
    ) -> Optional[CollectionOutlineItem]:
        if not self._collection_exists(collection_id):
            return None
        self._validate_item(collection_id, parent_id=parent_id, entry_id=entry_id)
        clean_type = self._normalize_type(item_type)
        clean_status = self._normalize_status(status)
        next_order = self._next_order(collection_id)
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO collection_outline_items (
                id, collection_id, parent_id, entry_id, title, item_type, status,
                summary, notes, pov, setting, timeline, tags_text,
                target_word_count, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                collection_id,
                parent_id,
                entry_id,
                title.strip() or "未命名大纲",
                clean_type,
                clean_status,
                summary,
                notes,
                pov,
                setting,
                timeline,
                serialize_tags(tags or []),
                target_word_count,
                next_order,
            ),
        )
        self._touch_collection(collection_id)
        return self.get(new_id)

    def update(
        self,
        item_id: str,
        *,
        title: str,
        item_type: str,
        status: str,
        summary: str = "",
        notes: str = "",
        parent_id: Optional[str] = None,
        entry_id: Optional[str] = None,
        pov: str = "",
        setting: str = "",
        timeline: str = "",
        tags: list[str] | None = None,
        target_word_count: Optional[int] = None,
    ) -> Optional[CollectionOutlineItem]:
        existing = self.get(item_id)
        if existing is None:
            return None
        self._validate_item(
            existing.collection_id,
            parent_id=parent_id,
            entry_id=entry_id,
            current_id=item_id,
        )
        self._conn.execute(
            """
            UPDATE collection_outline_items
               SET parent_id = ?,
                   entry_id = ?,
                   title = ?,
                   item_type = ?,
                   status = ?,
                   summary = ?,
                   notes = ?,
                   pov = ?,
                   setting = ?,
                   timeline = ?,
                   tags_text = ?,
                   target_word_count = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
                parent_id,
                entry_id,
                title.strip() or "未命名大纲",
                self._normalize_type(item_type),
                self._normalize_status(status),
                summary,
                notes,
                pov,
                setting,
                timeline,
                serialize_tags(tags or []),
                target_word_count,
                item_id,
            ),
        )
        self._touch_collection(existing.collection_id)
        return self.get(item_id)

    def delete(self, item_id: str, *, collection_id: Optional[str] = None) -> bool:
        existing = self.get(item_id)
        if existing is None:
            return False
        if collection_id is not None and existing.collection_id != collection_id:
            return False
        # Keep children visible instead of deleting the user's planning notes.
        self._conn.execute(
            "UPDATE collection_outline_items SET parent_id = NULL WHERE parent_id = ?",
            (item_id,),
        )
        cur = self._conn.execute(
            "DELETE FROM collection_outline_items WHERE id = ?",
            (item_id,),
        )
        if cur.rowcount > 0:
            self._compact(existing.collection_id)
            self._touch_collection(existing.collection_id)
        return cur.rowcount > 0

    def get(self, item_id: str) -> Optional[CollectionOutlineItem]:
        row = self._conn.execute(
            "SELECT * FROM collection_outline_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        return _row_to_outline_item(row) if row is not None else None

    def list_for_collection(self, collection_id: str) -> List[CollectionOutlineItem]:
        rows = self._conn.execute(
            """
            SELECT * FROM collection_outline_items
             WHERE collection_id = ?
             ORDER BY sort_order ASC, created_at ASC
            """,
            (collection_id,),
        ).fetchall()
        return [_row_to_outline_item(row) for row in rows]

    def reorder(self, collection_id: str, ordered_ids: list[str]) -> list[CollectionOutlineItem]:
        existing = self.list_for_collection(collection_id)
        valid = {item.id for item in existing}
        seen: set[str] = set()
        slot = 0
        for item_id in ordered_ids:
            if item_id in valid and item_id not in seen:
                self._conn.execute(
                    """
                    UPDATE collection_outline_items
                       SET sort_order = ?,
                           updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                     WHERE id = ?
                    """,
                    (slot, item_id),
                )
                seen.add(item_id)
                slot += 1
        for item in existing:
            if item.id in seen:
                continue
            self._conn.execute(
                """
                UPDATE collection_outline_items
                   SET sort_order = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (slot, item.id),
            )
            slot += 1
        self._touch_collection(collection_id)
        return self.list_for_collection(collection_id)

    def _collection_exists(self, collection_id: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM collections WHERE id = ?",
            (collection_id,),
        ).fetchone() is not None

    def _validate_item(
        self,
        collection_id: str,
        *,
        parent_id: Optional[str],
        entry_id: Optional[str],
        current_id: Optional[str] = None,
    ) -> None:
        if parent_id is not None:
            if parent_id == current_id:
                raise ValueError("Outline item cannot be its own parent")
            parent = self.get(parent_id)
            if parent is None or parent.collection_id != collection_id:
                raise ValueError("Parent outline item is not in this collection")
        if entry_id is not None:
            entry = self._conn.execute(
                "SELECT 1 FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if entry is None:
                raise ValueError("Linked article not found")

    def _next_order(self, collection_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order
              FROM collection_outline_items
             WHERE collection_id = ?
            """,
            (collection_id,),
        ).fetchone()
        return int(row["next_order"])

    def _compact(self, collection_id: str) -> None:
        rows = self._conn.execute(
            """
            SELECT id FROM collection_outline_items
             WHERE collection_id = ?
             ORDER BY sort_order ASC, created_at ASC
            """,
            (collection_id,),
        ).fetchall()
        for slot, row in enumerate(rows):
            self._conn.execute(
                "UPDATE collection_outline_items SET sort_order = ? WHERE id = ?",
                (slot, row["id"]),
            )

    def _touch_collection(self, collection_id: str) -> None:
        self._conn.execute(
            """
            UPDATE collections
               SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (collection_id,),
        )

    @staticmethod
    def _normalize_type(value: str) -> str:
        clean = (value or "scene").strip()
        if clean not in VALID_OUTLINE_TYPES:
            raise ValueError(f"Unsupported outline item type: {value}")
        return clean

    @staticmethod
    def _normalize_status(value: str) -> str:
        clean = (value or "idea").strip()
        if clean not in VALID_OUTLINE_STATUSES:
            raise ValueError(f"Unsupported outline status: {value}")
        return clean
