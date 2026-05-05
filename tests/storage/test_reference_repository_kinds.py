"""Tests for typed reference passages (M-RefTypes)."""
from __future__ import annotations

import sqlite3
import uuid

import pytest

from writer.domain.models.reference_passage import (
    REFERENCE_KIND_CHARACTER,
    REFERENCE_KIND_EXCERPT,
    REFERENCE_KIND_LOCATION,
    REFERENCE_KIND_SETTING,
)
from writer.storage.database import initialize_schema, open_and_initialize
from writer.storage.repositories.reference_repository import ReferenceRepository


@pytest.fixture()
def repo(tmp_path):
    conn = open_and_initialize(tmp_path / "writer.db")
    try:
        yield ReferenceRepository(conn)
    finally:
        conn.close()


def test_create_with_kind_round_trips(repo):
    p = repo.create(
        source_title="Aragorn",
        content="Heir of Isildur.",
        kind=REFERENCE_KIND_CHARACTER,
    )
    loaded = repo.get(p.id)
    assert loaded is not None
    assert loaded.kind == REFERENCE_KIND_CHARACTER


def test_create_default_kind_is_excerpt(repo):
    p = repo.create(source_title="t", content="c")
    assert p.kind == REFERENCE_KIND_EXCERPT


def test_update_changes_kind(repo):
    p = repo.create(source_title="t", content="c")
    updated = repo.update(
        p.id,
        source_title="t",
        content="c",
        kind=REFERENCE_KIND_LOCATION,
    )
    assert updated is not None
    assert updated.kind == REFERENCE_KIND_LOCATION


def test_list_by_kind_filters(repo):
    a = repo.create(source_title="A", content="x", kind=REFERENCE_KIND_CHARACTER)
    b = repo.create(source_title="B", content="x", kind=REFERENCE_KIND_SETTING)
    c = repo.create(source_title="C", content="x", kind=REFERENCE_KIND_CHARACTER)

    chars = repo.list_by_kind(REFERENCE_KIND_CHARACTER)
    settings = repo.list_by_kind(REFERENCE_KIND_SETTING)
    ids_chars = {p.id for p in chars}
    ids_settings = {p.id for p in settings}
    assert ids_chars == {a.id, c.id}
    assert ids_settings == {b.id}


def test_unknown_kind_normalises_to_excerpt(repo):
    p = repo.create(source_title="t", content="c", kind="bogus")
    assert p.kind == REFERENCE_KIND_EXCERPT


def test_migration_adds_kind_to_legacy_db(tmp_path):
    """Open a DB with the pre-typing reference_passages schema, then run
    initialize_schema and verify the kind column is added with default."""
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db, isolation_level=None)
    conn.row_factory = sqlite3.Row
    # Build a *legacy* reference_passages table without ``kind``.
    conn.execute(
        """
        CREATE TABLE reference_passages (
            id            TEXT PRIMARY KEY,
            source_title  TEXT NOT NULL,
            source_author TEXT NOT NULL DEFAULT '',
            content       TEXT NOT NULL,
            tags          TEXT NOT NULL DEFAULT '',
            created_at    TEXT NOT NULL DEFAULT
                (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at    TEXT NOT NULL DEFAULT
                (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    legacy_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO reference_passages (id, source_title, content) VALUES (?, ?, ?)",
        (legacy_id, "old quote", "legacy body"),
    )
    conn.close()

    conn2 = open_and_initialize(db)
    try:
        cols = {r["name"] for r in conn2.execute("PRAGMA table_info(reference_passages)")}
        assert "kind" in cols
        repo = ReferenceRepository(conn2)
        loaded = repo.get(legacy_id)
        assert loaded is not None
        assert loaded.kind == REFERENCE_KIND_EXCERPT
    finally:
        conn2.close()
