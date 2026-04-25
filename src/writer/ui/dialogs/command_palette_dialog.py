"""Lightweight command palette dialog.

Triggered via Ctrl+P (or the menu). Shows all available QActions collected
from the main window's menu bar. The user can type to filter and press Enter
or double-click to trigger the action.

Intentionally simple — no fuzzy matching, no icons, no categories. Just a
fast way to reach any menu action by keyboard.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from writer.ui.i18n import TR


class CommandPaletteDialog(QDialog):
    """Filter and trigger any registered QAction by name."""

    def __init__(
        self,
        actions: List[QAction],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("cmd.title"))
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.resize(480, 360)

        self._all_actions = [a for a in actions if a.text() and not a.isSeparator()]
        self._triggered_action: Optional[QAction] = None

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("cmd.placeholder"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)

        self._list = QListWidget()
        self._list.itemActivated.connect(self._on_activate)

        self._no_results = QLabel(TR("cmd.no_results"))
        self._no_results.setObjectName("NoResultsLabel")
        self._no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_results.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._no_results)

        self._search.installEventFilter(self)
        self._populate(self._all_actions)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def triggered_action(self) -> Optional[QAction]:
        """Return the action the user selected, or None if cancelled."""
        return self._triggered_action

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _populate(self, actions: List[QAction]) -> None:
        self._list.clear()
        visible = [a for a in actions if a.isEnabled()]
        for action in visible:
            label = action.text().replace("&", "")
            shortcut = action.shortcut()
            if not shortcut.isEmpty():
                label += f"  {shortcut.toString(QKeySequence.SequenceFormat.NativeText)}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, action)
            self._list.addItem(item)
        if visible:
            self._list.setCurrentRow(0)
        self._no_results.setVisible(not visible)
        self._list.setVisible(bool(visible))

    def _filter(self, text: str) -> None:
        query = text.strip().lower()
        if not query:
            self._populate(self._all_actions)
            return
        filtered = [
            a
            for a in self._all_actions
            if query in a.text().replace("&", "").lower()
        ]
        self._populate(filtered)

    def _on_activate(self, item: QListWidgetItem) -> None:
        action: Optional[QAction] = item.data(Qt.ItemDataRole.UserRole)
        if action is not None and action.isEnabled():
            self._triggered_action = action
            self.accept()
            action.trigger()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent

        if watched is self._search and event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event  # type: ignore[assignment]
            key = key_event.key()
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                current = self._list.currentItem()
                if current:
                    self._on_activate(current)
                return True
            if key == Qt.Key.Key_Down:
                row = self._list.currentRow()
                if row < self._list.count() - 1:
                    self._list.setCurrentRow(row + 1)
                return True
            if key == Qt.Key.Key_Up:
                row = self._list.currentRow()
                if row > 0:
                    self._list.setCurrentRow(row - 1)
                return True
            if key == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(watched, event)
