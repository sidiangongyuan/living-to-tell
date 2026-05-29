"""SQLite connection management and schema bootstrap.

Centralises connection creation, pragma configuration, and schema execution so
the rest of the codebase never opens raw connections or reads ``schema.sql``
directly.
"""
from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path
from typing import Optional

from writer.app.paths import database_path

_SCHEMA_RESOURCE_PACKAGE = "writer.storage"
_SCHEMA_RESOURCE_NAME = "schema.sql"


def _read_schema_sql() -> str:
    return resources.files(_SCHEMA_RESOURCE_PACKAGE).joinpath(_SCHEMA_RESOURCE_NAME).read_text(
        encoding="utf-8"
    )


def open_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a SQLite connection with project-wide pragmas applied."""
    target = Path(db_path) if db_path is not None else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Apply ``schema.sql`` to the given connection (idempotent).

    Order matters:
      1. Apply base schema (``schema.sql``) — this is safe on fresh DBs
         and leaves pre-existing tables untouched.
      2. Run column-level migrations (``_migrate``) to backfill new
         columns on older databases.
      3. Ensure indexes that depend on post-migration columns exist.
         These *cannot* live inside ``schema.sql`` because a pre-M5
         ``entries`` table does not yet have ``project_id`` /
         ``chapter_id`` when the script first runs.
    """
    conn.executescript(_read_schema_sql())
    _migrate(conn)
    _ensure_post_migration_indexes(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Backfill columns added after the initial schema.

    CREATE TABLE IF NOT EXISTS leaves pre-existing tables untouched, so we
    explicitly add new columns on older databases. Each migration step is
    idempotent and safe to run on fresh databases too.
    """
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(entries)")}
    if "project_id" not in cols:
        conn.execute("ALTER TABLE entries ADD COLUMN project_id TEXT")
    if "chapter_id" not in cols:
        conn.execute("ALTER TABLE entries ADD COLUMN chapter_id TEXT")
    if "sequence_order" not in cols:
        conn.execute("ALTER TABLE entries ADD COLUMN sequence_order INTEGER")
        _backfill_sequence_order(conn)
    else:
        # Column was added earlier — only backfill if some project-assigned
        # rows still lack a sequence_order. This keeps the migration
        # idempotent and avoids reshuffling an order the user has already
        # tidied.
        pending = conn.execute(
            "SELECT 1 FROM entries "
            "WHERE project_id IS NOT NULL AND sequence_order IS NULL LIMIT 1"
        ).fetchone()
        if pending is not None:
            _backfill_sequence_order(conn)
    if "tags_text" not in cols:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN tags_text TEXT NOT NULL DEFAULT ''"
        )
    # M7B: archive support.
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(entries)")}
    if "archived_at" not in cols:
        conn.execute("ALTER TABLE entries ADD COLUMN archived_at TEXT")
    # M8: curation status (unsorted / included / parking / discarded).
    if "curation_status" not in cols:
        conn.execute(
            "ALTER TABLE entries ADD COLUMN curation_status TEXT "
            "NOT NULL DEFAULT 'unsorted'"
        )

    # M-RefTypes: typed reference passages.
    ref_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(reference_passages)")
    }
    if "kind" not in ref_cols:
        conn.execute(
            "ALTER TABLE reference_passages ADD COLUMN kind TEXT "
            "NOT NULL DEFAULT 'excerpt'"
        )
    # M-StyleSpecimen: usage kind + personal note for style specimens.
    added_usage_kind = False
    if "usage_kind" not in ref_cols:
        conn.execute(
            "ALTER TABLE reference_passages ADD COLUMN usage_kind TEXT "
            "NOT NULL DEFAULT 'style'"
        )
        added_usage_kind = True
    added_personal_note = False
    if "personal_note" not in ref_cols:
        conn.execute(
            "ALTER TABLE reference_passages ADD COLUMN personal_note TEXT "
            "NOT NULL DEFAULT ''"
        )
        added_personal_note = True
    _ensure_reference_passages_fts_schema(
        conn,
        force_rebuild=added_usage_kind or added_personal_note,
    )

    note_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(entry_writing_notes)")
    }
    if "board_x" not in note_cols:
        conn.execute("ALTER TABLE entry_writing_notes ADD COLUMN board_x INTEGER")
    if "board_y" not in note_cols:
        conn.execute("ALTER TABLE entry_writing_notes ADD COLUMN board_y INTEGER")
    if "board_width" not in note_cols:
        conn.execute(
            "ALTER TABLE entry_writing_notes "
            "ADD COLUMN board_width INTEGER NOT NULL DEFAULT 188"
        )
    if "color_key" not in note_cols:
        conn.execute(
            "ALTER TABLE entry_writing_notes "
            "ADD COLUMN color_key TEXT NOT NULL DEFAULT 'cream'"
        )
    if "z_index" not in note_cols:
        conn.execute(
            "ALTER TABLE entry_writing_notes "
            "ADD COLUMN z_index INTEGER NOT NULL DEFAULT 0"
        )


def _ensure_reference_passages_fts_schema(
    conn: sqlite3.Connection, *, force_rebuild: bool = False
) -> None:
    """Upgrade the reference-passage FTS table when its column layout changes.

    ``CREATE VIRTUAL TABLE IF NOT EXISTS`` leaves older FTS tables untouched, so
    adding searchable columns requires an explicit rebuild on upgraded
    databases.
    """
    fts_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(reference_passages_fts)")
    }
    expected = {
        "source_title",
        "source_author",
        "content",
        "tags",
        "usage_kind",
        "personal_note",
    }
    if expected.issubset(fts_cols) and not force_rebuild:
        return

    conn.executescript(
        """
        DROP TRIGGER IF EXISTS reference_passages_ai;
        DROP TRIGGER IF EXISTS reference_passages_ad;
        DROP TRIGGER IF EXISTS reference_passages_au;
        DROP TABLE IF EXISTS reference_passages_fts;

        CREATE VIRTUAL TABLE reference_passages_fts USING fts5(
            source_title,
            source_author,
            content,
            tags,
            usage_kind,
            personal_note,
            content='reference_passages',
            content_rowid='rowid',
            tokenize='unicode61'
        );

        CREATE TRIGGER reference_passages_ai AFTER INSERT ON reference_passages BEGIN
            INSERT INTO reference_passages_fts(
                rowid,
                source_title,
                source_author,
                content,
                tags,
                usage_kind,
                personal_note
            )
            VALUES (
                new.rowid,
                new.source_title,
                new.source_author,
                new.content,
                new.tags,
                new.usage_kind,
                new.personal_note
            );
        END;

        CREATE TRIGGER reference_passages_ad AFTER DELETE ON reference_passages BEGIN
            INSERT INTO reference_passages_fts(
                reference_passages_fts,
                rowid,
                source_title,
                source_author,
                content,
                tags,
                usage_kind,
                personal_note
            )
            VALUES (
                'delete',
                old.rowid,
                old.source_title,
                old.source_author,
                old.content,
                old.tags,
                old.usage_kind,
                old.personal_note
            );
        END;

        CREATE TRIGGER reference_passages_au AFTER UPDATE ON reference_passages BEGIN
            INSERT INTO reference_passages_fts(
                reference_passages_fts,
                rowid,
                source_title,
                source_author,
                content,
                tags,
                usage_kind,
                personal_note
            )
            VALUES (
                'delete',
                old.rowid,
                old.source_title,
                old.source_author,
                old.content,
                old.tags,
                old.usage_kind,
                old.personal_note
            );
            INSERT INTO reference_passages_fts(
                rowid,
                source_title,
                source_author,
                content,
                tags,
                usage_kind,
                personal_note
            )
            VALUES (
                new.rowid,
                new.source_title,
                new.source_author,
                new.content,
                new.tags,
                new.usage_kind,
                new.personal_note
            );
        END;
        """
    )
    conn.execute(
        "INSERT INTO reference_passages_fts(reference_passages_fts) VALUES ('rebuild')"
    )


def _backfill_sequence_order(conn: sqlite3.Connection) -> None:
    """Assign a stable per-container sequence_order to every entry that
    belongs to a project but doesn't yet have one.

    The container is ``(project_id, chapter_id)``. We rank inside each
    container by the old implicit ordering (``updated_at ASC,
    created_at ASC``) and continue numbering *after* any existing
    sequence_order values so previously tidied containers are preserved.
    """
    rows = conn.execute(
        """
        SELECT id, project_id, chapter_id, sequence_order
          FROM entries
         WHERE project_id IS NOT NULL
         ORDER BY project_id,
                  CASE WHEN chapter_id IS NULL THEN 1 ELSE 0 END,
                  chapter_id,
                  updated_at ASC,
                  created_at ASC,
                  id ASC
        """
    ).fetchall()

    next_order: dict[tuple[str, Optional[str]], int] = {}
    # First pass: compute the next free slot per container (max existing
    # sequence_order + 1, or 0 if the container is untouched).
    for row in rows:
        key = (row["project_id"], row["chapter_id"])
        existing = row["sequence_order"]
        if existing is not None:
            if key not in next_order or existing + 1 > next_order[key]:
                next_order[key] = existing + 1
        else:
            next_order.setdefault(key, 0)

    # Second pass: assign to rows that still need one.
    for row in rows:
        if row["sequence_order"] is not None:
            continue
        key = (row["project_id"], row["chapter_id"])
        slot = next_order.get(key, 0)
        conn.execute(
            "UPDATE entries SET sequence_order = ? WHERE id = ?",
            (slot, row["id"]),
        )
        next_order[key] = slot + 1


def _ensure_post_migration_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes that depend on columns added by ``_migrate``.

    Safe on both fresh and upgraded databases — ``CREATE INDEX IF NOT
    EXISTS`` is idempotent.
    """
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entries_project ON entries (project_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entries_chapter ON entries (chapter_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entries_project_container_order "
        "ON entries (project_id, chapter_id, sequence_order)"
    )
    note_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'entry_writing_notes'"
    ).fetchone()
    if note_table is None:
        return
    conn.execute("DROP INDEX IF EXISTS idx_entry_writing_notes_entry")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entry_writing_notes_entry
            ON entry_writing_notes (
                entry_id,
                status,
                pinned DESC,
                board_y ASC,
                board_x ASC,
                sort_order ASC
            )
        """
    )


def open_and_initialize(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Convenience helper used by bootstrap and tests."""
    conn = open_connection(db_path)
    initialize_schema(conn)
    return conn
