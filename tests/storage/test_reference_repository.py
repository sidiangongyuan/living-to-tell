"""Tests for the reference passage repository (M4A)."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container


@pytest.fixture()
def repo(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c.reference_repository
    finally:
        c.close()


def test_create_and_get_roundtrip(repo):
    passage = repo.create(
        source_title="Moby Dick",
        source_author="Melville",
        content="Call me Ishmael.",
        tags="sea,classic",
    )
    assert passage.id
    assert passage.source_title == "Moby Dick"
    assert passage.source_author == "Melville"
    assert passage.tags == "sea,classic"
    assert passage.created_at is not None

    loaded = repo.get(passage.id)
    assert loaded == passage


def test_requires_title_and_content(repo):
    with pytest.raises(ValueError):
        repo.create(source_title="   ", content="x")
    with pytest.raises(ValueError):
        repo.create(source_title="t", content="   ")


def test_update_changes_fields_and_updated_at(repo):
    passage = repo.create(source_title="t", content="original body")
    updated = repo.update(
        passage.id,
        source_title="t2",
        source_author="a",
        content="new body",
        tags="x",
    )
    assert updated is not None
    assert updated.source_title == "t2"
    assert updated.content == "new body"
    assert updated.tags == "x"


def test_update_missing_returns_none(repo):
    assert (
        repo.update("nope", source_title="t", content="c") is None
    )


def test_delete_removes_from_list_and_fts(repo):
    p1 = repo.create(source_title="alpha", content="the quick brown fox")
    repo.create(source_title="beta", content="another passage")
    assert len(repo.list_recent()) == 2
    repo.delete(p1.id)
    assert len(repo.list_recent()) == 1
    assert repo.search("quick") == []


def test_list_recent_orders_by_updated_at_desc(repo):
    import time

    a = repo.create(source_title="a", content="first")
    time.sleep(0.01)
    b = repo.create(source_title="b", content="second")
    time.sleep(0.01)
    # touch a so it bubbles to the top
    repo.update(a.id, source_title="a", content="first updated")
    ordered = repo.list_recent()
    assert [p.id for p in ordered[:2]] == [a.id, b.id]


def test_search_matches_title_author_content_and_tags(repo):
    p = repo.create(
        source_title="On Writing",
        source_author="Stephen King",
        content="Hard work beats talent",
        tags="craft advice",
    )
    assert [r.id for r in repo.search("writing")] == [p.id]
    assert [r.id for r in repo.search("stephen")] == [p.id]
    assert [r.id for r in repo.search("talent")] == [p.id]
    assert [r.id for r in repo.search("craft")] == [p.id]


def test_search_prefix_match_on_last_token(repo):
    p = repo.create(source_title="Gardening", content="prune the rosebush")
    assert [r.id for r in repo.search("rose")] == [p.id]


def test_search_empty_query_returns_empty(repo):
    repo.create(source_title="t", content="c")
    assert repo.search("   ") == []


def test_search_strips_punctuation(repo):
    p = repo.create(source_title="hello", content="world!")
    assert [r.id for r in repo.search("!!!")] == []
    assert [r.id for r in repo.search("world!")] == [p.id]


def test_get_many_preserves_order(repo):
    a = repo.create(source_title="a", content="a")
    b = repo.create(source_title="b", content="b")
    c = repo.create(source_title="c", content="c")
    got = repo.get_many([c.id, a.id, b.id])
    assert [p.id for p in got] == [c.id, a.id, b.id]


def test_count(repo):
    assert repo.count() == 0
    repo.create(source_title="t", content="c")
    assert repo.count() == 1
