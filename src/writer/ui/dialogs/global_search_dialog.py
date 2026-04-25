"""Global search dialog (M8): unified search across fragments + works."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
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
from writer.services.search_service import SearchHit
from writer.ui.i18n import TR


class GlobalSearchDialog(QDialog):
    """Search modal. ``selected_hit`` is set when the user picks one."""

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self.selected_hit: Optional[SearchHit] = None

        self.setWindowTitle(TR("search.title"))
        self.resize(520, 480)

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("search.placeholder"))
        self._search.textChanged.connect(self._refresh)

        self._results = QListWidget()
        self._results.itemDoubleClicked.connect(self._on_double_click)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Open).setText(TR("search.open"))
        buttons.accepted.connect(self._on_open)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._results, 1)
        layout.addWidget(buttons)

    def _refresh(self) -> None:
        self._results.clear()
        query = self._search.text().strip()
        if not query:
            return
        hits = self._container.search_service.search_all(query, limit=40)
        for hit in hits:
            kind_label = (
                TR("search.kind_fragment")
                if hit.kind == "fragment"
                else TR("search.kind_work")
            )
            text = f"[{kind_label}] {hit.title or TR('search.untitled')} — {hit.snippet}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, hit)
            self._results.addItem(item)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.selected_hit = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_open(self) -> None:
        item = self._results.currentItem()
        if item is None:
            return
        self.selected_hit = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
