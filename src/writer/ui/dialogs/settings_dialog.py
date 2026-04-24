"""AI + UI settings dialog.

Lets the user configure the OpenAI-compatible provider used for rewrite
actions, and optionally import the safe fields (``base_url``, ``model``,
``wire_api``) from a local Codex ``config.toml``. The API key itself is
never stored in the settings database — the dialog only configures the
*name* of the environment variable to read it from.

Language selection is also handled here; the change is persisted but only
takes effect after the application is restarted.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from writer.app.locale import LOCALE_EN, LOCALE_ZH_CN
from writer.app.settings import SUPPORTED_WIRE_APIS, Settings
from writer.domain.models.ai_config import AiConfig
from writer.services.ai.codex_config_importer import (
    CodexConfigImporter,
    CodexImportResult,
)
from writer.ui.i18n import TR


def _language_options():
    """Build language option list at call time so TR() uses the current locale."""
    return [
        (LOCALE_EN, TR("settings.lang_en")),
        (LOCALE_ZH_CN, TR("settings.lang_zh_cn")),
    ]


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        importer: Optional[CodexConfigImporter] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("settings.title"))
        self.resize(520, 360)

        self._settings = settings
        self._importer = importer or CodexConfigImporter()

        config = settings.load_ai_config()

        self._base_url = QLineEdit(config.base_url or "")
        self._base_url.setPlaceholderText("https://api.openai.com/v1")

        self._model = QLineEdit(config.model)

        self._wire_api = QComboBox()
        for value in SUPPORTED_WIRE_APIS:
            self._wire_api.addItem(value)
        idx = self._wire_api.findText(config.wire_api)
        self._wire_api.setCurrentIndex(idx if idx >= 0 else 0)

        self._api_key_source = QLineEdit(config.api_key_source)
        self._api_key_source.setPlaceholderText("env:OPENAI_API_KEY")

        self._key_status = QLabel()
        self._key_status.setStyleSheet("color: gray;")
        self._refresh_key_status()
        self._api_key_source.textChanged.connect(self._refresh_key_status)

        # Language selector
        self._language_combo = QComboBox()
        for locale_code, display_name in _language_options():
            self._language_combo.addItem(display_name, locale_code)
        current_lang = settings.language
        for i, (code, _) in enumerate(_language_options()):
            if code == current_lang:
                self._language_combo.setCurrentIndex(i)
                break

        form = QFormLayout()
        form.addRow(TR("settings.base_url"), self._base_url)
        form.addRow(TR("settings.model"), self._model)
        form.addRow(TR("settings.wire_api"), self._wire_api)
        form.addRow(TR("settings.api_key_source"), self._api_key_source)
        form.addRow("", self._key_status)
        form.addRow(TR("settings.language_label"), self._language_combo)

        import_button = QPushButton(TR("settings.import_codex"))
        import_button.clicked.connect(self._on_import_codex)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        action_row = QHBoxLayout()
        action_row.addWidget(import_button)
        action_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(action_row)
        layout.addWidget(button_box)

    def _refresh_key_status(self) -> None:
        source = self._api_key_source.text().strip()
        if not source.startswith("env:"):
            self._key_status.setText(TR("settings.key_only_env"))
            return
        var = source.split(":", 1)[1].strip()
        if not var:
            self._key_status.setText(TR("settings.key_enter_var"))
            return
        present = bool(os.environ.get(var, "").strip())
        if present:
            self._key_status.setText(TR("settings.key_set").format(var=var))
        else:
            self._key_status.setText(TR("settings.key_not_set").format(var=var))

    def _on_import_codex(self) -> None:
        default = self._importer.default_path()
        start_dir = str(default.parent) if default.parent.exists() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            TR("settings.codex_select_title"),
            start_dir,
            "TOML files (*.toml);;All files (*.*)",
        )
        if not path:
            return
        try:
            result: CodexImportResult = self._importer.import_from(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, TR("settings.codex_import_failed"), str(exc))
            return
        if result.is_empty():
            QMessageBox.information(
                self,
                TR("settings.nothing_imported"),
                TR("settings.nothing_imported_msg"),
            )
            return
        if result.base_url:
            self._base_url.setText(result.base_url)
        if result.model:
            self._model.setText(result.model)
        if result.wire_api:
            idx = self._wire_api.findText(result.wire_api)
            if idx >= 0:
                self._wire_api.setCurrentIndex(idx)
        QMessageBox.information(
            self, TR("settings.imported"), TR("settings.imported_msg")
        )

    def _on_accept(self) -> None:
        wire_api = self._wire_api.currentText().strip() or "responses"
        model = self._model.text().strip()
        api_key_source = self._api_key_source.text().strip() or "env:OPENAI_API_KEY"
        raw_base_url = self._base_url.text().strip()
        base_url = raw_base_url or None

        if not model:
            QMessageBox.warning(
                self, TR("settings.missing_model"), TR("settings.missing_model_msg")
            )
            return

        new_config = AiConfig(
            base_url=base_url,
            wire_api=wire_api,
            model=model,
            api_key_source=api_key_source,
        )
        try:
            self._settings.save_ai_config(new_config)
        except ValueError as exc:
            QMessageBox.warning(self, TR("settings.invalid_setting"), str(exc))
            return

        # Persist language selection; inform user a restart is required.
        new_locale = self._language_combo.currentData()
        if new_locale and new_locale != self._settings.language:
            self._settings.save_language(new_locale)
            QMessageBox.information(
                self,
                TR("settings.restart_required_title"),
                TR("settings.restart_required_msg"),
            )

        self.accept()
