"""UI smoke tests for M5 project/export flows."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_project_panel_crud(qtbot, container):
    from writer.ui.panels.project_panel import ProjectPanel

    panel = ProjectPanel(
        container.project_repository,
        container.chapter_repository,
        container.entry_repository,
        container.markdown_exporter,
        container.text_exporter,
    )
    qtbot.addWidget(panel)

    # create project via repo (bypass QInputDialog)
    project = container.project_repository.create("MyBook")
    panel.refresh_projects(select_id=project.id)
    assert panel.current_project().id == project.id

    # create chapters, verify ordering controls
    ch1 = container.chapter_repository.create(project.id, "One")
    ch2 = container.chapter_repository.create(project.id, "Two")
    panel._refresh_chapters(project.id, select_id=ch1.id)  # noqa: SLF001

    # move chapter down
    panel._move_chapter(1)  # noqa: SLF001
    ordered = [c.id for c in container.chapter_repository.list_for_project(project.id)]
    assert ordered == [ch2.id, ch1.id]


def test_assign_fragment_dialog_lists_projects_and_chapters(qtbot, container):
    from writer.ui.dialogs.assign_fragment_dialog import AssignFragmentDialog

    p = container.project_repository.create("P")
    ch = container.chapter_repository.create(p.id, "Ch1")
    entry = container.entry_repository.create(title="t", body="b")

    dialog = AssignFragmentDialog(
        container.project_repository,
        container.chapter_repository,
        current_project_id=None,
        current_chapter_id=None,
    )
    qtbot.addWidget(dialog)

    # set project to P -> chapters should populate
    idx = dialog._project_combo.findData(p.id)  # noqa: SLF001
    dialog._project_combo.setCurrentIndex(idx)  # noqa: SLF001
    assert dialog.selected_project_id() == p.id
    assert dialog._chapter_combo.count() == 2  # noqa: SLF001  (no-chapter + ch1)

    idx = dialog._chapter_combo.findData(ch.id)  # noqa: SLF001
    dialog._chapter_combo.setCurrentIndex(idx)  # noqa: SLF001
    assert dialog.selected_chapter_id() == ch.id

    # switching back to no-project disables chapter combo
    dialog._project_combo.setCurrentIndex(0)  # noqa: SLF001
    assert dialog.selected_project_id() is None
    assert dialog._chapter_combo.isEnabled() is False  # noqa: SLF001


def test_main_window_assign_updates_entry(qtbot, container, monkeypatch):
    from writer.ui import main_window as main_window_module
    from writer.ui.main_window import MainWindow

    p = container.project_repository.create("P")
    ch = container.chapter_repository.create(p.id, "Ch")
    entry = container.entry_repository.create(title="t", body="body")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    def _fake_exec(self):
        idx = self._project_combo.findData(p.id)  # noqa: SLF001
        self._project_combo.setCurrentIndex(idx)  # noqa: SLF001
        idx = self._chapter_combo.findData(ch.id)  # noqa: SLF001
        self._chapter_combo.setCurrentIndex(idx)  # noqa: SLF001
        return self.DialogCode.Accepted

    monkeypatch.setattr(
        main_window_module.AssignFragmentDialog, "exec", _fake_exec
    )

    window._on_assign_fragment()  # noqa: SLF001

    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.project_id == p.id
    assert reloaded.chapter_id == ch.id


def test_main_window_export_fragment_writes_file(
    qtbot, container, monkeypatch, tmp_path: Path
):
    from PySide6.QtWidgets import QFileDialog

    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="Hi", body="Some body")
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    target = tmp_path / "out.md"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), "")
    )

    window._on_export("fragment", "markdown")  # noqa: SLF001

    written = target.read_text(encoding="utf-8")
    assert written.startswith("# Hi\n")
    assert "Some body" in written


def test_main_window_export_project_requires_assignment(
    qtbot, container, monkeypatch
):
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="orphan", body="nope")
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    info_calls: list = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *a, **k: info_calls.append(a),
    )
    # Getting here would be a bug; assert we never do.
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not save")),
    )

    window._on_export("project", "markdown")  # noqa: SLF001
    assert len(info_calls) == 1


def test_main_window_export_project_full_flow(
    qtbot, container, monkeypatch, tmp_path: Path
):
    from PySide6.QtWidgets import QFileDialog

    from writer.ui.main_window import MainWindow

    p = container.project_repository.create("Book")
    ch = container.chapter_repository.create(p.id, "Intro")
    entry = container.entry_repository.create(title="Ch1", body="chapter body")
    container.entry_repository.assign_to_project(entry.id, p.id)
    container.entry_repository.assign_to_chapter(entry.id, ch.id)

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    target = tmp_path / "book.txt"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), "")
    )

    window._on_export("project", "text")  # noqa: SLF001

    out = target.read_text(encoding="utf-8")
    assert out.startswith("Book\n====")
    assert "Intro" in out
    assert "chapter body" in out


def test_main_window_assign_warns_on_cross_project_chapter(
    qtbot, container, monkeypatch
):
    """If the assign dialog somehow hands back a chapter from another
    project, the repository rejects it and MainWindow shows a warning
    instead of crashing."""
    from writer.ui import main_window as main_window_module
    from writer.ui.main_window import MainWindow

    p_a = container.project_repository.create("A")
    p_b = container.project_repository.create("B")
    ch_b = container.chapter_repository.create(p_b.id, "Ch-B")
    entry = container.entry_repository.create(title="t", body="b")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    # Force the dialog to return (project=A, chapter=ch_b from B).
    def _fake_exec(self):
        return self.DialogCode.Accepted

    monkeypatch.setattr(
        main_window_module.AssignFragmentDialog, "exec", _fake_exec
    )
    monkeypatch.setattr(
        main_window_module.AssignFragmentDialog,
        "selected_project_id",
        lambda self: p_a.id,
    )
    monkeypatch.setattr(
        main_window_module.AssignFragmentDialog,
        "selected_chapter_id",
        lambda self: ch_b.id,
    )

    warn_calls: list = []
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warn_calls.append(a)
    )

    window._on_assign_fragment()  # noqa: SLF001

    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.project_id == p_a.id
    assert reloaded.chapter_id is None
    assert len(warn_calls) == 1


# =================== M5C: project workspace ===================
def _build_panel(qtbot, container):
    from writer.ui.panels.project_panel import ProjectPanel

    panel = ProjectPanel(
        container.project_repository,
        container.chapter_repository,
        container.entry_repository,
        container.markdown_exporter,
        container.text_exporter,
    )
    qtbot.addWidget(panel)
    return panel


def test_project_panel_shows_unchaptered_and_chapters(qtbot, container):
    from writer.ui.panels.project_panel import _UNCHAPTERED_SENTINEL

    p = container.project_repository.create("P")
    ch = container.chapter_repository.create(p.id, "Ch")

    panel = _build_panel(qtbot, container)
    panel.refresh_projects(select_id=p.id)

    # Row 0 is the Unchaptered sentinel; row 1 is the chapter.
    from PySide6.QtCore import Qt

    assert panel._chapter_list.count() == 2  # noqa: SLF001
    assert (
        panel._chapter_list.item(0).data(Qt.ItemDataRole.UserRole)
        == _UNCHAPTERED_SENTINEL
    )
    assert panel._chapter_list.item(1).data(Qt.ItemDataRole.UserRole) == ch.id


def test_project_panel_entry_move_updates_sequence(qtbot, container):
    p = container.project_repository.create("P")
    a = container.entry_repository.create(title="A")
    b = container.entry_repository.create(title="B")
    container.entry_repository.assign_to_project(a.id, p.id)
    container.entry_repository.assign_to_project(b.id, p.id)

    panel = _build_panel(qtbot, container)
    panel.refresh_projects(select_id=p.id)
    # select Unchaptered section, first entry (A)
    panel._chapter_list.setCurrentRow(0)  # noqa: SLF001
    panel._entry_list.setCurrentRow(0)  # noqa: SLF001

    panel._move_entry(1)  # noqa: SLF001 move A down
    ordered = [
        e.id for e in container.entry_repository.list_unchaptered_for_project(p.id)
    ]
    assert ordered == [b.id, a.id]


def test_project_panel_move_to_chapter_and_back(qtbot, container, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    p = container.project_repository.create("P")
    ch = container.chapter_repository.create(p.id, "Ch")
    e = container.entry_repository.create(title="frag")
    container.entry_repository.assign_to_project(e.id, p.id)

    panel = _build_panel(qtbot, container)
    panel.refresh_projects(select_id=p.id)
    panel._chapter_list.setCurrentRow(0)  # Unchaptered  # noqa: SLF001
    panel._entry_list.setCurrentRow(0)  # noqa: SLF001

    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *a, **k: ("Ch", True))
    )
    panel._on_move_entry_to_chapter()  # noqa: SLF001
    assert container.entry_repository.get(e.id).chapter_id == ch.id

    panel._on_move_entry_to_unchaptered()  # noqa: SLF001
    reloaded = container.entry_repository.get(e.id)
    assert reloaded.chapter_id is None
    assert reloaded.project_id == p.id


def test_project_panel_remove_from_project(qtbot, container, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    p = container.project_repository.create("P")
    e = container.entry_repository.create(title="frag")
    container.entry_repository.assign_to_project(e.id, p.id)

    panel = _build_panel(qtbot, container)
    panel.refresh_projects(select_id=p.id)
    panel._chapter_list.setCurrentRow(0)  # noqa: SLF001
    panel._entry_list.setCurrentRow(0)  # noqa: SLF001

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    panel._on_remove_entry()  # noqa: SLF001

    reloaded = container.entry_repository.get(e.id)
    assert reloaded.project_id is None
    assert reloaded.sequence_order is None


def test_project_panel_description_edit_persists(qtbot, container):
    p = container.project_repository.create("P")
    panel = _build_panel(qtbot, container)
    panel.refresh_projects(select_id=p.id)

    panel._description_edit.setPlainText("A short blurb.")  # noqa: SLF001
    panel._on_save_description()  # noqa: SLF001

    reloaded = container.project_repository.get(p.id)
    assert reloaded.description == "A short blurb."


def test_project_panel_inline_export_markdown(qtbot, container, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QFileDialog

    p = container.project_repository.create("Book")
    ch = container.chapter_repository.create(p.id, "Intro")
    e = container.entry_repository.create(title="Ch1", body="chapter body")
    container.entry_repository.assign_to_project(e.id, p.id)
    container.entry_repository.assign_to_chapter(e.id, ch.id)

    panel = _build_panel(qtbot, container)
    panel.refresh_projects(select_id=p.id)

    target = tmp_path / "book.md"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), "")
    )
    panel._on_export("markdown")  # noqa: SLF001

    out = target.read_text(encoding="utf-8")
    assert out.startswith("# Book")
    assert "## Intro" in out
    assert "chapter body" in out

