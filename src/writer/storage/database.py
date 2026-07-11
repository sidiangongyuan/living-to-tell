"""SQLite connection management and schema bootstrap.

Centralises connection creation, pragma configuration, and schema execution so
the rest of the codebase never opens raw connections or reads ``schema.sql``
directly.
"""
from __future__ import annotations

import sqlite3
import threading
from importlib import resources
from pathlib import Path
from typing import Optional

from writer.app.paths import database_path

_SCHEMA_RESOURCE_PACKAGE = "writer.storage"
_SCHEMA_RESOURCE_NAME = "schema.sql"


class _SerializedCursor(sqlite3.Cursor):
    """Serialize cursor stepping on the process-wide desktop connection."""

    @property
    def _connection_lock(self):
        return self.connection._access_lock  # type: ignore[attr-defined]  # noqa: SLF001

    def execute(self, sql, parameters=()):
        with self._connection_lock:
            return super().execute(sql, parameters)

    def executemany(self, sql, parameters):
        with self._connection_lock:
            return super().executemany(sql, parameters)

    def executescript(self, sql_script):
        with self._connection_lock:
            return super().executescript(sql_script)

    def fetchone(self):
        with self._connection_lock:
            return super().fetchone()

    def fetchmany(self, size=None):
        with self._connection_lock:
            if size is None:
                return super().fetchmany()
            return super().fetchmany(size)

    def fetchall(self):
        with self._connection_lock:
            return super().fetchall()

    def __next__(self):
        with self._connection_lock:
            return super().__next__()

    def close(self):
        with self._connection_lock:
            return super().close()


class SerializedConnection(sqlite3.Connection):
    """A SQLite connection safe for FastAPI's concurrent worker threads.

    The desktop backend intentionally owns one long-lived connection. SQLite
    may be built in serialized mode, but Python cursor operations can still
    overlap when synchronous routes run in different worker threads. The
    re-entrant lock keeps each operation atomic and holds explicit transactions
    until their matching COMMIT or ROLLBACK.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._access_lock = threading.RLock()
        self._transaction_owner: Optional[int] = None

    def cursor(self, factory=_SerializedCursor):
        with self._access_lock:
            return super().cursor(factory)

    @property
    def in_transaction(self) -> bool:
        with self._access_lock:
            return sqlite3.Connection.in_transaction.__get__(self)

    @staticmethod
    def _statement_verb(sql: object) -> str:
        clean = str(sql).lstrip()
        return clean.split(None, 1)[0].upper() if clean else ""

    def execute(self, sql, parameters=()):
        verb = self._statement_verb(sql)
        thread_id = threading.get_ident()
        transaction_lock_acquired = False
        if verb == "BEGIN":
            self._access_lock.acquire()
            transaction_lock_acquired = True
        try:
            with self._access_lock:
                result = self.cursor().execute(sql, parameters)
            if verb == "BEGIN":
                self._transaction_owner = thread_id
            return result
        except BaseException:
            if transaction_lock_acquired:
                self._access_lock.release()
            raise
        finally:
            if verb in {"COMMIT", "END", "ROLLBACK"}:
                self._release_transaction_lock(thread_id)

    def executemany(self, sql, parameters):
        with self._access_lock:
            return self.cursor().executemany(sql, parameters)

    def executescript(self, sql_script):
        with self._access_lock:
            return self.cursor().executescript(sql_script)

    def commit(self) -> None:
        thread_id = threading.get_ident()
        try:
            with self._access_lock:
                super().commit()
        finally:
            self._release_transaction_lock(thread_id)

    def rollback(self) -> None:
        thread_id = threading.get_ident()
        try:
            with self._access_lock:
                super().rollback()
        finally:
            self._release_transaction_lock(thread_id)

    def backup(self, target, *, pages=-1, progress=None, name="main", sleep=0.250):
        with self._access_lock:
            return super().backup(
                target,
                pages=pages,
                progress=progress,
                name=name,
                sleep=sleep,
            )

    def __enter__(self):
        self._access_lock.acquire()
        try:
            return super().__enter__()
        except BaseException:
            self._access_lock.release()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self._release_transaction_lock(threading.get_ident())
            self._access_lock.release()

    def close(self) -> None:
        thread_id = threading.get_ident()
        try:
            with self._access_lock:
                super().close()
        finally:
            self._release_transaction_lock(thread_id)

    def _release_transaction_lock(self, thread_id: int) -> None:
        if self._transaction_owner != thread_id:
            return
        self._transaction_owner = None
        self._access_lock.release()


def _read_schema_sql() -> str:
    return resources.files(_SCHEMA_RESOURCE_PACKAGE).joinpath(_SCHEMA_RESOURCE_NAME).read_text(
        encoding="utf-8"
    )


def open_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a SQLite connection with project-wide pragmas applied."""
    target = Path(db_path) if db_path is not None else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        target,
        isolation_level=None,
        check_same_thread=False,
        factory=SerializedConnection,
    )
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

    collection_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(collections)")
    }
    if "project_type" not in collection_cols:
        conn.execute(
            "ALTER TABLE collections ADD COLUMN project_type TEXT "
            "NOT NULL DEFAULT 'general'"
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
            "ADD COLUMN board_width INTEGER NOT NULL DEFAULT 248"
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

    ai_card_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(ai_cards)")
    }
    if "tags_text" not in ai_card_cols:
        conn.execute(
            "ALTER TABLE ai_cards ADD COLUMN tags_text TEXT NOT NULL DEFAULT ''"
        )

    version_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(entry_versions)")
    }
    if "title_snapshot" not in version_cols:
        conn.execute(
            "ALTER TABLE entry_versions ADD COLUMN title_snapshot TEXT NOT NULL DEFAULT ''"
        )
    if "tags_snapshot" not in version_cols:
        conn.execute(
            "ALTER TABLE entry_versions ADD COLUMN tags_snapshot TEXT NOT NULL DEFAULT ''"
        )
    if "label" not in version_cols:
        conn.execute(
            "ALTER TABLE entry_versions ADD COLUMN label TEXT NOT NULL DEFAULT ''"
        )
    if "reason" not in version_cols:
        conn.execute(
            "ALTER TABLE entry_versions ADD COLUMN reason TEXT NOT NULL DEFAULT ''"
        )
    if "word_count" not in version_cols:
        conn.execute(
            "ALTER TABLE entry_versions ADD COLUMN word_count INTEGER NOT NULL DEFAULT 0"
        )
        conn.execute(
            "UPDATE entry_versions SET word_count = length(content) WHERE word_count = 0"
        )
    if "char_count" not in version_cols:
        conn.execute(
            "ALTER TABLE entry_versions ADD COLUMN char_count INTEGER NOT NULL DEFAULT 0"
        )
        conn.execute(
            "UPDATE entry_versions SET char_count = length(content) WHERE char_count = 0"
        )

    motif_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(motif_nodes)")
    }
    if "profile_json" not in motif_cols:
        conn.execute(
            "ALTER TABLE motif_nodes ADD COLUMN profile_json TEXT NOT NULL DEFAULT '{}'"
        )

    agent_settings_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(collection_agent_settings)")
    }
    if "active_session_id" not in agent_settings_cols:
        conn.execute(
            "ALTER TABLE collection_agent_settings ADD COLUMN active_session_id TEXT"
        )

    agent_run_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(collection_agent_runs)")
    }
    if "session_id" not in agent_run_cols:
        conn.execute("ALTER TABLE collection_agent_runs ADD COLUMN session_id TEXT")
    if "mode" not in agent_run_cols:
        conn.execute(
            "ALTER TABLE collection_agent_runs ADD COLUMN mode TEXT "
            "NOT NULL DEFAULT 'discuss'"
        )
    if "draft_id" not in agent_run_cols:
        conn.execute("ALTER TABLE collection_agent_runs ADD COLUMN draft_id TEXT")


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
    collection_entries = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'collection_entries'"
    ).fetchone()
    if collection_entries is not None:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_collection_entries_collection_order "
            "ON collection_entries (collection_id, sort_order)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_collection_entries_entry "
            "ON collection_entries (entry_id)"
        )
    collection_outline_items = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'collection_outline_items'"
    ).fetchone()
    if collection_outline_items is not None:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_collection_outline_collection_order "
            "ON collection_outline_items (collection_id, sort_order)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_collection_outline_entry "
            "ON collection_outline_items (entry_id)"
        )


def open_and_initialize(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Convenience helper used by bootstrap and tests."""
    conn = open_connection(db_path)
    initialize_schema(conn)
    return conn
