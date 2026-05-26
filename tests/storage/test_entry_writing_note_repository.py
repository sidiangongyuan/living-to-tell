"""Tests for EntryWritingNoteRepository and note schema bootstrap."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from writer.domain.models.entry_writing_note import (
    NOTE_STATUS_DONE,
    NOTE_STATUS_OPEN,
)
from writer.storage.database import initialize_schema, open_and_initialize
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.entry_writing_note_repository import (
    EntryWritingNoteRepository,
)


@pytest.fixture()
def conn(tmp_path: Path):
    c = open_and_initialize(tmp_path / "writer.db")
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def entries(conn) -> EntryRepository:
    return EntryRepository(conn)


@pytest.fixture()
def repo(conn) -> EntryWritingNoteRepository:
    return EntryWritingNoteRepository(conn)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _indexes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA index_list({table})")}


def test_create_get_update_and_delete(
    repo: EntryWritingNoteRepository,
    entries: EntryRepository,
) -> None:
    entry = entries.create(title="Fragment", body="Draft")

    created = repo.create(entry_id=entry.id, body="  rough idea  ", pinned=True)

    assert created.id
    assert created.entry_id == entry.id
    assert created.body == "rough idea"
    assert created.status == NOTE_STATUS_OPEN
    assert created.pinned is True
    assert created.sort_order == 0
    assert created.created_at and created.updated_at
    assert repo.get(created.id) == created

    time.sleep(0.005)
    updated = repo.update_body(created.id, "  revised note  ")

    assert updated is not None
    assert updated.body == "revised note"
    assert updated.updated_at > created.updated_at

    repo.delete(created.id)

    assert repo.get(created.id) is None


def test_list_for_entry_orders_open_pinned_then_sort_order(
    repo: EntryWritingNoteRepository,
    entries: EntryRepository,
) -> None:
    entry = entries.create(title="Fragment")
    other_entry = entries.create(title="Other")

    first = repo.create(entry_id=entry.id, body="first")
    second = repo.create(entry_id=entry.id, body="second")
    third = repo.create(entry_id=entry.id, body="third", pinned=True)
    fourth = repo.create(entry_id=entry.id, body="fourth")
    repo.create(entry_id=other_entry.id, body="foreign", pinned=True)

    pinned_second = repo.set_pinned(second.id, True)
    done_fourth = repo.set_done(fourth.id, True)

    assert pinned_second is not None
    assert pinned_second.pinned is True
    assert done_fourth is not None
    assert done_fourth.status == NOTE_STATUS_DONE

    assert [
        first.sort_order,
        second.sort_order,
        third.sort_order,
        fourth.sort_order,
    ] == [0, 1, 2, 3]
    assert [note.id for note in repo.list_for_entry(entry.id)] == [
        second.id,
        third.id,
        first.id,
    ]
    assert [note.id for note in repo.list_for_entry(entry.id, include_done=True)] == [
        second.id,
        third.id,
        first.id,
        fourth.id,
    ]


def test_count_open_for_entry_tracks_done_and_reopened_notes(
    repo: EntryWritingNoteRepository,
    entries: EntryRepository,
) -> None:
    entry = entries.create()
    other_entry = entries.create()
    first = repo.create(entry_id=entry.id, body="first")
    repo.create(entry_id=entry.id, body="second")
    repo.create(entry_id=other_entry.id, body="other")

    assert repo.count_open_for_entry(entry.id) == 2
    assert repo.count_open_for_entry(other_entry.id) == 1

    done = repo.set_done(first.id, True)

    assert done is not None
    assert done.status == NOTE_STATUS_DONE
    assert done.completed_at is not None
    assert repo.count_open_for_entry(entry.id) == 1

    reopened = repo.set_done(first.id, False)

    assert reopened is not None
    assert reopened.status == NOTE_STATUS_OPEN
    assert reopened.completed_at is None
    assert repo.count_open_for_entry(entry.id) == 2


def test_delete_entry_cascades_writing_notes(
    repo: EntryWritingNoteRepository,
    entries: EntryRepository,
) -> None:
    entry = entries.create(title="Fragment")
    first = repo.create(entry_id=entry.id, body="first")
    second = repo.create(entry_id=entry.id, body="second")

    assert [note.id for note in repo.list_for_entry(entry.id, include_done=True)] == [
        first.id,
        second.id,
    ]

    assert entries.delete(entry.id) is True
    assert repo.get(first.id) is None
    assert repo.get(second.id) is None
    assert repo.list_for_entry(entry.id, include_done=True) == []
    assert repo.count_open_for_entry(entry.id) == 0


def test_initialize_schema_adds_entry_writing_notes_table_to_legacy_db(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE entries (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '',
            body        TEXT NOT NULL DEFAULT '',
            entry_type  TEXT NOT NULL DEFAULT 'fragment',
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        INSERT INTO entries (id, title, body) VALUES ('e1', 'Old', 'existing row');
        """
    )
    conn.commit()
    conn.close()

    upgraded = open_and_initialize(db_path)
    try:
        assert {
            "id",
            "entry_id",
            "body",
            "status",
            "pinned",
            "sort_order",
            "created_at",
            "updated_at",
            "completed_at",
        }.issubset(_columns(upgraded, "entry_writing_notes"))
        assert "idx_entry_writing_notes_entry" in _indexes(
            upgraded, "entry_writing_notes"
        )

        note = EntryWritingNoteRepository(upgraded).create(
            entry_id="e1",
            body="migrated note",
        )

        assert note.entry_id == "e1"
        assert note.body == "migrated note"
    finally:
        upgraded.close()


def test_initialize_schema_for_entry_writing_notes_is_idempotent(
    tmp_path: Path,
) -> None:
    conn = open_and_initialize(tmp_path / "writer.db")
    try:
        entries = EntryRepository(conn)
        repo = EntryWritingNoteRepository(conn)
        entry = entries.create()
        note = repo.create(entry_id=entry.id, body="keep me")

        initialize_schema(conn)
        initialize_schema(conn)

        assert "idx_entry_writing_notes_entry" in _indexes(
            conn, "entry_writing_notes"
        )
        assert repo.get(note.id) is not None
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM entry_writing_notes WHERE id = ?",
            (note.id,),
        ).fetchone()
        assert row["n"] == 1
    finally:
        conn.close()
