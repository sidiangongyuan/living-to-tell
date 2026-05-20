"""Tests for the Markdown and TXT exporters (M5)."""
from __future__ import annotations

import time

import pytest

from writer.app.container import build_container


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def _make_entry(container, *, title, body, project_id=None, chapter_id=None):
    e = container.entry_repository.create(title=title, body=body)
    if project_id is not None:
        container.entry_repository.assign_to_project(e.id, project_id)
    if chapter_id is not None:
        container.entry_repository.assign_to_chapter(e.id, chapter_id)
    return container.entry_repository.get(e.id)


# --------------------------- fragment export ---------------------------
def test_markdown_export_entry(container):
    entry = _make_entry(container, title="Hello", body="World body")
    out = container.markdown_exporter.export_entry(entry)
    assert out == "# Hello\n\nWorld body\n"


def test_text_export_entry(container):
    entry = _make_entry(container, title="Hello", body="World body")
    out = container.text_exporter.export_entry(entry)
    assert out == "Hello\n=====\n\nWorld body\n"


def test_text_export_entry_keeps_epigraph_raw(container):
    body = "世界微尘里，吾宁爱与憎。\n——《北青萝》 李商隐\n\n正文第一段。"
    entry = _make_entry(container, title="Hello", body=body)

    out = container.text_exporter.export_entry(entry)

    assert body in out


def test_export_entry_untitled(container):
    entry = _make_entry(container, title="", body="just body")
    md = container.markdown_exporter.export_entry(entry)
    assert md.startswith("# Untitled\n")


def test_markdown_export_entry_renders_epigraph_once(container):
    entry = _make_entry(
        container,
        title="Hello",
        body="世界微尘里，吾宁爱与憎。\n——《北青萝》 李商隐\n\n正文第一段。",
    )

    out = container.markdown_exporter.export_entry(entry)

    assert "> 世界微尘里，吾宁爱与憎。" in out
    assert "> -- 《北青萝》 李商隐" in out
    assert out.count("世界微尘里，吾宁爱与憎。") == 1
    assert "正文第一段。" in out


# --------------------------- project export ----------------------------
def test_markdown_export_project_ordering(container):
    p = container.project_repository.create("Book", "About stuff")
    ch1 = container.chapter_repository.create(p.id, "One")
    ch2 = container.chapter_repository.create(p.id, "Two")

    e_a = _make_entry(container, title="A", body="aaa", project_id=p.id, chapter_id=ch1.id)
    time.sleep(0.01)
    e_b = _make_entry(container, title="B", body="bbb", project_id=p.id, chapter_id=ch1.id)
    time.sleep(0.01)
    e_c = _make_entry(container, title="C", body="ccc", project_id=p.id, chapter_id=ch2.id)
    time.sleep(0.01)
    _make_entry(container, title="Orphan", body="ooo", project_id=p.id)

    out = container.markdown_exporter.export_project(p)

    # project header + description
    assert out.startswith("# Book\n\nAbout stuff\n")
    # chapter order
    assert out.index("## One") < out.index("## Two") < out.index("## Unchaptered")
    # entry order inside Ch1
    assert out.index("### A") < out.index("### B")
    # bodies present
    for body in ("aaa", "bbb", "ccc", "ooo"):
        assert body in out


def test_text_export_project_structure(container):
    p = container.project_repository.create("Book")
    ch = container.chapter_repository.create(p.id, "One")
    _make_entry(container, title="A", body="aaa", project_id=p.id, chapter_id=ch.id)

    out = container.text_exporter.export_project(p)
    assert out.startswith("Book\n====")
    assert "One\n---" in out
    assert "A\n~\n\naaa" in out


def test_export_reflects_only_accepted_body_not_ai_history(container):
    """AI history versions must never leak into exports."""
    p = container.project_repository.create("Book")
    e = _make_entry(container, title="Chapter", body="accepted body", project_id=p.id)

    # Seed a fake AI version — exporter must ignore it.
    container.version_repository.add(
        entry_id=e.id,
        version_type="ai_generated",
        content="GHOST AI TEXT THAT MUST NOT EXPORT",
        provider="dummy",
        model="dummy",
    )

    md = container.markdown_exporter.export_project(p)
    txt = container.text_exporter.export_project(p)
    assert "accepted body" in md and "accepted body" in txt
    assert "GHOST" not in md and "GHOST" not in txt


def test_markdown_export_skips_empty_chapter_with_no_title(container):
    p = container.project_repository.create("Book")
    container.chapter_repository.create(p.id, "")  # empty and no entries
    out = container.markdown_exporter.export_project(p)
    assert "## " not in out  # no chapter heading at all


def test_reorder_changes_export_order(container):
    p = container.project_repository.create("Book")
    ch1 = container.chapter_repository.create(p.id, "One")
    ch2 = container.chapter_repository.create(p.id, "Two")
    _make_entry(container, title="A", body="aaa", project_id=p.id, chapter_id=ch1.id)
    _make_entry(container, title="B", body="bbb", project_id=p.id, chapter_id=ch2.id)

    container.chapter_repository.reorder(p.id, [ch2.id, ch1.id])
    out = container.markdown_exporter.export_project(p)
    assert out.index("## Two") < out.index("## One")


# --------------- stable ordering regression (M5C) ---------------
def test_editing_entry_does_not_change_export_order(container):
    p = container.project_repository.create("Book")
    ch = container.chapter_repository.create(p.id, "Ch")
    a = _make_entry(container, title="A", body="aa", project_id=p.id, chapter_id=ch.id)
    b = _make_entry(container, title="B", body="bb", project_id=p.id, chapter_id=ch.id)
    c = _make_entry(container, title="C", body="cc", project_id=p.id, chapter_id=ch.id)

    before = container.markdown_exporter.export_project(p)

    # Touch the earliest-created entry so that updated_at becomes the newest.
    # Under the old updated_at-based ordering this would have shuffled A
    # to the end; with explicit sequence_order it must stay first.
    time.sleep(0.01)
    container.entry_repository.update(a.id, title=a.title, body="aa edited")

    after = container.markdown_exporter.export_project(p)
    assert before.index("### A") < before.index("### B") < before.index("### C")
    assert after.index("### A") < after.index("### B") < after.index("### C")


def test_reorder_container_reflects_in_project_export(container):
    p = container.project_repository.create("Book")
    ch = container.chapter_repository.create(p.id, "Ch")
    a = _make_entry(container, title="A", body="aa", project_id=p.id, chapter_id=ch.id)
    b = _make_entry(container, title="B", body="bb", project_id=p.id, chapter_id=ch.id)
    c = _make_entry(container, title="C", body="cc", project_id=p.id, chapter_id=ch.id)

    container.entry_repository.reorder_container(p.id, ch.id, [c.id, a.id, b.id])
    out = container.markdown_exporter.export_project(p)
    assert out.index("### C") < out.index("### A") < out.index("### B")
