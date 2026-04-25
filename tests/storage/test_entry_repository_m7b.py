"""M7B additions to EntryRepository: delete_many, set_archived, sort, archive filters."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from writer.storage.database import open_and_initialize
from writer.storage.repositories.entry_repository import (
    SORT_CREATED,
    SORT_TITLE,
    SORT_UPDATED,
    EntryRepository,
)


@pytest.fixture()
def repo(tmp_path: Path) -> EntryRepository:
    conn = open_and_initialize(tmp_path / "m7b.sqlite3")
    return EntryRepository(conn)


def test_delete_many_removes_only_specified_ids(repo: EntryRepository) -> None:
    a = repo.create(title="a")
    b = repo.create(title="b")
    c = repo.create(title="c")

    removed = repo.delete_many([a.id, c.id])

    assert removed == 2
    assert repo.get(a.id) is None
    assert repo.get(c.id) is None
    assert repo.get(b.id) is not None


def test_delete_many_ignores_empty_and_missing(repo: EntryRepository) -> None:
    a = repo.create(title="a")

    assert repo.delete_many([]) == 0
    assert repo.delete_many(["", "does-not-exist"]) == 0
    assert repo.get(a.id) is not None


def test_set_archived_roundtrip(repo: EntryRepository) -> None:
    entry = repo.create(title="archive-me")

    archived = repo.set_archived(entry.id, True)
    assert archived is not None
    assert archived.archived_at is not None

    unarchived = repo.set_archived(entry.id, False)
    assert unarchived is not None
    assert unarchived.archived_at is None


def test_list_recent_hides_archived_by_default(repo: EntryRepository) -> None:
    kept = repo.create(title="kept")
    gone = repo.create(title="gone")
    repo.set_archived(gone.id, True)

    default_ids = [e.id for e in repo.list_recent()]
    assert kept.id in default_ids
    assert gone.id not in default_ids

    all_ids = {e.id for e in repo.list_recent(include_archived=True)}
    assert {kept.id, gone.id} <= all_ids

    archived_only = [e.id for e in repo.list_recent(archived_only=True)]
    assert archived_only == [gone.id]


def test_list_recent_sort_modes(repo: EntryRepository) -> None:
    z = repo.create(title="zeta")
    time.sleep(0.005)
    a = repo.create(title="alpha")
    time.sleep(0.005)
    m = repo.create(title="mu")

    by_updated = [e.id for e in repo.list_recent(sort=SORT_UPDATED)]
    assert by_updated[0] == m.id  # most-recent update first

    by_created = [e.id for e in repo.list_recent(sort=SORT_CREATED)]
    assert by_created[0] == m.id

    by_title = [e.title for e in repo.list_recent(sort=SORT_TITLE)]
    assert by_title == sorted(by_title, key=str.lower)


# ---------------------------------------------------------------------------
# insert_restored: preserves project / chapter / sequence / archived_at
# ---------------------------------------------------------------------------


def _make_project_and_chapter(conn, project_id="p1", chapter_id="c1"):
    conn.execute(
        "INSERT INTO projects (id, name) VALUES (?, ?)",
        (project_id, "Project 1"),
    )
    conn.execute(
        "INSERT INTO chapters (id, project_id, title) VALUES (?, ?, ?)",
        (chapter_id, project_id, "Chapter 1"),
    )


def test_insert_restored_preserves_metadata(repo: EntryRepository) -> None:
    _make_project_and_chapter(repo._conn)
    restored = repo.insert_restored(
        title="back",
        body="body",
        tags=["a"],
        project_id="p1",
        chapter_id="c1",
        sequence_order=7,
        archived_at="2024-01-01T00:00:00.000Z",
    )
    assert restored.project_id == "p1"
    assert restored.chapter_id == "c1"
    assert restored.sequence_order == 7
    assert restored.archived_at == "2024-01-01T00:00:00.000Z"
    assert restored.tags == ["a"]


def test_insert_restored_bumps_sequence_on_collision(
    repo: EntryRepository,
) -> None:
    _make_project_and_chapter(repo._conn)
    # Existing entry occupies sequence 0 in the chapter.
    repo._conn.execute(
        """
        INSERT INTO entries (id, title, body, entry_type,
                             project_id, chapter_id, sequence_order)
        VALUES ('existing', 't', '', 'fragment', 'p1', 'c1', 0)
        """
    )
    restored = repo.insert_restored(
        title="x",
        body="",
        project_id="p1",
        chapter_id="c1",
        sequence_order=0,
    )
    # Collision → appended after the existing entry.
    assert restored.sequence_order == 1


def test_insert_restored_drops_chapter_when_project_mismatch(
    repo: EntryRepository,
) -> None:
    _make_project_and_chapter(repo._conn, project_id="p1", chapter_id="c1")
    _make_project_and_chapter(repo._conn, project_id="p2", chapter_id="c2")
    restored = repo.insert_restored(
        title="x",
        body="",
        project_id="p1",
        chapter_id="c2",  # belongs to p2, not p1
    )
    assert restored.project_id == "p1"
    assert restored.chapter_id is None


def test_insert_restored_without_project_leaves_unassigned(
    repo: EntryRepository,
) -> None:
    restored = repo.insert_restored(title="x", body="")
    assert restored.project_id is None
    assert restored.chapter_id is None
    assert restored.sequence_order is None
    assert restored.archived_at is None
