-- Writer schema.
-- Milestone 1: app_settings.
-- Milestone 2: entries, entry_versions, FTS5 search.

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS entries (
    id             TEXT PRIMARY KEY,
    title          TEXT NOT NULL DEFAULT '',
    body           TEXT NOT NULL DEFAULT '',
    entry_type     TEXT NOT NULL DEFAULT 'fragment',
    project_id     TEXT,
    chapter_id     TEXT,
    sequence_order INTEGER,
    tags_text      TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_entries_updated_at ON entries (updated_at DESC);

CREATE TABLE IF NOT EXISTS entry_versions (
    id           TEXT PRIMARY KEY,
    entry_id     TEXT NOT NULL,
    version_type TEXT NOT NULL,
    content      TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    provider     TEXT,
    model        TEXT,
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entry_versions_entry
    ON entry_versions (entry_id, created_at DESC);

-- FTS5 external-content index over entries(title, body).
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    title,
    body,
    content='entries',
    content_rowid='rowid',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, title, body)
    VALUES (new.rowid, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body)
    VALUES ('delete', old.rowid, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body)
    VALUES ('delete', old.rowid, old.title, old.body);
    INSERT INTO entries_fts(rowid, title, body)
    VALUES (new.rowid, new.title, new.body);
END;

-- Milestone 4A: reference passage library.
CREATE TABLE IF NOT EXISTS reference_passages (
    id            TEXT PRIMARY KEY,
    source_title  TEXT NOT NULL,
    source_author TEXT NOT NULL DEFAULT '',
    content       TEXT NOT NULL,
    tags          TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_references_updated_at
    ON reference_passages (updated_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS reference_passages_fts USING fts5(
    source_title,
    source_author,
    content,
    tags,
    content='reference_passages',
    content_rowid='rowid',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS reference_passages_ai AFTER INSERT ON reference_passages BEGIN
    INSERT INTO reference_passages_fts(rowid, source_title, source_author, content, tags)
    VALUES (new.rowid, new.source_title, new.source_author, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS reference_passages_ad AFTER DELETE ON reference_passages BEGIN
    INSERT INTO reference_passages_fts(reference_passages_fts, rowid, source_title, source_author, content, tags)
    VALUES ('delete', old.rowid, old.source_title, old.source_author, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS reference_passages_au AFTER UPDATE ON reference_passages BEGIN
    INSERT INTO reference_passages_fts(reference_passages_fts, rowid, source_title, source_author, content, tags)
    VALUES ('delete', old.rowid, old.source_title, old.source_author, old.content, old.tags);
    INSERT INTO reference_passages_fts(rowid, source_title, source_author, content, tags)
    VALUES (new.rowid, new.source_title, new.source_author, new.content, new.tags);
END;

-- Milestone 5: projects and chapters.
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_updated_at
    ON projects (updated_at DESC);

CREATE TABLE IF NOT EXISTS chapters (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_chapters_project_order
    ON chapters (project_id, sort_order);

-- Indexes on entries.project_id / entries.chapter_id are created by
-- database._ensure_post_migration_indexes() so they can't run before the
-- migration step finishes backfilling those columns on pre-M5 databases.
