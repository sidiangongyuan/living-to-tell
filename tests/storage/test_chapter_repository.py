"""Tests for the chapter repository (M5)."""
from __future__ import annotations

import pytest

from writer.app.container import build_container


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def project(container):
    return container.project_repository.create("P")


def test_create_appends_with_increasing_sort_order(container, project):
    repo = container.chapter_repository
    a = repo.create(project.id, "A")
    b = repo.create(project.id, "B")
    c = repo.create(project.id, "C")
    assert [ch.sort_order for ch in (a, b, c)] == [0, 1, 2]
    assert [ch.id for ch in repo.list_for_project(project.id)] == [a.id, b.id, c.id]


def test_rename_updates_title(container, project):
    repo = container.chapter_repository
    ch = repo.create(project.id, "old")
    renamed = repo.rename(ch.id, "new")
    assert renamed.title == "new"


def test_delete_detaches_entries(container, project):
    repo = container.chapter_repository
    ch = repo.create(project.id, "Ch")
    e = container.entry_repository.create(title="t", body="b")
    container.entry_repository.assign_to_project(e.id, project.id)
    container.entry_repository.assign_to_chapter(e.id, ch.id)

    assert repo.delete(ch.id) is True
    assert repo.get(ch.id) is None
    reloaded = container.entry_repository.get(e.id)
    assert reloaded.project_id == project.id
    assert reloaded.chapter_id is None


def test_reorder_rewrites_sort_order(container, project):
    repo = container.chapter_repository
    a = repo.create(project.id, "A")
    b = repo.create(project.id, "B")
    c = repo.create(project.id, "C")

    repo.reorder(project.id, [c.id, a.id, b.id])
    order = [ch.id for ch in repo.list_for_project(project.id)]
    assert order == [c.id, a.id, b.id]


def test_reorder_rejects_foreign_chapter(container, project):
    repo = container.chapter_repository
    a = repo.create(project.id, "A")
    other_project = container.project_repository.create("Other")
    other_ch = repo.create(other_project.id, "O")
    with pytest.raises(ValueError):
        repo.reorder(project.id, [a.id, other_ch.id])


def test_list_for_project_scopes_correctly(container, project):
    repo = container.chapter_repository
    other = container.project_repository.create("other")
    repo.create(project.id, "A")
    repo.create(other.id, "B")
    assert [ch.title for ch in repo.list_for_project(project.id)] == ["A"]


def test_entry_assign_project_clears_chapter(container, project):
    repo = container.chapter_repository
    ch = repo.create(project.id, "Ch")
    e = container.entry_repository.create(title="t", body="b")
    container.entry_repository.assign_to_project(e.id, project.id)
    container.entry_repository.assign_to_chapter(e.id, ch.id)

    # reassign to null project must also clear chapter
    detached = container.entry_repository.assign_to_project(e.id, None)
    assert detached.project_id is None
    assert detached.chapter_id is None
