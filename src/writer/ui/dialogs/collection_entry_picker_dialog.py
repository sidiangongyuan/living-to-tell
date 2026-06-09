"""Dialog to pick one or more entries/articles for collection membership."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.models.entry import Entry
from writer.ui.i18n import TR
from writer.ui.widgets.empty_state import EmptyStateCard


def _excerpt(text: str, *, limit: int = 120) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _entry_word_count(body: str) -> int:
    if not body:
        return 0
    total = 0
    token: list[str] = []
    for ch in body:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            if token:
                text = "".join(token).strip()
                if text:
                    total += 1
                token = []
            total += 1
            continue
        token.append(ch)
    if token:
        for part in "".join(token).split():
            if part.strip():
                total += 1
    return total


class _ArticlePickerCard(QFrame):
    def __init__(self, entry: Entry, *, disabled: bool, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("SpecimenPreviewCard")

        title = QLabel(entry.title.strip() or TR("search.untitled"))
        title.setObjectName("SpecimenPreviewTitle")
        title.setWordWrap(True)

        excerpt = QLabel(_excerpt(entry.body))
        excerpt.setObjectName("SpecimenPreviewMeta")
        excerpt.setWordWrap(True)
        excerpt.setVisible(bool(excerpt.text()))

        tags_text = ", ".join(entry.tags) if entry.tags else TR("article_picker.meta_no_tags")
        meta_parts = [
            TR("article_picker.meta_words").format(count=_entry_word_count(entry.body)),
            TR("article_picker.meta_tags").format(tags=tags_text),
        ]
        if entry.curation_status:
            meta_parts.append(
                TR("article_picker.meta_status").format(status=entry.curation_status)
            )
        meta = QLabel(" · ".join(part for part in meta_parts if part))
        meta.setObjectName("SpecimenPreviewNote")
        meta.setWordWrap(True)

        badge = QLabel(TR("article_picker.existing_badge"))
        badge.setObjectName("MetaLabel")
        badge.setVisible(disabled)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(excerpt)
        layout.addWidget(meta)
        layout.addWidget(badge)


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
        self._selected_ids_cache: set[str] = set()
        self.selected_entry_id: Optional[str] = None
        self.selected_entry_ids: list[str] = []

        self.setWindowTitle(TR("article_picker.title"))
        self.resize(620, 600)

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("article_picker.search_placeholder"))
        self._search.textChanged.connect(self._refresh)

        self._selected_count = QLabel(TR("article_picker.selected_count").format(count=0))
        self._selected_count.setObjectName("MetaLabel")

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.itemDoubleClicked.connect(self._on_double_click)

        self._empty = EmptyStateCard(
            TR("article_picker.empty_title"),
            TR("article_picker.empty_desc"),
        )
        empty_wrap = QWidget()
        empty_layout = QVBoxLayout(empty_wrap)
        empty_layout.setContentsMargins(16, 16, 16, 16)
        empty_layout.addWidget(self._empty)
        empty_layout.addStretch(1)

        self._content_stack = QWidget()
        content_layout = QVBoxLayout(self._content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._list)
        content_layout.addWidget(empty_wrap)
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
        layout.addWidget(self._content_stack, 1)
        layout.addWidget(buttons)

        self._refresh()

    def _iter_entries(self) -> list[Entry]:
        repo = self._container.entry_repository
        if hasattr(repo, "list_recent"):
            return repo.list_recent(limit=500, include_archived=False)
        return []

    def _set_empty_visible(self, visible: bool) -> None:
        self._list.setVisible(not visible)
        self._empty_wrap.setVisible(visible)

    def _refresh(self) -> None:
        query = self._search.text().strip().lower()
        self._list.blockSignals(True)
        self._list.clear()
        visible_count = 0
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
            visible_count += 1
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            flags = item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            item.setFlags(flags)
            item.setCheckState(
                Qt.CheckState.Checked
                if entry.id in self._selected_ids_cache
                else Qt.CheckState.Unchecked
            )
            self._list.addItem(item)
            card = _ArticlePickerCard(entry, disabled=False)
            item.setSizeHint(card.sizeHint())
            self._list.setItemWidget(item, card)
        self._list.blockSignals(False)
        self._set_empty_visible(visible_count == 0)
        self._update_selected_state()

    def _checked_ids(self) -> list[str]:
        ids: list[str] = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                entry_id = item.data(Qt.ItemDataRole.UserRole)
                if entry_id:
                    ids.append(entry_id)
        return ids

    def _sync_selected_ids_from_visible_items(self) -> None:
        visible_ids: set[str] = set()
        checked_ids: set[str] = set()
        for row in range(self._list.count()):
            item = self._list.item(row)
            entry_id = item.data(Qt.ItemDataRole.UserRole)
            if not entry_id:
                continue
            visible_ids.add(entry_id)
            if item.checkState() == Qt.CheckState.Checked:
                checked_ids.add(entry_id)
        self._selected_ids_cache.difference_update(visible_ids - checked_ids)
        self._selected_ids_cache.update(checked_ids)
        self._update_selected_state()

    def _update_selected_state(self) -> None:
        self.selected_entry_ids = [
            entry.id
            for entry in self._iter_entries()
            if entry.id in self._selected_ids_cache
            and entry.id not in self._excluded_entry_ids
        ]
        self.selected_entry_id = self.selected_entry_ids[0] if self.selected_entry_ids else None
        self._selected_count.setText(
            TR("article_picker.selected_count").format(count=len(self.selected_entry_ids))
        )
        self._ok_btn.setEnabled(bool(self.selected_entry_ids))

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        self._sync_selected_ids_from_visible_items()

    def _on_double_click(self, item: QListWidgetItem) -> None:
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return
        target = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(target)
        if target == Qt.CheckState.Checked:
            self._on_accept()

    def _on_accept(self) -> None:
        self._sync_selected_ids_from_visible_items()
        if not self.selected_entry_ids:
            return
        self.accept()
