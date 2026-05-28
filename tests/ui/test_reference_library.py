"""UI tests for the reference library panel and picker dialog (M4A)."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_library_panel_create_edit_delete(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    panel = ReferenceLibraryPanel(container.reference_repository)
    qtbot.addWidget(panel)

    panel._on_new()  # noqa: SLF001
    panel._title_edit.setText("Moby Dick")  # noqa: SLF001
    panel._author_edit.setText("Melville")  # noqa: SLF001
    panel._content_edit.setPlainText("Call me Ishmael.")  # noqa: SLF001
    panel._on_save()  # noqa: SLF001
    assert container.reference_repository.count() == 1
    assert "1" in panel._stat_labels["total"].text()  # noqa: SLF001
    assert panel._group_list.count() == 2  # noqa: SLF001
    assert "《Moby Dick》" in panel._book_header_title.text()  # noqa: SLF001

    # select, edit
    panel._list.setCurrentRow(0)  # noqa: SLF001
    assert panel._title_edit.text() == "Moby Dick"  # noqa: SLF001
    panel._author_edit.setText("H. Melville")  # noqa: SLF001
    panel._on_save()  # noqa: SLF001
    loaded = container.reference_repository.list_recent()[0]
    assert loaded.source_author == "H. Melville"

    # search filters
    panel._search.setText("zzz_no_match_zzz")  # noqa: SLF001
    assert panel._list.count() == 0  # noqa: SLF001
    panel._search.clear()  # noqa: SLF001
    assert panel._list.count() == 1  # noqa: SLF001

    # delete via repo directly (bypass confirm dialog)
    container.reference_repository.delete(loaded.id)
    panel.refresh()
    assert panel._list.count() == 0  # noqa: SLF001


def test_reference_library_filters_ignore_mouse_wheel(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    class _Wheel:
        ignored = False

        def ignore(self):
            self.ignored = True

    panel = ReferenceLibraryPanel(container.reference_repository)
    qtbot.addWidget(panel)

    controls = [
        panel._kind_filter_combo,  # noqa: SLF001
        panel._usage_kind_filter_combo,  # noqa: SLF001
        panel._group_mode_combo,  # noqa: SLF001
        panel._kind_combo,  # noqa: SLF001
        panel._usage_kind_combo,  # noqa: SLF001
    ]
    for control in controls:
        before = control.currentIndex()
        event = _Wheel()
        control.wheelEvent(event)  # noqa: SLF001
        assert event.ignored is True
        assert control.currentIndex() == before


def test_reference_library_dialog_enables_resize_controls(qtbot, container):
    from PySide6.QtCore import Qt

    from writer.ui.dialogs.reference_library_dialog import ReferenceLibraryDialog

    dialog = ReferenceLibraryDialog(container.reference_repository)
    qtbot.addWidget(dialog)

    assert dialog.minimumWidth() >= 980
    assert dialog.minimumHeight() >= 680
    assert dialog.isSizeGripEnabled() is True
    assert bool(dialog.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint)


def test_library_panel_shows_stats_cards(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    repo = container.reference_repository
    repo.create(source_title="A", content="same text", tags="moon", usage_kind="imagery")
    repo.create(source_title="B", content="same text", tags="moon", usage_kind="imagery")

    panel = ReferenceLibraryPanel(repo)
    qtbot.addWidget(panel)

    assert "2" in panel._stat_labels["total"].text()  # noqa: SLF001
    assert "moon" in panel._stat_labels["tags"].text()  # noqa: SLF001
    assert "2" in panel._stat_labels["duplicates"].text()  # noqa: SLF001

    buttons = panel._stats_tab_group.buttons()  # noqa: SLF001
    tags_button = next(
        button for button in buttons if button.text() in {"Tags", "标签"}
    )
    tags_button.click()
    assert panel._stats_stack.currentWidget() is panel._stats_pages["tags"]  # noqa: SLF001


def test_library_panel_card_delete_button_removes_target_passage(
    qtbot, container, monkeypatch
):
    from PySide6.QtWidgets import QMessageBox

    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    repo = container.reference_repository
    keep = repo.create(source_title="Keep", content="keep body")
    drop = repo.create(source_title="Drop", content="drop body")

    monkeypatch.setattr(
        "writer.ui.panels.reference_library_panel.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    panel = ReferenceLibraryPanel(repo)
    qtbot.addWidget(panel)
    panel.show()

    target_row = next(
        row
        for row in range(panel._list.count())  # noqa: SLF001
        if panel._list.item(row).data(0x0100) == drop.id  # noqa: SLF001
    )
    card = panel._list.itemWidget(panel._list.item(target_row))  # noqa: SLF001
    card._delete_button.click()  # noqa: SLF001

    remaining_ids = {passage.id for passage in repo.list_recent()}
    assert keep.id in remaining_ids
    assert drop.id not in remaining_ids
    assert panel._list.count() == 1  # noqa: SLF001


def test_library_panel_source_mode_acts_like_bookshelf(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    repo = container.reference_repository
    repo.create(
        source_title="Book A",
        source_author="Author A",
        content="alpha",
        usage_kind="style",
        tags="风格参考",
    )
    repo.create(
        source_title="Book A",
        source_author="Author A",
        content="beta",
        usage_kind="imagery",
        tags="意象表达",
    )
    repo.create(source_title="Book B", source_author="Author B", content="gamma")

    panel = ReferenceLibraryPanel(repo)
    qtbot.addWidget(panel)

    assert panel._group_list.count() == 3  # noqa: SLF001
    panel._select_group_key("book a")  # noqa: SLF001

    assert panel._active_group_key == "book a"  # noqa: SLF001
    assert panel._list.count() == 2  # noqa: SLF001
    assert panel._book_header_title.text() == "《Book A》"  # noqa: SLF001
    assert "Author A" in panel._book_header_author.text()  # noqa: SLF001
    assert "2" in panel._book_header_meta.text()  # noqa: SLF001

    panel._select_group_key("__all__")  # noqa: SLF001
    assert panel._list.count() == 3  # noqa: SLF001
    assert panel._book_header_title.text() in {"All shelves", "全部书架"}  # noqa: SLF001


def test_library_panel_save_default_group_mode_and_restore(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    first = ReferenceLibraryPanel(
        container.reference_repository,
        settings=container.settings,
    )
    qtbot.addWidget(first)

    idx = first._group_mode_combo.findData("recent")  # noqa: SLF001
    first._group_mode_combo.setCurrentIndex(idx)  # noqa: SLF001
    first._save_group_mode_as_default()  # noqa: SLF001

    second = ReferenceLibraryPanel(
        container.reference_repository,
        settings=container.settings,
    )
    qtbot.addWidget(second)
    assert second._group_mode_combo.currentData() == "recent"  # noqa: SLF001


def test_library_grouping_helper_groups_unlabeled_source_and_tag():
    from writer.domain.models.reference_passage import ReferencePassage
    from writer.ui.reference_grouping import (
        GROUP_MODE_SOURCE,
        GROUP_MODE_TAG,
        group_reference_passages,
    )

    passages = [
        ReferencePassage(id="a", source_title="", content="alpha", tags=""),
        ReferencePassage(id="b", source_title="Book", content="beta", tags="sea"),
    ]

    source_groups = group_reference_passages(passages, GROUP_MODE_SOURCE)
    assert any(group.title in {"未标注来源", "Unlabeled Source"} for group in source_groups)

    tag_groups = group_reference_passages(passages, GROUP_MODE_TAG)
    assert any(group.title in {"未标注标签", "Unlabeled Tag"} for group in tag_groups)


def test_library_panel_save_refreshes_and_selects_new_passage(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    panel = ReferenceLibraryPanel(container.reference_repository)
    qtbot.addWidget(panel)

    idx = panel._group_mode_combo.findData("usage")  # noqa: SLF001
    panel._group_mode_combo.setCurrentIndex(idx)  # noqa: SLF001

    panel._on_new()  # noqa: SLF001
    panel._title_edit.setText("New Book")  # noqa: SLF001
    panel._content_edit.setPlainText("New body")  # noqa: SLF001
    panel._on_save()  # noqa: SLF001

    current = panel._list.currentItem()  # noqa: SLF001
    assert current is not None
    assert current.data(0x0100) is not None
    assert panel._title_edit.text() == "New Book"  # noqa: SLF001


def test_library_panel_uses_widget_cards_without_native_item_text(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    repo = container.reference_repository
    repo.create(source_title="Card Book", source_author="Author", content="paper body")

    panel = ReferenceLibraryPanel(repo)
    qtbot.addWidget(panel)

    item = panel._list.item(0)  # noqa: SLF001
    card = panel._list.itemWidget(item)  # noqa: SLF001

    assert item.text() == ""
    assert item.data(0x0101).source_title == "Card Book"  # noqa: SLF001
    assert card is not None
    assert card.objectName() == "ReferenceListCard"
    assert card.property("current") is True


def test_library_panel_loads_selected_passage_content_and_new_starts_blank(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    passage = container.reference_repository.create(
        source_title="Selected Book",
        source_author="Author",
        content="Loaded passage body",
        tags="心理描写",
    )

    panel = ReferenceLibraryPanel(container.reference_repository)
    qtbot.addWidget(panel)

    current = panel._list.currentItem()  # noqa: SLF001
    assert current is not None
    assert current.data(0x0100) == passage.id
    assert panel._content_edit.toPlainText() == "Loaded passage body"  # noqa: SLF001

    panel._on_new()  # noqa: SLF001
    assert panel._content_edit.toPlainText() == ""  # noqa: SLF001
    assert not hasattr(panel, "_category_chip_buttons")  # noqa: SLF001


def test_picker_returns_checked_contents(qtbot, container):
    from PySide6.QtCore import Qt

    from writer.ui.dialogs.reference_picker_dialog import ReferencePickerDialog

    a = container.reference_repository.create(
        source_title="A", content="content-A"
    )
    container.reference_repository.create(source_title="B", content="content-B")

    dialog = ReferencePickerDialog(container.reference_repository)
    qtbot.addWidget(dialog)

    # tick A
    for row in range(dialog._list.count()):  # noqa: SLF001
        item = dialog._list.item(row)  # noqa: SLF001
        if item.data(Qt.ItemDataRole.UserRole) == a.id:
            item.setCheckState(Qt.CheckState.Checked)

    dialog._on_use()  # noqa: SLF001
    assert dialog.selected_contents() == ["content-A"]
    assert dialog.was_skipped() is False


def test_picker_skip_returns_empty(qtbot, container):
    from writer.ui.dialogs.reference_picker_dialog import ReferencePickerDialog

    container.reference_repository.create(source_title="A", content="content-A")
    dialog = ReferencePickerDialog(container.reference_repository)
    qtbot.addWidget(dialog)

    dialog._on_skip()  # noqa: SLF001
    assert dialog.selected_contents() == []
    assert dialog.was_skipped() is True


def test_main_window_passes_references_into_request(qtbot, container, monkeypatch):
    """End-to-end: picker returns refs → rewrite request carries them."""
    from writer.domain.enums import RewriteAction
    from writer.services.ai.interfaces import (
        AiProvider,
        RewriteResponse,
    )
    from writer.services.ai.rewrite_service import RewriteService
    from writer.ui import main_window as main_window_module
    from writer.ui.main_window import MainWindow

    # M7B: preflight requires the API-key env var to be present before the
    # rewrite is dispatched. The recording provider does not actually read
    # the key, but the preflight does.
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-real")

    captured: list = []

    class _RecordingProvider(AiProvider):
        name = "rec"

        def rewrite(self, request):
            captured.append(list(request.references))
            return RewriteResponse(
                content="REW", model="m", provider=self.name
            )

    container.rewrite_service = RewriteService(  # type: ignore[attr-defined]
        container.entry_repository,
        container.version_repository,
        lambda: _RecordingProvider(),
    )
    container.reference_repository.create(
        source_title="R1", content="inspiration-1"
    )
    entry = container.entry_repository.create(title="t", body="hello world")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    # Force the picker to accept with the first (only) passage checked.
    def _fake_picker_exec(self):
        from PySide6.QtCore import Qt

        for row in range(self._list.count()):
            self._list.item(row).setCheckState(Qt.CheckState.Checked)
        self._on_use()
        return self.DialogCode.Accepted

    monkeypatch.setattr(
        main_window_module.ReferencePickerDialog, "exec", _fake_picker_exec
    )

    # Auto-accept the compare dialog.
    class _FakeCompareDialog:
        DialogCode = type("DC", (), {"Accepted": 1})

        def __init__(self, *args, **kwargs):
            self._text = kwargs.get("generated_text", "")

        def exec(self):
            return 1

        def accept_mode(self):
            return main_window_module.AcceptMode.FULL

        def accepted_text(self):
            return self._text

        def accepted_selection_text(self):
            return ""

    monkeypatch.setattr(
        main_window_module, "RewriteCompareDialog", _FakeCompareDialog
    )

    # Skip the progress modal.
    from PySide6.QtWidgets import QProgressDialog

    monkeypatch.setattr(QProgressDialog, "exec", lambda self: 0)

    window._on_rewrite(RewriteAction.POLISH)  # noqa: SLF001
    qtbot.wait(200)

    assert captured == [["inspiration-1"]]
