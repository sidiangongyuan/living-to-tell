"""AI settings dialog.

Lets the user configure the OpenAI-compatible provider used for rewrite
actions, and optionally import the safe fields (``base_url``, ``model``,
``wire_api``) from a local Codex ``config.toml``. The API key itself is
never stored in the settings database — the dialog only configures the
*name* of the environment variable to read it from.
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

from writer.app.settings import SUPPORTED_WIRE_APIS, Settings
from writer.domain.models.ai_config import AiConfig
from writer.services.ai.codex_config_importer import (
    CodexConfigImporter,
    CodexImportResult,
)


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        importer: Optional[CodexConfigImporter] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Settings")
        self.resize(520, 320)

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

        form = QFormLayout()
        form.addRow("Base URL", self._base_url)
        form.addRow("Model", self._model)
        form.addRow("Wire API", self._wire_api)
        form.addRow("API key source", self._api_key_source)
        form.addRow("", self._key_status)

        import_button = QPushButton("Import from Codex config…")
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
            self._key_status.setText(
                "Only env:VAR is supported. The API key is never stored on disk."
            )
            return
        var = source.split(":", 1)[1].strip()
        if not var:
            self._key_status.setText("Enter an environment variable name after env:.")
            return
        present = bool(os.environ.get(var, "").strip())
        if present:
            self._key_status.setText(f"✓ {var} is set in the current environment.")
        else:
            self._key_status.setText(
                f"⚠ {var} is not set. Export it before invoking AI."
            )

    def _on_import_codex(self) -> None:
        default = self._importer.default_path()
        start_dir = str(default.parent) if default.parent.exists() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Codex config.toml",
            start_dir,
            "TOML files (*.toml);;All files (*.*)",
        )
        if not path:
            return
        try:
            result: CodexImportResult = self._importer.import_from(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        if result.is_empty():
            QMessageBox.information(
                self,
                "Nothing imported",
                "No supported fields (base_url / model / wire_api) were found.",
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
            self, "Imported", "Codex configuration imported. Click OK to save."
        )

    def _on_accept(self) -> None:
        wire_api = self._wire_api.currentText().strip() or "responses"
        model = self._model.text().strip()
        api_key_source = self._api_key_source.text().strip() or "env:OPENAI_API_KEY"
        raw_base_url = self._base_url.text().strip()
        base_url = raw_base_url or None

        if not model:
            QMessageBox.warning(self, "Missing model", "Please enter a model name.")
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
            QMessageBox.warning(self, "Invalid setting", str(exc))
            return
        self.accept()
