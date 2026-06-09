"""Dialog to add the current article to one or more collections."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.ui.i18n import TR
from writer.ui.widgets.empty_state import EmptyStateCard


class EntryCollectionPickerDialog(QDialog):
    def __init__(
        self,
        container: AppContainer,
        *,
        entry_id: str,
        excluded_collection_ids: set[str] | None = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._entry_id = entry_id
        self._excluded_collection_ids = excluded_collection_ids or set()
        self._selected_ids_cache: set[str] = set()
        self.selected_collection_ids: list[str] = []

        self.setWindowTitle(TR("collection_picker.title"))
        self.resize(520, 520)

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("collection_picker.search_placeholder"))
        self._search.textChanged.connect(self._refresh)

        self._selected_count = QLabel(
            TR("collection_picker.selected_count").format(count=0)
        )
        self._selected_count.setObjectName("MetaLabel")

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.itemDoubleClicked.connect(self._on_double_click)

        self._empty = EmptyStateCard(
            TR("collection_picker.empty_title"),
            TR("collection_picker.empty_desc"),
        )
        empty_wrap = QWidget()
        empty_layout = QVBoxLayout(empty_wrap)
        empty_layout.setContentsMargins(16, 16, 16, 16)
        empty_layout.addWidget(self._empty)
        empty_layout.addStretch(1)
        self._empty_wrap = empty_wrap

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._selected_count)
        layout.addWidget(self._list, 1)
        layout.addWidget(empty_wrap, 1)
        layout.addWidget(buttons)

        self._refresh()

    def _collections(self) -> list:
        try:
            return list(self._container.collection_repository.list_all())
        except AttributeError:
            return []

    def _set_empty_visible(self, visible: bool) -> None:
        self._list.setVisible(not visible)
        self._empty_wrap.setVisible(visible)

    def _refresh(self) -> None:
        query = self._search.text().strip().lower()
        self._list.blockSignals(True)
        self._list.clear()
        visible_count = 0
        for collection in self._collections():
            if collection.id in self._excluded_collection_ids:
                continue
            haystacks = [
                (collection.name or "").lower(),
                (collection.description or "").lower(),
            ]
            if query and not any(query in haystack for haystack in haystacks):
                continue
            visible_count += 1
            item = QListWidgetItem(collection.name or TR("collections.untitled"))
            item.setToolTip(collection.description or item.text())
            item.setData(Qt.ItemDataRole.UserRole, collection.id)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setCheckState(
                Qt.CheckState.Checked
                if collection.id in self._selected_ids_cache
                else Qt.CheckState.Unchecked
            )
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._set_empty_visible(visible_count == 0)
        self._update_selected_state()

    def _sync_selected_ids_from_visible_items(self) -> None:
        visible_ids: set[str] = set()
        checked_ids: set[str] = set()
        for row in range(self._list.count()):
            item = self._list.item(row)
            collection_id = item.data(Qt.ItemDataRole.UserRole)
            if not collection_id:
                continue
            visible_ids.add(collection_id)
            if item.checkState() == Qt.CheckState.Checked:
                checked_ids.add(collection_id)
        self._selected_ids_cache.difference_update(visible_ids - checked_ids)
        self._selected_ids_cache.update(checked_ids)
        self._update_selected_state()

    def _update_selected_state(self) -> None:
        self.selected_collection_ids = [
            collection.id
            for collection in self._collections()
            if collection.id in self._selected_ids_cache
            and collection.id not in self._excluded_collection_ids
        ]
        self._selected_count.setText(
            TR("collection_picker.selected_count").format(
                count=len(self.selected_collection_ids)
            )
        )
        self._ok_btn.setEnabled(bool(self.selected_collection_ids))

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        self._sync_selected_ids_from_visible_items()

    def _on_double_click(self, item: QListWidgetItem) -> None:
        target = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(target)

    def _on_accept(self) -> None:
        self._sync_selected_ids_from_visible_items()
        if not self.selected_collection_ids:
            return
        self.accept()
