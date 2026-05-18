"""Specimen picker dialog (M-StyleSpecimen)."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEvent, QSignalBlocker, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.app.settings import Settings
from writer.domain.models.reference_passage import (
    REFERENCE_KIND_CHARACTER,
    REFERENCE_KIND_EXCERPT,
    REFERENCE_KIND_LOCATION,
    REFERENCE_KIND_SETTING,
    REFERENCE_KINDS,
    USAGE_KINDS,
    ReferencePassage,
)
from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.ui.dialogs.specimen_similarity import rank_similar_passages
from writer.ui.i18n import TR
from writer.ui.reference_grouping import (
    ALL_GROUP_KEY,
    DEFAULT_SPECIMEN_PICKER_GROUP_MODE,
    NON_PASSAGE_ITEM,
    PassageGroup,
    compact_text,
    find_group_key_for_passage,
    group_mode_options,
    group_reference_passages,
    normalize_group_mode,
    source_group_title,
    split_tags,
    usage_kind_label,
)

_KIND_LABEL_KEYS = {
    REFERENCE_KIND_CHARACTER: "reflib.kind_character",
    REFERENCE_KIND_LOCATION: "reflib.kind_location",
    REFERENCE_KIND_SETTING: "reflib.kind_setting",
    REFERENCE_KIND_EXCERPT: "reflib.kind_excerpt",
}

_ITEM_AUX_TEXT_ROLE = Qt.ItemDataRole.UserRole + 8
_SHELF_ITEM_MIN_HEIGHT = 82
_SPECIMEN_CARD_MIN_HEIGHT = 212


def _kind_label(kind: str) -> str:
    return TR(_KIND_LABEL_KEYS.get(kind, "reflib.kind_excerpt"))


def _blank(value: str) -> str:
    return value.strip() if value and value.strip() else TR("context.no_value")


def _refresh_dynamic_style(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _apply_conservative_size_hint(
    item: QListWidgetItem,
    widget: QWidget,
    *,
    min_height: int,
) -> None:
    widget.ensurePolished()
    height = max(
        min_height,
        widget.minimumSizeHint().height(),
        widget.sizeHint().height(),
    )
    item.setSizeHint(QSize(0, height))


class _ClickableCard(QWidget):
    clicked = Signal()

    def _bind_click_target(self, widget: QWidget) -> None:
        widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and getattr(event, "button", lambda: None)() == Qt.MouseButton.LeftButton
        ):
            self.clicked.emit()
        return super().eventFilter(watched, event)


class _GroupShelfCard(_ClickableCard):
    def __init__(
        self,
        title: str,
        *,
        subtitle: str = "",
        count: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SpecimenShelfCard")
        self.setProperty("current", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("SpecimenShelfTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        meta_parts = []
        if subtitle:
            meta_parts.append(subtitle)
        if count:
            meta_parts.append(TR("reflib.group_count").format(count=count))
        meta_label = QLabel(" · ".join(meta_parts))
        meta_label.setObjectName("SpecimenShelfMeta")
        meta_label.setWordWrap(True)
        meta_label.setVisible(bool(meta_parts))
        layout.addWidget(meta_label)

        for widget in (self, title_label, meta_label):
            self._bind_click_target(widget)

    def set_current(self, current: bool) -> None:
        if self.property("current") == current:
            return
        self.setProperty("current", current)
        _refresh_dynamic_style(self)


class _SpecimenListCard(_ClickableCard):
    selection_toggled = Signal(bool)

    def __init__(
        self,
        passage: ReferencePassage,
        *,
        checked: bool,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SpecimenListCard")
        self.setProperty("checked", False)
        self.setProperty("current", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        heading = QWidget()
        heading_layout = QVBoxLayout(heading)
        heading_layout.setContentsMargins(0, 0, 0, 0)
        heading_layout.setSpacing(2)

        title = QLabel(source_group_title(passage.source_title))
        title.setObjectName("SpecimenListTitle")
        title.setWordWrap(True)
        heading_layout.addWidget(title)

        author = QLabel(_blank(passage.source_author))
        author.setObjectName("SpecimenListAuthor")
        author.setWordWrap(True)
        heading_layout.addWidget(author)

        header.addWidget(heading, 1)

        self._select_button = QPushButton()
        self._select_button.setObjectName("SpecimenSelectBadge")
        self._select_button.setCheckable(True)
        self._select_button.setAutoDefault(False)
        self._select_button.clicked.connect(
            lambda checked: self.selection_toggled.emit(checked)
        )
        header.addWidget(
            self._select_button,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )
        layout.addLayout(header)

        chips = QWidget()
        chips_layout = QHBoxLayout(chips)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)
        for text in (
            usage_kind_label(passage.usage_kind),
            _kind_label(passage.kind),
            *[f"#{tag}" for tag in split_tags(passage.tags)[:3]],
        ):
            chip = QLabel(text)
            chip.setObjectName("SpecimenSoftChip")
            chips_layout.addWidget(chip)
        chips_layout.addStretch(1)
        layout.addWidget(chips)

        excerpt = QLabel(compact_text(passage.content, limit=180))
        excerpt.setObjectName("SpecimenListExcerpt")
        excerpt.setWordWrap(True)
        layout.addWidget(excerpt)

        note = passage.personal_note.strip()
        self._note_label = QLabel(compact_text(note, limit=110) if note else "")
        self._note_label.setObjectName("SpecimenListNote")
        self._note_label.setWordWrap(True)
        self._note_label.setVisible(bool(note))
        layout.addWidget(self._note_label)

        self.set_checked(checked)

        for widget in (
            self,
            heading,
            title,
            author,
            chips,
            excerpt,
            self._note_label,
        ):
            self._bind_click_target(widget)
        for index in range(chips_layout.count()):
            chip = chips_layout.itemAt(index).widget()
            if isinstance(chip, QWidget):
                self._bind_click_target(chip)

    def set_checked(self, checked: bool) -> None:
        checked = bool(checked)
        with QSignalBlocker(self._select_button):
            self._select_button.setChecked(checked)
        self._select_button.setText(
            TR("specimen.selected_badge") if checked else TR("specimen.select_action")
        )
        if self.property("checked") != checked:
            self.setProperty("checked", checked)
            _refresh_dynamic_style(self)
        _refresh_dynamic_style(self._select_button)

    def set_current(self, current: bool) -> None:
        if self.property("current") == current:
            return
        self.setProperty("current", current)
        _refresh_dynamic_style(self)


class SpecimenPickerDialog(QDialog):
    """Multi-select picker for style specimens."""

    def __init__(
        self,
        repo: ReferenceRepository,
        *,
        preselect_query: str = "",
        recommended_text: str = "",
        preselected_ids: Optional[list[str]] = None,
        settings: Optional[Settings] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("specimen.picker_title"))
        self.resize(1180, 700)
        self._repo = repo
        self._settings = settings
        self._selected: List[ReferencePassage] = []
        self._recommended_text = recommended_text.strip()
        self._checked_ids_cache: set[str] = set(preselected_ids or [])
        self._preview_collapsed = False
        self._grouped_passages: list[PassageGroup] = []

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("rlp.search_placeholder"))
        if preselect_query:
            self._search.setText(preselect_query)

        self._kind_filter = QComboBox()
        self._kind_filter.setObjectName("SpecimenKindFilter")
        self._kind_filter.addItem(TR("reflib.kind_filter_all"), None)
        for kind in REFERENCE_KINDS:
            self._kind_filter.addItem(_kind_label(kind), kind)

        self._usage_filter = QComboBox()
        self._usage_filter.setObjectName("SpecimenUsageKindFilter")
        self._usage_filter.addItem(TR("reflib.usage_kind_filter_all"), None)
        for uk in USAGE_KINDS:
            self._usage_filter.addItem(usage_kind_label(uk), uk)

        self._group_mode_combo = QComboBox()
        self._group_mode_combo.setObjectName("SpecimenGroupModeCombo")
        for mode, label in group_mode_options():
            self._group_mode_combo.addItem(label, mode)
        self._set_group_mode(self._initial_group_mode())

        self._save_default_btn = QPushButton(TR("reflib.save_default_view"))
        self._save_default_btn.setObjectName("GhostButton")
        self._save_default_btn.setEnabled(self._settings is not None)
        self._save_default_btn.clicked.connect(self._save_group_mode_as_default)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self._search, 1)
        controls.addWidget(self._kind_filter)
        controls.addWidget(self._usage_filter)
        controls.addWidget(QLabel(TR("reflib.group_mode_label")))
        controls.addWidget(self._group_mode_combo)
        controls.addWidget(self._save_default_btn)

        self._group_label = QLabel(TR("specimen.shelf_title"))
        self._group_label.setObjectName("SpecimenSectionTitle")
        self._group_list = QListWidget()
        self._group_list.setObjectName("SpecimenShelfList")
        self._group_list.setSpacing(6)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._group_label)
        left_layout.addWidget(self._group_list, 1)

        self._list = QListWidget()
        self._list.setObjectName("SpecimenCardList")
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setUniformItemSizes(False)
        self._list.setSpacing(6)

        center_header = QLabel(TR("specimen.collection_title"))
        center_header.setObjectName("SpecimenSectionTitle")

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_layout.addWidget(center_header)
        center_layout.addWidget(self._list, 1)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

        self._preview_card = QFrame()
        self._preview_card.setObjectName("SpecimenPreviewCard")
        preview_layout = QVBoxLayout(self._preview_card)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(8)

        header_row = QHBoxLayout()
        self._preview_header = QLabel(TR("specimen.inspector_title"))
        self._preview_header.setObjectName("SpecimenSectionTitle")
        header_row.addWidget(self._preview_header, 1)
        self._preview_toggle_btn = QPushButton(TR("specimen.collapse_btn"))
        self._preview_toggle_btn.setObjectName("GhostButton")
        self._preview_toggle_btn.clicked.connect(self._toggle_preview_collapsed)
        header_row.addWidget(self._preview_toggle_btn)
        self._preview_close_btn = QPushButton(TR("specimen.close_btn"))
        self._preview_close_btn.setObjectName("GhostButton")
        self._preview_close_btn.clicked.connect(self._close_preview)
        header_row.addWidget(self._preview_close_btn)
        preview_layout.addLayout(header_row)

        self._preview_title = QLabel("")
        self._preview_title.setObjectName("SpecimenPreviewTitle")
        self._preview_title.setWordWrap(True)
        self._preview_source = QLabel("")
        self._preview_source.setObjectName("SpecimenPreviewMeta")
        self._preview_source.setWordWrap(True)
        self._preview_meta = QLabel("")
        self._preview_meta.setObjectName("SpecimenPreviewMeta")
        self._preview_meta.setWordWrap(True)
        self._preview_tags = QLabel("")
        self._preview_tags.setObjectName("SpecimenPreviewMeta")
        self._preview_tags.setWordWrap(True)
        self._preview_note = QLabel("")
        self._preview_note.setObjectName("SpecimenPreviewNote")
        self._preview_note.setWordWrap(True)
        self._preview_body = QTextEdit()
        self._preview_body.setObjectName("SpecimenPreviewBody")
        self._preview_body.setReadOnly(True)
        self._preview_body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._preview_body.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._preview_body.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._preview_content = QWidget()
        preview_content_layout = QVBoxLayout(self._preview_content)
        preview_content_layout.setContentsMargins(0, 0, 0, 0)
        preview_content_layout.setSpacing(6)
        preview_content_layout.addWidget(self._preview_title)
        preview_content_layout.addWidget(self._preview_source)
        preview_content_layout.addWidget(self._preview_meta)
        preview_content_layout.addWidget(self._preview_tags)
        preview_content_layout.addWidget(self._preview_note)
        preview_content_layout.addWidget(self._preview_body, 1)
        preview_layout.addWidget(self._preview_content, 1)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(left)
        self._splitter.addWidget(center)
        self._splitter.addWidget(self._preview_card)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 3)
        self._splitter.setStretchFactor(2, 2)
        self._splitter.setSizes([220, 520, 360])

        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self._splitter, 1)
        layout.addWidget(self._button_box)

        self._search.textChanged.connect(lambda _: self._refresh())
        self._kind_filter.currentIndexChanged.connect(lambda _: self._refresh())
        self._usage_filter.currentIndexChanged.connect(lambda _: self._refresh())
        self._group_mode_combo.currentIndexChanged.connect(lambda _: self._refresh())
        self._group_list.currentItemChanged.connect(self._on_group_changed)
        self._list.currentItemChanged.connect(self._on_current_item_changed)
        self._list.itemChanged.connect(self._on_item_changed)

        self._refresh()

    @property
    def selected_passages(self) -> List[ReferencePassage]:
        return list(self._selected)

    def _initial_group_mode(self) -> str:
        if self._settings is not None:
            try:
                return normalize_group_mode(
                    self._settings.specimen_picker_default_group_mode(),
                    default=DEFAULT_SPECIMEN_PICKER_GROUP_MODE,
                )
            except Exception:  # noqa: BLE001
                pass
        return DEFAULT_SPECIMEN_PICKER_GROUP_MODE

    def _set_group_mode(self, mode: str) -> None:
        index = self._group_mode_combo.findData(mode)
        self._group_mode_combo.setCurrentIndex(max(0, index))

    def _current_group_mode(self) -> str:
        return normalize_group_mode(
            self._group_mode_combo.currentData(),
            default=DEFAULT_SPECIMEN_PICKER_GROUP_MODE,
        )

    def _save_group_mode_as_default(self) -> None:
        if self._settings is None:
            return
        self._settings.save_specimen_picker_default_group_mode(
            self._current_group_mode()
        )

    def _refresh(self) -> None:
        query = self._search.text().strip()
        usage_kind: Optional[str] = self._usage_filter.currentData()
        kind: Optional[str] = self._kind_filter.currentData()

        if query:
            passages = self._repo.search(query, kind=kind, usage_kind=usage_kind)
        elif self._recommended_text:
            candidates = self._repo.list_recent(kind=kind, usage_kind=usage_kind, limit=500)
            passages = rank_similar_passages(
                candidates,
                self._recommended_text,
                limit=200,
            ) or self._repo.list_recent(kind=kind, usage_kind=usage_kind)
        else:
            passages = self._repo.list_recent(kind=kind, usage_kind=usage_kind)

        self._sync_visible_checked_ids()
        current_id = self._current_item_id()
        selected_group_key = self._current_group_key()
        grouped = group_reference_passages(passages, self._current_group_mode())
        self._grouped_passages = grouped
        target_group_key = self._resolve_group_key(
            grouped,
            preferred_group_key=selected_group_key,
            preferred_passage_id=current_id,
        )
        self._rebuild_group_list(grouped, selected_key=target_group_key)
        self._populate_passage_list(
            grouped,
            group_key=target_group_key,
            preferred_id=current_id,
        )

    def _resolve_group_key(
        self,
        groups: list[PassageGroup],
        *,
        preferred_group_key: Optional[str],
        preferred_passage_id: Optional[str],
    ) -> Optional[str]:
        if not groups:
            return None
        if preferred_group_key == ALL_GROUP_KEY:
            return ALL_GROUP_KEY
        keys = {group.key for group in groups}
        if preferred_group_key and preferred_group_key in keys:
            return preferred_group_key
        matched = find_group_key_for_passage(groups, preferred_passage_id)
        if matched:
            return matched
        return ALL_GROUP_KEY

    def _rebuild_group_list(
        self,
        groups: list[PassageGroup],
        *,
        selected_key: Optional[str],
    ) -> None:
        self._group_list.blockSignals(True)
        try:
            self._group_list.clear()
            if groups:
                self._append_group_item(
                    ALL_GROUP_KEY,
                    TR("reflib.all_groups"),
                    count=sum(group.count for group in groups),
                )
            for group in groups:
                self._append_group_item(
                    group.key,
                    group.title,
                    subtitle=group.subtitle,
                    count=group.count,
                )
            if selected_key is not None:
                self._select_group_key(selected_key)
            elif self._group_list.count() > 0:
                self._group_list.setCurrentRow(0)
        finally:
            self._group_list.blockSignals(False)

    def _append_group_item(
        self,
        key: str,
        title: str,
        *,
        subtitle: str = "",
        count: int = 0,
    ) -> None:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setData(
            _ITEM_AUX_TEXT_ROLE,
            " · ".join(
                part
                for part in (title, subtitle, TR("reflib.group_count").format(count=count))
                if part
            ),
        )
        item.setToolTip(item.data(_ITEM_AUX_TEXT_ROLE))
        self._group_list.addItem(item)
        card = _GroupShelfCard(
            title,
            subtitle=subtitle,
            count=count,
            parent=self._group_list,
        )
        card.clicked.connect(lambda key=key: self._select_group_key(key))
        self._group_list.setItemWidget(item, card)
        _apply_conservative_size_hint(item, card, min_height=_SHELF_ITEM_MIN_HEIGHT)

    def _select_group_key(self, group_key: str) -> None:
        for row in range(self._group_list.count()):
            item = self._group_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == group_key:
                self._group_list.setCurrentRow(row)
                return

    def _current_group_key(self) -> Optional[str]:
        item = self._group_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    def _visible_passages_for_group(
        self,
        groups: list[PassageGroup],
        group_key: Optional[str],
    ) -> list[ReferencePassage]:
        active_groups = groups
        if group_key and group_key != ALL_GROUP_KEY:
            active_groups = [group for group in groups if group.key == group_key]
        ordered: list[ReferencePassage] = []
        seen_ids: set[str] = set()
        for group in active_groups:
            for section in group.sections:
                for passage in section.passages:
                    if passage.id in seen_ids:
                        continue
                    seen_ids.add(passage.id)
                    ordered.append(passage)
        return ordered

    def _populate_passage_list(
        self,
        groups: list[PassageGroup],
        *,
        group_key: Optional[str],
        preferred_id: Optional[str],
    ) -> None:
        passages = self._visible_passages_for_group(groups, group_key)
        self._list.blockSignals(True)
        try:
            self._list.clear()
            target_row: Optional[int] = None
            for passage in passages:
                item = QListWidgetItem()
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                item.setData(Qt.ItemDataRole.UserRole, passage.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, passage)
                item.setData(Qt.ItemDataRole.DisplayRole, "")
                item.setData(
                    _ITEM_AUX_TEXT_ROLE,
                    " · ".join(
                        part
                        for part in (
                            source_group_title(passage.source_title),
                            _blank(passage.source_author),
                            compact_text(passage.content, limit=180),
                            passage.personal_note.strip(),
                        )
                        if part
                    ),
                )
                state = (
                    Qt.CheckState.Checked
                    if passage.id in self._checked_ids_cache
                    else Qt.CheckState.Unchecked
                )
                item.setCheckState(state)
                item.setToolTip(item.data(_ITEM_AUX_TEXT_ROLE))
                self._list.addItem(item)
                card = _SpecimenListCard(
                    passage,
                    checked=state == Qt.CheckState.Checked,
                    parent=self._list,
                )
                card.clicked.connect(lambda item=item: self._select_passage_item(item))
                card.selection_toggled.connect(
                    lambda checked, item=item: self._set_item_checked_state(item, checked)
                )
                self._list.setItemWidget(item, card)
                _apply_conservative_size_hint(
                    item,
                    card,
                    min_height=_SPECIMEN_CARD_MIN_HEIGHT,
                )
                if preferred_id and passage.id == preferred_id:
                    target_row = self._list.row(item)
            if target_row is not None:
                self._list.setCurrentRow(target_row)
            elif self._list.count() > 0:
                self._list.setCurrentRow(0)
            else:
                self._clear_preview()
        finally:
            self._list.blockSignals(False)
        current = self._list.currentItem()
        if current is not None:
            self._update_preview_content(current)
        else:
            self._clear_preview()
        self._refresh_group_card_states()
        self._refresh_passage_card_states()

    def _on_group_changed(self, _current, _previous) -> None:
        self._refresh_group_card_states()
        self._populate_passage_list(
            self._grouped_passages,
            group_key=self._current_group_key(),
            preferred_id=self._current_item_id(),
        )

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        passage_id = item.data(Qt.ItemDataRole.UserRole)
        if not passage_id or passage_id == NON_PASSAGE_ITEM:
            return
        checked = item.checkState() == Qt.CheckState.Checked
        if checked:
            self._checked_ids_cache.add(passage_id)
        else:
            self._checked_ids_cache.discard(passage_id)
        widget = self._list.itemWidget(item)
        if isinstance(widget, _SpecimenListCard):
            widget.set_checked(checked)

    def _sync_visible_checked_ids(self) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            passage_id = item.data(Qt.ItemDataRole.UserRole)
            if not passage_id or passage_id == NON_PASSAGE_ITEM:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                self._checked_ids_cache.add(passage_id)
            else:
                self._checked_ids_cache.discard(passage_id)

    def _on_current_item_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous,
    ) -> None:
        if current is None:
            self._clear_preview()
            self._refresh_passage_card_states()
            return
        self._update_preview_content(current)
        self._refresh_passage_card_states()

    def _show_preview_for_item(self, item: Optional[QListWidgetItem]) -> None:
        if item is None:
            self._clear_preview()
            return
        self._list.setCurrentItem(item)
        self._update_preview_content(item)

    def _update_preview_content(self, item: QListWidgetItem) -> None:
        passage = item.data(Qt.ItemDataRole.UserRole + 1)
        if not isinstance(passage, ReferencePassage):
            self._clear_preview()
            return
        self._preview_card.show()
        self._preview_title.setText(source_group_title(passage.source_title))
        self._preview_source.setText(
            " · ".join(
                [
                    f"{TR('specimen.source_label')}: {source_group_title(passage.source_title)}",
                    f"{TR('rlp.author_label')}: {_blank(passage.source_author)}",
                ]
            )
        )
        self._preview_meta.setText(
            " · ".join(
                [
                    f"{TR('specimen.type_label')}: {_kind_label(passage.kind)}",
                    f"{TR('reflib.usage_kind_label')}: {usage_kind_label(passage.usage_kind)}",
                ]
            )
        )
        tags_text = ", ".join(split_tags(passage.tags))
        self._preview_tags.setText(f"{TR('rlp.tags_label')}: {_blank(tags_text)}")
        note = passage.personal_note.strip()
        self._preview_note.setText(
            f"{TR('reflib.personal_note_label')}: {note}" if note else ""
        )
        self._preview_note.setVisible(bool(note))
        self._preview_body.setPlainText(passage.content or "")
        self._preview_body.moveCursor(
            self._preview_body.textCursor().MoveOperation.Start
        )

    def _current_item_id(self) -> Optional[str]:
        current = self._list.currentItem()
        if current is None:
            return None
        value = current.data(Qt.ItemDataRole.UserRole)
        if isinstance(value, str) and value != NON_PASSAGE_ITEM:
            return value
        return None

    def _clear_preview(self) -> None:
        self._preview_title.setText("")
        self._preview_source.setText("")
        self._preview_meta.setText("")
        self._preview_tags.setText("")
        self._preview_note.setText("")
        self._preview_note.setVisible(False)
        self._preview_body.clear()
        if self._list.count() == 0:
            self._preview_card.hide()
        else:
            self._preview_card.setVisible(not self._preview_collapsed)

    def _toggle_preview_collapsed(self) -> None:
        self._preview_collapsed = not self._preview_collapsed
        self._preview_content.setVisible(not self._preview_collapsed)
        self._preview_toggle_btn.setText(
            TR("specimen.expand_btn")
            if self._preview_collapsed
            else TR("specimen.collapse_btn")
        )

    def _close_preview(self) -> None:
        self._preview_card.hide()

    def _select_passage_item(self, item: QListWidgetItem) -> None:
        if item.data(Qt.ItemDataRole.UserRole) == NON_PASSAGE_ITEM:
            return
        self._list.setCurrentItem(item)

    def _set_item_checked_state(
        self,
        item: Optional[QListWidgetItem],
        checked: bool,
    ) -> None:
        if item is None or item.data(Qt.ItemDataRole.UserRole) == NON_PASSAGE_ITEM:
            return
        target = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        if item.checkState() == target:
            widget = self._list.itemWidget(item)
            if isinstance(widget, _SpecimenListCard):
                widget.set_checked(checked)
            return
        item.setCheckState(target)

    def _refresh_group_card_states(self) -> None:
        current_key = self._current_group_key()
        for row in range(self._group_list.count()):
            item = self._group_list.item(row)
            widget = self._group_list.itemWidget(item)
            if isinstance(widget, _GroupShelfCard):
                widget.set_current(item.data(Qt.ItemDataRole.UserRole) == current_key)

    def _refresh_passage_card_states(self) -> None:
        current_id = self._current_item_id()
        for row in range(self._list.count()):
            item = self._list.item(row)
            widget = self._list.itemWidget(item)
            if isinstance(widget, _SpecimenListCard):
                widget.set_current(item.data(Qt.ItemDataRole.UserRole) == current_id)
                widget.set_checked(item.checkState() == Qt.CheckState.Checked)

    def _checked_ids(self) -> set:
        self._sync_visible_checked_ids()
        return set(self._checked_ids_cache)

    def _collect_checked_passages(self) -> List[ReferencePassage]:
        self._sync_visible_checked_ids()
        out: List[ReferencePassage] = []
        if not self._checked_ids_cache:
            return out
        passages = self._repo.list_recent(limit=1000)
        by_id = {passage.id: passage for passage in passages}
        for passage_id in self._checked_ids_cache:
            passage = by_id.get(passage_id)
            if passage is not None:
                out.append(passage)
        return out

    def _on_accept(self) -> None:
        self._selected = self._collect_checked_passages()
        self.accept()
