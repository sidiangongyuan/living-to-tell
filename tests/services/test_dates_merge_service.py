"""Tests for the dates → merge-to-draft service helpers (M-Dates)."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container
from writer.services.dates_merge_service import (
    MergeOutputType,
    build_merge_plan,
    save_merged_draft_as_fragment,
)


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_build_merge_plan_includes_all_bodies_and_instructions(container):
    repo = container.entry_repository
    a = repo.create(title="Day 1", body="hello-aaa")
    b = repo.create(title="Day 2", body="world-bbb")

    plan = build_merge_plan([a, b], MergeOutputType.PROSE)

    assert plan.source_ids == (a.id, b.id)
    text = plan.request.text
    assert "hello-aaa" in text
    assert "world-bbb" in text
    # Instructions reflect the chosen output type.
    assert "prose" in (plan.request.extra_instructions or "").lower()


def test_build_merge_plan_section_and_outline_pick_distinct_tasks(container):
    repo = container.entry_repository
    a = repo.create(title="t", body="aaa")
    b = repo.create(title="t", body="bbb")

    p_section = build_merge_plan([a, b], MergeOutputType.SECTION)
    p_outline = build_merge_plan([a, b], MergeOutputType.OUTLINE)

    assert p_section.request.task_type != p_outline.request.task_type
    assert "outline" in (p_outline.request.extra_instructions or "").lower()


def test_build_merge_plan_rejects_empty():
    with pytest.raises(ValueError):
        build_merge_plan([], MergeOutputType.PROSE)


def test_save_merged_draft_creates_new_fragment_with_source_footer(container):
    repo = container.entry_repository
    a = repo.create(title="x", body="aaa")
    b = repo.create(title="y", body="bbb")
    a_body_before, b_body_before = a.body, b.body

    new_entry = save_merged_draft_as_fragment(
        repo,
        "merged body text",
        title="Merged",
        source_ids=[a.id, b.id],
    )

    # New entry exists with footer.
    fetched = repo.get(new_entry.id)
    assert fetched.title == "Merged"
    assert "merged body text" in fetched.body
    assert "Sources:" in fetched.body
    assert a.id in fetched.body and b.id in fetched.body
    # The "merged" tag is auto-applied.
    assert "merged" in fetched.tags

    # Source entries are untouched.
    assert repo.get(a.id).body == a_body_before
    assert repo.get(b.id).body == b_body_before
