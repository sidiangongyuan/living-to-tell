"""Tests for VersionHistoryService (M5D)."""
from __future__ import annotations

import pytest

from writer.app.container import build_container
from writer.domain.enums import VersionType
from writer.services.version_history_service import VersionHistoryService


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def svc(container) -> VersionHistoryService:
    return container.version_history_service


# ------------------------------------------------------------------
# list_history
# ------------------------------------------------------------------

def test_list_history_empty(svc, container):
    entry = container.entry_repository.create(title="t", body="b")
    assert svc.list_history(entry.id) == []


def test_list_history_newest_first(svc, container):
    import time

    entry = container.entry_repository.create(title="t", body="b")
    v1 = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="old"
    )
    time.sleep(0.02)
    v2 = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.AI_POLISH.value, content="polished",
        provider="openai", model="gpt-4o",
    )
    history = svc.list_history(entry.id)
    assert len(history) == 2
    # Newest first (list_for_entry already orders DESC)
    assert history[0].id == v2.id
    assert history[1].id == v1.id


# ------------------------------------------------------------------
# version_type_label
# ------------------------------------------------------------------

def test_version_type_label_known_types():
    assert VersionHistoryService.version_type_label("original") == "Original"
    assert VersionHistoryService.version_type_label("ai_polish") == "AI Polish"
    assert VersionHistoryService.version_type_label("manual_checkpoint") == "Checkpoint"
    assert VersionHistoryService.version_type_label("manual_snapshot") == "Snapshot (pre-restore)"


def test_version_type_label_unknown_falls_back_to_raw():
    assert VersionHistoryService.version_type_label("custom_thing") == "custom_thing"


# ------------------------------------------------------------------
# manual checkpoints
# ------------------------------------------------------------------

def test_save_manual_checkpoint_persists_current_body(svc, container):
    entry = container.entry_repository.create(title="t", body="checkpoint body")

    version = svc.save_manual_checkpoint(entry.id)

    assert version.version_type == VersionType.MANUAL_CHECKPOINT.value
    assert version.content == "checkpoint body"
    assert svc.list_history(entry.id)[0].id == version.id


def test_save_manual_checkpoint_raises_for_missing_entry(svc):
    with pytest.raises(ValueError, match="not found"):
        svc.save_manual_checkpoint("missing-entry")


def test_delete_version_removes_one_history_row(svc, container):
    entry = container.entry_repository.create(title="t", body="body")
    keep = container.version_repository.add(
        entry_id=entry.id,
        version_type=VersionType.ORIGINAL.value,
        content="keep",
    )
    remove = container.version_repository.add(
        entry_id=entry.id,
        version_type=VersionType.MANUAL_CHECKPOINT.value,
        content="remove",
    )

    svc.delete_version(entry.id, remove.id)

    assert [version.id for version in svc.list_history(entry.id)] == [keep.id]


def test_delete_version_rejects_mismatched_entry(svc, container):
    entry = container.entry_repository.create(title="t", body="body")
    other = container.entry_repository.create(title="other", body="body")
    version = container.version_repository.add(
        entry_id=entry.id,
        version_type=VersionType.MANUAL_CHECKPOINT.value,
        content="remove",
    )

    with pytest.raises(ValueError, match="not found"):
        svc.delete_version(other.id, version.id)


# ------------------------------------------------------------------
# restore — happy path
# ------------------------------------------------------------------

def test_restore_replaces_body(svc, container):
    entry = container.entry_repository.create(title="Hello", body="current body")
    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="original body"
    )

    outcome = svc.restore(entry.id, v.id)

    assert outcome.was_noop is False
    assert outcome.new_body == "original body"
    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.body == "original body"


def test_restore_saves_manual_snapshot_before_overwrite(svc, container):
    entry = container.entry_repository.create(title="t", body="live body")
    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="old body"
    )

    outcome = svc.restore(entry.id, v.id)

    assert outcome.snapshot_version_id is not None
    snap = container.version_repository.get(outcome.snapshot_version_id)
    assert snap is not None
    assert snap.version_type == VersionType.MANUAL_SNAPSHOT.value
    assert snap.content == "live body"


def test_restore_does_not_change_title(svc, container):
    entry = container.entry_repository.create(title="My Title", body="current")
    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="old"
    )
    svc.restore(entry.id, v.id)
    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.title == "My Title"


def test_restore_does_not_change_project_or_chapter(svc, container):
    p = container.project_repository.create("P")
    ch = container.chapter_repository.create(p.id, "Ch")
    entry = container.entry_repository.create(title="t", body="current")
    container.entry_repository.assign_to_project(entry.id, p.id)
    container.entry_repository.assign_to_chapter(entry.id, ch.id)
    seq_before = container.entry_repository.get(entry.id).sequence_order

    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="old"
    )
    svc.restore(entry.id, v.id)
    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.project_id == p.id
    assert reloaded.chapter_id == ch.id
    assert reloaded.sequence_order == seq_before


def test_restore_noop_when_content_identical(svc, container):
    entry = container.entry_repository.create(title="t", body="same body")
    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="same body"
    )

    outcome = svc.restore(entry.id, v.id)

    assert outcome.was_noop is True
    assert outcome.snapshot_version_id is None
    # No new version should have been written.
    assert len(svc.list_history(entry.id)) == 1


def test_restore_noop_does_not_write_snapshot(svc, container):
    entry = container.entry_repository.create(title="t", body="same")
    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="same"
    )
    svc.restore(entry.id, v.id)
    # Still only the original version — no MANUAL_SNAPSHOT added.
    all_versions = container.version_repository.list_for_entry(entry.id)
    assert len(all_versions) == 1
    assert all_versions[0].version_type == VersionType.ORIGINAL.value


# ------------------------------------------------------------------
# restore — error handling
# ------------------------------------------------------------------

def test_restore_raises_on_nonexistent_version(svc, container):
    entry = container.entry_repository.create(title="t", body="b")
    with pytest.raises(ValueError, match="not found"):
        svc.restore(entry.id, "nonexistent-version-id")


def test_restore_raises_when_version_belongs_to_different_entry(svc, container):
    a = container.entry_repository.create(title="A", body="a body")
    b = container.entry_repository.create(title="B", body="b body")
    v = container.version_repository.add(
        entry_id=b.id, version_type=VersionType.ORIGINAL.value, content="b original"
    )
    with pytest.raises(ValueError):
        svc.restore(a.id, v.id)


# ------------------------------------------------------------------
# consecutive restores stay recoverable
# ------------------------------------------------------------------

def test_consecutive_restores_each_save_snapshot(svc, container):
    entry = container.entry_repository.create(title="t", body="body-1")
    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="body-0"
    )

    svc.restore(entry.id, v.id)
    # body is now "body-0"; a MANUAL_SNAPSHOT of "body-1" was saved.
    assert container.entry_repository.get(entry.id).body == "body-0"

    # Add another version and restore back.
    v2 = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.AI_POLISH.value, content="body-2"
    )
    svc.restore(entry.id, v2.id)
    assert container.entry_repository.get(entry.id).body == "body-2"

    manual_snaps = [
        h for h in svc.list_history(entry.id)
        if h.version_type == VersionType.MANUAL_SNAPSHOT.value
    ]
    assert len(manual_snaps) == 2
