"""Tests for EntryRepository, VersionRepository, and SearchService (FTS5)."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from writer.services.search_service import SearchService, _build_match_expression
from writer.storage.database import open_and_initialize
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.version_repository import VersionRepository


@pytest.fixture()
def conn(tmp_path: Path):
    c = open_and_initialize(tmp_path / "m2.sqlite3")
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def repo(conn) -> EntryRepository:
    return EntryRepository(conn)


@pytest.fixture()
def versions(conn) -> VersionRepository:
    return VersionRepository(conn)


@pytest.fixture()
def search(conn) -> SearchService:
    return SearchService(conn)


# EntryRepository ---------------------------------------------------------
def test_create_then_get(repo: EntryRepository) -> None:
    entry = repo.create(title="hello", body="world")
    assert entry.id
    fetched = repo.get(entry.id)
    assert fetched is not None
    assert fetched.title == "hello"
    assert fetched.body == "world"
    assert fetched.entry_type == "fragment"
    assert fetched.created_at and fetched.updated_at


def test_count(repo: EntryRepository) -> None:
    assert repo.count() == 0
    repo.create()
    repo.create()
    assert repo.count() == 2


def test_list_recent_orders_by_updated_at_desc(repo: EntryRepository) -> None:
    a = repo.create(title="a")
    time.sleep(0.005)
    b = repo.create(title="b")
    time.sleep(0.005)
    c = repo.create(title="c")
    ids = [e.id for e in repo.list_recent()]
    assert ids[:3] == [c.id, b.id, a.id]


def test_update_changes_updated_at_and_moves_to_top(repo: EntryRepository) -> None:
    a = repo.create(title="a")
    time.sleep(0.005)
    b = repo.create(title="b")
    time.sleep(0.005)
    updated = repo.update(a.id, title="a-edited", body="more")
    assert updated is not None
    assert updated.title == "a-edited"
    assert updated.body == "more"
    ids = [e.id for e in repo.list_recent()]
    assert ids[0] == a.id
    assert ids[1] == b.id


def test_update_missing_returns_none(repo: EntryRepository) -> None:
    assert repo.update("does-not-exist", title="x", body="y") is None


def test_delete_removes_entry(repo: EntryRepository) -> None:
    e = repo.create()
    assert repo.delete(e.id) is True
    assert repo.get(e.id) is None
    assert repo.delete(e.id) is False


def test_delete_cascades_versions(repo: EntryRepository, versions: VersionRepository) -> None:
    e = repo.create(title="t")
    versions.add(entry_id=e.id, version_type="original", content="t")
    assert len(versions.list_for_entry(e.id)) == 1
    repo.delete(e.id)
    assert versions.list_for_entry(e.id) == []


# VersionRepository -------------------------------------------------------
def test_versions_round_trip(repo: EntryRepository, versions: VersionRepository) -> None:
    e = repo.create()
    v1 = versions.add(
        entry_id=e.id, version_type="ai_polish", content="polished",
        provider="openai", model="gpt-4o-mini",
    )
    assert v1.id and v1.created_at
    fetched = versions.get(v1.id)
    assert fetched is not None
    assert fetched.content == "polished"
    assert fetched.provider == "openai"
    assert fetched.model == "gpt-4o-mini"
    listed = versions.list_for_entry(e.id)
    assert [v.id for v in listed] == [v1.id]


# SearchService / FTS5 ---------------------------------------------------
def test_build_match_expression_quotes_tokens_and_prefixes_last() -> None:
    assert _build_match_expression("hello world") == '"hello" "world"*'
    assert _build_match_expression("  ") == ""
    # operator-like punctuation is stripped, neutralising injection
    assert _build_match_expression("foo OR bar*") == '"foo" "OR" "bar"*'


def test_search_finds_by_title(repo: EntryRepository, search: SearchService) -> None:
    a = repo.create(title="autumn leaves", body="quiet street")
    repo.create(title="summer storm", body="loud rain")
    results = search.search("autumn")
    assert [e.id for e in results] == [a.id]


def test_search_finds_by_body_and_prefix(
    repo: EntryRepository, search: SearchService
) -> None:
    a = repo.create(title="a", body="the writer toolchain")
    repo.create(title="b", body="something unrelated")
    results = search.search("writ")
    assert a.id in [e.id for e in results]


def test_search_reflects_updates(
    repo: EntryRepository, search: SearchService
) -> None:
    e = repo.create(title="initial", body="placeholder")
    assert search.search("renamed") == []
    repo.update(e.id, title="renamed", body="placeholder")
    assert [r.id for r in search.search("renamed")] == [e.id]


def test_search_empty_query_returns_empty(search: SearchService) -> None:
    assert search.search("") == []
    assert search.search("   ") == []


def test_search_after_delete_excludes_entry(
    repo: EntryRepository, search: SearchService
) -> None:
    e = repo.create(title="ephemeral", body="x")
    assert [r.id for r in search.search("ephemeral")] == [e.id]
    repo.delete(e.id)
    assert search.search("ephemeral") == []


# Assignment consistency (M5) --------------------------------------------
@pytest.fixture()
def project_and_chapter_repos(conn):
    from writer.storage.repositories.chapter_repository import ChapterRepository
    from writer.storage.repositories.project_repository import ProjectRepository

    return ProjectRepository(conn), ChapterRepository(conn)


def test_assign_to_chapter_rejects_cross_project(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p_a = projects.create("A")
    p_b = projects.create("B")
    ch_b = chapters.create(p_b.id, "Ch-B")
    entry = repo.create(title="t", body="b")
    repo.assign_to_project(entry.id, p_a.id)

    with pytest.raises(ValueError):
        repo.assign_to_chapter(entry.id, ch_b.id)

    reloaded = repo.get(entry.id)
    assert reloaded.project_id == p_a.id
    assert reloaded.chapter_id is None


def test_assign_to_chapter_requires_entry_to_have_project(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    entry = repo.create(title="t", body="b")  # no project

    with pytest.raises(ValueError):
        repo.assign_to_chapter(entry.id, ch.id)

    reloaded = repo.get(entry.id)
    assert reloaded.chapter_id is None


def test_assign_to_chapter_rejects_unknown_chapter(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, _chapters = project_and_chapter_repos
    p = projects.create("P")
    entry = repo.create()
    repo.assign_to_project(entry.id, p.id)
    with pytest.raises(ValueError):
        repo.assign_to_chapter(entry.id, "does-not-exist")


def test_changing_project_clears_foreign_chapter(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p_a = projects.create("A")
    p_b = projects.create("B")
    ch_b = chapters.create(p_b.id, "Ch-B")
    entry = repo.create()

    repo.assign_to_project(entry.id, p_b.id)
    repo.assign_to_chapter(entry.id, ch_b.id)
    assert repo.get(entry.id).chapter_id == ch_b.id

    repo.assign_to_project(entry.id, p_a.id)
    reloaded = repo.get(entry.id)
    assert reloaded.project_id == p_a.id
    assert reloaded.chapter_id is None


def test_clearing_project_clears_chapter(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    entry = repo.create()
    repo.assign_to_project(entry.id, p.id)
    repo.assign_to_chapter(entry.id, ch.id)

    repo.assign_to_project(entry.id, None)
    reloaded = repo.get(entry.id)
    assert reloaded.project_id is None
    assert reloaded.chapter_id is None


def test_same_project_chapter_assignment_succeeds(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    entry = repo.create()
    repo.assign_to_project(entry.id, p.id)
    result = repo.assign_to_chapter(entry.id, ch.id)
    assert result is not None
    assert result.chapter_id == ch.id


def test_reassigning_to_same_project_preserves_chapter(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    entry = repo.create()
    repo.assign_to_project(entry.id, p.id)
    repo.assign_to_chapter(entry.id, ch.id)
    repo.assign_to_project(entry.id, p.id)  # same project again
    assert repo.get(entry.id).chapter_id == ch.id


def test_assign_to_chapter_none_clears(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    entry = repo.create()
    repo.assign_to_project(entry.id, p.id)
    repo.assign_to_chapter(entry.id, ch.id)
    result = repo.assign_to_chapter(entry.id, None)
    assert result is not None
    assert result.chapter_id is None
    assert result.project_id == p.id


# Stable sequence_order (M5C) --------------------------------------------
def test_assign_to_project_appends_to_unchaptered(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, _chapters = project_and_chapter_repos
    p = projects.create("P")
    a = repo.create(title="a")
    b = repo.create(title="b")
    c = repo.create(title="c")
    repo.assign_to_project(a.id, p.id)
    repo.assign_to_project(b.id, p.id)
    repo.assign_to_project(c.id, p.id)
    seq = [
        e.sequence_order for e in repo.list_unchaptered_for_project(p.id)
    ]
    assert seq == [0, 1, 2]
    ids = [e.id for e in repo.list_unchaptered_for_project(p.id)]
    assert ids == [a.id, b.id, c.id]


def test_switch_project_clears_chapter_and_appends(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p_a = projects.create("A")
    p_b = projects.create("B")
    ch_b = chapters.create(p_b.id, "Ch-B")

    entry = repo.create()
    repo.assign_to_project(entry.id, p_b.id)
    repo.assign_to_chapter(entry.id, ch_b.id)
    assert repo.get(entry.id).chapter_id == ch_b.id

    # Pre-populate A unchaptered bucket so we can verify "append to end".
    existing = repo.create(title="existing")
    repo.assign_to_project(existing.id, p_a.id)
    assert repo.get(existing.id).sequence_order == 0

    repo.assign_to_project(entry.id, p_a.id)
    reloaded = repo.get(entry.id)
    assert reloaded.project_id == p_a.id
    assert reloaded.chapter_id is None
    assert reloaded.sequence_order == 1


def test_assign_to_chapter_appends_to_chapter_end(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    entries = [repo.create(title=f"e{i}") for i in range(3)]
    for e in entries:
        repo.assign_to_project(e.id, p.id)
        repo.assign_to_chapter(e.id, ch.id)
    listed = repo.list_for_chapter(ch.id)
    assert [e.id for e in listed] == [e.id for e in entries]
    assert [e.sequence_order for e in listed] == [0, 1, 2]


def test_move_chapter_to_unchaptered_appends(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    unch = repo.create()
    repo.assign_to_project(unch.id, p.id)  # seq 0 in unchaptered
    chaptered = repo.create()
    repo.assign_to_project(chaptered.id, p.id)
    repo.assign_to_chapter(chaptered.id, ch.id)

    repo.assign_to_chapter(chaptered.id, None)
    rows = repo.list_unchaptered_for_project(p.id)
    assert [e.id for e in rows] == [unch.id, chaptered.id]
    assert rows[1].sequence_order == 1


def test_reorder_container_rewrites_sequence_order(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    a = repo.create()
    b = repo.create()
    c = repo.create()
    for e in (a, b, c):
        repo.assign_to_project(e.id, p.id)
        repo.assign_to_chapter(e.id, ch.id)

    repo.reorder_container(p.id, ch.id, [c.id, a.id, b.id])
    assert [e.id for e in repo.list_for_chapter(ch.id)] == [c.id, a.id, b.id]


def test_reorder_container_for_unchaptered(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, _chapters = project_and_chapter_repos
    p = projects.create("P")
    a = repo.create(); b = repo.create(); c = repo.create()
    for e in (a, b, c):
        repo.assign_to_project(e.id, p.id)

    repo.reorder_container(p.id, None, [b.id, c.id, a.id])
    assert [
        e.id for e in repo.list_unchaptered_for_project(p.id)
    ] == [b.id, c.id, a.id]


def test_reorder_container_rejects_cross_container(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    a = repo.create(); b = repo.create()
    repo.assign_to_project(a.id, p.id)  # unchaptered
    repo.assign_to_project(b.id, p.id)
    repo.assign_to_chapter(b.id, ch.id)  # chaptered

    with pytest.raises(ValueError):
        # Trying to reorder chapter container with an unchaptered entry.
        repo.reorder_container(p.id, ch.id, [a.id, b.id])


def test_reassign_same_project_preserves_sequence_order(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    a = repo.create(); b = repo.create()
    repo.assign_to_project(a.id, p.id)
    repo.assign_to_project(b.id, p.id)
    repo.assign_to_chapter(b.id, ch.id)
    seq_before = repo.get(b.id).sequence_order

    # Re-assign same project / same chapter — must not shuffle order.
    repo.assign_to_project(b.id, p.id)
    repo.assign_to_chapter(b.id, ch.id)
    assert repo.get(b.id).sequence_order == seq_before


def test_delete_project_clears_sequence_order(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, _chapters = project_and_chapter_repos
    p = projects.create("P")
    e = repo.create()
    repo.assign_to_project(e.id, p.id)
    assert repo.get(e.id).sequence_order == 0

    projects.delete(p.id)
    reloaded = repo.get(e.id)
    assert reloaded.project_id is None
    assert reloaded.chapter_id is None
    assert reloaded.sequence_order is None


def test_delete_chapter_preserves_entry_order_as_unchaptered(
    repo: EntryRepository, project_and_chapter_repos
) -> None:
    projects, chapters = project_and_chapter_repos
    p = projects.create("P")
    ch = chapters.create(p.id, "Ch")
    # existing unchaptered entry
    u = repo.create(title="u"); repo.assign_to_project(u.id, p.id)
    # chaptered in specific order a, b, c
    a = repo.create(title="a"); repo.assign_to_project(a.id, p.id); repo.assign_to_chapter(a.id, ch.id)
    b = repo.create(title="b"); repo.assign_to_project(b.id, p.id); repo.assign_to_chapter(b.id, ch.id)
    c = repo.create(title="c"); repo.assign_to_project(c.id, p.id); repo.assign_to_chapter(c.id, ch.id)

    chapters.delete(ch.id)

    rows = repo.list_unchaptered_for_project(p.id)
    # existing first, then a, b, c in their original chapter order
    assert [e.id for e in rows] == [u.id, a.id, b.id, c.id]
    # sequence_order is monotonically increasing
    seqs = [e.sequence_order for e in rows]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


# ---------------------------------------------------------------------------
# M5E: Tags round-trip, normalization, and query tests
# ---------------------------------------------------------------------------

from writer.storage.repositories.entry_repository import parse_tags, serialize_tags


def test_parse_tags_basic() -> None:
    assert parse_tags("summer, childhood, restraint") == [
        "summer", "childhood", "restraint"
    ]


def test_parse_tags_trims_whitespace() -> None:
    assert parse_tags("  summer  ,  childhood  ") == ["summer", "childhood"]


def test_parse_tags_drops_empty() -> None:
    assert parse_tags(",, hello, , world, ,") == ["hello", "world"]


def test_parse_tags_case_insensitive_dedup_preserves_first() -> None:
    assert parse_tags("Summer, childhood, summer, restraint") == [
        "Summer", "childhood", "restraint"
    ]


def test_parse_tags_all_empty_returns_empty() -> None:
    assert parse_tags("") == []
    assert parse_tags("  , ,  ") == []


def test_serialize_tags_joins_with_comma_space() -> None:
    assert serialize_tags(["summer", "childhood"]) == "summer, childhood"


def test_serialize_tags_empty() -> None:
    assert serialize_tags([]) == ""


def test_create_with_tags_round_trips(repo: EntryRepository) -> None:
    entry = repo.create(title="t", body="b", tags=["summer", "childhood"])
    assert entry.tags == ["summer", "childhood"]
    reloaded = repo.get(entry.id)
    assert reloaded is not None
    assert reloaded.tags == ["summer", "childhood"]


def test_update_with_tags_persists(repo: EntryRepository) -> None:
    entry = repo.create(title="t", body="b")
    assert entry.tags == []
    updated = repo.update(entry.id, title="t", body="b", tags=["autumn", "rain"])
    assert updated is not None
    assert updated.tags == ["autumn", "rain"]
    reloaded = repo.get(entry.id)
    assert reloaded.tags == ["autumn", "rain"]


def test_update_without_tags_preserves_existing(repo: EntryRepository) -> None:
    entry = repo.create(title="t", body="b", tags=["legacy"])
    repo.update(entry.id, title="t2", body="b2")  # no tags kwarg
    reloaded = repo.get(entry.id)
    assert reloaded.tags == ["legacy"]


def test_entry_with_no_tags_has_empty_list(repo: EntryRepository) -> None:
    entry = repo.create(title="t", body="b")
    assert entry.tags == []


def test_list_all_tags_distinct_sorted(repo: EntryRepository) -> None:
    repo.create(tags=["zebra", "apple"])
    repo.create(tags=["banana", "apple"])  # "apple" is a dup
    repo.create(tags=["cherry"])
    all_tags = repo.list_all_tags()
    assert all_tags == sorted(all_tags, key=str.lower)
    # case-insensitive distinct: apple, banana, cherry, zebra
    assert len(all_tags) == 4
    assert all(t in all_tags for t in ["apple", "banana", "cherry", "zebra"])


def test_list_all_tags_empty_when_no_tags(repo: EntryRepository) -> None:
    repo.create(title="t", body="b")
    assert repo.list_all_tags() == []


def test_list_recent_by_tag_returns_matching_entries(
    repo: EntryRepository,
) -> None:
    a = repo.create(title="a", tags=["summer"])
    b = repo.create(title="b", tags=["summer", "rain"])
    repo.create(title="c", tags=["winter"])
    result = repo.list_recent_by_tag("summer")
    ids = [e.id for e in result]
    assert a.id in ids
    assert b.id in ids
    assert "c" not in ids


def test_list_recent_by_tag_case_insensitive(repo: EntryRepository) -> None:
    a = repo.create(title="a", tags=["Summer"])
    result = repo.list_recent_by_tag("summer")
    assert a.id in [e.id for e in result]


def test_list_recent_by_tag_no_false_positives(repo: EntryRepository) -> None:
    repo.create(title="t", body="b")
    result = repo.list_recent_by_tag("summer")
    assert result == []
