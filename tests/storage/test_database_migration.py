"""Regression tests for M5 schema migrations.

Protects two scenarios that used to break:
  * a pre-M5 database (``entries`` table without ``project_id`` /
    ``chapter_id`` columns) must upgrade cleanly when the app boots,
  * a partially-upgraded database (only one of the new columns present)
    must still converge to the full shape.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from writer.storage.database import (
    _ensure_post_migration_indexes,
    _migrate,
    initialize_schema,
    open_and_initialize,
    open_connection,
)


def _make_pre_m5_db(path: Path) -> None:
    """Build the M2-era ``entries`` table (no project_id / chapter_id)."""
    conn = sqlite3.connect(path)
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


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _indexes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA index_list({table})")}


def test_pre_m5_database_upgrades_without_error(tmp_path: Path) -> None:
    db_path = tmp_path / "writer.db"
    _make_pre_m5_db(db_path)

    # This is the call that used to raise "no such column: project_id"
    # because idx_entries_project was baked into schema.sql before
    # _migrate() ran.
    conn = open_and_initialize(db_path)
    try:
        cols = _columns(conn, "entries")
        assert "project_id" in cols
        assert "chapter_id" in cols

        idx_names = _indexes(conn, "entries")
        assert "idx_entries_project" in idx_names
        assert "idx_entries_chapter" in idx_names

        # Legacy row must still be present and readable with the new columns.
        row = conn.execute(
            "SELECT id, project_id, chapter_id FROM entries WHERE id = ?",
            ("e1",),
        ).fetchone()
        assert row["id"] == "e1"
        assert row["project_id"] is None
        assert row["chapter_id"] is None
    finally:
        conn.close()


def test_pre_m5_database_supports_full_m5_flow_after_upgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "writer.db"
    _make_pre_m5_db(db_path)
    conn = open_and_initialize(db_path)
    try:
        from writer.storage.repositories.chapter_repository import ChapterRepository
        from writer.storage.repositories.entry_repository import EntryRepository
        from writer.storage.repositories.project_repository import ProjectRepository

        projects = ProjectRepository(conn)
        chapters = ChapterRepository(conn)
        entries = EntryRepository(conn)

        project = projects.create("Book")
        chapter = chapters.create(project.id, "Ch1")
        entry = entries.create(title="t", body="b")
        entries.assign_to_project(entry.id, project.id)
        entries.assign_to_chapter(entry.id, chapter.id)

        reloaded = entries.get(entry.id)
        assert reloaded.project_id == project.id
        assert reloaded.chapter_id == chapter.id
    finally:
        conn.close()


def test_partially_upgraded_database_converges(tmp_path: Path) -> None:
    """Only ``project_id`` has been added; ``chapter_id`` is still missing."""
    db_path = tmp_path / "writer.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE entries (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '',
            body        TEXT NOT NULL DEFAULT '',
            entry_type  TEXT NOT NULL DEFAULT 'fragment',
            project_id  TEXT,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        """
    )
    conn.commit()
    conn.close()

    conn = open_and_initialize(db_path)
    try:
        cols = _columns(conn, "entries")
        assert {"project_id", "chapter_id"}.issubset(cols)

        idx_names = _indexes(conn, "entries")
        assert "idx_entries_project" in idx_names
        assert "idx_entries_chapter" in idx_names
    finally:
        conn.close()


def test_initialize_schema_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "writer.db"
    conn = open_and_initialize(db_path)
    try:
        # Running initialize_schema again should not raise or duplicate
        # anything.
        initialize_schema(conn)
        initialize_schema(conn)
        idx_names = _indexes(conn, "entries")
        assert "idx_entries_project" in idx_names
        assert "idx_entries_chapter" in idx_names
    finally:
        conn.close()


def test_ensure_post_migration_indexes_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "writer.db"
    conn = open_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE entries (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                chapter_id TEXT,
                sequence_order INTEGER
            );
            """
        )
        _ensure_post_migration_indexes(conn)
        _ensure_post_migration_indexes(conn)
        idx_names = _indexes(conn, "entries")
        assert "idx_entries_project" in idx_names
        assert "idx_entries_chapter" in idx_names
        assert "idx_entries_project_container_order" in idx_names
    finally:
        conn.close()


def test_pre_m5_database_backfills_sequence_order(tmp_path: Path) -> None:
    """A pre-M5 entries row that already carries project/chapter data
    (e.g. migrated from a hand-crafted M5B snapshot) must be given a
    contiguous sequence_order per container during upgrade."""
    db_path = tmp_path / "writer.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE entries (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '',
            body        TEXT NOT NULL DEFAULT '',
            entry_type  TEXT NOT NULL DEFAULT 'fragment',
            project_id  TEXT,
            chapter_id  TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        -- Mirror the pre-M5 FTS shadow so migration UPDATEs don't corrupt
        -- the external-content index when triggers fire.
        CREATE VIRTUAL TABLE entries_fts USING fts5(
            title, body,
            content='entries',
            content_rowid='rowid',
            tokenize='unicode61'
        );
        CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, title, body)
            VALUES (new.rowid, new.title, new.body);
        END;
        CREATE TRIGGER entries_ad AFTER DELETE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, title, body)
            VALUES ('delete', old.rowid, old.title, old.body);
        END;
        CREATE TRIGGER entries_au AFTER UPDATE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, title, body)
            VALUES ('delete', old.rowid, old.title, old.body);
            INSERT INTO entries_fts(rowid, title, body)
            VALUES (new.rowid, new.title, new.body);
        END;

        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '2024-01-01',
            updated_at TEXT NOT NULL DEFAULT '2024-01-01'
        );
        CREATE TABLE chapters (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT '2024-01-01',
            updated_at TEXT NOT NULL DEFAULT '2024-01-01'
        );
        INSERT INTO projects (id, name) VALUES ('p1', 'P');
        INSERT INTO chapters (id, project_id, title, sort_order)
            VALUES ('c1', 'p1', 'Ch', 0);

        INSERT INTO entries
          (id, project_id, chapter_id, created_at, updated_at)
        VALUES
          -- chaptered entries: edited-order a (older), b (newer), c (newest)
          ('a', 'p1', 'c1', '2024-01-01T00:00:00Z', '2024-01-01T00:00:01Z'),
          ('b', 'p1', 'c1', '2024-01-01T00:00:00Z', '2024-01-01T00:00:02Z'),
          ('c', 'p1', 'c1', '2024-01-01T00:00:00Z', '2024-01-01T00:00:03Z'),
          -- unchaptered entry
          ('u', 'p1', NULL, '2024-01-01T00:00:00Z', '2024-01-01T00:00:04Z'),
          -- no-project entry should stay with NULL sequence_order
          ('x', NULL,  NULL, '2024-01-01T00:00:00Z', '2024-01-01T00:00:05Z');
        """
    )
    conn.commit()
    conn.close()

    conn = open_and_initialize(db_path)
    try:
        rows = {
            row["id"]: row["sequence_order"]
            for row in conn.execute(
                "SELECT id, sequence_order FROM entries"
            )
        }
        # Chaptered entries ordered by updated_at ASC: a=0, b=1, c=2
        assert rows["a"] == 0
        assert rows["b"] == 1
        assert rows["c"] == 2
        # Only unchaptered in the project gets seq 0
        assert rows["u"] == 0
        # Entries without a project stay NULL
        assert rows["x"] is None
    finally:
        conn.close()


def test_migration_does_not_reshuffle_existing_sequence_order(
    tmp_path: Path,
) -> None:
    """Running initialize_schema repeatedly on a fully-migrated DB must
    not disturb user-chosen ordering."""
    db_path = tmp_path / "writer.db"
    conn = open_and_initialize(db_path)
    try:
        from writer.storage.repositories.chapter_repository import ChapterRepository
        from writer.storage.repositories.entry_repository import EntryRepository
        from writer.storage.repositories.project_repository import ProjectRepository

        projects = ProjectRepository(conn)
        chapters = ChapterRepository(conn)
        entries = EntryRepository(conn)
        p = projects.create("P")
        ch = chapters.create(p.id, "Ch")
        a = entries.create(); b = entries.create(); c = entries.create()
        for e in (a, b, c):
            entries.assign_to_project(e.id, p.id)
            entries.assign_to_chapter(e.id, ch.id)
        # User-ordered: reverse.
        entries.reorder_container(p.id, ch.id, [c.id, b.id, a.id])
        seqs_before = {
            row["id"]: row["sequence_order"]
            for row in conn.execute("SELECT id, sequence_order FROM entries")
        }

        # Re-run initialize_schema multiple times.
        initialize_schema(conn)
        initialize_schema(conn)

        seqs_after = {
            row["id"]: row["sequence_order"]
            for row in conn.execute("SELECT id, sequence_order FROM entries")
        }
        assert seqs_before == seqs_after
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# M5E: tags_text migration tests
# ---------------------------------------------------------------------------

def test_pre_m5e_database_gets_tags_text_column(tmp_path: Path) -> None:
    """An older DB without tags_text gets it added on open_and_initialize."""
    db_path = tmp_path / "writer.db"
    _make_pre_m5_db(db_path)
    conn = open_and_initialize(db_path)
    try:
        cols = _columns(conn, "entries")
        assert "tags_text" in cols
    finally:
        conn.close()


def test_pre_m5e_old_rows_have_empty_tags_text(tmp_path: Path) -> None:
    """Existing rows receive an empty string for tags_text after migration."""
    db_path = tmp_path / "writer.db"
    _make_pre_m5_db(db_path)
    conn = open_and_initialize(db_path)
    try:
        row = conn.execute(
            "SELECT tags_text FROM entries WHERE id = 'e1'"
        ).fetchone()
        assert row is not None
        assert row[0] == ""
    finally:
        conn.close()


def test_tags_text_migration_is_idempotent(tmp_path: Path) -> None:
    """Running initialize_schema multiple times on a current DB is safe."""
    db_path = tmp_path / "writer.db"
    conn = open_and_initialize(db_path)
    try:
        initialize_schema(conn)
        initialize_schema(conn)
        cols = _columns(conn, "entries")
        assert "tags_text" in cols
    finally:
        conn.close()
