"""Persistence for reusable AI cards (M10A)."""
from __future__ import annotations

import sqlite3
import uuid
from typing import List, Optional

from writer.domain.models.ai_card import AiCard


def _row_to_card(row: sqlite3.Row) -> AiCard:
    return AiCard(
        id=row["id"],
        kind=row["kind"],
        name=row["name"],
        body=row["body"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class AiCardRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, *, kind: str, name: str, body: str) -> AiCard:
        new_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO ai_cards (id, kind, name, body) VALUES (?, ?, ?, ?)",
            (new_id, kind, name, body),
        )
        loaded = self.get(new_id)
        assert loaded is not None
        return loaded

    def update(
        self, card_id: str, *, name: str, body: str, kind: str | None = None
    ) -> Optional[AiCard]:
        if kind is None:
            self._conn.execute(
                """
                UPDATE ai_cards
                   SET name = ?, body = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (name, body, card_id),
            )
        else:
            self._conn.execute(
                """
                UPDATE ai_cards
                   SET kind = ?, name = ?, body = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                 WHERE id = ?
                """,
                (kind, name, body, card_id),
            )
        return self.get(card_id)

    def delete(self, card_id: str) -> None:
        self._conn.execute("DELETE FROM ai_cards WHERE id = ?", (card_id,))

    def get(self, card_id: str) -> Optional[AiCard]:
        row = self._conn.execute(
            "SELECT * FROM ai_cards WHERE id = ?", (card_id,)
        ).fetchone()
        return _row_to_card(row) if row else None

    def list_all(self) -> List[AiCard]:
        rows = self._conn.execute(
            "SELECT * FROM ai_cards ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_card(r) for r in rows]

    def list_by_kind(self, kind: str) -> List[AiCard]:
        rows = self._conn.execute(
            "SELECT * FROM ai_cards WHERE kind = ? ORDER BY updated_at DESC",
            (kind,),
        ).fetchall()
        return [_row_to_card(r) for r in rows]
