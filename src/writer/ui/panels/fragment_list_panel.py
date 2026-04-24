"""Left pane: recent fragments list with a small search box and 'New' button."""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.entry import Entry

_ALL_TAGS_LABEL = "All tags"


def _summary_for(entry: Entry) -> str:
    title = entry.title.strip()
    if title:
        return title
    body = entry.body.strip()
    if body:
        first_line = body.splitlines()[0]
        return first_line[:60]
    return "(empty fragment)"


class FragmentListPanel(QWidget):
    entry_selected = Signal(str)
    new_requested = Signal()
    search_changed = Signal(str)
    tag_filter_changed = Signal(str)  # emits "" for "All tags"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search fragments…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self.search_changed)

        self._new_button = QPushButton("New")
        self._new_button.setToolTip("Create a new blank fragment (Ctrl+N)")
        self._new_button.clicked.connect(self.new_requested)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self._search, 1)
        top.addWidget(self._new_button, 0)

        self._tag_combo = QComboBox()
        self._tag_combo.addItem(_ALL_TAGS_LABEL)
        self._tag_combo.currentIndexChanged.connect(self._on_tag_changed)

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._emit_selection)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(top)
        layout.addWidget(self._tag_combo)
        layout.addWidget(self._list, 1)

    # ------------------------------------------------------------------
    # Tag filter helpers
    # ------------------------------------------------------------------

    def set_tag_options(self, tags: list[str]) -> None:
        """Repopulate the tag combo, preserving the current selection if possible."""
        current = self.current_tag_filter()
        self._tag_combo.blockSignals(True)
        self._tag_combo.clear()
        self._tag_combo.addItem(_ALL_TAGS_LABEL)
        for tag in tags:
            self._tag_combo.addItem(tag)
        # Restore previous selection or fall back to "All tags"
        if current:
            idx = self._tag_combo.findText(current)
            self._tag_combo.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self._tag_combo.setCurrentIndex(0)
        self._tag_combo.blockSignals(False)

    def current_tag_filter(self) -> Optional[str]:
        """Return the active tag filter, or ``None`` for "All tags"."""
        text = self._tag_combo.currentText()
        if text == _ALL_TAGS_LABEL:
            return None
        return text or None

    def _on_tag_changed(self) -> None:
        self.tag_filter_changed.emit(self._tag_combo.currentText())

    # ------------------------------------------------------------------
    # List population
    # ------------------------------------------------------------------

    def set_entries(self, entries: List[Entry], *, select_id: Optional[str] = None) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for entry in entries:
            item = QListWidgetItem(_summary_for(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._list.addItem(item)
            if select_id and entry.id == select_id:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)
        if select_id is None and self._list.count() > 0 and self._list.currentRow() < 0:
            self._list.setCurrentRow(0)
            current_id = self._current_id()
            if current_id:
                self.entry_selected.emit(current_id)

    def current_entry_id(self) -> Optional[str]:
        return self._current_id()

    def search_text(self) -> str:
        return self._search.text()

    def clear_search(self) -> None:
        self._search.clear()

    def reset_tag_filter(self) -> None:
        """Reset the tag filter combo back to 'All tags'."""
        self._tag_combo.setCurrentIndex(0)

    def _current_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _emit_selection(self) -> None:
        entry_id = self._current_id()
        if entry_id:
            self.entry_selected.emit(entry_id)
