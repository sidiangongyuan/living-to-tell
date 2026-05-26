"""UI tests for VersionHistoryDialog and MainWindow version history flow (M5D)."""
from __future__ import annotations

import pytest

from writer.app.container import build_container
from writer.domain.enums import VersionType


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


# ------------------------------------------------------------------
# VersionHistoryDialog
# ------------------------------------------------------------------

def test_dialog_empty_state_disables_restore(qtbot, container):
    from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog

    entry = container.entry_repository.create(title="t", body="b")
    dialog = VersionHistoryDialog(
        entry_id=entry.id,
        live_body=entry.body,
        service=container.version_history_service,
    )
    qtbot.addWidget(dialog)

    assert not dialog._restore_btn.isEnabled()  # noqa: SLF001
    assert dialog._version_list.count() == 1  # placeholder item  # noqa: SLF001
    assert dialog.restored_body() is None


def test_dialog_lists_versions(qtbot, container):
    import time

    from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog

    entry = container.entry_repository.create(title="t", body="current")
    container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="orig"
    )
    time.sleep(0.02)
    container.version_repository.add(
        entry_id=entry.id,
        version_type=VersionType.AI_POLISH.value,
        content="polished",
        provider="openai",
        model="gpt-4o",
    )

    dialog = VersionHistoryDialog(
        entry_id=entry.id,
        live_body=entry.body,
        service=container.version_history_service,
    )
    qtbot.addWidget(dialog)

    # Two versions listed.
    assert dialog._version_list.count() == 2  # noqa: SLF001
    # First (newest) item contains the AI_POLISH label.
    first_text = dialog._version_list.item(0).text()  # noqa: SLF001
    assert "AI Polish" in first_text
    assert "openai" in first_text


def test_dialog_selecting_version_enables_restore(qtbot, container):
    from PySide6.QtCore import Qt

    from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog

    entry = container.entry_repository.create(title="t", body="current")
    container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="orig"
    )

    dialog = VersionHistoryDialog(
        entry_id=entry.id,
        live_body=entry.body,
        service=container.version_history_service,
    )
    qtbot.addWidget(dialog)

    dialog._version_list.setCurrentRow(0)  # noqa: SLF001
    assert dialog._restore_btn.isEnabled()  # noqa: SLF001
    # Selected body pane shows the version content.
    assert dialog._selected_edit.toPlainText() == "orig"  # noqa: SLF001


def test_dialog_restore_updates_restored_body(qtbot, container, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog

    entry = container.entry_repository.create(title="t", body="current")
    container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="orig body"
    )

    dialog = VersionHistoryDialog(
        entry_id=entry.id,
        live_body=entry.body,
        service=container.version_history_service,
    )
    qtbot.addWidget(dialog)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: None)
    )

    dialog._version_list.setCurrentRow(0)  # noqa: SLF001
    dialog._on_restore()  # noqa: SLF001

    assert dialog.restored_body() == "orig body"
    # Current pane should have updated.
    assert dialog._current_edit.toPlainText() == "orig body"  # noqa: SLF001


def test_dialog_restore_noop_shows_info_not_error(qtbot, container, monkeypatch):
    """Restoring a version with identical content must not crash."""
    from PySide6.QtWidgets import QMessageBox

    from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog

    entry = container.entry_repository.create(title="t", body="same content")
    container.version_repository.add(
        entry_id=entry.id,
        version_type=VersionType.ORIGINAL.value,
        content="same content",
    )

    dialog = VersionHistoryDialog(
        entry_id=entry.id,
        live_body=entry.body,
        service=container.version_history_service,
    )
    qtbot.addWidget(dialog)

    info_calls: list = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *a, **k: info_calls.append(a)),
    )

    dialog._version_list.setCurrentRow(0)  # noqa: SLF001
    dialog._on_restore()  # noqa: SLF001

    # No restore was done so restored_body stays None.
    assert dialog.restored_body() is None
    assert len(info_calls) == 1  # "Nothing changed" information was shown


# ------------------------------------------------------------------
# MainWindow Version History integration
# ------------------------------------------------------------------

def test_main_window_version_history_reloads_entry_after_restore(
    qtbot, container, monkeypatch
):
    from PySide6.QtWidgets import QDialog

    from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="t", body="live")
    v = container.version_repository.add(
        entry_id=entry.id, version_type=VersionType.ORIGINAL.value, content="original"
    )

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    # Simulate dialog: actually run the restore so the DB is updated,
    # then let restored_body() return the new content.
    def _fake_exec(self_dlg):
        outcome = container.version_history_service.restore(entry.id, v.id)
        self_dlg._restored_body = outcome.new_body  # noqa: SLF001
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(VersionHistoryDialog, "exec", _fake_exec)

    window._on_open_version_history()  # noqa: SLF001

    # After reload the editor should reflect the restored body.
    assert window._editor_panel.body_text() == "original"  # noqa: SLF001


def test_main_window_version_history_no_entry_is_noop(qtbot, container, monkeypatch):
    """Opening Version History with no active entry must not crash."""
    from writer.ui.main_window import MainWindow

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._editor_panel.set_entry(None)  # noqa: SLF001

    # Should silently do nothing.
    window._on_open_version_history()  # noqa: SLF001


def test_main_window_save_checkpoint_flushes_current_fragment(
    qtbot, container, monkeypatch
):
    from PySide6.QtWidgets import QMessageBox

    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="t", body="initial")
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001
    window._editor_panel.replace_body("checkpoint now")  # noqa: SLF001
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok),
    )

    window._on_save_checkpoint()  # noqa: SLF001

    versions = container.version_repository.list_for_entry(entry.id)
    assert len(versions) == 1
    assert versions[0].version_type == VersionType.MANUAL_CHECKPOINT.value
    assert versions[0].content == "checkpoint now"


def test_main_window_manual_save_does_not_create_checkpoint(qtbot, container):
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="t", body="initial")
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001
    window._editor_panel.replace_body("manual save only")  # noqa: SLF001

    window._on_manual_save()  # noqa: SLF001

    assert container.entry_repository.get(entry.id).body == "manual save only"
    assert container.version_repository.list_for_entry(entry.id) == []


# ------------------------------------------------------------------
# Duplicate chapter title fix
# ------------------------------------------------------------------

def test_move_to_chapter_with_duplicate_titles(qtbot, container, monkeypatch):
    """When two chapters share a title the picker must still map to the
    correct chapter id without ambiguity."""
    from PySide6.QtWidgets import QInputDialog

    from writer.ui.panels.project_panel import ProjectPanel

    p = container.project_repository.create("P")
    ch1 = container.chapter_repository.create(p.id, "Part One")
    ch2 = container.chapter_repository.create(p.id, "Part One")  # duplicate title
    ch3 = container.chapter_repository.create(p.id, "Part One")  # third duplicate

    entry = container.entry_repository.create(title="frag")
    container.entry_repository.assign_to_project(entry.id, p.id)

    panel = ProjectPanel(
        container.project_repository,
        container.chapter_repository,
        container.entry_repository,
        container.markdown_exporter,
        container.text_exporter,
    )
    qtbot.addWidget(panel)
    panel.refresh_projects(select_id=p.id)
    panel._chapter_list.setCurrentRow(0)  # Unchaptered  # noqa: SLF001
    panel._entry_list.setCurrentRow(0)  # noqa: SLF001

    # Simulate user picking the second "Part One (2)" which maps to ch2.
    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *a, **k: ("Part One (2)", True))
    )
    panel._on_move_entry_to_chapter()  # noqa: SLF001

    assert container.entry_repository.get(entry.id).chapter_id == ch2.id


def test_move_to_chapter_empty_title_distinguished(qtbot, container, monkeypatch):
    """Empty-title chapters must show as 'Untitled chapter' and be selectable."""
    from PySide6.QtWidgets import QInputDialog

    from writer.ui.panels.project_panel import ProjectPanel

    p = container.project_repository.create("P")
    ch_empty1 = container.chapter_repository.create(p.id, "")
    ch_empty2 = container.chapter_repository.create(p.id, "")  # another empty

    entry = container.entry_repository.create(title="frag")
    container.entry_repository.assign_to_project(entry.id, p.id)

    panel = ProjectPanel(
        container.project_repository,
        container.chapter_repository,
        container.entry_repository,
        container.markdown_exporter,
        container.text_exporter,
    )
    qtbot.addWidget(panel)
    panel.refresh_projects(select_id=p.id)
    panel._chapter_list.setCurrentRow(0)  # Unchaptered  # noqa: SLF001
    panel._entry_list.setCurrentRow(0)  # noqa: SLF001

    # Pick the first "Untitled chapter (1)".
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda *a, **k: ("Untitled chapter (1)", True)),
    )
    panel._on_move_entry_to_chapter()  # noqa: SLF001

    assert container.entry_repository.get(entry.id).chapter_id == ch_empty1.id
