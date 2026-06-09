"""Collections panel: manage article-based collections in reading order."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.enums import EntryType
from writer.domain.models.entry import Entry
from writer.ui.dialogs.collection_entry_picker_dialog import CollectionEntryPickerDialog
from writer.ui.i18n import TR
from writer.ui.widgets.editor_find import PaperPlainTextEdit
from writer.ui.widgets.empty_state import EmptyStateCard


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


def _article_excerpt(body: str, *, limit: int = 180) -> str:
    text = " ".join((body or "").split())
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _display_entry_type(entry_type: str) -> str:
    value = (entry_type or "").strip().lower()
    if value in {"article", "essay", "story", "chapter"}:
        return value
    if value == EntryType.FRAGMENT.value:
        return "fragment"
    if not value:
        return "article"
    return value


@dataclass
class _CollectionEntryBundle:
    entry: Entry
    sort_order: int


class _CollectionArticleCard(QFrame):
    clicked = Signal(str)
    move_up_requested = Signal(str)
    move_down_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(
        self,
        entry: Entry,
        *,
        sort_order: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.entry_id = entry.id
        self._selected = False
        self.setObjectName("CollectionArticleCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", False)

        title = QLabel(entry.title.strip() or TR("search.untitled"))
        title.setObjectName("SpecimenPreviewTitle")
        title.setWordWrap(True)

        excerpt = QLabel(_article_excerpt(entry.body) or TR("collections.preview_empty"))
        excerpt.setObjectName("SpecimenPreviewMeta")
        excerpt.setWordWrap(True)

        meta_parts = [
            f"#{sort_order + 1}",
            TR("collections.article_words").format(count=_entry_word_count(entry.body)),
            _display_entry_type(entry.entry_type),
            entry.curation_status or "",
        ]
        meta = QLabel(" · ".join(part for part in meta_parts if part))
        meta.setObjectName("SpecimenPreviewMeta")
        meta.setWordWrap(True)

        tags_text = ", ".join(entry.tags) if entry.tags else TR("context.no_value")
        tags = QLabel(tags_text)
        tags.setObjectName("SpecimenPreviewNote")
        tags.setWordWrap(True)

        drag_hint = QLabel(TR("collections.article_drop_hint"))
        drag_hint.setObjectName("MetaLabel")
        drag_hint.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._up_btn = QPushButton("↑")
        self._up_btn.setObjectName("GhostButton")
        self._up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.entry_id))
        self._down_btn = QPushButton("↓")
        self._down_btn.setObjectName("GhostButton")
        self._down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.entry_id))
        self._remove_btn = QPushButton(TR("collections.remove_article"))
        self._remove_btn.setObjectName("GhostButton")
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.entry_id))

        btns = QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(6)
        btns.addWidget(self._up_btn)
        btns.addWidget(self._down_btn)
        btns.addStretch(1)
        btns.addWidget(self._remove_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(excerpt)
        layout.addWidget(meta)
        layout.addWidget(tags)
        layout.addWidget(drag_hint)
        layout.addLayout(btns)

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entry_id)
        super().mousePressEvent(event)


class _CollectionArticlesList(QListWidget):
    reordered = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("CollectionArticlesList")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSpacing(10)

    def dropEvent(self, event) -> None:  # noqa: N802
        super().dropEvent(event)
        ordered_ids: list[str] = []
        for row in range(self.count()):
            entry_id = self.item(row).data(Qt.ItemDataRole.UserRole)
            if entry_id:
                ordered_ids.append(entry_id)
        self.reordered.emit(ordered_ids)


class CollectionsPanel(QWidget):
    collection_selected = Signal(str)

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._entry_cards: list[_CollectionArticleCard] = []
        self._entry_bundles: list[_CollectionEntryBundle] = []
        self._selected_entry_id: Optional[str] = None
        self._description_save_timer = QTimer(self)
        self._description_save_timer.setSingleShot(True)
        self._description_save_timer.setInterval(300)
        self._description_save_timer.timeout.connect(self._flush_collection_metadata)
        self._suppress_description_flush = False
        self._suppress_title_flush = False
        self._suppress_article_reorder = False

        self._collections = QListWidget()
        self._collections.itemSelectionChanged.connect(self._on_collection_changed)

        self._new_btn = QPushButton(TR("collections.new"))
        self._new_btn.setObjectName("PrimaryButton")
        self._new_btn.clicked.connect(self._on_new_collection)
        self._rename_btn = QPushButton(TR("collections.rename"))
        self._rename_btn.clicked.connect(self._on_rename_collection)
        self._delete_btn = QPushButton(TR("collections.delete"))
        self._delete_btn.setObjectName("DangerButton")
        self._delete_btn.clicked.connect(self._on_delete_collection)

        coll_btns = QHBoxLayout()
        coll_btns.setContentsMargins(0, 0, 0, 0)
        coll_btns.setSpacing(6)
        for button in (self._new_btn, self._rename_btn, self._delete_btn):
            coll_btns.addWidget(button)
        coll_btns.addStretch(1)

        self._collections_empty = EmptyStateCard(
            TR("empty.collections_title"),
            TR("empty.collections_desc"),
            primary_label=TR("empty.collections_primary"),
            primary_callback=self._on_new_collection,
        )
        coll_empty_wrap = QWidget()
        cew = QVBoxLayout(coll_empty_wrap)
        cew.setContentsMargins(8, 16, 8, 16)
        cew.addWidget(self._collections_empty)
        cew.addStretch(1)

        self._collections_stack = QStackedWidget()
        self._collections_stack.addWidget(self._collections)
        self._collections_stack.addWidget(coll_empty_wrap)

        self._column_title = QLabel(TR("column.collections"))
        self._column_title.setObjectName("ColumnTitle")

        left = QWidget()
        left.setObjectName("WriterListColumn")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._column_title)
        left_layout.addLayout(coll_btns)
        left_layout.addWidget(QLabel(TR("collections.label")))
        left_layout.addWidget(self._collections_stack, 1)

        self._add_article_btn = QPushButton(TR("collections.add_article"))
        self._add_article_btn.setObjectName("PrimaryButton")
        self._add_article_btn.clicked.connect(self._on_add_article)
        self._remove_article_btn = QPushButton(TR("collections.remove_article"))
        self._remove_article_btn.clicked.connect(self._on_remove_article)
        self._export_btn = QPushButton(TR("collections.export"))
        self._export_btn.clicked.connect(self._on_export_collection)

        middle_header = QLabel(TR("collections.works_label"))
        middle_header.setObjectName("ColumnTitle")

        article_btns = QHBoxLayout()
        article_btns.setContentsMargins(0, 0, 0, 0)
        article_btns.setSpacing(6)
        article_btns.addWidget(self._add_article_btn)
        article_btns.addWidget(self._remove_article_btn)
        article_btns.addStretch(1)
        article_btns.addWidget(self._export_btn)

        self._article_search = QLineEdit()
        self._article_search.setPlaceholderText(TR("collections.search_articles"))
        self._article_search.textChanged.connect(self._refresh_articles)

        self._articles_list = _CollectionArticlesList()
        self._articles_list.itemSelectionChanged.connect(self._on_article_item_selection_changed)
        self._articles_list.reordered.connect(self._on_articles_reordered)

        self._articles_empty = EmptyStateCard(
            TR("collections.add_article_empty_title"),
            TR("collections.add_article_empty_desc"),
            primary_label=TR("collections.add_article_empty_primary"),
            primary_callback=self._on_add_article,
        )
        empty_wrap = QWidget()
        ewl = QVBoxLayout(empty_wrap)
        ewl.setContentsMargins(16, 16, 16, 16)
        ewl.addWidget(self._articles_empty)
        ewl.addStretch(1)

        self._articles_stack = QStackedWidget()
        self._articles_stack.addWidget(self._articles_list)
        self._articles_stack.addWidget(empty_wrap)

        middle = QWidget()
        middle.setObjectName("CollectionArticlesColumn")
        middle_layout = QVBoxLayout(middle)
        middle_layout.setContentsMargins(16, 16, 16, 16)
        middle_layout.setSpacing(8)
        middle_layout.addWidget(middle_header)
        middle_layout.addLayout(article_btns)
        middle_layout.addWidget(self._article_search)
        middle_layout.addWidget(self._articles_stack, 1)

        preview_header = QLabel(TR("collections.preview_title"))
        preview_header.setObjectName("ColumnTitle")

        self._collection_title_edit = QLineEdit()
        self._collection_title_edit.setPlaceholderText(TR("collections.new_name_prompt"))
        self._collection_title_edit.editingFinished.connect(self._flush_collection_title)

        self._collection_description = QPlainTextEdit()
        self._collection_description.setPlaceholderText(
            TR("collections.description_placeholder")
        )
        self._collection_description.setFixedHeight(110)
        self._collection_description.textChanged.connect(self._queue_description_save)

        self._preview_title = QLabel(TR("collections.preview_empty"))
        self._preview_title.setObjectName("SpecimenPreviewTitle")
        self._preview_title.setWordWrap(True)

        self._preview_meta = QLabel("")
        self._preview_meta.setObjectName("SpecimenPreviewMeta")
        self._preview_meta.setWordWrap(True)

        self._preview_tags = QLabel("")
        self._preview_tags.setObjectName("SpecimenPreviewMeta")
        self._preview_tags.setWordWrap(True)

        self._preview_body = PaperPlainTextEdit()
        self._preview_body.setObjectName("AISelectionPreview")
        self._preview_body.setReadOnly(True)
        self._preview_body.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        preview_card = QFrame()
        preview_card.setObjectName("SpecimenPreviewCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(8)
        preview_layout.addWidget(QLabel(TR("collections.article_preview_label")))
        preview_layout.addWidget(self._preview_title)
        preview_layout.addWidget(self._preview_meta)
        preview_layout.addWidget(self._preview_tags)
        preview_layout.addWidget(self._preview_body, 1)

        right = QWidget()
        right.setObjectName("CollectionPreviewColumn")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 16, 20, 16)
        right_layout.setSpacing(10)
        right_layout.addWidget(preview_header)
        right_layout.addWidget(QLabel(TR("collections.label")))
        right_layout.addWidget(self._collection_title_edit)
        right_layout.addWidget(QLabel(TR("collections.description_label")))
        right_layout.addWidget(self._collection_description)
        right_layout.addWidget(preview_card, 1)

        self._collection_unselected_card = EmptyStateCard(
            TR("empty.collection_unselected_title"),
            TR("empty.collection_unselected_desc"),
            primary_label=TR("empty.collection_unselected_primary"),
            primary_callback=self._on_new_collection,
        )
        unselected_wrap = QWidget()
        uw = QVBoxLayout(unselected_wrap)
        uw.setContentsMargins(32, 48, 32, 32)
        uw.addWidget(self._collection_unselected_card)
        uw.addStretch(1)

        self._workspace = QWidget()
        workspace_layout = QHBoxLayout(self._workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(middle, 4)
        workspace_layout.addWidget(right, 5)

        self._right_stack = QStackedWidget()
        self._right_stack.addWidget(self._workspace)
        self._right_stack.addWidget(unselected_wrap)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self._right_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 960])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.refresh_collections()

    # ------------------------------------------------------------------
    def refresh_collections(self) -> None:
        previous_collection_id = self._current_collection_id()
        self._collections.blockSignals(True)
        self._collections.clear()
        for collection in self._container.collection_repository.list_all():
            item = QListWidgetItem(collection.name or TR("collections.untitled"))
            item.setData(Qt.ItemDataRole.UserRole, collection.id)
            self._collections.addItem(item)
        self._collections.blockSignals(False)

        self._collections_stack.setCurrentIndex(1 if self._collections.count() == 0 else 0)

        if previous_collection_id is not None:
            for row in range(self._collections.count()):
                if (
                    self._collections.item(row).data(Qt.ItemDataRole.UserRole)
                    == previous_collection_id
                ):
                    self._collections.setCurrentRow(row)
                    self._load_collection_metadata()
                    self._refresh_articles()
                    self._update_right_stack()
                    return

        self._collections.clearSelection()
        self._collections.setCurrentRow(-1)
        self._selected_entry_id = None
        self._refresh_articles()
        self._load_collection_metadata()
        self._update_right_stack()

    def _current_collection_id(self) -> Optional[str]:
        item = self._collections.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _current_entry_id(self) -> Optional[str]:
        return self._selected_entry_id

    def _on_collection_changed(self) -> None:
        self._selected_entry_id = None
        self._load_collection_metadata()
        self._refresh_articles()
        self._update_right_stack()
        collection_id = self._current_collection_id()
        if collection_id:
            self.collection_selected.emit(collection_id)

    def _update_right_stack(self) -> None:
        self._right_stack.setCurrentIndex(0 if self._current_collection_id() else 1)

    def _load_collection_metadata(self) -> None:
        collection_id = self._current_collection_id()
        collection = (
            self._container.collection_repository.get(collection_id)
            if collection_id
            else None
        )
        self._suppress_title_flush = True
        self._suppress_description_flush = True
        try:
            self._collection_title_edit.setText(collection.name if collection else "")
            self._collection_title_edit.setEnabled(collection is not None)
            self._collection_description.setPlainText(
                collection.description if collection else ""
            )
            self._collection_description.setEnabled(collection is not None)
        finally:
            self._suppress_title_flush = False
            self._suppress_description_flush = False
        self._render_preview(None)

    def _queue_description_save(self) -> None:
        if self._suppress_description_flush:
            return
        if self._current_collection_id() is None:
            return
        self._description_save_timer.start()

    def _flush_collection_title(self) -> None:
        if self._suppress_title_flush:
            return
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        name = self._collection_title_edit.text().strip()
        self._container.collection_repository.rename(collection_id, name)
        current_item = self._collections.currentItem()
        if current_item is not None:
            current_item.setText(name or TR("collections.untitled"))

    def _flush_collection_metadata(self) -> None:
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        description = self._collection_description.toPlainText()
        update_description = getattr(
            self._container.collection_repository,
            "update_description",
            None,
        )
        if callable(update_description):
            update_description(collection_id, description)

    # ------------------------------------------------------------------
    def _collection_entry_bundles(self, collection_id: str) -> list[_CollectionEntryBundle]:
        repo = self._container.collection_repository
        entries_result: Any = None
        for method_name in (
            "list_entries",
            "list_articles",
            "list_entry_items",
            "list_collection_entries",
        ):
            method = getattr(repo, method_name, None)
            if callable(method):
                entries_result = method(collection_id)
                break
        if entries_result is None:
            return []

        bundles: list[_CollectionEntryBundle] = []
        for index, item in enumerate(entries_result):
            if isinstance(item, Entry):
                bundles.append(_CollectionEntryBundle(entry=item, sort_order=index))
                continue
            entry = getattr(item, "entry", None)
            if isinstance(entry, Entry):
                order = int(getattr(item, "sort_order", index))
                bundles.append(_CollectionEntryBundle(entry=entry, sort_order=order))
                continue
            entry_id = (
                getattr(item, "entry_id", None)
                or getattr(item, "article_id", None)
                or getattr(item, "item_id", None)
            )
            if entry_id:
                loaded = self._container.entry_repository.get(entry_id)
                if loaded is None:
                    continue
                order = int(getattr(item, "sort_order", index))
                bundles.append(_CollectionEntryBundle(entry=loaded, sort_order=order))
        bundles.sort(key=lambda bundle: bundle.sort_order)
        return bundles

    def _call_collection_mutation(
        self,
        names: tuple[str, ...],
        *args,
    ) -> Any:
        repo = self._container.collection_repository
        for name in names:
            method = getattr(repo, name, None)
            if callable(method):
                return method(*args)
        raise AttributeError(
            f"Collection repository is missing compatible methods: {', '.join(names)}"
        )

    def _refresh_articles(self) -> None:
        self._articles_list.blockSignals(True)
        self._articles_list.clear()
        self._articles_list.blockSignals(False)
        self._entry_cards.clear()
        self._entry_bundles.clear()

        collection_id = self._current_collection_id()
        if collection_id is None:
            self._articles_stack.setCurrentIndex(1)
            self._articles_empty.set_text(TR("collections.pick_first"), "")
            self._add_article_btn.setEnabled(False)
            self._render_preview(None)
            self._remove_article_btn.setEnabled(False)
            return
        self._add_article_btn.setEnabled(True)

        query = self._article_search.text().strip().lower()
        bundles = self._collection_entry_bundles(collection_id)
        self._entry_bundles = bundles

        visible: list[_CollectionEntryBundle] = []
        for bundle in bundles:
            entry = bundle.entry
            haystacks = [
                (entry.title or "").lower(),
                (entry.body or "").lower(),
                " ".join(entry.tags).lower(),
                (entry.curation_status or "").lower(),
            ]
            if query and not any(query in haystack for haystack in haystacks):
                continue
            visible.append(bundle)

        if not visible:
            if bundles:
                self._articles_empty.set_text(
                    TR("collections.no_search_results_title"),
                    TR("collections.no_search_results_desc"),
                )
            else:
                self._articles_empty.set_text(
                    TR("collections.add_article_empty_title"),
                    TR("collections.add_article_empty_desc"),
                )
            self._articles_stack.setCurrentIndex(1)
            self._selected_entry_id = None
            self._render_preview(None)
            self._remove_article_btn.setEnabled(False)
            return

        self._articles_stack.setCurrentIndex(0)
        valid_ids = {bundle.entry.id for bundle in visible}
        if self._selected_entry_id not in valid_ids:
            self._selected_entry_id = visible[0].entry.id

        self._suppress_article_reorder = True
        try:
            for bundle in visible:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, bundle.entry.id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                card = _CollectionArticleCard(bundle.entry, sort_order=bundle.sort_order)
                card.clicked.connect(self._select_entry)
                card.move_up_requested.connect(
                    lambda entry_id, delta=-1: self._move_entry(entry_id, delta)
                )
                card.move_down_requested.connect(
                    lambda entry_id, delta=1: self._move_entry(entry_id, delta)
                )
                card.remove_requested.connect(self._remove_entry_by_id)
                card.set_selected(bundle.entry.id == self._selected_entry_id)
                self._entry_cards.append(card)
                item.setSizeHint(card.sizeHint())
                self._articles_list.addItem(item)
                self._articles_list.setItemWidget(item, card)
                if bundle.entry.id == self._selected_entry_id:
                    self._articles_list.setCurrentItem(item)
        finally:
            self._suppress_article_reorder = False

        self._remove_article_btn.setEnabled(self._selected_entry_id is not None)
        self._render_preview(self._selected_entry())

    def _selected_entry(self) -> Optional[Entry]:
        if self._selected_entry_id is None:
            return None
        for bundle in self._entry_bundles:
            if bundle.entry.id == self._selected_entry_id:
                return bundle.entry
        return self._container.entry_repository.get(self._selected_entry_id)

    def _on_article_item_selection_changed(self) -> None:
        if self._suppress_article_reorder:
            return
        item = self._articles_list.currentItem()
        entry_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if entry_id:
            self._select_entry(entry_id)

    def _select_entry(self, entry_id: str) -> None:
        self._selected_entry_id = entry_id
        for row, card in enumerate(self._entry_cards):
            selected = card.entry_id == entry_id
            card.set_selected(selected)
            item = self._articles_list.item(row)
            if selected and item is not None and self._articles_list.currentItem() is not item:
                self._articles_list.setCurrentItem(item)
        self._remove_article_btn.setEnabled(True)
        self._render_preview(self._selected_entry())

    def _render_preview(self, entry: Optional[Entry]) -> None:
        if entry is None:
            self._preview_title.setText(TR("collections.preview_empty"))
            self._preview_meta.setText("")
            self._preview_tags.setText("")
            self._preview_body.setPlainText("")
            return

        self._preview_title.setText(entry.title.strip() or TR("search.untitled"))
        self._preview_meta.setText(
            " · ".join(
                [
                    TR("collections.article_words").format(count=_entry_word_count(entry.body)),
                    _display_entry_type(entry.entry_type),
                    entry.curation_status or "",
                ]
            ).strip(" ·")
        )
        tags_text = ", ".join(entry.tags) if entry.tags else TR("context.no_value")
        self._preview_tags.setText(tags_text)
        self._preview_body.setPlainText(entry.body or "")
        cursor = self._preview_body.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self._preview_body.setTextCursor(cursor)

    # ------------------------------------------------------------------
    def _on_new_collection(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            TR("collections.new"),
            TR("collections.new_name_prompt"),
        )
        if not ok:
            return
        collection = self._container.collection_repository.create(name=name.strip())
        self.refresh_collections()
        for row in range(self._collections.count()):
            if self._collections.item(row).data(Qt.ItemDataRole.UserRole) == collection.id:
                self._collections.setCurrentRow(row)
                break
        self._update_right_stack()

    def _on_rename_collection(self) -> None:
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        collection = self._container.collection_repository.get(collection_id)
        if collection is None:
            return
        name, ok = QInputDialog.getText(
            self,
            TR("collections.rename"),
            TR("collections.new_name_prompt"),
            text=collection.name,
        )
        if not ok:
            return
        self._container.collection_repository.rename(collection_id, name.strip())
        self.refresh_collections()

    def _on_delete_collection(self) -> None:
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        answer = QMessageBox.question(
            self,
            TR("collections.delete"),
            TR("collections.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._container.collection_repository.delete(collection_id)
        self.refresh_collections()

    def _on_add_article(self) -> None:
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        dialog = CollectionEntryPickerDialog(
            self._container,
            self._existing_collection_entry_ids(collection_id),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_entry_ids:
            return
        first_added: Optional[str] = None
        try:
            for entry_id in dialog.selected_entry_ids:
                result = self._call_collection_mutation(
                    ("add_entry", "add_article", "append_entry", "link_entry"),
                    collection_id,
                    entry_id,
                )
                if first_added is None and result is not None:
                    first_added = entry_id
        except AttributeError as exc:
            QMessageBox.information(self, TR("collections.add_article"), str(exc))
            return
        self._selected_entry_id = first_added or dialog.selected_entry_id
        self._refresh_articles()
        self.collection_selected.emit(collection_id)

    def _existing_collection_entry_ids(self, collection_id: str) -> set[str]:
        return {bundle.entry.id for bundle in self._collection_entry_bundles(collection_id)}

    def _on_remove_article(self) -> None:
        entry_id = self._current_entry_id()
        if entry_id is None:
            return
        self._remove_entry_by_id(entry_id)

    def _remove_entry_by_id(self, entry_id: str) -> None:
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        try:
            self._call_collection_mutation(
                ("remove_entry", "remove_article", "unlink_entry"),
                collection_id,
                entry_id,
            )
        except AttributeError as exc:
            QMessageBox.information(self, TR("collections.remove_article"), str(exc))
            return
        if self._selected_entry_id == entry_id:
            self._selected_entry_id = None
        self._refresh_articles()
        self.collection_selected.emit(collection_id)

    def _move_entry(self, entry_id: str, delta: int) -> None:
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        ordered_ids = [bundle.entry.id for bundle in self._entry_bundles]
        try:
            index = ordered_ids.index(entry_id)
        except ValueError:
            return
        new_index = max(0, min(len(ordered_ids) - 1, index + delta))
        if new_index == index:
            return
        ordered_ids.insert(new_index, ordered_ids.pop(index))
        self._persist_reordered_entries(collection_id, ordered_ids, selected_entry_id=entry_id)

    def _on_articles_reordered(self, ordered_ids: list[str]) -> None:
        if self._suppress_article_reorder:
            return
        collection_id = self._current_collection_id()
        if collection_id is None or not ordered_ids:
            return
        self._persist_reordered_entries(
            collection_id,
            ordered_ids,
            selected_entry_id=self._selected_entry_id,
        )

    def _persist_reordered_entries(
        self,
        collection_id: str,
        ordered_ids: list[str],
        *,
        selected_entry_id: Optional[str],
    ) -> None:
        try:
            self._call_collection_mutation(
                ("reorder_entries", "reorder_articles", "reorder_items"),
                collection_id,
                ordered_ids,
            )
        except AttributeError as exc:
            QMessageBox.information(self, TR("collections.works_label"), str(exc))
            return
        self._selected_entry_id = selected_entry_id
        self._refresh_articles()
        self.collection_selected.emit(collection_id)

    # ------------------------------------------------------------------
    def _on_export_collection(self) -> None:
        collection_id = self._current_collection_id()
        if collection_id is None:
            return
        path, _selected = QFileDialog.getSaveFileName(
            self,
            TR("collections.export"),
            "",
            TR("export.filter_all"),
        )
        if not path:
            return
        service = self._container.work_export_service
        try:
            lower = path.lower()
            if lower.endswith(".docx"):
                service.export_collection_docx(collection_id, path)
            elif lower.endswith(".md"):
                Path(path).write_text(
                    service.export_collection_md(collection_id),
                    encoding="utf-8",
                )
            else:
                Path(path).write_text(
                    service.export_collection_txt(collection_id),
                    encoding="utf-8",
                )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, TR("dlg.export_failed"), str(exc))
            return
        QMessageBox.information(
            self,
            TR("collections.export"),
            TR("collections.export_done").format(path=path),
        )
