"""Persistence for article collections."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.collection import Collection, CollectionItem
from writer.domain.models.entry import Entry
from writer.domain.models.work import Work
from writer.storage.repositories.entry_repository import _row_to_entry
from writer.storage.repositories.work_repository import _row_to_work

VALID_COLLECTION_PROJECT_TYPES = {"general", "novel", "essay", "nonfiction"}


def _row_to_collection(row: sqlite3.Row) -> Collection:
    return Collection(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        project_type=row["project_type"] if "project_type" in row.keys() else "general",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_item(row: sqlite3.Row) -> CollectionItem:
    return CollectionItem(
        id=row["id"],
        collection_id=row["collection_id"],
        entry_id=row["entry_id"] if "entry_id" in row.keys() else row["work_id"],
        sort_order=int(row["sort_order"]),
        created_at=row["created_at"],
    )


class CollectionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # writes — collections ---------------------------------------------
    def create(
        self,
        name: str = "",
        description: str = "",
        project_type: str = "general",
    ) -> Collection:
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO collections (id, name, description, project_type) VALUES (?, ?, ?, ?)",
            (new_id, name, description, self._normalize_project_type(project_type)),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def rename(self, collection_id: str, name: str) -> Optional[Collection]:
        cur = self._conn.execute(
            "UPDATE collections SET name = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (name, collection_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get(collection_id)

    def update_description(
        self, collection_id: str, description: str
    ) -> Optional[Collection]:
        cur = self._conn.execute(
            "UPDATE collections SET description = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (description, collection_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get(collection_id)

    def update_project_type(
        self, collection_id: str, project_type: str
    ) -> Optional[Collection]:
        cur = self._conn.execute(
            "UPDATE collections SET project_type = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (self._normalize_project_type(project_type), collection_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get(collection_id)

    def delete(self, collection_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM collections WHERE id = ?", (collection_id,)
        )
        return cur.rowcount > 0

    # writes — article items -------------------------------------------
    def add_entry(
        self, collection_id: str, entry_id: str
    ) -> Optional[CollectionItem]:
        """Add ``entry_id`` to ``collection_id``, idempotent."""
        coll = self.get(collection_id)
        if coll is None:
            return None
        entry_row = self._conn.execute(
            "SELECT 1 FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if entry_row is None:
            return None
        existing = self._conn.execute(
            "SELECT * FROM collection_entries "
            "WHERE collection_id = ? AND entry_id = ?",
            (collection_id, entry_id),
        ).fetchone()
        if existing is not None:
            return _row_to_item(existing)
        next_order = self._conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n "
            "FROM collection_entries WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()["n"]
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO collection_entries "
            "(id, collection_id, entry_id, sort_order) VALUES (?, ?, ?, ?)",
            (new_id, collection_id, entry_id, int(next_order)),
        )
        self._touch_collection(collection_id)
        return _row_to_item(
            self._conn.execute(
                "SELECT * FROM collection_entries WHERE id = ?", (new_id,)
            ).fetchone()
        )

    def remove_entry(self, collection_id: str, entry_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM collection_entries "
            "WHERE collection_id = ? AND entry_id = ?",
            (collection_id, entry_id),
        )
        if cur.rowcount > 0:
            self._compact_entries(collection_id)
            self._touch_collection(collection_id)
        return cur.rowcount > 0

    def reorder_entries(
        self, collection_id: str, ordered_entry_ids: List[str]
    ) -> None:
        rows = self._conn.execute(
            "SELECT entry_id FROM collection_entries WHERE collection_id = ?",
            (collection_id,),
        ).fetchall()
        valid = {r["entry_id"] for r in rows}
        seen: set[str] = set()
        slot = 0
        for eid in ordered_entry_ids:
            if eid in valid and eid not in seen:
                self._conn.execute(
                    "UPDATE collection_entries SET sort_order = ? "
                    "WHERE collection_id = ? AND entry_id = ?",
                    (slot, collection_id, eid),
                )
                seen.add(eid)
                slot += 1
        for eid in valid - seen:
            self._conn.execute(
                "UPDATE collection_entries SET sort_order = ? "
                "WHERE collection_id = ? AND entry_id = ?",
                (slot, collection_id, eid),
            )
            slot += 1
        self._touch_collection(collection_id)

    # writes — legacy work items ---------------------------------------
    def add_work(
        self, collection_id: str, work_id: str
    ) -> Optional[CollectionItem]:
        """Add ``work_id`` to ``collection_id``, idempotent.

        If the work is already present, returns the existing item; otherwise
        creates a new item appended at the end. Returns ``None`` if the
        collection or work does not exist.
        """
        coll = self.get(collection_id)
        if coll is None:
            return None
        work_row = self._conn.execute(
            "SELECT 1 FROM works WHERE id = ?", (work_id,)
        ).fetchone()
        if work_row is None:
            return None
        existing = self._conn.execute(
            "SELECT * FROM collection_items "
            "WHERE collection_id = ? AND work_id = ?",
            (collection_id, work_id),
        ).fetchone()
        if existing is not None:
            return _row_to_item(existing)
        next_order = self._conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n "
            "FROM collection_items WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()["n"]
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO collection_items "
            "(id, collection_id, work_id, sort_order) VALUES (?, ?, ?, ?)",
            (new_id, collection_id, work_id, int(next_order)),
        )
        self._conn.execute(
            "UPDATE collections SET updated_at = "
            "strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (collection_id,),
        )
        row = self._conn.execute(
            "SELECT id, collection_id, work_id AS entry_id, sort_order, created_at "
            "FROM collection_items WHERE id = ?",
            (new_id,),
        ).fetchone()
        return _row_to_item(row)

    def remove_work(self, collection_id: str, work_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM collection_items "
            "WHERE collection_id = ? AND work_id = ?",
            (collection_id, work_id),
        )
        if cur.rowcount > 0:
            self._compact(collection_id)
            self._conn.execute(
                "UPDATE collections SET updated_at = "
                "strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (collection_id,),
            )
        return cur.rowcount > 0

    def reorder_works(
        self, collection_id: str, ordered_work_ids: List[str]
    ) -> None:
        rows = self._conn.execute(
            "SELECT work_id FROM collection_items WHERE collection_id = ?",
            (collection_id,),
        ).fetchall()
        valid = {r["work_id"] for r in rows}
        seen: set[str] = set()
        slot = 0
        for wid in ordered_work_ids:
            if wid in valid and wid not in seen:
                self._conn.execute(
                    "UPDATE collection_items SET sort_order = ? "
                    "WHERE collection_id = ? AND work_id = ?",
                    (slot, collection_id, wid),
                )
                seen.add(wid)
                slot += 1
        for wid in valid - seen:
            self._conn.execute(
                "UPDATE collection_items SET sort_order = ? "
                "WHERE collection_id = ? AND work_id = ?",
                (slot, collection_id, wid),
            )
            slot += 1
        self._touch_collection(collection_id)

    # reads -------------------------------------------------------------
    def get(self, collection_id: str) -> Optional[Collection]:
        row = self._conn.execute(
            "SELECT * FROM collections WHERE id = ?", (collection_id,)
        ).fetchone()
        return _row_to_collection(row) if row is not None else None

    def list_all(self) -> List[Collection]:
        rows = self._conn.execute(
            "SELECT * FROM collections ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
        return [_row_to_collection(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM collections"
        ).fetchone()
        return int(row["n"])

    def list_works(self, collection_id: str) -> List[Work]:
        """Return legacy works inside this collection.

        Product code should use :meth:`list_entries`.
        """
        rows = self._conn.execute(
            """
            SELECT works.* FROM collection_items
            JOIN works ON works.id = collection_items.work_id
            WHERE collection_items.collection_id = ?
            ORDER BY collection_items.sort_order ASC, collection_items.created_at ASC
            """,
            (collection_id,),
        ).fetchall()
        return [_row_to_work(r) for r in rows]

    def list_collections_containing(self, work_id: str) -> List[Collection]:
        """Return legacy collections containing a work id."""
        rows = self._conn.execute(
            """
            SELECT collections.* FROM collection_items
            JOIN collections ON collections.id = collection_items.collection_id
            WHERE collection_items.work_id = ?
            ORDER BY collections.name ASC
            """,
            (work_id,),
        ).fetchall()
        return [_row_to_collection(r) for r in rows]

    def list_entries(self, collection_id: str) -> List[Entry]:
        """Return articles inside this collection, in user-defined order."""
        rows = self._conn.execute(
            """
            SELECT entries.* FROM collection_entries
            JOIN entries ON entries.id = collection_entries.entry_id
            WHERE collection_entries.collection_id = ?
            ORDER BY collection_entries.sort_order ASC,
                     collection_entries.created_at ASC
            """,
            (collection_id,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def list_entry_items(self, collection_id: str) -> List[CollectionItem]:
        rows = self._conn.execute(
            "SELECT * FROM collection_entries WHERE collection_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (collection_id,),
        ).fetchall()
        return [_row_to_item(r) for r in rows]

    def list_collections_containing_entry(self, entry_id: str) -> List[Collection]:
        rows = self._conn.execute(
            """
            SELECT collections.* FROM collection_entries
            JOIN collections ON collections.id = collection_entries.collection_id
            WHERE collection_entries.entry_id = ?
            ORDER BY collections.name ASC
            """,
            (entry_id,),
        ).fetchall()
        return [_row_to_collection(r) for r in rows]

    # private -----------------------------------------------------------
    def _compact_entries(self, collection_id: str) -> None:
        rows = self._conn.execute(
            "SELECT id FROM collection_entries WHERE collection_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (collection_id,),
        ).fetchall()
        for slot, r in enumerate(rows):
            self._conn.execute(
                "UPDATE collection_entries SET sort_order = ? WHERE id = ?",
                (slot, r["id"]),
            )

    def _compact(self, collection_id: str) -> None:
        rows = self._conn.execute(
            "SELECT id FROM collection_items WHERE collection_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (collection_id,),
        ).fetchall()
        for slot, r in enumerate(rows):
            self._conn.execute(
                "UPDATE collection_items SET sort_order = ? WHERE id = ?",
                (slot, r["id"]),
            )

    def _touch_collection(self, collection_id: str) -> None:
        self._conn.execute(
            "UPDATE collections SET updated_at = "
            "strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (collection_id,),
        )

    @staticmethod
    def _normalize_project_type(value: str) -> str:
        clean = (value or "general").strip()
        if clean not in VALID_COLLECTION_PROJECT_TYPES:
            raise ValueError(f"Unsupported collection project type: {value}")
        return clean
