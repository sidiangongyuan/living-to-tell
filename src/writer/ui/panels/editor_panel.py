"""Right pane: title + body editor for the active fragment."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from writer.domain.models.entry import Entry
from writer.storage.repositories.entry_repository import serialize_tags


class EditorPanel(QWidget):
    content_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._entry_id: Optional[str] = None

        self._title = QLineEdit()
        self._title.setPlaceholderText("Title (optional)")
        self._title.textChanged.connect(self._on_changed)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("Tags (comma-separated)")
        self._tags.textChanged.connect(self._on_changed)

        self._body = QPlainTextEdit()
        self._body.setPlaceholderText("Start writing…")
        self._body.textChanged.connect(self._on_changed)

        self._meta = QLabel("")
        self._meta.setStyleSheet("color: gray; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._title)
        layout.addWidget(self._tags)
        layout.addWidget(self._body, 1)
        layout.addWidget(self._meta)

        self._loading = False
        self.set_entry(None)

    def set_entry(self, entry: Optional[Entry]) -> None:
        self._loading = True
        try:
            if entry is None:
                self._entry_id = None
                self._title.clear()
                self._tags.clear()
                self._body.clear()
                self._meta.setText("")
                self.setEnabled(False)
            else:
                self._entry_id = entry.id
                self._title.setText(entry.title)
                self._tags.setText(serialize_tags(entry.tags))
                self._body.setPlainText(entry.body)
                self._meta.setText(self._format_meta(entry))
                self.setEnabled(True)
        finally:
            self._loading = False

    def update_meta(self, text: str) -> None:
        self._meta.setText(text)

    def current_entry_id(self) -> Optional[str]:
        return self._entry_id

    def title_text(self) -> str:
        return self._title.text()

    def tags_text(self) -> str:
        """Return the raw tags string from the QLineEdit."""
        return self._tags.text()

    def body_text(self) -> str:
        return self._body.toPlainText()

    def selection_range(self) -> Optional[tuple[int, int]]:
        """Return ``(start, end)`` of the body selection, or None if empty."""
        cursor = self._body.textCursor()
        if not cursor.hasSelection():
            return None
        return cursor.selectionStart(), cursor.selectionEnd()

    def selected_body_text(self) -> str:
        cursor = self._body.textCursor()
        return cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else ""

    def replace_body(self, new_body: str) -> None:
        self._loading = True
        try:
            self._body.setPlainText(new_body)
        finally:
            self._loading = False

    def _on_changed(self) -> None:
        if self._loading or self._entry_id is None:
            return
        self.content_changed.emit()

    @staticmethod
    def _format_meta(entry: Entry) -> str:
        parts: list[str] = []
        if entry.created_at:
            parts.append(f"created {entry.created_at}")
        if entry.updated_at:
            parts.append(f"updated {entry.updated_at}")
        return "  |  ".join(parts)
