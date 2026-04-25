"""Storage-layer tests for M8 works / sections / collections / refs / versions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from writer.domain.enums import (
    CurationStatus,
    SectionType,
    WorkStatus,
    WorkVersionType,
)
from writer.storage.database import open_and_initialize
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.work_fragment_ref_repository import (
    WorkFragmentRefRepository,
)
from writer.storage.repositories.work_repository import (
    WorkRepository,
    rebuild_works_fts,
)
from writer.storage.repositories.work_section_repository import (
    WorkSectionRepository,
)
from writer.storage.repositories.work_version_repository import (
    WorkVersionRepository,
)


@pytest.fixture()
def conn(tmp_path: Path):
    c = open_and_initialize(tmp_path / "m8.sqlite3")
    try:
        yield c
    finally:
        c.close()


# ---------------------------------------------------------------------------
# WorkRepository
# ---------------------------------------------------------------------------


def test_create_work_defaults(conn) -> None:
    repo = WorkRepository(conn)
    w = repo.create(title="A novel", summary="Hooks")
    assert w.title == "A novel"
    assert w.status == WorkStatus.IDEA.value
    assert w.tags == []
    assert w.archived_at is None


def test_create_work_with_tags_and_target(conn) -> None:
    repo = WorkRepository(conn)
    w = repo.create(title="t", tags=["a", "b"], target_word_count=50000)
    assert w.tags == ["a", "b"]
    assert w.target_word_count == 50000


def test_update_work(conn) -> None:
    repo = WorkRepository(conn)
    w = repo.create(title="t")
    updated = repo.update(w.id, title="t2", summary="s2", tags=["x"])
    assert updated.title == "t2"
    assert updated.summary == "s2"
    assert updated.tags == ["x"]


def test_set_status_validates(conn) -> None:
    repo = WorkRepository(conn)
    w = repo.create(title="t")
    repo.set_status(w.id, WorkStatus.DRAFT.value)
    assert repo.get(w.id).status == WorkStatus.DRAFT.value
    with pytest.raises(ValueError):
        repo.set_status(w.id, "what")


def test_archive_hides_from_default_list(conn) -> None:
    repo = WorkRepository(conn)
    a = repo.create(title="a")
    b = repo.create(title="b")
    repo.set_archived(b.id, True)
    visible = {w.id for w in repo.list_recent()}
    assert a.id in visible
    assert b.id not in visible
    archived = {w.id for w in repo.list_recent(archived_only=True)}
    assert archived == {b.id}


def test_delete_work_cascades_sections_and_fts(conn) -> None:
    repo = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = repo.create(title="t")
    secs.create(w.id, content="hello world")
    repo.delete(w.id)
    assert repo.get(w.id) is None
    assert secs.list_for_work(w.id) == []
    fts = conn.execute(
        "SELECT COUNT(*) AS n FROM works_fts WHERE work_id = ?", (w.id,)
    ).fetchone()
    assert fts["n"] == 0


# ---------------------------------------------------------------------------
# WorkSectionRepository
# ---------------------------------------------------------------------------


def test_create_section_appends_in_order(conn) -> None:
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = works.create(title="t")
    s1 = secs.create(w.id, content="one")
    s2 = secs.create(w.id, content="two")
    s3 = secs.create(w.id, content="three")
    listed = secs.list_for_work(w.id)
    assert [s.id for s in listed] == [s1.id, s2.id, s3.id]
    assert [s.sort_order for s in listed] == [0, 1, 2]


def test_section_type_validation(conn) -> None:
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = works.create(title="t")
    s = secs.create(w.id, section_type=SectionType.HEADING.value, content="Ch1")
    assert s.section_type == SectionType.HEADING.value
    with pytest.raises(ValueError):
        secs.create(w.id, section_type="quote")


def test_move_up_down(conn) -> None:
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = works.create(title="t")
    a = secs.create(w.id, content="a")
    b = secs.create(w.id, content="b")
    c = secs.create(w.id, content="c")
    secs.move(c.id, -1)  # c up by 1
    order = [s.id for s in secs.list_for_work(w.id)]
    assert order == [a.id, c.id, b.id]
    secs.move(a.id, 5)  # clamped to bottom
    order = [s.id for s in secs.list_for_work(w.id)]
    assert order == [c.id, b.id, a.id]


def test_reorder_partial_list_appends_remainder(conn) -> None:
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = works.create(title="t")
    a = secs.create(w.id, content="a")
    b = secs.create(w.id, content="b")
    c = secs.create(w.id, content="c")
    secs.reorder(w.id, [c.id])  # only c specified
    order = [s.id for s in secs.list_for_work(w.id)]
    assert order[0] == c.id
    assert set(order[1:]) == {a.id, b.id}


def test_delete_section_compacts_order(conn) -> None:
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = works.create(title="t")
    a = secs.create(w.id, content="a")
    b = secs.create(w.id, content="b")
    c = secs.create(w.id, content="c")
    secs.delete(b.id)
    order = secs.list_for_work(w.id)
    assert [s.id for s in order] == [a.id, c.id]
    assert [s.sort_order for s in order] == [0, 1]


def test_insert_text_at_clamps(conn) -> None:
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = works.create(title="t")
    s = secs.create(w.id, content="abcdef")
    secs.insert_text_at(s.id, 3, "XYZ")
    assert secs.get(s.id).content == "abcXYZdef"
    secs.insert_text_at(s.id, 999, "!")
    assert secs.get(s.id).content.endswith("!")
    secs.insert_text_at(s.id, -5, "@")
    assert secs.get(s.id).content.startswith("@")


def test_section_changes_rebuild_fts(conn) -> None:
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    w = works.create(title="My Novel", summary="prologue")
    secs.create(w.id, content="lighthouse on the rocks")
    rebuild_works_fts(conn, w.id)  # idempotent re-call OK
    rows = conn.execute(
        "SELECT body FROM works_fts WHERE work_id = ?", (w.id,)
    ).fetchall()
    assert len(rows) == 1
    assert "lighthouse" in rows[0]["body"]


# ---------------------------------------------------------------------------
# CollectionRepository
# ---------------------------------------------------------------------------


def test_collection_add_and_list_works_in_order(conn) -> None:
    works = WorkRepository(conn)
    colls = CollectionRepository(conn)
    coll = colls.create(name="Anthology")
    a = works.create(title="a")
    b = works.create(title="b")
    c = works.create(title="c")
    colls.add_work(coll.id, a.id)
    colls.add_work(coll.id, b.id)
    colls.add_work(coll.id, c.id)
    order = [w.id for w in colls.list_works(coll.id)]
    assert order == [a.id, b.id, c.id]


def test_collection_add_is_idempotent(conn) -> None:
    works = WorkRepository(conn)
    colls = CollectionRepository(conn)
    coll = colls.create(name="X")
    a = works.create(title="a")
    first = colls.add_work(coll.id, a.id)
    again = colls.add_work(coll.id, a.id)
    assert first.id == again.id
    assert len(colls.list_works(coll.id)) == 1


def test_collection_remove_and_compact(conn) -> None:
    works = WorkRepository(conn)
    colls = CollectionRepository(conn)
    coll = colls.create(name="X")
    a = works.create(title="a")
    b = works.create(title="b")
    c = works.create(title="c")
    for w in (a, b, c):
        colls.add_work(coll.id, w.id)
    colls.remove_work(coll.id, b.id)
    rows = conn.execute(
        "SELECT work_id, sort_order FROM collection_items "
        "WHERE collection_id = ? ORDER BY sort_order ASC",
        (coll.id,),
    ).fetchall()
    assert [r["work_id"] for r in rows] == [a.id, c.id]
    assert [r["sort_order"] for r in rows] == [0, 1]


def test_collection_reorder(conn) -> None:
    works = WorkRepository(conn)
    colls = CollectionRepository(conn)
    coll = colls.create(name="X")
    a, b, c = (works.create(title=t) for t in ("a", "b", "c"))
    for w in (a, b, c):
        colls.add_work(coll.id, w.id)
    colls.reorder_works(coll.id, [c.id, a.id, b.id])
    assert [w.id for w in colls.list_works(coll.id)] == [c.id, a.id, b.id]


def test_collection_lookup_by_work(conn) -> None:
    works = WorkRepository(conn)
    colls = CollectionRepository(conn)
    a = works.create(title="a")
    c1 = colls.create(name="c1")
    c2 = colls.create(name="c2")
    colls.add_work(c1.id, a.id)
    colls.add_work(c2.id, a.id)
    found = {c.id for c in colls.list_collections_containing(a.id)}
    assert found == {c1.id, c2.id}


# ---------------------------------------------------------------------------
# WorkFragmentRefRepository
# ---------------------------------------------------------------------------


def test_record_and_query_refs(conn) -> None:
    entries = EntryRepository(conn)
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    refs = WorkFragmentRefRepository(conn)
    e = entries.create(title="frag")
    w = works.create(title="w")
    s = secs.create(w.id, content="")
    refs.record(work_id=w.id, section_id=s.id, entry_id=e.id, included_text="hi")
    by_work = refs.list_for_work(w.id)
    assert len(by_work) == 1
    by_entry = refs.list_for_entry(e.id)
    assert len(by_entry) == 1
    using = refs.list_works_using_entry(e.id)
    assert [x.id for x in using] == [w.id]


def test_section_delete_keeps_ref_with_null_section(conn) -> None:
    entries = EntryRepository(conn)
    works = WorkRepository(conn)
    secs = WorkSectionRepository(conn)
    refs = WorkFragmentRefRepository(conn)
    e = entries.create(title="frag")
    w = works.create(title="w")
    s = secs.create(w.id, content="")
    refs.record(work_id=w.id, section_id=s.id, entry_id=e.id, included_text="hi")
    secs.delete(s.id)
    rows = refs.list_for_work(w.id)
    assert len(rows) == 1
    assert rows[0].section_id is None


def test_entry_delete_cascades_refs(conn) -> None:
    entries = EntryRepository(conn)
    works = WorkRepository(conn)
    refs = WorkFragmentRefRepository(conn)
    e = entries.create(title="frag")
    w = works.create(title="w")
    refs.record(work_id=w.id, section_id=None, entry_id=e.id, included_text="x")
    entries.delete(e.id)
    assert refs.list_for_work(w.id) == []


# ---------------------------------------------------------------------------
# WorkVersionRepository
# ---------------------------------------------------------------------------


def test_work_versions_round_trip(conn) -> None:
    works = WorkRepository(conn)
    versions = WorkVersionRepository(conn)
    w = works.create(title="t")
    payload = json.dumps({"title": "t", "sections": []})
    v = versions.add(
        work_id=w.id,
        version_type=WorkVersionType.MANUAL.value,
        content_json=payload,
        label="initial",
    )
    listed = versions.list_for_work(w.id)
    assert [x.id for x in listed] == [v.id]
    fetched = versions.get(v.id)
    assert fetched.content_json == payload


# ---------------------------------------------------------------------------
# Curation status migration
# ---------------------------------------------------------------------------


def test_entry_default_curation_status(conn) -> None:
    entries = EntryRepository(conn)
    e = entries.create(title="x")
    assert e.curation_status == CurationStatus.UNSORTED.value


def test_entry_set_curation_status(conn) -> None:
    entries = EntryRepository(conn)
    e = entries.create(title="x")
    entries.set_curation_status(e.id, CurationStatus.INCLUDED.value)
    assert entries.get(e.id).curation_status == CurationStatus.INCLUDED.value
    with pytest.raises(ValueError):
        entries.set_curation_status(e.id, "bogus")
