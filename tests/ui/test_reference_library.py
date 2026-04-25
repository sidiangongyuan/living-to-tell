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
