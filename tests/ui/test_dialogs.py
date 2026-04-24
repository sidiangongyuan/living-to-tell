"""Minimal interaction tests for the M3 dialogs.

These don't open a window for the user — they construct the dialogs in
offscreen Qt and drive their public methods to confirm the wiring holds.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtWidgets import QDialog

from writer.app.container import build_container
from writer.app.settings import (
    KEY_AI_BASE_URL,
    KEY_AI_MODEL,
    KEY_AI_WIRE_API,
)
from writer.services.ai.codex_config_importer import (
    CodexConfigImporter,
    CodexImportResult,
)
from writer.ui.dialogs.rewrite_compare_dialog import RewriteCompareDialog
from writer.ui.dialogs.settings_dialog import SettingsDialog


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


class _StubImporter(CodexConfigImporter):
    def __init__(self, result: CodexImportResult):
        self._result = result

    def import_from(self, path):  # noqa: D401
        return self._result


def test_settings_dialog_loads_initial_values(qtbot, container):
    container.settings.set(KEY_AI_BASE_URL, "https://orig.example/v1")
    container.settings.set(KEY_AI_MODEL, "orig-model")
    container.settings.set(KEY_AI_WIRE_API, "responses")

    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    assert dialog._base_url.text() == "https://orig.example/v1"  # noqa: SLF001
    assert dialog._model.text() == "orig-model"  # noqa: SLF001
    assert dialog._wire_api.currentText() == "responses"  # noqa: SLF001


def test_settings_dialog_accept_persists_changes(qtbot, container):
    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    dialog._base_url.setText("https://new.example/v1")  # noqa: SLF001
    dialog._model.setText("new-model")  # noqa: SLF001
    dialog._wire_api.setCurrentText("responses")  # noqa: SLF001
    dialog._api_key_source.setText("env:WRITER_CUSTOM_KEY")  # noqa: SLF001
    dialog._on_accept()  # noqa: SLF001

    cfg = container.settings.load_ai_config()
    assert cfg.base_url == "https://new.example/v1"
    assert cfg.model == "new-model"
    assert cfg.wire_api == "responses"
    assert cfg.api_key_source == "env:WRITER_CUSTOM_KEY"


def test_settings_dialog_rejects_empty_model(qtbot, container, monkeypatch):
    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)
    dialog._model.setText("")  # noqa: SLF001

    seen: list = []
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *a, **k: seen.append(a) or QMessageBox.StandardButton.Ok,
    )
    dialog._on_accept()  # noqa: SLF001

    assert seen, "Expected a warning when model is empty"
    assert dialog.result() == 0  # not accepted


def test_settings_dialog_codex_import_populates_fields(qtbot, container, monkeypatch):
    importer = _StubImporter(
        CodexImportResult(
            base_url="https://imported.example/v1",
            model="imported-model",
            wire_api="responses",
        )
    )
    dialog = SettingsDialog(container.settings, importer=importer)
    qtbot.addWidget(dialog)

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *a, **k: ("dummy.toml", "")
    )
    monkeypatch.setattr(
        QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok
    )
    dialog._on_import_codex()  # noqa: SLF001

    assert dialog._base_url.text() == "https://imported.example/v1"  # noqa: SLF001
    assert dialog._model.text() == "imported-model"  # noqa: SLF001
    assert dialog._wire_api.currentText() == "responses"  # noqa: SLF001


def test_compare_dialog_returns_edited_text(qtbot):
    dialog = RewriteCompareDialog(
        original_text="hello",
        generated_text="HELLO",
        action_label="polish",
        provider_label="fake · m",
    )
    qtbot.addWidget(dialog)

    assert dialog.accepted_text() == "HELLO"
    dialog._generated_edit.setPlainText("HELLO!")  # noqa: SLF001
    assert dialog.accepted_text() == "HELLO!"


def test_compare_dialog_cancel_does_not_signal_accept(qtbot):
    dialog = RewriteCompareDialog(
        original_text="x",
        generated_text="y",
        action_label="polish",
    )
    qtbot.addWidget(dialog)
    dialog.reject()
    assert dialog.result() == 0


# ---------------------------------------------------------------------------
# M6A: AcceptMode + Accept Selection tests
# ---------------------------------------------------------------------------

from writer.ui.dialogs.rewrite_compare_dialog import AcceptMode


def test_compare_dialog_accept_selection_disabled_when_no_selection(qtbot):
    dialog = RewriteCompareDialog(
        original_text="orig", generated_text="generated", action_label="polish"
    )
    qtbot.addWidget(dialog)
    assert not dialog._accept_selection_btn.isEnabled()  # noqa: SLF001


def test_compare_dialog_accept_selection_enabled_when_text_selected(qtbot):
    from PySide6.QtGui import QTextCursor

    dialog = RewriteCompareDialog(
        original_text="orig", generated_text="generated", action_label="polish"
    )
    qtbot.addWidget(dialog)

    cursor = dialog._generated_edit.textCursor()  # noqa: SLF001
    cursor.select(QTextCursor.SelectionType.WordUnderCursor)
    dialog._generated_edit.setTextCursor(cursor)  # noqa: SLF001

    assert dialog._accept_selection_btn.isEnabled()  # noqa: SLF001


def test_compare_dialog_full_accept_mode(qtbot):
    dialog = RewriteCompareDialog(
        original_text="orig", generated_text="generated", action_label="polish"
    )
    qtbot.addWidget(dialog)
    dialog._on_accept_full()  # noqa: SLF001
    assert dialog.accept_mode() is AcceptMode.FULL
    assert dialog.accepted_text() == "generated"
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_compare_dialog_partial_accept_mode(qtbot):
    from PySide6.QtGui import QTextCursor

    dialog = RewriteCompareDialog(
        original_text="orig", generated_text="hello world", action_label="polish"
    )
    qtbot.addWidget(dialog)

    # Select "hello"
    cursor = dialog._generated_edit.textCursor()  # noqa: SLF001
    cursor.setPosition(0)
    cursor.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
    dialog._generated_edit.setTextCursor(cursor)  # noqa: SLF001

    dialog._on_accept_selection()  # noqa: SLF001
    assert dialog.accept_mode() is AcceptMode.PARTIAL
    assert dialog.accepted_selection_text() == "hello"
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_compare_dialog_partial_accept_with_edited_generated_text(qtbot):
    """User edits generated pane before doing partial accept — selection comes
    from the edited content, not the original AI result."""
    from PySide6.QtGui import QTextCursor

    dialog = RewriteCompareDialog(
        original_text="orig", generated_text="AI result", action_label="polish"
    )
    qtbot.addWidget(dialog)

    # User edits the pane
    dialog._generated_edit.setPlainText("edited AI result")  # noqa: SLF001

    # Select "edited"
    cursor = dialog._generated_edit.textCursor()  # noqa: SLF001
    cursor.setPosition(0)
    cursor.setPosition(6, QTextCursor.MoveMode.KeepAnchor)
    dialog._generated_edit.setTextCursor(cursor)  # noqa: SLF001

    dialog._on_accept_selection()  # noqa: SLF001
    assert dialog.accepted_selection_text() == "edited"
    assert dialog.accept_mode() is AcceptMode.PARTIAL


def test_compare_dialog_cancel_mode_returns_rejected(qtbot):
    dialog = RewriteCompareDialog(
        original_text="orig", generated_text="gen", action_label="polish"
    )
    qtbot.addWidget(dialog)
    dialog.reject()
    assert dialog.result() == QDialog.DialogCode.Rejected
