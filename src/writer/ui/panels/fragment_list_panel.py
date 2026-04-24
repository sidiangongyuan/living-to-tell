"""Left pane: recent fragments list with a small search box and 'New' button."""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.entry import Entry
from writer.ui.i18n import TR
from writer.ui.tag_colors import get_tag_color


class _TagDotDelegate(QStyledItemDelegate):
    """Draws a small coloured dot on the right side of list items that have tags."""

    _DOT_SIZE = 8
    _DOT_MARGIN = 6

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        tags: list[str] = index.data(Qt.ItemDataRole.UserRole + 1) or []
        if not tags:
            return
        bg, _fg = get_tag_color(tags[0])
        color = QColor(bg)
        # Make the dot slightly darker than the pale background.
        color = color.darker(130)
        r = option.rect
        x = r.right() - self._DOT_MARGIN - self._DOT_SIZE
        y = r.top() + (r.height() - self._DOT_SIZE) // 2
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(x, y, self._DOT_SIZE, self._DOT_SIZE)
        painter.restore()


def _summary_for(entry: Entry) -> str:
    title = entry.title.strip()
    if title:
        return title
    body = entry.body.strip()
    if body:
        first_line = body.splitlines()[0]
        return first_line[:60]
    return TR("list.empty_fragment")


class FragmentListPanel(QWidget):
    entry_selected = Signal(str)
    new_requested = Signal()
    search_changed = Signal(str)
    tag_filter_changed = Signal(str)  # emits "" for "All tags"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("list.search_placeholder"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self.search_changed)

        self._new_button = QPushButton(TR("list.new_button"))
        self._new_button.setToolTip(TR("list.new_button_tooltip"))
        self._new_button.clicked.connect(self.new_requested)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self._search, 1)
        top.addWidget(self._new_button, 0)

        self._tag_combo = QComboBox()
        self._tag_combo.addItem(TR("list.all_tags"))
        self._tag_combo.currentIndexChanged.connect(self._on_tag_changed)

        self._list = QListWidget()
        self._list.setItemDelegate(_TagDotDelegate(self._list))
        self._list.itemSelectionChanged.connect(self._emit_selection)

        # Empty state label shown when the list is empty
        self._empty_label = QLabel(TR("list.empty_state"))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #888888; font-size: 13px; padding: 24px;"
        )
        self._empty_label.setWordWrap(True)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._list)        # index 0
        self._stack.addWidget(self._empty_label)  # index 1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(top)
        layout.addWidget(self._tag_combo)
        layout.addWidget(self._stack, 1)

    # ------------------------------------------------------------------
    # Tag filter helpers
    # ------------------------------------------------------------------

    def set_tag_options(self, tags: list[str]) -> None:
        """Repopulate the tag combo, preserving the current selection if possible."""
        current = self.current_tag_filter()
        self._tag_combo.blockSignals(True)
        self._tag_combo.clear()
        self._tag_combo.addItem(TR("list.all_tags"))
        for tag in tags:
            self._tag_combo.addItem(tag)
            # Colour the combo item to match the tag palette
            idx = self._tag_combo.count() - 1
            bg, fg = get_tag_color(tag)
            self._tag_combo.setItemData(
                idx, QColor(bg), Qt.ItemDataRole.BackgroundRole
            )
            self._tag_combo.setItemData(
                idx, QColor(fg), Qt.ItemDataRole.ForegroundRole
            )
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
        if text == TR("list.all_tags"):
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
            item.setData(Qt.ItemDataRole.UserRole + 1, list(entry.tags))
            self._list.addItem(item)
            if select_id and entry.id == select_id:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)
        if select_id is None and self._list.count() > 0 and self._list.currentRow() < 0:
            self._list.setCurrentRow(0)
            current_id = self._current_id()
            if current_id:
                self.entry_selected.emit(current_id)

        # Show empty-state label when there are no results
        self._stack.setCurrentIndex(0 if entries else 1)
        if not entries:
            search = self._search.text().strip()
            tag = self.current_tag_filter()
            if search or tag:
                self._empty_label.setText(TR("list.empty_search"))
            else:
                self._empty_label.setText(TR("list.empty_state"))

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
