"""Right pane: title + body editor for the active fragment."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.entry import Entry
from writer.storage.repositories.entry_repository import serialize_tags
from writer.ui.i18n import TR
from writer.ui.tag_colors import tag_style_sheet


class EditorPanel(QWidget):
    content_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._entry_id: Optional[str] = None

        self._title = QLineEdit()
        self._title.setPlaceholderText(TR("editor.title_placeholder"))
        self._title.textChanged.connect(self._on_changed)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText(TR("editor.tags_placeholder"))
        self._tags.textChanged.connect(self._on_changed)
        self._tags.textChanged.connect(self._update_tag_chips)

        # Tag chip row — hidden when no tags
        self._tag_chips_widget = QWidget()
        self._tag_chips_layout = QHBoxLayout(self._tag_chips_widget)
        self._tag_chips_layout.setContentsMargins(0, 2, 0, 2)
        self._tag_chips_layout.setSpacing(4)
        self._tag_chips_layout.addStretch(1)
        self._tag_chips_widget.setVisible(False)

        self._body = QPlainTextEdit()
        self._body.setPlaceholderText(TR("editor.body_placeholder"))
        self._body.textChanged.connect(self._on_changed)
        self._body.textChanged.connect(self._update_word_count)
        self._body.selectionChanged.connect(self._update_word_count)

        self._meta = QLabel("")
        self._meta.setStyleSheet("color: gray; font-size: 11px;")

        self._word_count = QLabel("")
        self._word_count.setStyleSheet("color: gray; font-size: 11px;")
        self._word_count.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.addWidget(self._meta, 1)
        bottom_row.addWidget(self._word_count, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._title)
        layout.addWidget(self._tags)
        layout.addWidget(self._tag_chips_widget)
        layout.addWidget(self._body, 1)
        layout.addLayout(bottom_row)

        self._loading = False
        self.set_entry(None)
        self._update_word_count()

    def set_entry(self, entry: Optional[Entry]) -> None:
        self._loading = True
        try:
            if entry is None:
                self._entry_id = None
                self._title.clear()
                self._tags.clear()
                self._body.clear()
                self._meta.setText("")
                self._update_tag_chips("")
                self.setEnabled(False)
            else:
                self._entry_id = entry.id
                self._title.setText(entry.title)
                self._tags.setText(serialize_tags(entry.tags))
                self._body.setPlainText(entry.body)
                self._meta.setText(self._format_meta(entry))
                self._update_tag_chips(serialize_tags(entry.tags))
                self.setEnabled(True)
        finally:
            self._loading = False

    def focus_body(self) -> None:
        """Move keyboard focus to the body editor and place cursor at end."""
        self._body.setFocus()
        cursor = self._body.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._body.setTextCursor(cursor)

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

    def _update_tag_chips(self, text: str = "") -> None:
        """Rebuild tag chip labels from the tags QLineEdit."""
        # Remove all existing chip labels (leave the trailing stretch)
        while self._tag_chips_layout.count() > 1:
            item = self._tag_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        raw = self._tags.text() if not text and hasattr(self, "_tags") else text
        tags = [t.strip() for t in raw.split(",") if t.strip()]
        for tag in tags:
            chip = QLabel(tag)
            chip.setStyleSheet(tag_style_sheet(tag))
            self._tag_chips_layout.insertWidget(
                self._tag_chips_layout.count() - 1, chip
            )
        self._tag_chips_widget.setVisible(bool(tags))

    def _format_meta(self, entry: Entry) -> str:
        parts: list[str] = []
        created_label = TR("editor.meta_created")
        updated_label = TR("editor.meta_updated")
        if entry.created_at:
            parts.append(f"{created_label} {entry.created_at}")
        if entry.updated_at:
            parts.append(f"{updated_label} {entry.updated_at}")
        return "  |  ".join(parts)

    # ------------------------------------------------------------------
    # M7B: live word / character count
    # ------------------------------------------------------------------

    def _update_word_count(self) -> None:
        body = self._body.toPlainText()
        words = _count_words(body)
        chars = len(body)
        selected = self.selected_body_text()
        if selected:
            self._word_count.setText(
                TR("editor.word_count_with_sel").format(
                    words=words,
                    chars=chars,
                    sel_words=_count_words(selected),
                    sel_chars=len(selected),
                )
            )
        else:
            self._word_count.setText(
                TR("editor.word_count").format(words=words, chars=chars)
            )


def _count_words(text: str) -> int:
    """Word count that treats CJK characters individually and splits
    non-CJK runs on whitespace (matches the intuition for mixed CN/EN
    drafts)."""
    if not text:
        return 0
    total = 0
    buffer: list[str] = []
    for ch in text:
        if _is_cjk(ch):
            if buffer:
                total += len("".join(buffer).split())
                buffer.clear()
            total += 1
        else:
            buffer.append(ch)
    if buffer:
        total += len("".join(buffer).split())
    return total


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF      # CJK Unified Ideographs
        or 0x3040 <= code <= 0x309F   # Hiragana
        or 0x30A0 <= code <= 0x30FF   # Katakana
        or 0xAC00 <= code <= 0xD7AF   # Hangul Syllables
        or 0x3400 <= code <= 0x4DBF   # CJK Unified Ideographs Extension A
    )
