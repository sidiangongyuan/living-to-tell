"""Persistence for collection-level project outlines."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.collection_outline import CollectionOutlineItem
from writer.storage.repositories.entry_repository import serialize_tags


VALID_OUTLINE_TYPES = {"part", "chapter", "scene", "note"}
VALID_OUTLINE_STATUSES = {"idea", "drafting", "revising", "done", "parked"}
CONTAINER_TYPES = {"part", "chapter"}


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
        board_sort_order=int(row["board_sort_order"]),
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
        clean_type = self._normalize_type(item_type)
        clean_status = self._normalize_status(status)
        self._validate_item(
            collection_id,
            item_type=clean_type,
            parent_id=parent_id,
            entry_id=entry_id,
        )
        next_order = self._next_order(collection_id)
        next_board_order = self._next_board_order(collection_id, clean_status)
        new_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO collection_outline_items (
                id, collection_id, parent_id, entry_id, title, item_type, status,
                summary, notes, pov, setting, timeline, tags_text,
                target_word_count, sort_order, board_sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                next_board_order,
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
        clean_type = self._normalize_type(item_type)
        clean_status = self._normalize_status(status)
        next_board_order = existing.board_sort_order
        if clean_status != existing.status:
            next_board_order = self._next_board_order(existing.collection_id, clean_status)
        structural_change = (
            clean_type != existing.item_type
            or parent_id != existing.parent_id
            or entry_id != existing.entry_id
        )
        self._validate_item(
            existing.collection_id,
            item_type=clean_type,
            parent_id=parent_id,
            entry_id=entry_id,
            current_id=item_id,
            enforce_structure=structural_change,
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
                   board_sort_order = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (
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
                next_board_order,
                item_id,
            ),
        )
        if clean_status != existing.status:
            self._compact_board_status(existing.collection_id, existing.status)
        self._touch_collection(existing.collection_id)
        return self.get(item_id)

    def update_status(
        self,
        item_id: str,
        status: str,
        *,
        collection_id: Optional[str] = None,
    ) -> Optional[CollectionOutlineItem]:
        existing = self.get(item_id)
        if existing is None or (
            collection_id is not None and existing.collection_id != collection_id
        ):
            return None
        clean_status = self._normalize_status(status)
        next_board_order = existing.board_sort_order
        if clean_status != existing.status:
            next_board_order = self._next_board_order(existing.collection_id, clean_status)
        self._conn.execute(
            """
            UPDATE collection_outline_items
               SET status = ?,
                   board_sort_order = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
             WHERE id = ?
            """,
            (clean_status, next_board_order, item_id),
        )
        if clean_status != existing.status:
            self._compact_board_status(existing.collection_id, existing.status)
        self._touch_collection(existing.collection_id)
        return self.get(item_id)

    def move_board_position(
        self,
        item_id: str,
        *,
        status: str,
        target_index: int,
        collection_id: Optional[str] = None,
    ) -> list[CollectionOutlineItem]:
        if target_index < 0:
            raise ValueError("看板位置无效。")
        existing = self.get(item_id)
        if existing is None or (
            collection_id is not None and existing.collection_id != collection_id
        ):
            return []
        clean_status = self._normalize_status(status)
        source_ids = self._board_ids(existing.collection_id, existing.status)
        from_index = source_ids.index(existing.id)
        if clean_status == existing.status:
            raw_target = min(target_index, len(source_ids))
            adjusted_target = raw_target
            if raw_target > from_index:
                adjusted_target -= 1
            reordered = [row_id for row_id in source_ids if row_id != existing.id]
            adjusted_target = max(0, min(adjusted_target, len(reordered)))
            reordered.insert(adjusted_target, existing.id)
            if reordered == source_ids:
                return self.list_for_collection(existing.collection_id)
            self._rewrite_board_ids(
                existing.collection_id,
                clean_status,
                reordered,
                moved_item_id=existing.id,
            )
            self._touch_collection(existing.collection_id)
            return self.list_for_collection(existing.collection_id)

        dest_ids = self._board_ids(existing.collection_id, clean_status)
        insert_at = max(0, min(target_index, len(dest_ids)))
        reordered_dest = list(dest_ids)
        reordered_dest.insert(insert_at, existing.id)
        reordered_source = [row_id for row_id in source_ids if row_id != existing.id]
        self._rewrite_board_ids(existing.collection_id, existing.status, reordered_source)
        self._rewrite_board_ids(
            existing.collection_id,
            clean_status,
            reordered_dest,
            moved_item_id=existing.id,
        )
        self._touch_collection(existing.collection_id)
        return self.list_for_collection(existing.collection_id)

    def make_container(
        self,
        item_id: str,
        *,
        collection_id: Optional[str] = None,
    ) -> tuple[Optional[CollectionOutlineItem], Optional[CollectionOutlineItem], bool]:
        """Turn a linked chapter into a container without losing its article.

        The linked article moves to a new first content child. Calling this on an
        already-unlinked chapter is idempotent.
        """
        existing = self.get(item_id)
        if existing is None or (
            collection_id is not None and existing.collection_id != collection_id
        ):
            return None, None, False
        if existing.item_type != "chapter":
            raise ValueError("只有章节可以拆成子项。")
        if existing.entry_id is None:
            return existing, None, False

        entry = self._conn.execute(
            "SELECT title FROM entries WHERE id = ?",
            (existing.entry_id,),
        ).fetchone()
        if entry is None:
            raise ValueError("关联的文章已不存在，请先整理这个结构节点。")

        started_transaction = not self._conn.in_transaction
        savepoint = f"outline_make_container_{uuid.uuid4().hex}"
        try:
            if started_transaction:
                self._conn.execute("BEGIN IMMEDIATE")
            else:
                self._conn.execute(f"SAVEPOINT {savepoint}")

            self._conn.execute(
                """
                UPDATE collection_outline_items
                   SET sort_order = sort_order + 1
                 WHERE collection_id = ? AND sort_order > ?
                """,
                (existing.collection_id, existing.sort_order),
            )
            self._conn.execute(
                """
                UPDATE collection_outline_items
                   SET entry_id = NULL,
                       target_word_count = NULL,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (existing.id,),
            )
            child_id = str(uuid.uuid4())
            self._conn.execute(
                """
                INSERT INTO collection_outline_items (
                    id, collection_id, parent_id, entry_id, title, item_type,
                    status, summary, notes, pov, setting, timeline, tags_text,
                    target_word_count, sort_order, board_sort_order
                ) VALUES (?, ?, ?, ?, ?, 'scene', ?, '', '', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    child_id,
                    existing.collection_id,
                    existing.id,
                    existing.entry_id,
                    str(entry["title"] or existing.title or "未命名文章"),
                    existing.status,
                    existing.pov,
                    existing.setting,
                    existing.timeline,
                    existing.tags_text,
                    existing.target_word_count,
                    existing.sort_order + 1,
                    self._next_board_order(existing.collection_id, existing.status),
                ),
            )
            self._touch_collection(existing.collection_id)
            if started_transaction:
                self._conn.execute("COMMIT")
            else:
                self._conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        except BaseException:
            if started_transaction and self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
            elif not started_transaction:
                self._conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self._conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise

        return self.get(existing.id), self.get(child_id), True

    def delete(self, item_id: str, *, collection_id: Optional[str] = None) -> bool:
        existing = self.get(item_id)
        if existing is None:
            return False
        if collection_id is not None and existing.collection_id != collection_id:
            return False
        children = self._children(item_id)
        for child in children:
            if not self._is_valid_parent_pair(child.item_type, existing.parent_id):
                raise ValueError("这个节点仍有子项。请先移动或删除子项，再删除该节点。")
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
            self._compact_board_status(existing.collection_id, existing.status)
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
        item_type: str,
        parent_id: Optional[str],
        entry_id: Optional[str],
        current_id: Optional[str] = None,
        enforce_structure: bool = True,
    ) -> None:
        parent: Optional[CollectionOutlineItem] = None
        if parent_id is not None:
            if parent_id == current_id:
                raise ValueError("结构节点不能把自己设为上级。")
            parent = self.get(parent_id)
            if parent is None or parent.collection_id != collection_id:
                raise ValueError("所选上级节点不属于当前作品集。")
            if current_id is not None and self._is_descendant(
                parent_id,
                descendant_of=current_id,
            ):
                raise ValueError("结构节点不能移动到自己的子项下面。")
        if entry_id is not None:
            entry = self._conn.execute(
                "SELECT 1 FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if entry is None:
                raise ValueError("关联的文章不存在，请重新选择。")
            duplicate = self._conn.execute(
                """
                SELECT id FROM collection_outline_items
                 WHERE collection_id = ? AND entry_id = ?
                   AND (? IS NULL OR id != ?)
                 LIMIT 1
                """,
                (collection_id, entry_id, current_id, current_id),
            ).fetchone()
            if duplicate is not None:
                raise ValueError("这篇文章已经放在当前作品集的其他结构位置。")

        if not enforce_structure:
            return
        if not self._is_valid_parent_pair(item_type, parent_id, parent):
            if parent_id is None:
                raise ValueError("顶层只能放分部或章节。")
            raise ValueError("这个父子层级不成立，请按分部 → 章节 → 正文子项组织。")
        if item_type in {"part", "note"} and entry_id is not None:
            raise ValueError("分部和笔记不能关联正文。")
        if parent is not None and parent.entry_id is not None:
            raise ValueError("这个章节已直接关联正文；请先将它拆成子项。")

        children = self._children(current_id) if current_id else []
        if children and item_type not in CONTAINER_TYPES:
            raise ValueError("正文子项和笔记不能继续包含子项。")
        if children and entry_id is not None:
            raise ValueError("作为容器的章节不能同时直接关联正文。")
        if children:
            allowed_children = {"chapter", "note"} if item_type == "part" else {"scene", "note"}
            if any(child.item_type not in allowed_children for child in children):
                raise ValueError("现有子项与目标类型不兼容，请先整理子项。")

    def _children(self, item_id: Optional[str]) -> list[CollectionOutlineItem]:
        if not item_id:
            return []
        rows = self._conn.execute(
            """
            SELECT * FROM collection_outline_items
             WHERE parent_id = ?
             ORDER BY sort_order ASC, created_at ASC
            """,
            (item_id,),
        ).fetchall()
        return [_row_to_outline_item(row) for row in rows]

    def _is_valid_parent_pair(
        self,
        item_type: str,
        parent_id: Optional[str],
        parent: Optional[CollectionOutlineItem] = None,
    ) -> bool:
        if parent_id is None:
            return item_type in {"part", "chapter"}
        resolved = parent or self.get(parent_id)
        if resolved is None:
            return False
        if resolved.item_type == "part":
            return item_type in {"chapter", "note"}
        if resolved.item_type == "chapter":
            return item_type in {"scene", "note"}
        return False

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

    def _next_board_order(self, collection_id: str, status: str) -> int:
        row = self._conn.execute(
            """
            SELECT COALESCE(MAX(board_sort_order), -1) + 1 AS next_order
              FROM collection_outline_items
             WHERE collection_id = ? AND status = ?
            """,
            (collection_id, status),
        ).fetchone()
        return int(row["next_order"])

    def _board_ids(self, collection_id: str, status: str) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT id FROM collection_outline_items
             WHERE collection_id = ? AND status = ?
             ORDER BY board_sort_order ASC, sort_order ASC, created_at ASC, id ASC
            """,
            (collection_id, status),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    def _is_descendant(self, item_id: str, *, descendant_of: str) -> bool:
        current = self.get(item_id)
        seen: set[str] = set()
        while current is not None and current.parent_id is not None:
            if current.parent_id == descendant_of:
                return True
            if current.parent_id in seen:
                return True
            seen.add(current.parent_id)
            current = self.get(current.parent_id)
        return False

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

    def _compact_board_status(self, collection_id: str, status: str) -> None:
        for slot, item_id in enumerate(self._board_ids(collection_id, status)):
            self._conn.execute(
                "UPDATE collection_outline_items SET board_sort_order = ? WHERE id = ?",
                (slot, item_id),
            )

    def _rewrite_board_ids(
        self,
        collection_id: str,
        status: str,
        ordered_ids: list[str],
        *,
        moved_item_id: Optional[str] = None,
    ) -> None:
        for slot, current_id in enumerate(ordered_ids):
            if current_id == moved_item_id:
                self._conn.execute(
                    """
                    UPDATE collection_outline_items
                       SET status = ?,
                           board_sort_order = ?,
                           updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                     WHERE id = ? AND collection_id = ?
                    """,
                    (status, slot, current_id, collection_id),
                )
                continue
            self._conn.execute(
                """
                UPDATE collection_outline_items
                   SET board_sort_order = ?
                 WHERE id = ? AND collection_id = ? AND status = ?
                """,
                (slot, current_id, collection_id, status),
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
            raise ValueError("不支持这个结构节点类型。")
        return clean

    @staticmethod
    def _normalize_status(value: str) -> str:
        clean = (value or "idea").strip()
        if clean not in VALID_OUTLINE_STATUSES:
            raise ValueError("不支持这个结构状态。")
        return clean
