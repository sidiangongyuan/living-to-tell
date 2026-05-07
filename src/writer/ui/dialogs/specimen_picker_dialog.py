"""Specimen picker dialog (M-StyleSpecimen).

Lets the user search, filter by usage kind, and select one or more style
specimens to attach to an AI task.  Returns a list of ``ReferencePassage``
objects; empty list if nothing was selected.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.reference_passage import (
    USAGE_KINDS,
    ReferencePassage,
)
from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.ui.dialogs.specimen_similarity import rank_similar_passages
from writer.ui.i18n import TR

_USAGE_LABEL_KEYS = {
    "style": "reflib.usage_kind_style",
    "imagery": "reflib.usage_kind_imagery",
    "technique": "reflib.usage_kind_technique",
    "character": "reflib.usage_kind_character",
    "setting": "reflib.usage_kind_setting",
    "other": "reflib.usage_kind_other",
    "quote": "reflib.usage_kind_quote",
}


def _usage_label(uk: str) -> str:
    return TR(_USAGE_LABEL_KEYS.get(uk, "reflib.usage_kind_style"))


class SpecimenPickerDialog(QDialog):
    """Multi-select picker for style specimens."""

    def __init__(
        self,
        repo: ReferenceRepository,
        *,
        preselect_query: str = "",
        recommended_text: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("specimen.picker_title"))
        self.resize(560, 480)
        self._repo = repo
        self._selected: List[ReferencePassage] = []
        self._recommended_text = recommended_text.strip()

        # Search box
        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("rlp.search_placeholder"))
        if preselect_query:
            self._search.setText(preselect_query)

        # Usage kind filter
        self._usage_filter = QComboBox()
        self._usage_filter.setObjectName("SpecimenUsageKindFilter")
        self._usage_filter.addItem(TR("reflib.usage_kind_filter_all"), None)
        for uk in USAGE_KINDS:
            self._usage_filter.addItem(_usage_label(uk), uk)

        filter_row = QHBoxLayout()
        filter_row.addWidget(self._search, 1)
        filter_row.addWidget(self._usage_filter)

        # Passage list (checkbox multi-select)
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        # Buttons
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._button_box)

        # Wiring
        self._search.textChanged.connect(lambda _: self._refresh())
        self._usage_filter.currentIndexChanged.connect(lambda _: self._refresh())

        self._refresh()

    # --------------- public API ----------------

    @property
    def selected_passages(self) -> List[ReferencePassage]:
        """The passages confirmed by the user (non-empty only after accept)."""
        return list(self._selected)

    # --------------- internals ----------------

    def _refresh(self) -> None:
        query = self._search.text().strip()
        usage_kind: Optional[str] = self._usage_filter.currentData()

        if query:
            passages = self._repo.search(query, usage_kind=usage_kind)
        elif self._recommended_text:
            candidates = self._repo.list_recent(usage_kind=usage_kind, limit=500)
            passages = rank_similar_passages(
                candidates,
                self._recommended_text,
                limit=200,
            ) or self._repo.list_recent(usage_kind=usage_kind)
        else:
            passages = self._repo.list_recent(usage_kind=usage_kind)

        # Remember currently checked IDs so we can restore them after rebuild.
        checked_ids = self._checked_ids()

        self._list.blockSignals(True)
        try:
            self._list.clear()
            for passage in passages:
                label = passage.display_label()
                uk_badge = f"[{_usage_label(passage.usage_kind)}]"
                item = QListWidgetItem(f"{label}  {uk_badge}")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                state = (
                    Qt.CheckState.Checked
                    if passage.id in checked_ids
                    else Qt.CheckState.Unchecked
                )
                item.setCheckState(state)
                item.setData(Qt.ItemDataRole.UserRole, passage.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, passage)
                tip = passage.content[:300]
                if passage.personal_note:
                    tip += f"\n\nNote: {passage.personal_note[:200]}"
                item.setToolTip(tip)
                self._list.addItem(item)
        finally:
            self._list.blockSignals(False)

    def _checked_ids(self) -> set:
        result: set = set()
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                result.add(item.data(Qt.ItemDataRole.UserRole))
        return result

    def _collect_checked_passages(self) -> List[ReferencePassage]:
        out: List[ReferencePassage] = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                passage = item.data(Qt.ItemDataRole.UserRole + 1)
                if isinstance(passage, ReferencePassage):
                    out.append(passage)
        return out

    def _on_accept(self) -> None:
        self._selected = self._collect_checked_passages()
        self.accept()
