"""Embeddable reference-library panel (M4A)."""
from __future__ import annotations

from collections import Counter
from typing import Optional

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
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
    USAGE_KIND_STYLE,
    ReferencePassage,
    normalise_kind,
    normalise_usage_kind,
)
from writer.storage.repositories.reference_repository import (
    ReferenceRepository,
    normalize_reference_content,
)
from writer.ui.i18n import TR
from writer.ui.reference_grouping import (
    DEFAULT_REFERENCE_LIBRARY_GROUP_MODE,
    NON_PASSAGE_ITEM,
    PassageGroup,
    compact_text,
    group_mode_options,
    group_reference_passages,
    normalize_group_mode,
    source_group_title,
    split_tags,
    tag_group_title,
    usage_kind_label,
)


_KIND_LABEL_KEYS = {
    REFERENCE_KIND_CHARACTER: "reflib.kind_character",
    REFERENCE_KIND_LOCATION: "reflib.kind_location",
    REFERENCE_KIND_SETTING: "reflib.kind_setting",
    REFERENCE_KIND_EXCERPT: "reflib.kind_excerpt",
}

_ITEM_AUX_TEXT_ROLE = Qt.ItemDataRole.UserRole + 8
_GROUP_HEADER_MIN_HEIGHT = 78
_SECTION_HEADER_MIN_HEIGHT = 42
_REFERENCE_CARD_MIN_HEIGHT = 214


def _kind_label(kind: str) -> str:
    return TR(_KIND_LABEL_KEYS.get(normalise_kind(kind), "reflib.kind_excerpt"))


def _usage_kind_label(usage_kind: str) -> str:
    return usage_kind_label(usage_kind)


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


class _ReferenceGroupHeader(QWidget):
    def __init__(
        self,
        title: str,
        *,
        subtitle: str = "",
        count: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ReferenceGroupHeader")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 6)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("ReferenceGroupTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        parts = []
        if subtitle:
            parts.append(subtitle)
        if count:
            parts.append(TR("reflib.group_count").format(count=count))
        meta = QLabel(" · ".join(parts))
        meta.setObjectName("ReferenceGroupMeta")
        meta.setWordWrap(True)
        meta.setVisible(bool(parts))
        layout.addWidget(meta)


class _ReferenceSectionHeader(QWidget):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReferenceSectionHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 10, 4)
        layout.setSpacing(0)
        label = QLabel(title)
        label.setObjectName("ReferenceSectionTitle")
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)


class _ReferenceListCard(_ClickableCard):
    def __init__(
        self,
        passage: ReferencePassage,
        *,
        duplicate_risk: bool,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ReferenceListCard")
        self.setProperty("current", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel(source_group_title(passage.source_title))
        title.setObjectName("ReferenceCardTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        author = QLabel(_blank(passage.source_author))
        author.setObjectName("ReferenceCardAuthor")
        author.setWordWrap(True)
        layout.addWidget(author)

        excerpt = QLabel(compact_text(passage.content, limit=170))
        excerpt.setObjectName("ReferenceCardExcerpt")
        excerpt.setWordWrap(True)
        layout.addWidget(excerpt)

        chips = QWidget()
        chips_layout = QHBoxLayout(chips)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)
        tag_chips = [
            f"#{tag_group_title(tag)}" for tag in split_tags(passage.tags)[:3]
        ]
        if not tag_chips:
            tag_chips = [f"#{TR('specimen.group_unlabeled_tag')}"]
        chip_texts = [
            _usage_kind_label(passage.usage_kind),
            _kind_label(passage.kind),
            *tag_chips,
        ]
        for text in chip_texts:
            chip = QLabel(text)
            chip.setObjectName("SpecimenSoftChip")
            chips_layout.addWidget(chip)
        chips_layout.addStretch(1)
        layout.addWidget(chips)

        recent = (passage.updated_at or passage.created_at or "").strip()
        recent_label = recent[:10] if len(recent) >= 10 else TR("context.no_value")
        risk_text = (
            TR("reflib.list_duplicate_risk")
            if duplicate_risk
            else TR("reflib.list_duplicate_safe")
        )
        meta = QLabel(
            " · ".join(
                [
                    f"{TR('reflib.usage_kind_label')}: {_usage_kind_label(passage.usage_kind)}",
                    f"{TR('reflib.list_recent_edit')}: {recent_label}",
                    risk_text,
                ]
            )
        )
        meta.setObjectName("ReferenceCardMeta")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        for widget in (self, title, author, excerpt, chips, meta):
            self._bind_click_target(widget)
        for index in range(chips_layout.count()):
            chip = chips_layout.itemAt(index).widget()
            if isinstance(chip, QWidget):
                self._bind_click_target(chip)

    def set_current(self, current: bool) -> None:
        if self.property("current") == current:
            return
        self.setProperty("current", current)
        _refresh_dynamic_style(self)


class ReferenceLibraryPanel(QWidget):
    def __init__(
        self,
        repo: ReferenceRepository,
        parent: Optional[QWidget] = None,
        *,
        initial_usage_kind_filter: Optional[str] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._settings = settings
        self._current_id: Optional[str] = None
        self._stat_labels: dict[str, QLabel] = {}

        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("rlp.search_placeholder"))

        self._kind_filter_combo = QComboBox()
        self._kind_filter_combo.setObjectName("RefKindFilter")
        self._kind_filter_combo.addItem(TR("reflib.kind_filter_all"), None)
        for kind in REFERENCE_KINDS:
            self._kind_filter_combo.addItem(_kind_label(kind), kind)

        self._usage_kind_filter_combo = QComboBox()
        self._usage_kind_filter_combo.setObjectName("RefUsageKindFilter")
        self._usage_kind_filter_combo.addItem(TR("reflib.usage_kind_filter_all"), None)
        for uk in USAGE_KINDS:
            self._usage_kind_filter_combo.addItem(_usage_kind_label(uk), uk)

        self._group_mode_combo = QComboBox()
        self._group_mode_combo.setObjectName("RefGroupModeCombo")
        for mode, label in group_mode_options():
            self._group_mode_combo.addItem(label, mode)
        self._set_group_mode(self._initial_group_mode())

        self._save_default_view_btn = QPushButton(TR("reflib.save_default_view"))
        self._save_default_view_btn.setObjectName("GhostButton")
        self._save_default_view_btn.setEnabled(self._settings is not None)
        self._save_default_view_btn.clicked.connect(self._save_group_mode_as_default)

        self._list = QListWidget()
        self._list.setObjectName("ReferenceLibraryList")
        self._list.setSpacing(6)
        self._new_btn = QPushButton(TR("rlp.new_btn"))
        self._delete_btn = QPushButton(TR("rlp.delete_btn"))

        left_buttons = QHBoxLayout()
        left_buttons.addWidget(self._new_btn)
        left_buttons.addWidget(self._delete_btn)
        left_buttons.addStretch(1)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel(TR("reflib.group_mode_label")))
        controls_row.addWidget(self._group_mode_combo, 1)
        controls_row.addWidget(self._save_default_view_btn)

        kind_filter_row = QHBoxLayout()
        kind_filter_row.addWidget(QLabel(TR("reflib.kind_filter_label")))
        kind_filter_row.addWidget(self._kind_filter_combo, 1)

        usage_filter_row = QHBoxLayout()
        usage_filter_row.addWidget(QLabel(TR("reflib.usage_kind_label")))
        usage_filter_row.addWidget(self._usage_kind_filter_combo, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._search)
        left_layout.addLayout(controls_row)
        left_layout.addLayout(kind_filter_row)
        left_layout.addLayout(usage_filter_row)
        left_layout.addWidget(self._list, 1)
        left_layout.addLayout(left_buttons)

        self._title_edit = QLineEdit()
        self._author_edit = QLineEdit()
        self._tags_edit = QLineEdit()
        self._kind_combo = QComboBox()
        self._kind_combo.setObjectName("RefKindCombo")
        for kind in REFERENCE_KINDS:
            self._kind_combo.addItem(_kind_label(kind), kind)
        self._usage_kind_combo = QComboBox()
        self._usage_kind_combo.setObjectName("RefUsageKindCombo")
        for uk in USAGE_KINDS:
            self._usage_kind_combo.addItem(_usage_kind_label(uk), uk)
        self._personal_note_edit = QPlainTextEdit()
        self._personal_note_edit.setObjectName("RefPersonalNote")
        self._personal_note_edit.setPlaceholderText(TR("reflib.personal_note_label"))
        self._personal_note_edit.setMaximumHeight(80)
        self._content_edit = QPlainTextEdit()
        self._save_btn = QPushButton(TR("rlp.save_btn"))

        stats_box = QFrame()
        stats_box.setObjectName("RefStatsBox")
        stats_layout = QGridLayout(stats_box)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        stats_layout.setHorizontalSpacing(8)
        stats_layout.setVerticalSpacing(8)
        for idx, (key, label_key) in enumerate(
            (
                ("total", "reflib.stats_total"),
                ("usage", "reflib.stats_usage"),
                ("tags", "reflib.stats_tags"),
                ("duplicates", "reflib.stats_duplicates"),
            )
        ):
            card = QFrame()
            card.setObjectName("RefStatCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            title = QLabel(TR(label_key))
            title.setObjectName("RefStatTitle")
            value = QLabel("—")
            value.setObjectName("RefStatValue")
            value.setWordWrap(True)
            card_layout.addWidget(title)
            card_layout.addWidget(value)
            self._stat_labels[key] = value
            stats_layout.addWidget(card, idx // 2, idx % 2)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel(TR("rlp.source_title_label")))
        right_layout.addWidget(self._title_edit)
        right_layout.addWidget(QLabel(TR("rlp.author_label")))
        right_layout.addWidget(self._author_edit)
        right_layout.addWidget(QLabel(TR("reflib.kind_label")))
        right_layout.addWidget(self._kind_combo)
        right_layout.addWidget(QLabel(TR("reflib.usage_kind_label")))
        right_layout.addWidget(self._usage_kind_combo)
        right_layout.addWidget(QLabel(TR("rlp.tags_label")))
        right_layout.addWidget(self._tags_edit)
        right_layout.addWidget(QLabel(TR("reflib.personal_note_label")))
        right_layout.addWidget(self._personal_note_edit)
        right_layout.addWidget(QLabel(TR("rlp.content_label")))
        right_layout.addWidget(self._content_edit, 1)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_row.addWidget(self._save_btn)
        right_layout.addLayout(save_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 540])

        root = QVBoxLayout(self)
        root.addWidget(stats_box)
        root.addWidget(splitter)

        self._search.textChanged.connect(self._on_search_changed)
        self._kind_filter_combo.currentIndexChanged.connect(self._on_search_changed)
        self._usage_kind_filter_combo.currentIndexChanged.connect(self._on_search_changed)
        self._group_mode_combo.currentIndexChanged.connect(self._on_search_changed)
        self._list.currentItemChanged.connect(self._on_current_changed)
        self._new_btn.clicked.connect(self._on_new)
        self._delete_btn.clicked.connect(self._on_delete)
        self._save_btn.clicked.connect(self._on_save)

        if initial_usage_kind_filter is not None:
            self.set_usage_kind_filter(initial_usage_kind_filter)

        self.refresh()

    def _initial_group_mode(self) -> str:
        if self._settings is not None:
            try:
                return normalize_group_mode(
                    self._settings.reference_library_default_group_mode(),
                    default=DEFAULT_REFERENCE_LIBRARY_GROUP_MODE,
                )
            except Exception:  # noqa: BLE001
                pass
        return DEFAULT_REFERENCE_LIBRARY_GROUP_MODE

    def _set_group_mode(self, mode: str) -> None:
        idx = self._group_mode_combo.findData(mode)
        self._group_mode_combo.setCurrentIndex(max(0, idx))

    def _current_kind_filter(self) -> Optional[str]:
        return self._kind_filter_combo.currentData()

    def _current_usage_kind_filter(self) -> Optional[str]:
        return self._usage_kind_filter_combo.currentData()

    def _current_group_mode(self) -> str:
        return normalize_group_mode(
            self._group_mode_combo.currentData(),
            default=DEFAULT_REFERENCE_LIBRARY_GROUP_MODE,
        )

    def _save_group_mode_as_default(self) -> None:
        if self._settings is None:
            return
        self._settings.save_reference_library_default_group_mode(
            self._current_group_mode()
        )

    def set_usage_kind_filter(self, usage_kind: Optional[str]) -> None:
        idx = self._usage_kind_filter_combo.findData(usage_kind)
        self._usage_kind_filter_combo.setCurrentIndex(max(0, idx))

    def refresh(self, *, select_id: Optional[str] = None) -> None:
        query = self._search.text().strip()
        kind = self._current_kind_filter()
        usage_kind = self._current_usage_kind_filter()
        if query:
            items = self._repo.search(query, kind=kind, usage_kind=usage_kind)
        else:
            items = self._repo.list_recent(kind=kind, usage_kind=usage_kind)
        groups = group_reference_passages(items, self._current_group_mode())
        duplicate_ids = self._duplicate_ids(items)

        self._list.blockSignals(True)
        try:
            self._list.clear()
            first_selectable_row: Optional[int] = None
            target_row: Optional[int] = None
            show_group_headers = (
                any(group.count > 1 for group in groups)
                or self._current_group_mode() not in {DEFAULT_REFERENCE_LIBRARY_GROUP_MODE}
            )
            for group in groups:
                if show_group_headers:
                    self._append_group_header(group)
                show_section_headers = len(group.sections) > 1 or any(
                    section.title for section in group.sections
                )
                for section in group.sections:
                    if show_section_headers and section.title:
                        self._append_section_header(section.title)
                    for passage in section.passages:
                        item = QListWidgetItem()
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
                                    compact_text(passage.content, limit=170),
                                    passage.personal_note.strip(),
                                )
                                if part
                            ),
                        )
                        item.setToolTip(item.data(_ITEM_AUX_TEXT_ROLE))
                        self._list.addItem(item)
                        card = _ReferenceListCard(
                            passage,
                            duplicate_risk=passage.id in duplicate_ids,
                            parent=self._list,
                        )
                        card.clicked.connect(lambda item=item: self._select_item(item))
                        self._list.setItemWidget(item, card)
                        _apply_conservative_size_hint(
                            item,
                            card,
                            min_height=_REFERENCE_CARD_MIN_HEIGHT,
                        )
                        row = self._list.row(item)
                        if first_selectable_row is None:
                            first_selectable_row = row
                        if select_id is not None and passage.id == select_id:
                            target_row = row
        finally:
            self._list.blockSignals(False)

        if target_row is not None:
            self._list.setCurrentRow(target_row)
        elif first_selectable_row is not None:
            self._list.setCurrentRow(first_selectable_row)
        else:
            self._load_passage(None)
        self._refresh_card_states()
        self._refresh_stats()

    def _append_group_header(self, group: PassageGroup) -> None:
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setData(Qt.ItemDataRole.UserRole, NON_PASSAGE_ITEM)
        item.setData(
            _ITEM_AUX_TEXT_ROLE,
            " · ".join(
                part
                for part in (
                    group.title,
                    group.subtitle,
                    TR("reflib.group_count").format(count=group.count),
                )
                if part
            ),
        )
        item.setToolTip(item.data(_ITEM_AUX_TEXT_ROLE))
        self._list.addItem(item)
        card = _ReferenceGroupHeader(
            group.title,
            subtitle=group.subtitle,
            count=group.count,
            parent=self._list,
        )
        self._list.setItemWidget(item, card)
        _apply_conservative_size_hint(item, card, min_height=_GROUP_HEADER_MIN_HEIGHT)

    def _append_section_header(self, title: str) -> None:
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setData(Qt.ItemDataRole.UserRole, NON_PASSAGE_ITEM)
        item.setData(_ITEM_AUX_TEXT_ROLE, title)
        item.setToolTip(title)
        self._list.addItem(item)
        card = _ReferenceSectionHeader(title, parent=self._list)
        self._list.setItemWidget(item, card)
        _apply_conservative_size_hint(item, card, min_height=_SECTION_HEADER_MIN_HEIGHT)

    def _duplicate_ids(self, items: list[ReferencePassage]) -> set[str]:
        counts = Counter(
            normalized
            for normalized in (
                normalize_reference_content(passage.content)
                for passage in items
            )
            if normalized
        )
        return {
            passage.id
            for passage in items
            if counts.get(normalize_reference_content(passage.content), 0) > 1
        }

    def _refresh_stats(self) -> None:
        stats = self._repo.stats()
        self._stat_labels["total"].setText(
            TR("reflib.stats_total_value").format(
                count=stats.total,
                chars=stats.total_chars,
                recent=stats.recent_7d,
            )
        )
        usage = _compact_counter(stats.by_usage_kind, _usage_kind_label)
        self._stat_labels["usage"].setText(usage or TR("reflib.stats_empty"))
        tags = " · ".join(f"{tag}×{count}" for tag, count in stats.top_tags)
        self._stat_labels["tags"].setText(tags or TR("reflib.stats_empty"))
        self._stat_labels["duplicates"].setText(
            TR("reflib.stats_duplicates_value").format(
                count=stats.duplicate_risk_count
            )
        )

    def _load_passage(self, passage: Optional[ReferencePassage]) -> None:
        self._current_id = passage.id if passage else None
        self._title_edit.setText(passage.source_title if passage else "")
        self._author_edit.setText(passage.source_author if passage else "")
        self._tags_edit.setText(passage.tags if passage else "")
        kind = normalise_kind(passage.kind if passage else REFERENCE_KIND_EXCERPT)
        idx = self._kind_combo.findData(kind)
        if idx < 0:
            idx = self._kind_combo.findData(REFERENCE_KIND_EXCERPT)
        self._kind_combo.setCurrentIndex(max(0, idx))
        usage_kind = normalise_usage_kind(
            passage.usage_kind if passage else USAGE_KIND_STYLE
        )
        uidx = self._usage_kind_combo.findData(usage_kind)
        if uidx < 0:
            uidx = self._usage_kind_combo.findData(USAGE_KIND_STYLE)
        self._usage_kind_combo.setCurrentIndex(max(0, uidx))
        self._personal_note_edit.setPlainText(passage.personal_note if passage else "")
        self._content_edit.setPlainText(passage.content if passage else "")
        self._delete_btn.setEnabled(passage is not None)

    def _on_search_changed(self, _text: str) -> None:
        self.refresh(select_id=self._current_id)

    def _next_selectable_item(self, start_row: int) -> Optional[QListWidgetItem]:
        for row in range(max(0, start_row), self._list.count()):
            item = self._list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) != NON_PASSAGE_ITEM:
                return item
        for row in range(0, max(0, start_row)):
            item = self._list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) != NON_PASSAGE_ITEM:
                return item
        return None

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            self._load_passage(None)
            self._refresh_card_states()
            return
        ref_id = current.data(Qt.ItemDataRole.UserRole)
        if ref_id == NON_PASSAGE_ITEM:
            next_item = self._next_selectable_item(self._list.row(current))
            if next_item is not None:
                self._list.setCurrentItem(next_item)
            else:
                self._load_passage(None)
            return
        self._load_passage(self._repo.get(ref_id))
        self._refresh_card_states()

    def _select_item(self, item: QListWidgetItem) -> None:
        if item.data(Qt.ItemDataRole.UserRole) == NON_PASSAGE_ITEM:
            return
        self._list.setCurrentItem(item)

    def _refresh_card_states(self) -> None:
        current_id = self._current_id
        for row in range(self._list.count()):
            item = self._list.item(row)
            widget = self._list.itemWidget(item)
            if isinstance(widget, _ReferenceListCard):
                widget.set_current(item.data(Qt.ItemDataRole.UserRole) == current_id)

    def _on_new(self) -> None:
        self._current_id = None
        self._title_edit.clear()
        self._author_edit.clear()
        self._tags_edit.clear()
        self._content_edit.clear()
        self._personal_note_edit.clear()
        idx = self._kind_combo.findData(REFERENCE_KIND_EXCERPT)
        self._kind_combo.setCurrentIndex(max(0, idx))
        uidx = self._usage_kind_combo.findData(USAGE_KIND_STYLE)
        self._usage_kind_combo.setCurrentIndex(max(0, uidx))
        self._delete_btn.setEnabled(False)
        self._title_edit.setFocus()

    def _on_save(self) -> None:
        title = self._title_edit.text().strip()
        content = self._content_edit.toPlainText()
        if not title:
            QMessageBox.warning(self, TR("rlp.missing_title"), TR("rlp.missing_title_msg"))
            return
        if not content.strip():
            QMessageBox.warning(self, TR("rlp.missing_content"), TR("rlp.missing_content_msg"))
            return
        author = self._author_edit.text()
        tags = self._tags_edit.text()
        kind = normalise_kind(self._kind_combo.currentData())
        usage_kind = normalise_usage_kind(self._usage_kind_combo.currentData())
        personal_note = self._personal_note_edit.toPlainText()
        try:
            if self._current_id is None:
                passage = self._repo.create(
                    source_title=title,
                    source_author=author,
                    content=content,
                    tags=tags,
                    kind=kind,
                    usage_kind=usage_kind,
                    personal_note=personal_note,
                )
            else:
                passage = self._repo.update(
                    self._current_id,
                    source_title=title,
                    source_author=author,
                    content=content,
                    tags=tags,
                    kind=kind,
                    usage_kind=usage_kind,
                    personal_note=personal_note,
                )
        except ValueError as err:
            QMessageBox.warning(self, TR("rlp.invalid_ref"), str(err))
            return
        if passage is None:
            QMessageBox.warning(self, TR("rlp.not_found"), TR("rlp.not_found_msg"))
            self.refresh()
            return
        self.refresh(select_id=passage.id)

    def _on_delete(self) -> None:
        if self._current_id is None:
            return
        confirm = QMessageBox.question(
            self,
            TR("rlp.confirm_delete_title"),
            TR("rlp.confirm_delete_msg"),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._repo.delete(self._current_id)
        self._current_id = None
        self.refresh()


def _compact_counter(values: dict[str, int], label_fn) -> str:
    if not values:
        return ""
    ranked = sorted(values.items(), key=lambda item: (-item[1], label_fn(item[0])))
    return " · ".join(f"{label_fn(key)}×{count}" for key, count in ranked[:4])
