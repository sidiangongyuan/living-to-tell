"""Tests for the project repository (M5)."""
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


def test_create_requires_name(container):
    with pytest.raises(ValueError):
        container.project_repository.create("   ")


def test_create_and_get(container):
    p = container.project_repository.create("Novel", "A long book")
    assert p.name == "Novel"
    assert p.description == "A long book"
    assert container.project_repository.get(p.id) == p


def test_rename_and_update_description(container):
    p = container.project_repository.create("Draft")
    renamed = container.project_repository.rename(p.id, "Final title")
    assert renamed.name == "Final title"
    with_desc = container.project_repository.update_description(p.id, "new desc")
    assert with_desc.description == "new desc"


def test_rename_missing_returns_none(container):
    assert container.project_repository.rename("nope", "x") is None


def test_list_all_and_count(container):
    container.project_repository.create("A")
    container.project_repository.create("B")
    assert container.project_repository.count() == 2
    assert {p.name for p in container.project_repository.list_all()} == {"A", "B"}


def test_delete_cascades_chapters_and_detaches_entries(container):
    p = container.project_repository.create("P")
    ch = container.chapter_repository.create(p.id, "Ch1")
    e = container.entry_repository.create(title="t", body="b")
    container.entry_repository.assign_to_project(e.id, p.id)
    container.entry_repository.assign_to_chapter(e.id, ch.id)

    assert container.project_repository.delete(p.id) is True
    assert container.project_repository.get(p.id) is None
    assert container.chapter_repository.get(ch.id) is None

    detached = container.entry_repository.get(e.id)
    assert detached is not None
    assert detached.project_id is None
    assert detached.chapter_id is None
