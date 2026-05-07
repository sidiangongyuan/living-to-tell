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
    EditorDisplaySettings,
    KEY_AI_BASE_URL,
    KEY_AI_MODEL,
    KEY_AI_PROVIDER,
    KEY_AI_WIRE_API,
    KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
)
from writer.services.ai.codex_config_importer import (
    CodexConfigImporter,
    CodexImportResult,
)
from writer.services.ai.gemini_auth import (
    GEMINI_AUTH_SOURCE,
    GeminiAuthResolver,
    GeminiConfigImporter,
    GeminiImportResult,
)
from writer.ui.dialogs.rewrite_compare_dialog import AcceptMode
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


class _StubGeminiImporter(GeminiConfigImporter):
    def __init__(self, result: GeminiImportResult):
        self._result = result

    def import_default(self):  # noqa: D401
        return self._result


def test_settings_dialog_loads_initial_values(qtbot, container):
    container.settings.set(KEY_AI_PROVIDER, "gemini")
    container.settings.set(KEY_AI_BASE_URL, "https://orig.example/v1")
    container.settings.set(KEY_AI_MODEL, "orig-model")
    container.settings.set(KEY_AI_WIRE_API, "responses")

    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    assert dialog._base_url.text() == "https://orig.example/v1"  # noqa: SLF001
    assert dialog._provider_combo.currentData() == "gemini"  # noqa: SLF001
    assert dialog._model.text() == "orig-model"  # noqa: SLF001
    assert dialog._wire_api.currentText() == "responses"  # noqa: SLF001


def test_settings_dialog_accept_persists_changes(qtbot, container):
    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    dialog._provider_combo.setCurrentIndex(dialog._provider_combo.findData("gemini"))  # noqa: SLF001
    dialog._base_url.setText("https://new.example/v1")  # noqa: SLF001
    dialog._model.setText("new-model")  # noqa: SLF001
    dialog._wire_api.setCurrentText("responses")  # noqa: SLF001
    dialog._api_key_source.setText("env:GEMINI_API_KEY")  # noqa: SLF001
    dialog._on_accept()  # noqa: SLF001

    cfg = container.settings.load_ai_config()
    assert cfg.provider_key() == "gemini"
    assert cfg.base_url == "https://new.example/v1"
    assert cfg.model == "new-model"
    assert cfg.wire_api == "responses"
    assert cfg.api_key_source == "env:GEMINI_API_KEY"


def test_settings_dialog_persists_close_to_tray_toggle(qtbot, container):
    container.settings.set(KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED, "false")

    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    assert dialog._close_to_tray_checkbox.isChecked() is False  # noqa: SLF001
    dialog._close_to_tray_checkbox.setChecked(True)  # noqa: SLF001
    dialog._on_accept()  # noqa: SLF001

    assert container.settings.get(KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED) == "true"


def test_settings_dialog_loads_editor_display_settings(qtbot, container):
    container.settings.save_editor_display_settings(
        EditorDisplaySettings(
            font_size=20,
            line_height=2.0,
            paragraph_spacing=1.1,
            content_width=820,
            visual_first_line_indent_enabled=False,
            typewriter_mode_enabled=True,
        )
    )

    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    assert dialog._font_size.value() == 20  # noqa: SLF001
    assert dialog._line_height.value() == 2.0  # noqa: SLF001
    assert dialog._paragraph_spacing.value() == 1.1  # noqa: SLF001
    assert dialog._content_width.value() == 820  # noqa: SLF001
    assert dialog._visual_indent_checkbox.isChecked() is False  # noqa: SLF001
    assert dialog._typewriter_checkbox.isChecked() is True  # noqa: SLF001


def test_settings_dialog_persists_editor_display_settings(qtbot, container):
    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    dialog._font_size.setValue(21)  # noqa: SLF001
    dialog._line_height.setValue(1.9)  # noqa: SLF001
    dialog._paragraph_spacing.setValue(0.9)  # noqa: SLF001
    dialog._content_width.setValue(700)  # noqa: SLF001
    dialog._visual_indent_checkbox.setChecked(False)  # noqa: SLF001
    dialog._typewriter_checkbox.setChecked(False)  # noqa: SLF001
    dialog._on_accept()  # noqa: SLF001

    saved = container.settings.load_editor_display_settings()
    assert saved.font_size == 21
    assert saved.line_height == 1.9
    assert saved.paragraph_spacing == 0.9
    assert saved.content_width == 700
    assert saved.visual_first_line_indent_enabled is False
    assert saved.typewriter_mode_enabled is False


def test_settings_dialog_accept_persists_gemini_cli_provider(qtbot, container):
    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    dialog._provider_combo.setCurrentIndex(  # noqa: SLF001
        dialog._provider_combo.findData("gemini_cli")  # noqa: SLF001
    )
    dialog._on_accept()  # noqa: SLF001

    cfg = container.settings.load_ai_config()
    assert cfg.provider_key() == "gemini_cli"
    assert cfg.base_url is None
    assert cfg.model == "gemini-cli-default"
    assert cfg.api_key_source == "gemini-cli"


def test_settings_dialog_model_preset_updates_model(qtbot, container):
    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)

    dialog._provider_combo.setCurrentIndex(  # noqa: SLF001
        dialog._provider_combo.findData("gemini_cli")  # noqa: SLF001
    )
    idx = dialog._model_preset_combo.findData("gemini-2.5-flash")  # noqa: SLF001
    assert idx >= 0
    dialog._model_preset_combo.setCurrentIndex(idx)  # noqa: SLF001

    assert dialog._model.text() == "gemini-2.5-flash"  # noqa: SLF001


def test_settings_dialog_gemini_quota_button_updates_status(
    qtbot, container, monkeypatch
):
    from writer.services.ai.gemini_cli_provider import GeminiCliQuotaStatus
    import writer.ui.dialogs.settings_dialog as settings_dialog_mod
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        settings_dialog_mod,
        "gemini_cli_quota_status",
        lambda **kwargs: GeminiCliQuotaStatus(
            True,
            account="a@example.com",
            project_id="project-123",
            current_tier="Gemini Code Assist",
            paid_tier="Google One AI Pro",
            credits="included / not itemized",
        ),
    )
    monkeypatch.setattr(
        QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok
    )
    dialog = SettingsDialog(container.settings)
    qtbot.addWidget(dialog)
    dialog._provider_combo.setCurrentIndex(  # noqa: SLF001
        dialog._provider_combo.findData("gemini_cli")  # noqa: SLF001
    )

    dialog._on_check_gemini_cli_quota()  # noqa: SLF001

    assert "a@example.com" in dialog._key_status.text()  # noqa: SLF001
    assert "project-123" in dialog._key_status.text()  # noqa: SLF001


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

    assert dialog._provider_combo.currentData() == "openai"  # noqa: SLF001
    assert dialog._base_url.text() == "https://imported.example/v1"  # noqa: SLF001
    assert dialog._model.text() == "imported-model"  # noqa: SLF001
    assert dialog._wire_api.currentText() == "responses"  # noqa: SLF001


def test_settings_dialog_gemini_import_populates_fields(
    qtbot, container, monkeypatch, tmp_path
):
    importer = _StubGeminiImporter(
        GeminiImportResult(
            base_url="https://gemini.example/v1",
            model="gemini-3.1-pro",
            wire_api="responses",
        )
    )
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=gm-test\n", encoding="utf-8")
    dialog = SettingsDialog(
        container.settings,
        gemini_importer=importer,
        gemini_auth=GeminiAuthResolver(path=env_file),
    )
    qtbot.addWidget(dialog)

    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok
    )
    dialog._on_import_gemini()  # noqa: SLF001

    assert dialog._provider_combo.currentData() == "gemini"  # noqa: SLF001
    assert dialog._base_url.text() == "https://gemini.example/v1"  # noqa: SLF001
    assert dialog._model.text() == "gemini-3.1-pro"  # noqa: SLF001
    assert dialog._wire_api.currentText() == "responses"  # noqa: SLF001
    assert dialog._api_key_source.text() == GEMINI_AUTH_SOURCE  # noqa: SLF001


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
