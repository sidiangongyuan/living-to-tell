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
    archived_at    TEXT,
    curation_status TEXT NOT NULL DEFAULT 'unsorted',
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_entries_updated_at ON entries (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries (created_at DESC);

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

CREATE TABLE IF NOT EXISTS entry_writing_notes (
    id           TEXT PRIMARY KEY,
    entry_id     TEXT NOT NULL,
    body         TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'open',
    pinned       INTEGER NOT NULL DEFAULT 0,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    board_x      INTEGER,
    board_y      INTEGER,
    board_width  INTEGER NOT NULL DEFAULT 248,
    color_key    TEXT NOT NULL DEFAULT 'cream',
    z_index      INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at TEXT,
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entry_writing_notes_entry
    ON entry_writing_notes (entry_id, status, pinned DESC, sort_order ASC);

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
    kind          TEXT NOT NULL DEFAULT 'excerpt',
    usage_kind    TEXT NOT NULL DEFAULT 'style',
    personal_note TEXT NOT NULL DEFAULT '',
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
    usage_kind,
    personal_note,
    content='reference_passages',
    content_rowid='rowid',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS reference_passages_ai AFTER INSERT ON reference_passages BEGIN
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

CREATE TRIGGER IF NOT EXISTS reference_passages_ad AFTER DELETE ON reference_passages BEGIN
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

CREATE TRIGGER IF NOT EXISTS reference_passages_au AFTER UPDATE ON reference_passages BEGIN
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

-- ---------------------------------------------------------------------------
-- Milestone 8: works, work sections, collections, fragment refs, work versions.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS works (
    id                TEXT PRIMARY KEY,
    title             TEXT NOT NULL DEFAULT '',
    summary           TEXT NOT NULL DEFAULT '',
    status            TEXT NOT NULL DEFAULT 'idea',
    tags_text         TEXT NOT NULL DEFAULT '',
    target_word_count INTEGER,
    archived_at       TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_works_updated_at ON works (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_works_status ON works (status);

CREATE TABLE IF NOT EXISTS work_sections (
    id           TEXT PRIMARY KEY,
    work_id      TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL DEFAULT 'body',
    content      TEXT NOT NULL DEFAULT '',
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_work_sections_work_order
    ON work_sections (work_id, sort_order);

CREATE TABLE IF NOT EXISTS collections (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_collections_updated_at
    ON collections (updated_at DESC);

CREATE TABLE IF NOT EXISTS collection_items (
    id            TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    work_id       TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(collection_id, work_id)
);

CREATE INDEX IF NOT EXISTS idx_collection_items_collection_order
    ON collection_items (collection_id, sort_order);

-- Article-based collections. The legacy collection_items table above is
-- intentionally kept for old data, but product code uses this table.
CREATE TABLE IF NOT EXISTS collection_entries (
    id            TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    entry_id      TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(collection_id, entry_id)
);

CREATE INDEX IF NOT EXISTS idx_collection_entries_collection_order
    ON collection_entries (collection_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_collection_entries_entry
    ON collection_entries (entry_id);

CREATE TABLE IF NOT EXISTS work_fragment_refs (
    id            TEXT PRIMARY KEY,
    work_id       TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    section_id    TEXT REFERENCES work_sections(id) ON DELETE SET NULL,
    entry_id      TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    included_text TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_work_fragment_refs_work
    ON work_fragment_refs (work_id);
CREATE INDEX IF NOT EXISTS idx_work_fragment_refs_entry
    ON work_fragment_refs (entry_id);

CREATE TABLE IF NOT EXISTS work_versions (
    id           TEXT PRIMARY KEY,
    work_id      TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    version_type TEXT NOT NULL,
    content_json TEXT NOT NULL,
    label        TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_work_versions_work
    ON work_versions (work_id, created_at DESC);

-- Standalone (non-content) FTS5 over works. The repository keeps it in sync
-- whenever the work's title / summary / tags / sections change. We avoid
-- triggers across multiple tables for simplicity and clarity.
CREATE VIRTUAL TABLE IF NOT EXISTS works_fts USING fts5(
    work_id UNINDEXED,
    title,
    summary,
    body,
    tags,
    tokenize='unicode61'
);


-- ---------------------------------------------------------------------------
-- Milestone 10A: AI workspace — threads, messages, cards, task templates.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_threads (
    id          TEXT PRIMARY KEY,
    scope_kind  TEXT NOT NULL,           -- 'fragment' | 'work' | 'collection' | 'global'
    scope_id    TEXT,                    -- nullable for 'global'
    title       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_threads_scope
    ON ai_threads (scope_kind, scope_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS ai_messages (
    id          TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL REFERENCES ai_threads(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,           -- 'user' | 'assistant' | 'system'
    content     TEXT NOT NULL,
    meta_json   TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_messages_thread
    ON ai_messages (thread_id, created_at);

CREATE TABLE IF NOT EXISTS ai_cards (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,           -- 'style' | 'character' | 'setting'
    name        TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_cards_kind
    ON ai_cards (kind, updated_at DESC);

CREATE TABLE IF NOT EXISTS ai_task_templates (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    task_type   TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
