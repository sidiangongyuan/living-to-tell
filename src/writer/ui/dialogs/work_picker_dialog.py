"""Dialog to pick a single work (used by collections panel)."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.ui.i18n import TR


class WorkPickerDialog(QDialog):
    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self.selected_work_id: Optional[str] = None

        self.setWindowTitle(TR("work_picker.title"))
        self.resize(420, 480)

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("work_picker.search_placeholder"))
        self._search.textChanged.connect(self._refresh)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double_click)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        query = self._search.text().strip().lower()
        self._list.clear()
        for w in self._container.work_repository.list_recent(limit=500, include_archived=True):
            if query and query not in (w.title or "").lower() and query not in (w.summary or "").lower():
                continue
            label = f"{w.title or TR('works.untitled')}  [{w.status}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, w.id)
            self._list.addItem(item)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.selected_work_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_accept(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self.selected_work_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
