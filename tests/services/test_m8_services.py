"""Service-layer tests for M8 (WorkService + WorkExportService + global search)."""
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
from writer.services.export.work_exporter import WorkExportService
from writer.services.search_service import SearchService
from writer.services.work_service import WorkService, _word_count
from writer.storage.database import open_and_initialize
from writer.storage.repositories.collection_repository import CollectionRepository
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.work_fragment_ref_repository import (
    WorkFragmentRefRepository,
)
from writer.storage.repositories.work_repository import WorkRepository
from writer.storage.repositories.work_section_repository import (
    WorkSectionRepository,
)
from writer.storage.repositories.work_version_repository import (
    WorkVersionRepository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def conn(tmp_path: Path):
    c = open_and_initialize(tmp_path / "m8svc.sqlite3")
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def repos(conn):
    return {
        "entries": EntryRepository(conn),
        "works": WorkRepository(conn),
        "sections": WorkSectionRepository(conn),
        "refs": WorkFragmentRefRepository(conn),
        "versions": WorkVersionRepository(conn),
        "collections": CollectionRepository(conn),
    }


@pytest.fixture()
def work_service(conn, repos):
    return WorkService(
        conn,
        repos["works"],
        repos["sections"],
        repos["refs"],
        repos["versions"],
        repos["entries"],
    )


@pytest.fixture()
def export_service(repos):
    return WorkExportService(
        repos["works"], repos["sections"], repos["collections"]
    )


# ---------------------------------------------------------------------------
# include_fragment
# ---------------------------------------------------------------------------
def test_include_fragment_appends_to_existing_section_and_marks_entry(
    conn, repos, work_service
):
    work = repos["works"].create(title="Novel")
    section = repos["sections"].create(work.id, content="First paragraph.")
    entry = repos["entries"].create(title="Snippet", body="A snippet.")

    outcome = work_service.include_fragment(
        work_id=work.id,
        section_id=section.id,
        position=None,
        edited_text="Inserted line.",
        entry_id=entry.id,
    )

    refreshed = repos["sections"].get(section.id)
    assert refreshed is not None
    assert "First paragraph." in refreshed.content
    assert "Inserted line." in refreshed.content
    assert outcome.section.id == section.id
    assert outcome.ref.entry_id == entry.id
    assert outcome.ref.section_id == section.id
    assert outcome.ref.included_text == "Inserted line."

    e = repos["entries"].get(entry.id)
    assert e is not None
    assert e.curation_status == CurationStatus.INCLUDED.value


def test_include_fragment_creates_new_section_when_section_id_none(
    repos, work_service
):
    work = repos["works"].create(title="Empty")
    entry = repos["entries"].create(title="x", body="x")

    outcome = work_service.include_fragment(
        work_id=work.id,
        section_id=None,
        position=None,
        edited_text="Brand new section text.",
        entry_id=entry.id,
    )
    sections = repos["sections"].list_for_work(work.id)
    assert len(sections) == 1
    assert sections[0].id == outcome.section.id
    assert sections[0].content == "Brand new section text."
    assert sections[0].section_type == SectionType.BODY.value


def test_include_fragment_inserts_at_position(repos, work_service):
    work = repos["works"].create(title="W")
    section = repos["sections"].create(work.id, content="ABCDE")
    entry = repos["entries"].create(title="t", body="b")

    work_service.include_fragment(
        work_id=work.id,
        section_id=section.id,
        position=2,
        edited_text="!!",
        entry_id=entry.id,
    )
    refreshed = repos["sections"].get(section.id)
    assert refreshed is not None
    assert refreshed.content == "AB!!CDE"


def test_include_fragment_rejects_section_from_other_work(
    repos, work_service
):
    work_a = repos["works"].create(title="A")
    work_b = repos["works"].create(title="B")
    section_b = repos["sections"].create(work_b.id, content="x")
    entry = repos["entries"].create(title="t", body="b")

    with pytest.raises(ValueError):
        work_service.include_fragment(
            work_id=work_a.id,
            section_id=section_b.id,
            position=None,
            edited_text="oops",
            entry_id=entry.id,
        )


def test_include_fragment_rolls_back_on_failure(conn, repos, work_service):
    """If something inside the transaction fails, no partial state remains."""
    work = repos["works"].create(title="W")
    entry = repos["entries"].create(title="t", body="b")
    section = repos["sections"].create(work.id, content="seed")

    # Force a failure during ref recording by passing an invalid section id
    # via direct call — and confirm no curation status flip.
    with pytest.raises(ValueError):
        work_service.include_fragment(
            work_id=work.id,
            section_id="nonexistent-section-id",
            position=None,
            edited_text="text",
            entry_id=entry.id,
        )
    e = repos["entries"].get(entry.id)
    assert e is not None
    assert e.curation_status == CurationStatus.UNSORTED.value


# ---------------------------------------------------------------------------
# Snapshot / restore
# ---------------------------------------------------------------------------
def test_save_manual_snapshot_serialises_full_work(repos, work_service):
    work = repos["works"].create(
        title="Story",
        summary="A summary.",
        tags=["alpha", "beta"],
        target_word_count=5000,
    )
    repos["sections"].create(
        work.id,
        section_type=SectionType.HEADING.value,
        content="Chapter One",
    )
    repos["sections"].create(work.id, content="Body of one.")

    version = work_service.save_manual_snapshot(work.id, label="checkpoint")
    assert version.version_type == WorkVersionType.MANUAL.value
    assert version.label == "checkpoint"

    payload = json.loads(version.content_json)
    assert payload["work"]["title"] == "Story"
    assert payload["work"]["tags"] == ["alpha", "beta"]
    assert payload["work"]["target_word_count"] == 5000
    assert len(payload["sections"]) == 2
    assert payload["sections"][0]["section_type"] == SectionType.HEADING.value
    assert payload["sections"][1]["content"] == "Body of one."


def test_restore_version_replaces_state_and_writes_pre_restore(
    repos, work_service
):
    work = repos["works"].create(title="Original", summary="orig sum")
    s1 = repos["sections"].create(work.id, content="orig section 1")
    repos["sections"].create(work.id, content="orig section 2")
    snapshot = work_service.save_manual_snapshot(work.id)

    # Mutate work after the snapshot.
    repos["works"].update(work.id, title="MUTATED", summary="changed")
    repos["sections"].update_content(s1.id, "MUTATED CONTENT")
    repos["sections"].create(work.id, content="extra section")

    outcome = work_service.restore_version(work.id, snapshot.id)

    assert outcome.work.title == "Original"
    assert outcome.work.summary == "orig sum"
    contents = [s.content for s in outcome.sections]
    assert contents == ["orig section 1", "orig section 2"]

    # A pre-restore snapshot was saved.
    assert outcome.pre_restore_version.version_type == (
        WorkVersionType.PRE_RESTORE.value
    )
    pre_payload = json.loads(outcome.pre_restore_version.content_json)
    assert pre_payload["work"]["title"] == "MUTATED"


def test_restore_version_rejects_mismatched_work(repos, work_service):
    work_a = repos["works"].create(title="A")
    work_b = repos["works"].create(title="B")
    snap_a = work_service.save_manual_snapshot(work_a.id)
    with pytest.raises(ValueError):
        work_service.restore_version(work_b.id, snap_a.id)


# ---------------------------------------------------------------------------
# Word count
# ---------------------------------------------------------------------------
def test_compute_word_count_handles_cjk_and_latin(repos, work_service):
    work = repos["works"].create(title="W")
    repos["sections"].create(work.id, content="Hello world from python")
    repos["sections"].create(work.id, content="你好 世界")
    assert work_service.compute_word_count(work.id) == 4 + 4


def test_word_count_helper_edge_cases():
    assert _word_count("") == 0
    assert _word_count("   ") == 0
    assert _word_count("one two three") == 3
    assert _word_count("中文测试") == 4


# ---------------------------------------------------------------------------
# Global search
# ---------------------------------------------------------------------------
def test_search_all_returns_fragments_and_works(conn, repos, work_service):
    repos["entries"].create(title="Alpha entry", body="dragons appear here")
    work = repos["works"].create(title="Dragon Tales", summary="big book")
    repos["sections"].create(work.id, content="Once upon a dragon time")

    svc = SearchService(conn)
    hits = svc.search_all("dragon")
    kinds = {h.kind for h in hits}
    assert kinds == {"fragment", "work"}

    work_hit = next(h for h in hits if h.kind == "work")
    assert work_hit.id == work.id
    assert work_hit.section_id is not None  # locator filled in


def test_search_works_only(conn, repos):
    repos["works"].create(title="Salamander chronicles")
    svc = SearchService(conn)
    works = svc.search_works("salamander")
    assert len(works) == 1
    assert "Salamander" in works[0].title


def test_search_returns_empty_for_no_query(conn):
    svc = SearchService(conn)
    assert svc.search("") == []
    assert svc.search_all("   ") == []
    assert svc.search_works("!!!") == []


# ---------------------------------------------------------------------------
# Exporters: text + markdown
# ---------------------------------------------------------------------------
def test_export_work_txt_and_md(repos, export_service):
    work = repos["works"].create(title="Solo Work", summary="A summary line.")
    repos["sections"].create(
        work.id,
        section_type=SectionType.HEADING.value,
        content="Chapter 1",
    )
    repos["sections"].create(work.id, content="The body of chapter one.")

    txt = export_service.export_work_txt(work.id)
    assert "Solo Work" in txt
    assert "A summary line." in txt
    assert "Chapter 1" in txt
    assert "The body of chapter one." in txt

    md = export_service.export_work_md(work.id)
    assert "# Solo Work" in md
    assert "## Chapter 1" in md
    assert "The body of chapter one." in md


def test_export_collection_txt_and_md_includes_toc(repos, export_service):
    coll = repos["collections"].create(name="Anthology", description="desc")
    w1 = repos["works"].create(title="One")
    w2 = repos["works"].create(title="Two")
    repos["sections"].create(w1.id, content="alpha")
    repos["sections"].create(w2.id, content="beta")
    repos["collections"].add_work(coll.id, w1.id)
    repos["collections"].add_work(coll.id, w2.id)

    txt = export_service.export_collection_txt(coll.id)
    assert "Anthology" in txt
    assert "Contents" in txt
    assert "1. One" in txt
    assert "2. Two" in txt
    assert "alpha" in txt and "beta" in txt

    md = export_service.export_collection_md(coll.id)
    assert "# Anthology" in md
    assert "## Contents" in md
    assert "1. One" in md
    # Each work title is rendered as a heading inside the collection.
    assert "## One" in md and "## Two" in md


# ---------------------------------------------------------------------------
# Exporter: docx (only runs if python-docx is importable)
# ---------------------------------------------------------------------------
def test_export_work_docx_writes_file(tmp_path, repos, export_service):
    pytest.importorskip("docx")
    work = repos["works"].create(title="Docx Work", summary="x")
    repos["sections"].create(work.id, content="Hello docx world.")
    out = tmp_path / "out.docx"
    result = export_service.export_work_docx(work.id, str(out))
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_export_collection_docx_writes_file(tmp_path, repos, export_service):
    pytest.importorskip("docx")
    coll = repos["collections"].create(name="C")
    work = repos["works"].create(title="W")
    repos["sections"].create(work.id, content="x")
    repos["collections"].add_work(coll.id, work.id)
    out = tmp_path / "coll.docx"
    export_service.export_collection_docx(coll.id, str(out))
    assert out.exists()
    assert out.stat().st_size > 0
