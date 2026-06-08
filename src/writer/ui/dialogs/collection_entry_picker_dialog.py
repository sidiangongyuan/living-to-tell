"""Dialog to pick an entry/article for a collection."""
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


def _excerpt(text: str, *, limit: int = 72) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


class CollectionEntryPickerDialog(QDialog):
    def __init__(
        self,
        container: AppContainer,
        excluded_entry_ids: set[str] | None = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._excluded_entry_ids = excluded_entry_ids or set()
        self.selected_entry_id: Optional[str] = None

        self.setWindowTitle(TR("article_picker.title"))
        self.resize(520, 520)

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("article_picker.search_placeholder"))
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

    def _iter_entries(self) -> list[Entry]:
        repo = self._container.entry_repository
        if hasattr(repo, "list_recent"):
            return repo.list_recent(limit=500, include_archived=False)
        return []

    def _refresh(self) -> None:
        query = self._search.text().strip().lower()
        self._list.clear()
        for entry in self._iter_entries():
            if entry.id in self._excluded_entry_ids:
                continue
            haystacks = [
                (entry.title or "").lower(),
                (entry.body or "").lower(),
                " ".join(entry.tags).lower(),
                (entry.entry_type or "").lower(),
            ]
            if query and not any(query in haystack for haystack in haystacks):
                continue
            label = entry.title.strip() or TR("search.untitled")
            summary = _excerpt(entry.body)
            suffix = f" [{entry.curation_status}]" if entry.curation_status else ""
            item = QListWidgetItem(f"{label}{suffix}")
            item.setToolTip(summary or label)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._list.addItem(item)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.selected_entry_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_accept(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self.selected_entry_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
