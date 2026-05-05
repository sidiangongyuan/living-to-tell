"""Lightweight quick-capture window for background jotting."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from writer.app.quick_capture import derive_quick_capture_title, quick_capture_tag
from writer.storage.repositories.entry_repository import EntryRepository, _word_count
from writer.ui.i18n import TR


class QuickCaptureWindow(QWidget):
    entry_saved = Signal(str)
    open_writer_requested = Signal(object)
    session_entry_changed = Signal(object)

    def __init__(
        self,
        repository: EntryRepository,
        *,
        debounce_ms: int = 500,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repository
        self._entry_id: Optional[str] = None
        self._shutting_down = False
        self._loading = False
        self._last_saved_title = ""
        self._last_saved_body = ""

        self.setObjectName("QuickCaptureWindow")
        self.setWindowTitle(TR("quick.window_title"))
        self.resize(520, 420)
        self.setWindowFlag(Qt.WindowType.Window, True)

        self._title_edit = QLineEdit()
        self._title_edit.setObjectName("QuickCaptureTitle")
        self._title_edit.setPlaceholderText(TR("quick.title_placeholder"))
        self._title_edit.textChanged.connect(self._on_content_changed)
        self._title_edit.installEventFilter(self)

        self._body_edit = QPlainTextEdit()
        self._body_edit.setObjectName("QuickCaptureBody")
        self._body_edit.setPlaceholderText(TR("quick.body_placeholder"))
        self._body_edit.textChanged.connect(self._on_content_changed)
        self._body_edit.installEventFilter(self)

        self._status_label = QLabel(TR("quick.status_unsaved"))
        self._status_label.setObjectName("QuickCaptureStatus")
        self._stats_label = QLabel("")
        self._stats_label.setObjectName("QuickCaptureStats")
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._save_close_btn = QPushButton(TR("quick.save_close"))
        self._save_close_btn.clicked.connect(self.save_and_close)
        self._save_new_btn = QPushButton(TR("quick.save_new"))
        self._save_new_btn.clicked.connect(self.save_and_new)
        self._open_writer_btn = QPushButton(TR("quick.open_writer"))
        self._open_writer_btn.clicked.connect(self._on_open_writer)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.addWidget(self._status_label, 0)
        status_row.addStretch(1)
        status_row.addWidget(self._stats_label, 0)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addWidget(self._save_close_btn)
        button_row.addWidget(self._save_new_btn)
        button_row.addStretch(1)
        button_row.addWidget(self._open_writer_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self._title_edit)
        layout.addWidget(self._body_edit, 1)
        layout.addLayout(status_row)
        layout.addLayout(button_row)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(debounce_ms)
        self._save_timer.timeout.connect(self.save_now)

        self._save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        self._save_new_return_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self._save_new_enter_shortcut = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self._escape_shortcut = QShortcut(QKeySequence("Esc"), self)
        for shortcut in (
            self._save_shortcut,
            self._save_new_return_shortcut,
            self._save_new_enter_shortcut,
            self._escape_shortcut,
        ):
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._save_shortcut.activated.connect(self.save_now)
        self._save_new_return_shortcut.activated.connect(self.save_and_new)
        self._save_new_enter_shortcut.activated.connect(self.save_and_new)
        self._escape_shortcut.activated.connect(self._on_escape)

        self.start_new()

    @property
    def current_entry_id(self) -> Optional[str]:
        return self._entry_id

    def start_new(self) -> None:
        self._loading = True
        try:
            self._entry_id = None
            self._last_saved_title = ""
            self._last_saved_body = ""
            self._title_edit.clear()
            self._body_edit.clear()
        finally:
            self._loading = False
        self._save_timer.stop()
        self._set_save_state("unsaved")
        self._update_stats()
        self.session_entry_changed.emit(None)

    def load_entry(self, entry) -> None:
        self._loading = True
        try:
            self._entry_id = entry.id
            self._title_edit.setText(entry.title)
            self._body_edit.setPlainText(entry.body)
            self._last_saved_title = entry.title
            self._last_saved_body = entry.body
        finally:
            self._loading = False
        self._save_timer.stop()
        self._set_save_state("saved")
        self._update_stats()
        self.session_entry_changed.emit(entry.id)

    def save_now(self) -> Optional[str]:
        self._save_timer.stop()
        body = self._body_edit.toPlainText()
        if not body.strip():
            self._set_save_state("unsaved")
            self._update_stats()
            return self._entry_id

        title = self._resolved_title()
        if title != self._title_edit.text():
            self._loading = True
            try:
                self._title_edit.setText(title)
            finally:
                self._loading = False

        if self._entry_id is None:
            self._set_save_state("saving")
            entry = self._repo.create(
                title=title,
                body=body,
                tags=[quick_capture_tag()],
            )
            self._entry_id = entry.id
            self._last_saved_title = entry.title
            self._last_saved_body = entry.body
            self._set_save_state("saved")
            self._update_stats()
            self.session_entry_changed.emit(entry.id)
            self.entry_saved.emit(entry.id)
            return entry.id

        if (title, body) == (self._last_saved_title, self._last_saved_body):
            self._set_save_state("saved")
            self._update_stats()
            return self._entry_id

        self._set_save_state("saving")
        updated = self._repo.update(self._entry_id, title=title, body=body)
        if updated is not None:
            self._last_saved_title = updated.title
            self._last_saved_body = updated.body
            self._set_save_state("saved")
            self._update_stats()
            self.entry_saved.emit(updated.id)
        return self._entry_id

    def save_and_close(self) -> None:
        self.save_now()
        self.hide()

    def save_and_new(self) -> None:
        self.save_now()
        self.start_new()
        self.show_for_typing()

    def shutdown(self) -> None:
        self._shutting_down = True
        self.save_now()
        self.close()

    def show_for_typing(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self._focus_body()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._shutting_down:
            self.save_now()
            super().closeEvent(event)
            return
        if self._has_meaningful_body():
            self.save_now()
        else:
            self.start_new()
        self.hide()
        event.ignore()

    def eventFilter(self, watched, event):  # noqa: N802
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
                self.save_now()
                return True
            if modifiers == Qt.KeyboardModifier.ControlModifier and key in {
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            }:
                self.save_and_new()
                return True
            if key == Qt.Key.Key_Escape and modifiers == Qt.KeyboardModifier.NoModifier:
                self._on_escape()
                return True
        return super().eventFilter(watched, event)

    def _on_content_changed(self) -> None:
        if self._loading:
            return
        self._update_stats()
        if not self._has_meaningful_body():
            self._set_save_state("unsaved")
            return
        if self._entry_id is None:
            self.save_now()
            return
        self._set_save_state("unsaved")
        self._save_timer.start()

    def _on_open_writer(self) -> None:
        entry_id = self.save_now()
        self.open_writer_requested.emit(entry_id)

    def _on_escape(self) -> None:
        if self._has_meaningful_body():
            self.save_and_close()
            return
        self.start_new()
        self.hide()

    def _resolved_title(self) -> str:
        return self._title_edit.text().strip() or derive_quick_capture_title(
            self._body_edit.toPlainText()
        )

    def _has_meaningful_body(self) -> bool:
        return bool(self._body_edit.toPlainText().strip())

    def _set_save_state(self, state: str) -> None:
        key = {
            "saved": "quick.status_saved",
            "saving": "quick.status_saving",
            "unsaved": "quick.status_unsaved",
        }.get(state, "quick.status_unsaved")
        self._status_label.setText(TR(key))

    def _update_stats(self) -> None:
        body = self._body_edit.toPlainText()
        self._stats_label.setText(
            TR("quick.stats").format(words=_word_count(body), chars=len(body))
        )

    def _focus_body(self) -> None:
        QTimer.singleShot(0, self._apply_body_focus)

    def _apply_body_focus(self) -> None:
        if self.isVisible():
            self._body_edit.setFocus()