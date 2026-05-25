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

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from writer.app.locale import LOCALE_EN, LOCALE_ZH_CN
from writer.app.settings import (
    DEFAULT_EDITOR_FONT_FAMILY,
    DEFAULT_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
    EditorDisplaySettings,
    KEY_AI_GEMINI_CLI_PROXY,
    KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
    MAX_EDITOR_CONTENT_WIDTH,
    SUPPORTED_WIRE_APIS,
    Settings,
)
from writer.domain.models.ai_config import AiConfig
from writer.services.ai.codex_auth import CODEX_AUTH_SOURCE, CodexAuthResolver
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
from writer.services.ai.gemini_cli_provider import (
    GEMINI_CLI_AUTH_SOURCE,
    GEMINI_CLI_DEFAULT_MODEL,
    GEMINI_CLI_MODEL_PRESETS,
    GEMINI_CLI_PROXY_ENV,
    detect_gemini_cli_proxy,
    find_gemini_cli,
    gemini_cli_quota_status,
    gemini_cli_oauth_status,
)
from writer.ui.i18n import TR


def _language_options():
    """Build language option list at call time so TR() uses the current locale."""
    return [
        (LOCALE_EN, TR("settings.lang_en")),
        (LOCALE_ZH_CN, TR("settings.lang_zh_cn")),
    ]


def _provider_options():
    return [
        ("openai", TR("settings.provider_openai")),
        ("gemini", TR("settings.provider_gemini")),
        ("gemini_cli", TR("settings.provider_gemini_cli")),
    ]


_MODEL_PRESETS = {
    "openai": (
        "gpt-4o-mini",
        "gpt-4.1-mini",
        "gpt-4.1",
    ),
    "gemini": (
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ),
    "gemini_cli": GEMINI_CLI_MODEL_PRESETS,
}

_EDITOR_FONT_PRESETS = (
    (
        "serif",
        "settings.editor_font_preset_serif",
        DEFAULT_EDITOR_FONT_FAMILY,
    ),
    (
        "sans",
        "settings.editor_font_preset_sans",
        "Noto Sans SC, MiSans, Microsoft YaHei UI, 微软雅黑, Segoe UI, Arial",
    ),
    (
        "mono",
        "settings.editor_font_preset_mono",
        "Cascadia Code, Cascadia Mono, Consolas, Courier New",
    ),
)
_CUSTOM_FONT_PRESET = "custom"


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        importer: Optional[CodexConfigImporter] = None,
        codex_auth: Optional[CodexAuthResolver] = None,
        gemini_importer: Optional[GeminiConfigImporter] = None,
        gemini_auth: Optional[GeminiAuthResolver] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("settings.title"))
        self.resize(680, 700)

        self._settings = settings
        self._importer = importer or CodexConfigImporter()
        self._codex_auth = codex_auth or CodexAuthResolver()
        self._gemini_importer = gemini_importer or GeminiConfigImporter()
        self._gemini_auth = gemini_auth or GeminiAuthResolver()

        config = settings.load_ai_config()
        editor_settings = settings.load_editor_display_settings()

        self._provider_combo = QComboBox()
        for provider_key, display_name in _provider_options():
            self._provider_combo.addItem(display_name, provider_key)
        provider_index = self._provider_combo.findData(config.provider_key())
        self._provider_combo.setCurrentIndex(provider_index if provider_index >= 0 else 0)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        self._base_url = QLineEdit(config.base_url or "")

        self._model = QLineEdit(config.model)

        self._model_preset_combo = QComboBox()
        self._model_preset_combo.currentIndexChanged.connect(self._on_model_preset_changed)

        self._wire_api = QComboBox()
        for value in SUPPORTED_WIRE_APIS:
            self._wire_api.addItem(value)
        idx = self._wire_api.findText(config.wire_api)
        self._wire_api.setCurrentIndex(idx if idx >= 0 else 0)

        self._api_key_source = QLineEdit(config.api_key_source)

        self._gemini_cli_proxy = QLineEdit(
            config.gemini_cli_proxy or settings.get(KEY_AI_GEMINI_CLI_PROXY, "") or ""
        )
        self._gemini_cli_proxy.setPlaceholderText("http://127.0.0.1:PORT")
        self._gemini_cli_proxy.textChanged.connect(self._refresh_key_status)

        self._key_status = QLabel()
        self._key_status.setObjectName("MetaLabel")
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

        close_to_tray_raw = settings.get(
            KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
            "true" if DEFAULT_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED else "false",
        )
        self._close_to_tray_checkbox = QCheckBox(TR("settings.close_to_tray_label"))
        self._close_to_tray_checkbox.setChecked(
            (close_to_tray_raw or "").strip().lower() == "true"
        )

        self._font_size = QSpinBox()
        self._font_size.setRange(12, 32)
        self._font_size.setValue(editor_settings.font_size)
        self._font_size.setSuffix(" px")

        self._font_preset_combo = QComboBox()
        for key, label_key, _family in _EDITOR_FONT_PRESETS:
            self._font_preset_combo.addItem(TR(label_key), key)
        self._font_preset_combo.addItem(
            TR("settings.editor_font_preset_custom"), _CUSTOM_FONT_PRESET
        )
        self._font_preset_combo.currentIndexChanged.connect(
            self._on_editor_font_preset_changed
        )

        self._font_family_combo = QComboBox()
        self._font_family_combo.setEditable(True)
        self._populate_font_family_combo(editor_settings.font_family)
        self._font_family_combo.currentTextChanged.connect(
            self._on_editor_font_family_changed
        )
        self._sync_font_preset_to_family(editor_settings.font_family)

        self._line_height = QDoubleSpinBox()
        self._line_height.setRange(1.2, 2.6)
        self._line_height.setSingleStep(0.1)
        self._line_height.setDecimals(1)
        self._line_height.setValue(editor_settings.line_height)

        self._paragraph_spacing = QDoubleSpinBox()
        self._paragraph_spacing.setRange(0.0, 2.0)
        self._paragraph_spacing.setSingleStep(0.1)
        self._paragraph_spacing.setDecimals(1)
        self._paragraph_spacing.setValue(editor_settings.paragraph_spacing)

        self._content_width = QSpinBox()
        self._content_width.setRange(520, MAX_EDITOR_CONTENT_WIDTH)
        self._content_width.setSingleStep(20)
        self._content_width.setValue(editor_settings.content_width)
        self._content_width.setSuffix(" px")

        self._page_vertical_padding = QSpinBox()
        self._page_vertical_padding.setRange(12, 96)
        self._page_vertical_padding.setSingleStep(4)
        self._page_vertical_padding.setValue(editor_settings.page_vertical_padding)
        self._page_vertical_padding.setSuffix(" px")

        self._page_gap = QSpinBox()
        self._page_gap.setRange(0, 96)
        self._page_gap.setSingleStep(4)
        self._page_gap.setValue(editor_settings.page_gap)
        self._page_gap.setSuffix(" px")

        self._visual_indent_checkbox = QCheckBox(TR("settings.editor_visual_indent"))
        self._visual_indent_checkbox.setChecked(
            editor_settings.visual_first_line_indent_enabled
        )
        self._typewriter_checkbox = QCheckBox(TR("settings.editor_typewriter_mode"))
        self._typewriter_checkbox.setChecked(editor_settings.typewriter_mode_enabled)
        self._auto_indent_checkbox = QCheckBox(TR("settings.editor_auto_paragraph_indent"))
        self._auto_indent_checkbox.setChecked(
            editor_settings.auto_paragraph_indent_enabled
        )
        self._soft_page_guides_checkbox = QCheckBox(TR("settings.editor_soft_page_guides"))
        self._soft_page_guides_checkbox.setChecked(
            editor_settings.soft_page_guides_enabled
        )
        self._reduced_motion_checkbox = QCheckBox(TR("settings.reduced_motion"))
        self._reduced_motion_checkbox.setChecked(settings.reduced_motion_enabled())

        appearance_group = QGroupBox(TR("settings.group_appearance"))
        appearance_form = QFormLayout(appearance_group)
        appearance_form.addRow(TR("settings.language_label"), self._language_combo)

        writing_group = QGroupBox(TR("settings.group_writing"))
        writing_form = QFormLayout(writing_group)
        writing_form.addRow(TR("settings.editor_font_preset"), self._font_preset_combo)
        writing_form.addRow(TR("settings.editor_font_family"), self._font_family_combo)
        writing_form.addRow(TR("settings.editor_font_size"), self._font_size)
        writing_form.addRow(TR("settings.editor_line_height"), self._line_height)
        writing_form.addRow(
            TR("settings.editor_paragraph_spacing"),
            self._paragraph_spacing,
        )
        writing_form.addRow(TR("settings.editor_content_width"), self._content_width)
        writing_form.addRow(
            TR("settings.editor_page_vertical_padding"),
            self._page_vertical_padding,
        )
        writing_form.addRow(TR("settings.editor_page_gap"), self._page_gap)
        writing_form.addRow("", self._visual_indent_checkbox)
        writing_form.addRow("", self._typewriter_checkbox)
        writing_form.addRow("", self._auto_indent_checkbox)
        writing_form.addRow("", self._soft_page_guides_checkbox)
        writing_form.addRow("", self._reduced_motion_checkbox)

        ai_group = QGroupBox(TR("settings.group_ai"))
        ai_form = QFormLayout(ai_group)
        ai_form.addRow(TR("settings.provider"), self._provider_combo)
        ai_form.addRow(TR("settings.base_url"), self._base_url)
        ai_form.addRow(TR("settings.model"), self._model)
        ai_form.addRow(TR("settings.model_preset"), self._model_preset_combo)
        ai_form.addRow(TR("settings.wire_api"), self._wire_api)
        ai_form.addRow(TR("settings.api_key_source"), self._api_key_source)
        ai_form.addRow(TR("settings.gemini_cli_proxy"), self._gemini_cli_proxy)
        self._gemini_cli_proxy_label = ai_form.labelForField(self._gemini_cli_proxy)
        ai_form.addRow("", self._key_status)

        quick_capture_group = QGroupBox(TR("settings.group_quick_capture"))
        quick_capture_layout = QVBoxLayout(quick_capture_group)
        quick_capture_layout.setContentsMargins(12, 12, 12, 12)
        quick_capture_layout.addWidget(self._close_to_tray_checkbox)

        import_button = QPushButton(TR("settings.import_codex"))
        import_button.clicked.connect(self._on_import_codex)

        gemini_button = QPushButton(TR("settings.import_gemini"))
        gemini_button.clicked.connect(self._on_import_gemini)

        self._gemini_quota_button = QPushButton(TR("settings.gemini_cli_quota_btn"))
        self._gemini_quota_button.clicked.connect(self._on_check_gemini_cli_quota)

        test_button = QPushButton(TR("settings.test_btn"))
        test_button.clicked.connect(self._on_test_config)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        action_row = QHBoxLayout()
        action_row.addWidget(import_button)
        action_row.addWidget(gemini_button)
        action_row.addWidget(self._gemini_quota_button)
        action_row.addWidget(test_button)
        action_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(appearance_group)
        layout.addWidget(writing_group)
        layout.addWidget(ai_group)
        layout.addLayout(action_row)
        layout.addWidget(quick_capture_group)
        layout.addWidget(button_box)

        self._refresh_provider_ui()
        self._refresh_key_status()

    def _current_provider_key(self) -> str:
        value = self._provider_combo.currentData()
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
        return "openai"

    def _on_provider_changed(self) -> None:
        self._refresh_provider_ui(adjust_defaults=True)

    def _on_model_preset_changed(self) -> None:
        value = self._model_preset_combo.currentData()
        if isinstance(value, str) and value.strip():
            self._model.setText(value.strip())

    def _refresh_provider_ui(self, *, adjust_defaults: bool = False) -> None:
        provider = self._current_provider_key()
        self._base_url.setEnabled(provider != "gemini_cli")
        self._api_key_source.setEnabled(provider != "gemini_cli")
        show_gemini_cli = provider == "gemini_cli"
        self._gemini_cli_proxy.setVisible(show_gemini_cli)
        self._gemini_quota_button.setVisible(show_gemini_cli)
        if self._gemini_cli_proxy_label is not None:
            self._gemini_cli_proxy_label.setVisible(show_gemini_cli)
        if provider == "gemini_cli":
            self._base_url.setPlaceholderText(TR("settings.gemini_cli_base_url_hint"))
            self._api_key_source.setPlaceholderText(GEMINI_CLI_AUTH_SOURCE)
            self._model.setPlaceholderText(GEMINI_CLI_DEFAULT_MODEL)
            if not self._gemini_cli_proxy.text().strip():
                detected_proxy = detect_gemini_cli_proxy()
                if detected_proxy:
                    self._gemini_cli_proxy.setText(detected_proxy)
            if adjust_defaults:
                self._base_url.clear()
                self._api_key_source.setText(GEMINI_CLI_AUTH_SOURCE)
                self._model.setText(GEMINI_CLI_DEFAULT_MODEL)
        elif provider == "gemini":
            self._base_url.setPlaceholderText("https://generativelanguage.googleapis.com")
            self._api_key_source.setPlaceholderText("env:GEMINI_API_KEY / gemini")
            self._model.setPlaceholderText("gemini-2.5-flash")
        else:
            self._base_url.setPlaceholderText("https://api.openai.com/v1")
            self._api_key_source.setPlaceholderText("env:OPENAI_API_KEY / codex")
            self._model.setPlaceholderText("gpt-4o-mini")
        self._refresh_model_presets(provider)
        self._refresh_key_status()

    def _refresh_model_presets(self, provider: str) -> None:
        current = self._model.text().strip()
        self._model_preset_combo.blockSignals(True)
        try:
            self._model_preset_combo.clear()
            self._model_preset_combo.addItem(TR("settings.model_preset_custom"), "")
            for value in _MODEL_PRESETS.get(provider, ()): 
                self._model_preset_combo.addItem(value, value)
            idx = self._model_preset_combo.findData(current)
            self._model_preset_combo.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self._model_preset_combo.blockSignals(False)

    def _populate_font_family_combo(self, current: str) -> None:
        self._font_family_combo.blockSignals(True)
        try:
            self._font_family_combo.clear()
            self._font_family_combo.addItem(current)
            for family in sorted(set(QFontDatabase.families())):
                if self._font_family_combo.findText(family) < 0:
                    self._font_family_combo.addItem(family)
            self._font_family_combo.setCurrentText(current)
        finally:
            self._font_family_combo.blockSignals(False)

    def _on_editor_font_preset_changed(self) -> None:
        preset = self._font_preset_combo.currentData()
        if preset == _CUSTOM_FONT_PRESET:
            return
        family = _font_family_for_preset(preset)
        if not family:
            return
        self._font_family_combo.blockSignals(True)
        try:
            self._font_family_combo.setCurrentText(family)
        finally:
            self._font_family_combo.blockSignals(False)

    def _on_editor_font_family_changed(self, family: str) -> None:
        self._sync_font_preset_to_family(family)

    def _sync_font_preset_to_family(self, family: str) -> None:
        normalized = _normalize_font_family(family)
        target = _CUSTOM_FONT_PRESET
        for key, _label, preset_family in _EDITOR_FONT_PRESETS:
            if normalized == _normalize_font_family(preset_family):
                target = key
                break
        idx = self._font_preset_combo.findData(target)
        if idx >= 0 and idx != self._font_preset_combo.currentIndex():
            self._font_preset_combo.blockSignals(True)
            try:
                self._font_preset_combo.setCurrentIndex(idx)
            finally:
                self._font_preset_combo.blockSignals(False)

    def _refresh_key_status(self) -> None:
        if self._current_provider_key() == "gemini_cli":
            found = find_gemini_cli()
            if not found:
                self._key_status.setText(TR("settings.gemini_cli_missing"))
                return
            auth = gemini_cli_oauth_status()
            proxy = self._gemini_cli_proxy.text().strip() or TR("settings.gemini_cli_proxy_auto")
            if auth.available:
                account = auth.account or TR("settings.gemini_cli_unknown_account")
                self._key_status.setText(
                    TR("settings.gemini_cli_ready").format(
                        path=found,
                        account=account,
                        proxy=proxy,
                    )
                )
            else:
                self._key_status.setText(
                    TR("settings.gemini_cli_auth_missing").format(
                        path=auth.creds_path,
                        proxy_env=GEMINI_CLI_PROXY_ENV,
                    )
                )
            return
        source = self._api_key_source.text().strip()
        if source.lower() == CODEX_AUTH_SOURCE:
            status = self._codex_auth.status()
            if status.available:
                self._key_status.setText(
                    TR("settings.codex_auth_available").format(path=status.path)
                )
            else:
                reason_key = {
                    "missing_file": "settings.codex_auth_missing_file",
                    "missing_key": "settings.codex_auth_missing_key",
                    "unreadable": "settings.codex_auth_unreadable",
                }.get(status.reason, "settings.codex_auth_missing_file")
                self._key_status.setText(TR(reason_key).format(path=status.path))
            return
        if source.lower() == GEMINI_AUTH_SOURCE:
            status = self._gemini_auth.status()
            if status.available:
                self._key_status.setText(
                    TR("settings.gemini_auth_available").format(path=status.path)
                )
            else:
                reason_key = {
                    "missing_file": "settings.gemini_auth_missing_file",
                    "missing_key": "settings.gemini_auth_missing_key",
                    "unreadable": "settings.gemini_auth_unreadable",
                }.get(status.reason, "settings.gemini_auth_missing_file")
                self._key_status.setText(TR(reason_key).format(path=status.path))
            return
        if source.startswith("literal:"):
            self._key_status.setText(TR("settings.key_only_env"))
            return
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
        provider_idx = self._provider_combo.findData("openai")
        if provider_idx >= 0:
            self._provider_combo.setCurrentIndex(provider_idx)
        # If the imported config says it needs OpenAI-style auth AND a local
        # Codex auth file is actually readable, wire the credential source
        # to 'codex' so the user does not also have to export an env var.
        auto_codex = False
        if result.requires_openai_auth:
            status = self._codex_auth.status()
            if status.available:
                self._api_key_source.setText(CODEX_AUTH_SOURCE)
                auto_codex = True
        body_key = (
            "settings.codex_imported_body_with_auth"
            if auto_codex
            else "settings.codex_imported_body"
        )
        QMessageBox.information(
            self,
            TR("settings.codex_imported_title"),
            TR(body_key),
        )

    def _on_import_gemini(self) -> None:
        try:
            result: GeminiImportResult = self._gemini_importer.import_default()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, TR("settings.gemini_import_failed"), str(exc))
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
        provider_idx = self._provider_combo.findData("gemini")
        if provider_idx >= 0:
            self._provider_combo.setCurrentIndex(provider_idx)

        auto_gemini = False
        status = self._gemini_auth.status()
        if status.available:
            self._api_key_source.setText(GEMINI_AUTH_SOURCE)
            auto_gemini = True
        body_key = (
            "settings.gemini_imported_body_with_auth"
            if auto_gemini
            else "settings.gemini_imported_body"
        )
        QMessageBox.information(
            self,
            TR("settings.gemini_imported_title"),
            TR(body_key),
        )

    def _on_check_gemini_cli_quota(self) -> None:
        proxy = self._gemini_cli_proxy.text().strip() or detect_gemini_cli_proxy()
        status = gemini_cli_quota_status(proxy_url=proxy, timeout_seconds=30)
        if status.available:
            message = _format_gemini_cli_quota_status(status)
            self._key_status.setText(message)
            QMessageBox.information(
                self,
                TR("settings.gemini_cli_quota_title"),
                message,
            )
            return
        message = TR("settings.gemini_cli_quota_unavailable").format(
            reason=status.reason or "unknown"
        )
        self._key_status.setText(message)
        QMessageBox.warning(
            self,
            TR("settings.gemini_cli_quota_title"),
            message,
        )

    def _on_test_config(self) -> None:
        """Run preflight on the CURRENT (unsaved) form values.

        Local-only validation: does not send a network request. It
        checks that the form yields a valid AiConfig, that the API key
        source is env:VAR, and that the env var is present.
        """
        from writer.services.ai.preflight import (
            format_issues,
            preflight_rewrite,
        )

        wire_api = self._wire_api.currentText().strip() or "responses"
        provider_name = self._current_provider_key()
        model = self._model.text().strip() or (
            GEMINI_CLI_DEFAULT_MODEL if provider_name == "gemini_cli" else ""
        )
        api_key_source = (
            GEMINI_CLI_AUTH_SOURCE
            if provider_name == "gemini_cli"
            else self._api_key_source.text().strip() or "env:OPENAI_API_KEY"
        )
        raw_base_url = "" if provider_name == "gemini_cli" else self._base_url.text().strip()

        candidate = AiConfig(
            provider_name=provider_name,
            base_url=raw_base_url or None,
            wire_api=wire_api,
            model=model,
            api_key_source=api_key_source,
            gemini_cli_proxy=(
                self._gemini_cli_proxy.text().strip() or None
                if provider_name == "gemini_cli"
                else None
            ),
        )
        # Use a non-empty sentinel so the "empty text" rule never fires —
        # this button validates CONFIG, not editor state.
        issues = preflight_rewrite(
            candidate,
            target_text="_",
            has_entry=True,
            codex_auth=self._codex_auth,
            gemini_auth=self._gemini_auth,
        )
        if issues:
            QMessageBox.warning(
                self,
                TR("settings.test_fail_title"),
                format_issues(issues),
            )
            return
        QMessageBox.information(
            self,
            TR("settings.test_ok_title"),
            TR("settings.test_ok_msg"),
        )

    def _on_accept(self) -> None:
        wire_api = self._wire_api.currentText().strip() or "responses"
        provider_name = self._current_provider_key()
        model = self._model.text().strip() or (
            GEMINI_CLI_DEFAULT_MODEL if provider_name == "gemini_cli" else ""
        )
        if provider_name == "gemini_cli" and model.strip().lower() == "gpt-4o-mini":
            model = GEMINI_CLI_DEFAULT_MODEL
        api_key_source = (
            GEMINI_CLI_AUTH_SOURCE
            if provider_name == "gemini_cli"
            else self._api_key_source.text().strip() or "env:OPENAI_API_KEY"
        )
        raw_base_url = self._base_url.text().strip()
        base_url = None if provider_name == "gemini_cli" else raw_base_url or None

        if not model:
            QMessageBox.warning(
                self, TR("settings.missing_model"), TR("settings.missing_model_msg")
            )
            return

        new_config = AiConfig(
            provider_name=provider_name,
            base_url=base_url,
            wire_api=wire_api,
            model=model,
            api_key_source=api_key_source,
            gemini_cli_proxy=(
                self._gemini_cli_proxy.text().strip() or None
                if provider_name == "gemini_cli"
                else None
            ),
        )
        try:
            self._settings.save_ai_config(new_config)
        except ValueError as exc:
            QMessageBox.warning(self, TR("settings.invalid_setting"), str(exc))
            return

        self._settings.save_editor_display_settings(
            EditorDisplaySettings(
                font_size=self._font_size.value(),
                line_height=self._line_height.value(),
                paragraph_spacing=self._paragraph_spacing.value(),
                content_width=self._content_width.value(),
                page_vertical_padding=self._page_vertical_padding.value(),
                page_gap=self._page_gap.value(),
                font_family=self._font_family_combo.currentText().strip(),
                visual_first_line_indent_enabled=self._visual_indent_checkbox.isChecked(),
                typewriter_mode_enabled=self._typewriter_checkbox.isChecked(),
                auto_paragraph_indent_enabled=self._auto_indent_checkbox.isChecked(),
                soft_page_guides_enabled=self._soft_page_guides_checkbox.isChecked(),
            )
        )
        self._settings.save_reduced_motion_enabled(
            self._reduced_motion_checkbox.isChecked()
        )

        # Persist language selection; inform user a restart is required.
        new_locale = self._language_combo.currentData()
        if new_locale and new_locale != self._settings.language:
            self._settings.save_language(new_locale)
            QMessageBox.information(
                self,
                TR("settings.restart_required_title"),
                TR("settings.restart_required_msg"),
            )

        self._settings.set(
            KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
            "true" if self._close_to_tray_checkbox.isChecked() else "false",
        )

        self.accept()


def _format_gemini_cli_quota_status(status) -> str:
    return TR("settings.gemini_cli_quota_status").format(
        account=status.account or TR("settings.gemini_cli_unknown_account"),
        project=status.project_id or TR("context.no_value"),
        current_tier=status.current_tier or TR("context.no_value"),
        paid_tier=status.paid_tier or TR("context.no_value"),
        credits=status.credits or TR("context.no_value"),
    )


def _font_family_for_preset(preset: object) -> str:
    for key, _label, family in _EDITOR_FONT_PRESETS:
        if key == preset:
            return family
    return ""


def _normalize_font_family(value: str) -> str:
    return " ".join((value or "").replace("'", "").replace('"', "").split()).casefold()
