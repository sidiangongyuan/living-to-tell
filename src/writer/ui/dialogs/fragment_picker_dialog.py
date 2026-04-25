"""Dialog to pick a single fragment (used by AI workspace attachments)."""
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
from writer.domain.models.entry import Entry
from writer.ui.i18n import TR


class FragmentPickerDialog(QDialog):
    """Pick a fragment to attach as AI context."""

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self.selected_entry: Optional[Entry] = None

        self.setWindowTitle(TR("ai.attachments.add_fragment"))
        self.resize(420, 480)

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("list.search_placeholder"))
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

        self._all_entries: list[Entry] = []
        self._load()
        self._refresh()

    def _load(self) -> None:
        try:
            self._all_entries = list(
                self._container.entry_repository.list_recent(limit=500)
            )
        except Exception:  # noqa: BLE001
            self._all_entries = []

    def _refresh(self) -> None:
        query = self._search.text().strip().lower()
        self._list.clear()
        for entry in self._all_entries:
            title = (entry.title or TR("list.empty_fragment")).strip()
            haystack = (title + " " + (entry.body or "")[:200]).lower()
            if query and query not in haystack:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._list.addItem(item)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self._select(item)

    def _on_accept(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self._select(item)

    def _select(self, item: QListWidgetItem) -> None:
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        for entry in self._all_entries:
            if entry.id == entry_id:
                self.selected_entry = entry
                self.accept()
                return
