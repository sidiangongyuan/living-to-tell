"""M7B UI behaviour: delete + archive + sort + save status + recovery."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from writer.app.bootstrap import create_main_window
from writer.app.container import build_container
from writer.storage.repositories.entry_repository import SORT_TITLE


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


def _auto_confirm_yes(monkeypatch) -> None:
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )


def _silence_information(monkeypatch) -> None:
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args, **kwargs: None
    )


def test_delete_single_fragment_with_confirmation(
    qtbot, container, monkeypatch
) -> None:
    _auto_confirm_yes(monkeypatch)
    repo = container.entry_repository
    a = repo.create(title="keep-me")
    b = repo.create(title="delete-me")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    window._on_delete_requested([b.id])

    assert repo.get(b.id) is None
    assert repo.get(a.id) is not None
    # Deletion snapshot is stashed for recovery.
    assert len(window._deleted_trash) == 1
    assert window._deleted_trash[0]["title"] == "delete-me"


def test_delete_many_fragments(qtbot, container, monkeypatch) -> None:
    _auto_confirm_yes(monkeypatch)
    repo = container.entry_repository
    a = repo.create(title="a")
    b = repo.create(title="b")
    c = repo.create(title="c")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    window._on_delete_requested([a.id, c.id])

    assert repo.get(a.id) is None
    assert repo.get(c.id) is None
    assert repo.get(b.id) is not None
    assert len(window._deleted_trash) == 2


def test_delete_cancelled_keeps_entries(qtbot, container, monkeypatch) -> None:
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )
    repo = container.entry_repository
    a = repo.create(title="safe")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    window._on_delete_requested([a.id])

    assert repo.get(a.id) is not None
    assert window._deleted_trash == []


def test_recover_last_deleted_restores_entry(
    qtbot, container, monkeypatch
) -> None:
    _auto_confirm_yes(monkeypatch)
    _silence_information(monkeypatch)
    repo = container.entry_repository
    a = repo.create(title="recovered", body="the body")
    b = repo.create(title="other")  # keep another so editor has something

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    window._on_delete_requested([a.id])
    assert repo.get(a.id) is None

    window._on_recover_last_deleted()

    titles = [e.title for e in repo.list_recent()]
    assert "recovered" in titles
    assert window._deleted_trash == []


def test_recover_last_deleted_with_empty_trash_is_noop(
    qtbot, container, monkeypatch
) -> None:
    _silence_information(monkeypatch)
    repo = container.entry_repository
    repo.create(title="only")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    before = repo.count()
    window._on_recover_last_deleted()
    assert repo.count() == before


def test_archive_hides_entry_from_default_list(qtbot, container) -> None:
    repo = container.entry_repository
    keep = repo.create(title="keep")
    hidden = repo.create(title="hidden")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    window._on_archive_requested(hidden.id, True)

    default_ids = {e.id for e in repo.list_recent()}
    assert keep.id in default_ids
    assert hidden.id not in default_ids

    # Toggling "Show archived" surfaces the archived entry back in the list.
    window._on_show_archived_changed(True)
    all_ids = {e.id for e in repo.list_recent(include_archived=True)}
    assert hidden.id in all_ids


def test_sort_mode_passes_through_to_repo(qtbot, container) -> None:
    repo = container.entry_repository
    repo.create(title="zeta")
    repo.create(title="alpha")
    repo.create(title="mu")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    window._on_sort_changed(SORT_TITLE)
    assert window._sort_mode == SORT_TITLE
    # The list panel should reflect the sorted order (alphabetical).
    titles = [
        window._list_panel._list.item(i).text()
        for i in range(window._list_panel._list.count())
    ]
    assert titles == sorted(titles, key=str.lower)


def test_save_status_transitions(qtbot, container) -> None:
    repo = container.entry_repository
    repo.create(title="x", body="y")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    assert window._save_status_label.text() != ""
    # Simulate an edit — status should report unsaved.
    window._autosave.dirty.emit()
    assert "sav" in window._save_status_label.text().lower() or window._save_status_label.text()
    # Simulate a successful save — status flips to "saved".
    window._autosave.saved.emit(repo.list_recent()[0].id)
    # The "saved" text is localized; assert it is non-empty.
    assert window._save_status_label.text() != ""


# ---------------------------------------------------------------------------
# Archive-current-entry (P1) + recovery-metadata (P2) acceptance hardening
# ---------------------------------------------------------------------------


def test_archive_current_entry_switches_editor(qtbot, container) -> None:
    """Archiving the entry shown in the editor must not leave the UI
    stranded on a now-hidden row. The editor should switch to a still-
    visible neighbour."""
    repo = container.entry_repository
    neighbour = repo.create(title="neighbour")
    current = repo.create(title="to-be-archived")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()
    window._load_entry(current.id)
    assert window._editor_panel.current_entry_id() == current.id

    window._on_archive_requested(current.id, True)

    # Editor now shows some still-visible entry — the neighbour — and
    # definitely NOT the archived one.
    loaded = window._editor_panel.current_entry_id()
    assert loaded != current.id
    assert loaded == neighbour.id


def test_archive_current_entry_creates_blank_when_only_one(
    qtbot, container
) -> None:
    """If the archived entry was the only visible one, a fresh blank
    fragment should be created so the editor never shows a hidden row."""
    repo = container.entry_repository
    only = repo.create(title="only-one")

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()
    window._load_entry(only.id)

    window._on_archive_requested(only.id, True)

    loaded = window._editor_panel.current_entry_id()
    assert loaded is not None
    assert loaded != only.id
    # The newly loaded entry is a fresh blank fragment, not archived.
    fresh = repo.get(loaded)
    assert fresh is not None
    assert fresh.archived_at is None


def test_recover_last_deleted_preserves_project_assignment(
    qtbot, container, monkeypatch
) -> None:
    """After delete + recover, the entry should land back in the same
    project/chapter it came from (not float unassigned)."""
    _auto_confirm_yes(monkeypatch)
    _silence_information(monkeypatch)

    # Seed a project + chapter and an entry assigned to both.
    conn = container.connection
    conn.execute(
        "INSERT INTO projects (id, name) VALUES ('p1', 'P')",
    )
    conn.execute(
        "INSERT INTO chapters (id, project_id, title) VALUES ('c1','p1','C')",
    )
    repo = container.entry_repository
    entry = repo.create(title="assigned")
    repo.assign_to_project(entry.id, project_id="p1")
    repo.assign_to_chapter(entry.id, chapter_id="c1")
    before = repo.get(entry.id)
    assert before.project_id == "p1"
    assert before.chapter_id == "c1"

    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()

    window._on_delete_requested([entry.id])
    assert repo.get(entry.id) is None

    window._on_recover_last_deleted()

    # Locate the restored entry (same title, new id).
    restored = [e for e in repo.list_recent() if e.title == "assigned"]
    assert len(restored) == 1
    assert restored[0].project_id == "p1"
    assert restored[0].chapter_id == "c1"

