"""Reference picker dialog (M4A).

Shown before each AI rewrite so the user can optionally attach reference
passages to the prompt. Three exit modes:

* **Accepted** — user clicked "Use selected": returns the chosen contents
  (may be an empty list if nothing was ticked).
* **Skip** — user clicked "Skip references": returns ``[]``. Semantically
  the same as Accepted with no ticks, but surfaced as a distinct button
  so the intent is explicit.
* **Rejected / closed** — returns ``None`` and the caller aborts the
  rewrite.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.reference_passage import ReferencePassage
from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.ui.i18n import TR


class ReferencePickerDialog(QDialog):
    def __init__(
        self, repo: ReferenceRepository, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("refpicker.title"))
        self.resize(560, 440)
        self._repo = repo
        self._selected_contents: List[str] = []
        self._skipped = False

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("refpicker.search_placeholder"))
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        self._use_btn = QPushButton(TR("refpicker.use_btn"))
        self._skip_btn = QPushButton(TR("refpicker.skip_btn"))
        self._cancel_btn = QPushButton(TR("refpicker.cancel_btn"))

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self._use_btn)
        button_row.addWidget(self._skip_btn)
        button_row.addWidget(self._cancel_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(TR("refpicker.hint")))
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)
        layout.addLayout(button_row)

        # wiring
        self._search.textChanged.connect(lambda _t: self._refresh())
        self._use_btn.clicked.connect(self._on_use)
        self._skip_btn.clicked.connect(self._on_skip)
        self._cancel_btn.clicked.connect(self.reject)

        self._refresh()

    # --------------- public ----------------
    def selected_contents(self) -> List[str]:
        return list(self._selected_contents)

    def was_skipped(self) -> bool:
        return self._skipped

    # --------------- internals ----------------
    def _refresh(self) -> None:
        query = self._search.text().strip()
        items = (
            self._repo.search(query) if query else self._repo.list_recent()
        )
        self._list.clear()
        for passage in items:
            self._append_item(passage)

    def _append_item(self, passage: ReferencePassage) -> None:
        item = QListWidgetItem(passage.display_label())
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Unchecked)
        item.setData(Qt.ItemDataRole.UserRole, passage.id)
        item.setToolTip(passage.content[:400])
        self._list.addItem(item)

    def _collect_checked_ids(self) -> List[str]:
        out: List[str] = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                out.append(item.data(Qt.ItemDataRole.UserRole))
        return out

    def _on_use(self) -> None:
        ids = self._collect_checked_ids()
        passages = self._repo.get_many(ids)
        self._selected_contents = [p.content for p in passages]
        self._skipped = False
        self.accept()

    def _on_skip(self) -> None:
        self._selected_contents = []
        self._skipped = True
        self.accept()
