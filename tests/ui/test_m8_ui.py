"""UI tests for M8 panels and dialogs."""
from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtWidgets import QDialog

from writer.app.container import build_container
from writer.domain.enums import CurationStatus, SectionType
from writer.ui.dialogs.global_search_dialog import GlobalSearchDialog
from writer.ui.dialogs.include_fragment_dialog import IncludeFragmentDialog
from writer.ui.dialogs.work_picker_dialog import WorkPickerDialog
from writer.ui.dialogs.work_versions_dialog import WorkVersionsDialog
from writer.ui.panels.collections_panel import CollectionsPanel
from writer.ui.panels.work_editor_panel import WorkEditorPanel
from writer.ui.panels.works_panel import WorksPanel


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


# ---------------------------------------------------------------------------
# WorksPanel + WorkEditorPanel
# ---------------------------------------------------------------------------
def test_works_panel_creates_and_lists_work(qtbot, container):
    panel = WorksPanel(container)
    qtbot.addWidget(panel)
    panel.show()

    assert panel._list.count() == 0
    panel._on_new_work()
    assert panel._list.count() == 1
    # Editor on the right loaded the new work
    assert panel._editor._work_id is not None


def test_work_editor_adds_body_section_and_saves_content(qtbot, container):
    work = container.work_repository.create(title="Demo")
    panel = WorkEditorPanel(container)
    qtbot.addWidget(panel)
    panel.load_work(work.id)
    assert panel._sections.count() == 0

    panel._add_section(SectionType.BODY.value)
    assert panel._sections.count() == 1
    section_id = panel._current_section_id
    assert section_id is not None

    panel._editor.setPlainText("Hello world.")
    panel._flush_section_content()
    refreshed = container.work_section_repository.get(section_id)
    assert refreshed is not None
    assert refreshed.content == "Hello world."


def test_work_editor_move_section_up_down(qtbot, container):
    work = container.work_repository.create(title="W")
    s1 = container.work_section_repository.create(work.id, content="one")
    s2 = container.work_section_repository.create(work.id, content="two")
    s3 = container.work_section_repository.create(work.id, content="three")

    panel = WorkEditorPanel(container)
    qtbot.addWidget(panel)
    panel.load_work(work.id)
    panel.focus_section(s2.id)
    panel._move_section(-1)

    ordered = container.work_section_repository.list_for_work(work.id)
    assert [s.id for s in ordered] == [s2.id, s1.id, s3.id]


def test_work_editor_snapshot_button_writes_version(qtbot, container):
    work = container.work_repository.create(title="X")
    container.work_section_repository.create(work.id, content="body")

    panel = WorkEditorPanel(container)
    qtbot.addWidget(panel)
    panel.load_work(work.id)

    # Patch the success popup so it does not block.
    from PySide6.QtWidgets import QMessageBox
    real_info = QMessageBox.information
    QMessageBox.information = lambda *a, **k: QMessageBox.StandardButton.Ok
    try:
        panel._on_save_snapshot()
    finally:
        QMessageBox.information = real_info

    versions = container.work_version_repository.list_for_work(work.id)
    assert len(versions) == 1


# ---------------------------------------------------------------------------
# IncludeFragmentDialog
# ---------------------------------------------------------------------------
def test_include_fragment_dialog_inserts_into_existing_section(qtbot, container):
    work = container.work_repository.create(title="Target")
    container.work_section_repository.create(work.id, content="Existing.")
    entry = container.entry_repository.create(title="Frag", body="payload")

    dlg = IncludeFragmentDialog(container, entry)
    qtbot.addWidget(dlg)
    # Default selection: first work + first section.
    dlg._editor.setPlainText("INSERTED")
    dlg._on_accept()
    assert dlg.included_outcome is not None

    # Entry is now marked included.
    refreshed_entry = container.entry_repository.get(entry.id)
    assert refreshed_entry is not None
    assert refreshed_entry.curation_status == CurationStatus.INCLUDED.value
    # Section content contains the inserted text.
    sections = container.work_section_repository.list_for_work(work.id)
    assert any("INSERTED" in s.content for s in sections)


def test_include_fragment_dialog_creates_new_section_when_chosen(qtbot, container):
    work = container.work_repository.create(title="Target")
    entry = container.entry_repository.create(title="Frag", body="payload")

    dlg = IncludeFragmentDialog(container, entry)
    qtbot.addWidget(dlg)
    # No existing sections → only the "(new section)" sentinel appears.
    assert dlg._section_combo.count() == 1
    dlg._editor.setPlainText("BRAND NEW")
    dlg._on_accept()

    sections = container.work_section_repository.list_for_work(work.id)
    assert len(sections) == 1
    assert sections[0].content == "BRAND NEW"


# ---------------------------------------------------------------------------
# GlobalSearchDialog
# ---------------------------------------------------------------------------
def test_global_search_dialog_returns_mixed_hits(qtbot, container):
    container.entry_repository.create(title="Findable fragment", body="abc")
    work = container.work_repository.create(title="Findable work")
    container.work_section_repository.create(work.id, content="some prose")

    dlg = GlobalSearchDialog(container)
    qtbot.addWidget(dlg)
    dlg._search.setText("findable")
    # Refresh is wired to textChanged; trigger it explicitly to be safe.
    dlg._refresh()
    assert dlg._results.count() >= 2


# ---------------------------------------------------------------------------
# CollectionsPanel
# ---------------------------------------------------------------------------
def test_collections_panel_create_and_add_work(qtbot, container):
    work = container.work_repository.create(title="W")

    panel = CollectionsPanel(container)
    qtbot.addWidget(panel)
    assert panel._collections.count() == 0

    coll = container.collection_repository.create(name="C1")
    panel.refresh_collections()
    assert panel._collections.count() == 1

    container.collection_repository.add_work(coll.id, work.id)
    # M9A: collections list no longer auto-selects row 0; pick the
    # collection explicitly before refreshing the works subpanel.
    panel._collections.setCurrentRow(0)
    panel._refresh_works()
    assert panel._works.count() == 1


def test_work_picker_dialog_filters(qtbot, container):
    container.work_repository.create(title="Alpha")
    container.work_repository.create(title="Beta")

    dlg = WorkPickerDialog(container)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 2
    dlg._search.setText("alph")
    dlg._refresh()
    assert dlg._list.count() == 1


# ---------------------------------------------------------------------------
# WorkVersionsDialog
# ---------------------------------------------------------------------------
def test_work_versions_dialog_lists_snapshots(qtbot, container):
    work = container.work_repository.create(title="V")
    container.work_section_repository.create(work.id, content="seed")
    container.work_service.save_manual_snapshot(work.id, label="first")
    container.work_service.save_manual_snapshot(work.id, label="second")

    dlg = WorkVersionsDialog(container, work.id)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 2


# ---------------------------------------------------------------------------
# Audit-fix coverage: include-fragment selection + explicit position,
# Works archive UI, single-work export.
# ---------------------------------------------------------------------------
def test_include_fragment_dialog_uses_default_text_for_selection(qtbot, container):
    container.work_repository.create(title="W")
    entry = container.entry_repository.create(
        title="Frag", body="FULL BODY TEXT"
    )

    dlg = IncludeFragmentDialog(container, entry, default_text="ONLY SELECTED")
    qtbot.addWidget(dlg)
    assert dlg._editor.toPlainText() == "ONLY SELECTED"


def test_include_fragment_dialog_falls_back_to_body_when_no_selection(
    qtbot, container
):
    container.work_repository.create(title="W")
    entry = container.entry_repository.create(title="Frag", body="FALLBACK")

    dlg = IncludeFragmentDialog(container, entry, default_text=None)
    qtbot.addWidget(dlg)
    assert dlg._editor.toPlainText() == "FALLBACK"


def test_include_fragment_dialog_inserts_at_explicit_position(qtbot, container):
    work = container.work_repository.create(title="Target")
    section = container.work_section_repository.create(
        work.id, content="ABCDE"
    )
    entry = container.entry_repository.create(title="Frag", body="x")

    dlg = IncludeFragmentDialog(container, entry, default_text="X")
    qtbot.addWidget(dlg)
    # Place insertion at offset 2 ("AB|CDE")
    dlg.set_insert_position(2)
    assert dlg.current_insert_position() == 2
    dlg._on_accept()

    refreshed = container.work_section_repository.get(section.id)
    assert refreshed is not None
    assert refreshed.content == "ABXCDE"


def test_include_fragment_dialog_default_position_appends(qtbot, container):
    work = container.work_repository.create(title="Target")
    section = container.work_section_repository.create(
        work.id, content="ABCDE"
    )
    entry = container.entry_repository.create(title="Frag", body="x")

    dlg = IncludeFragmentDialog(container, entry, default_text="Z")
    qtbot.addWidget(dlg)
    # User just presses OK — default cursor was placed at end.
    assert dlg.current_insert_position() == 5
    dlg._on_accept()

    refreshed = container.work_section_repository.get(section.id)
    assert refreshed is not None
    assert refreshed.content == "ABCDEZ"


def test_works_panel_archive_toggle_visibility(qtbot, container):
    work = container.work_repository.create(title="Archivable")
    panel = WorksPanel(container)
    qtbot.addWidget(panel)

    # Default list shows the new work.
    assert panel._list.count() == 1
    panel._select_id(work.id)

    # Archive it: list should empty (default hides archived).
    panel._on_toggle_archive()
    assert panel._list.count() == 0

    # Toggle "Show archived": work reappears with badge.
    panel._show_archived.setChecked(True)
    assert panel._list.count() == 1
    label = panel._list.item(0).text()
    from writer.ui.i18n import TR

    assert TR("works.archived_badge") in label

    # Unarchive via the same button (now labelled "Unarchive").
    panel._select_id(work.id)
    panel._on_toggle_archive()
    panel._show_archived.setChecked(False)
    assert panel._list.count() == 1
    refreshed = container.work_repository.get(work.id)
    assert refreshed is not None and refreshed.archived_at is None


def test_works_panel_archive_button_label_reflects_state(qtbot, container):
    work = container.work_repository.create(title="W")
    panel = WorksPanel(container)
    qtbot.addWidget(panel)
    panel._select_id(work.id)

    from writer.ui.i18n import TR

    assert panel._archive_btn.text() == TR("works.archive")
    panel._on_toggle_archive()
    panel._show_archived.setChecked(True)
    panel._select_id(work.id)
    assert panel._archive_btn.text() == TR("works.unarchive")


def test_works_panel_export_work_writes_txt_and_md(qtbot, container, tmp_path):
    work = container.work_repository.create(title="Exportable")
    container.work_section_repository.create(
        work.id, content="Hello export."
    )
    panel = WorksPanel(container)
    qtbot.addWidget(panel)
    panel._select_id(work.id)

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    real_save = QFileDialog.getSaveFileName
    real_info = QMessageBox.information

    txt_path = tmp_path / "out.txt"
    md_path = tmp_path / "out.md"
    QMessageBox.information = lambda *a, **k: QMessageBox.StandardButton.Ok
    try:
        QFileDialog.getSaveFileName = lambda *a, **k: (str(txt_path), "")
        panel._on_export_work()
        assert txt_path.exists()
        assert "Hello export." in txt_path.read_text(encoding="utf-8")

        QFileDialog.getSaveFileName = lambda *a, **k: (str(md_path), "")
        panel._on_export_work()
        assert md_path.exists()
        assert "Hello export." in md_path.read_text(encoding="utf-8")
    finally:
        QFileDialog.getSaveFileName = real_save
        QMessageBox.information = real_info


def test_works_panel_export_work_writes_docx(qtbot, container, tmp_path):
    pytest.importorskip("docx")
    work = container.work_repository.create(title="Exportable")
    container.work_section_repository.create(
        work.id, content="Hello docx."
    )
    panel = WorksPanel(container)
    qtbot.addWidget(panel)
    panel._select_id(work.id)

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    real_save = QFileDialog.getSaveFileName
    real_info = QMessageBox.information
    docx_path = tmp_path / "out.docx"
    QMessageBox.information = lambda *a, **k: QMessageBox.StandardButton.Ok
    QFileDialog.getSaveFileName = lambda *a, **k: (str(docx_path), "")
    try:
        panel._on_export_work()
    finally:
        QFileDialog.getSaveFileName = real_save
        QMessageBox.information = real_info

    assert docx_path.exists()
    assert docx_path.stat().st_size > 0

