"""Embeddable reference-library panel (M4A)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
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
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
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
    ALL_GROUP_KEY,
    DEFAULT_REFERENCE_LIBRARY_GROUP_MODE,
    PassageGroup,
    compact_text,
    find_group_key_for_passage,
    group_mode_label,
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

_CATEGORY_TAGS: tuple[tuple[str, str], ...] = (
    ("environment", "环境描写"),
    ("character", "人物描写"),
    ("psychology", "心理描写"),
    ("philosophy", "哲思句子"),
    ("reflection", "思考句子"),
    ("imagery", "意象表达"),
    ("technique", "叙事技巧"),
    ("style", "风格参考"),
    ("other", "其他"),
)

_CATEGORY_LABEL_KEYS = {
    "environment": "reflib.category_environment",
    "character": "reflib.category_character",
    "psychology": "reflib.category_psychology",
    "philosophy": "reflib.category_philosophy",
    "reflection": "reflib.category_reflection",
    "imagery": "reflib.category_imagery",
    "technique": "reflib.category_technique",
    "style": "reflib.category_style",
    "other": "reflib.category_other",
}

_STAT_TABS: tuple[tuple[str, str], ...] = (
    ("total", "reflib.stat_view_total"),
    ("usage", "reflib.stat_view_usage"),
    ("type", "reflib.stat_view_type"),
    ("tags", "reflib.stat_view_tags"),
    ("duplicates", "reflib.stat_view_duplicates"),
    ("recent", "reflib.stat_view_recent"),
)

_ITEM_AUX_TEXT_ROLE = Qt.ItemDataRole.UserRole + 8
_SHELF_ITEM_MIN_HEIGHT = 96
_REFERENCE_CARD_MIN_HEIGHT = 248


@dataclass(frozen=True)
class _ScopeStats:
    total: int
    total_chars: int
    recent_7d: int
    source_count: int
    author_count: int
    duplicate_risk_count: int
    duplicate_clusters: tuple[tuple[str, tuple[ReferencePassage, ...]], ...]
    by_kind: dict[str, int]
    by_usage_kind: dict[str, int]
    top_tags: tuple[tuple[str, int], ...]
    recent_items: tuple[ReferencePassage, ...]


def _kind_label(kind: str) -> str:
    return TR(_KIND_LABEL_KEYS.get(normalise_kind(kind), "reflib.kind_excerpt"))


def _usage_kind_label(usage_kind: str) -> str:
    return usage_kind_label(usage_kind)


def _blank(value: str) -> str:
    return value.strip() if value and value.strip() else TR("context.no_value")


def _wrap_book_title(value: str) -> str:
    title = (value or "").strip()
    if not title:
        return TR("specimen.group_unlabeled_source")
    if title == TR("specimen.group_unlabeled_source"):
        return title
    return f"《{title}》"


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
    width_hint: Optional[int] = None,
) -> None:
    widget.ensurePolished()
    height_candidates = [
        min_height,
        widget.minimumSizeHint().height(),
        widget.sizeHint().height(),
    ]
    if width_hint and width_hint > 0:
        layout = widget.layout()
        if layout is not None and layout.hasHeightForWidth():
            height_candidates.append(layout.totalHeightForWidth(width_hint))
        if widget.hasHeightForWidth():
            height_candidates.append(widget.heightForWidth(width_hint))
    item.setSizeHint(QSize(0, max(height for height in height_candidates if height > 0)))


def _clear_layout(layout) -> None:
    while layout.count():
        child = layout.takeAt(0)
        widget = child.widget()
        sub_layout = child.layout()
        if widget is not None:
            widget.deleteLater()
        elif sub_layout is not None:
            _clear_layout(sub_layout)


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


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


class _ReferenceShelfCard(_ClickableCard):
    def __init__(
        self,
        title: str,
        *,
        subtitle: str = "",
        count: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ReferenceShelfCard")
        self.setProperty("current", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("ReferenceShelfTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        meta_parts = []
        if subtitle:
            meta_parts.append(subtitle)
        if count:
            meta_parts.append(TR("reflib.group_count").format(count=count))
        meta_label = QLabel(" · ".join(meta_parts))
        meta_label.setObjectName("ReferenceShelfMeta")
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


class _ReferenceListCard(_ClickableCard):
    delete_requested = Signal(str)

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
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        source = QLabel(source_group_title(passage.source_title))
        source.setObjectName("ReferenceCardSource")
        source.setWordWrap(True)
        header.addWidget(source, 1)

        self._delete_button = QPushButton(TR("rlp.delete_btn"))
        self._delete_button.setObjectName("DangerButton")
        self._delete_button.setAutoDefault(False)
        self._delete_button.setToolTip(TR("rlp.delete_btn"))
        self._delete_button.clicked.connect(
            lambda _checked=False, passage_id=passage.id: self.delete_requested.emit(passage_id)
        )
        header.addWidget(
            self._delete_button,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )
        layout.addLayout(header)

        author = QLabel(_blank(passage.source_author))
        author.setObjectName("ReferenceCardAuthor")
        author.setWordWrap(True)
        layout.addWidget(author)

        quote = QLabel(compact_text(passage.content, limit=240))
        quote.setObjectName("ReferenceQuoteText")
        quote.setWordWrap(True)
        layout.addWidget(quote)

        note = passage.personal_note.strip()
        note_label = QLabel(note if len(note) <= 120 else compact_text(note, limit=120))
        note_label.setObjectName("ReferenceCardNote")
        note_label.setWordWrap(True)
        note_label.setVisible(bool(note))
        layout.addWidget(note_label)

        chips = QWidget()
        chips_layout = QHBoxLayout(chips)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)
        chip_texts = [
            _usage_kind_label(passage.usage_kind),
            _kind_label(passage.kind),
            *[f"#{tag_group_title(tag)}" for tag in split_tags(passage.tags)[:4]],
        ]
        if len(chip_texts) == 2:
            chip_texts.append(f"#{TR('specimen.group_unlabeled_tag')}")
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
                    f"{TR('reflib.kind_label')}: {_kind_label(passage.kind)}",
                    f"{TR('reflib.list_recent_edit')}: {recent_label}",
                    risk_text,
                ]
            )
        )
        meta.setObjectName("ReferenceCardMeta")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        for widget in (self, source, author, quote, note_label, chips, meta):
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
        self._active_group_key: Optional[str] = ALL_GROUP_KEY
        self._grouped_passages: list[PassageGroup] = []
        self._filtered_passages: list[ReferencePassage] = []
        self._visible_passages: list[ReferencePassage] = []
        self._duplicate_ids_cache: set[str] = set()
        self._stat_labels: dict[str, QLabel] = {}
        self._stat_body_layouts = {}
        self._category_chip_buttons: dict[str, QPushButton] = {}

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

        self._group_label = QLabel()
        self._group_label.setObjectName("ReferenceSectionTitle")
        self._group_list = QListWidget()
        self._group_list.setObjectName("ReferenceShelfList")
        self._group_list.setSpacing(6)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._group_label)
        left_layout.addWidget(self._group_list, 1)

        self._book_header = QFrame()
        self._book_header.setObjectName("ReferenceBookHeader")
        header_layout = QVBoxLayout(self._book_header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(6)
        self._book_header_title = QLabel("")
        self._book_header_title.setObjectName("ReferenceBookTitle")
        self._book_header_title.setWordWrap(True)
        self._book_header_author = QLabel("")
        self._book_header_author.setObjectName("ReferenceBookAuthor")
        self._book_header_author.setWordWrap(True)
        self._book_header_meta = QLabel("")
        self._book_header_meta.setObjectName("ReferenceBookMeta")
        self._book_header_meta.setWordWrap(True)
        self._book_header_summary = QLabel("")
        self._book_header_summary.setObjectName("ReferenceBookSummary")
        self._book_header_summary.setWordWrap(True)
        self._book_header_tags = QLabel("")
        self._book_header_tags.setObjectName("ReferenceBookSummary")
        self._book_header_tags.setWordWrap(True)
        self._book_header_chip_row = QWidget()
        self._book_header_chip_layout = QHBoxLayout(self._book_header_chip_row)
        self._book_header_chip_layout.setContentsMargins(0, 0, 0, 0)
        self._book_header_chip_layout.setSpacing(6)
        header_layout.addWidget(self._book_header_title)
        header_layout.addWidget(self._book_header_author)
        header_layout.addWidget(self._book_header_meta)
        header_layout.addWidget(self._book_header_summary)
        header_layout.addWidget(self._book_header_tags)
        header_layout.addWidget(self._book_header_chip_row)

        self._list = QListWidget()
        self._list.setObjectName("ReferenceLibraryList")
        self._list.setSpacing(8)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        center_layout.addWidget(self._book_header)
        center_layout.addWidget(self._list, 1)

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
        self._personal_note_edit.setMaximumHeight(90)
        self._content_edit = QPlainTextEdit()
        self._content_edit.setObjectName("ReferenceQuoteEditor")
        self._save_btn = QPushButton(TR("rlp.save_btn"))
        self._save_btn.setObjectName("PrimaryButton")
        self._new_btn = QPushButton(TR("rlp.new_btn"))
        self._new_btn.setObjectName("GhostButton")
        self._delete_btn = QPushButton(TR("rlp.delete_btn"))
        self._delete_btn.setObjectName("DangerButton")

        category_label = QLabel(TR("reflib.category_label"))
        category_label.setObjectName("MetaLabel")
        category_grid = QGridLayout()
        category_grid.setContentsMargins(0, 0, 0, 0)
        category_grid.setHorizontalSpacing(8)
        category_grid.setVerticalSpacing(8)
        for index, (key, _stored_tag) in enumerate(_CATEGORY_TAGS):
            chip = QPushButton(TR(_CATEGORY_LABEL_KEYS[key]))
            chip.setObjectName("RefCategoryChip")
            chip.setCheckable(True)
            chip.setAutoDefault(False)
            chip.clicked.connect(
                lambda checked, category_key=key: self._on_category_chip_clicked(
                    category_key,
                    checked,
                )
            )
            category_grid.addWidget(chip, index // 3, index % 3)
            self._category_chip_buttons[key] = chip

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)
        editor_layout.addWidget(QLabel(TR("rlp.source_title_label")))
        editor_layout.addWidget(self._title_edit)
        editor_layout.addWidget(QLabel(TR("rlp.author_label")))
        editor_layout.addWidget(self._author_edit)
        editor_layout.addWidget(QLabel(TR("reflib.kind_label")))
        editor_layout.addWidget(self._kind_combo)
        editor_layout.addWidget(QLabel(TR("reflib.usage_kind_label")))
        editor_layout.addWidget(self._usage_kind_combo)
        editor_layout.addWidget(QLabel(TR("rlp.tags_label")))
        editor_layout.addWidget(self._tags_edit)
        editor_layout.addWidget(category_label)
        editor_layout.addLayout(category_grid)
        editor_layout.addWidget(QLabel(TR("reflib.personal_note_label")))
        editor_layout.addWidget(self._personal_note_edit)
        editor_layout.addWidget(QLabel(TR("rlp.content_label")))
        editor_layout.addWidget(self._content_edit, 1)
        button_row = QHBoxLayout()
        button_row.addWidget(self._new_btn)
        button_row.addWidget(self._delete_btn)
        button_row.addStretch(1)
        button_row.addWidget(self._save_btn)
        editor_layout.addLayout(button_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([260, 520, 430])

        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        controls_row.addWidget(self._search, 1)
        controls_row.addWidget(QLabel(TR("reflib.kind_filter_label")))
        controls_row.addWidget(self._kind_filter_combo)
        controls_row.addWidget(QLabel(TR("reflib.usage_kind_label")))
        controls_row.addWidget(self._usage_kind_filter_combo)
        controls_row.addWidget(QLabel(TR("reflib.group_mode_label")))
        controls_row.addWidget(self._group_mode_combo)
        controls_row.addWidget(self._save_default_view_btn)

        stats_box = QFrame()
        stats_box.setObjectName("RefStatsBox")
        stats_layout = QVBoxLayout(stats_box)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(10)

        stats_tabs_row = QHBoxLayout()
        stats_tabs_row.setSpacing(8)
        self._stats_scope_label = QLabel("")
        self._stats_scope_label.setObjectName("RefStatScope")
        self._stats_tab_group = QButtonGroup(self)
        self._stats_tab_group.setExclusive(True)
        self._stats_stack = QStackedWidget()
        self._stats_pages: dict[str, QWidget] = {}
        for index, (key, label_key) in enumerate(_STAT_TABS):
            button = QPushButton(TR(label_key))
            button.setObjectName("RefStatTab")
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.clicked.connect(
                lambda checked, current_index=index: self._on_stat_tab_selected(
                    current_index,
                    checked,
                )
            )
            self._stats_tab_group.addButton(button)
            stats_tabs_row.addWidget(button)
            page = self._create_stat_page(key)
            self._stats_stack.addWidget(page)
            self._stats_pages[key] = page
            if index == 0:
                button.setChecked(True)
        stats_tabs_row.addStretch(1)
        stats_tabs_row.addWidget(self._stats_scope_label)
        stats_layout.addLayout(stats_tabs_row)
        stats_layout.addWidget(self._stats_stack)

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.addWidget(stats_box)
        root.addLayout(controls_row)
        root.addWidget(splitter, 1)

        self._search.textChanged.connect(self._on_search_changed)
        self._kind_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._usage_kind_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._group_mode_combo.currentIndexChanged.connect(self._on_group_mode_changed)
        self._group_list.currentItemChanged.connect(self._on_group_changed)
        self._list.currentItemChanged.connect(self._on_current_changed)
        self._new_btn.clicked.connect(self._on_new)
        self._delete_btn.clicked.connect(self._on_delete)
        self._save_btn.clicked.connect(self._on_save)
        self._tags_edit.textChanged.connect(self._sync_category_chips_from_tags)

        if initial_usage_kind_filter is not None:
            self.set_usage_kind_filter(initial_usage_kind_filter)

        self.refresh()

    def _create_stat_page(self, key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        summary = QLabel(TR("reflib.stats_empty"))
        summary.setObjectName("RefStatValue")
        summary.setWordWrap(True)
        layout.addWidget(summary)
        self._stat_labels[key] = summary

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        layout.addWidget(body, 1)
        self._stat_body_layouts[key] = body_layout
        return page

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

    def _is_bookshelf_mode(self) -> bool:
        return self._current_group_mode() in {"source", "source_usage"}

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
            items = self._repo.search(query, limit=1000, kind=kind, usage_kind=usage_kind)
        else:
            items = self._repo.list_recent(limit=1000, kind=kind, usage_kind=usage_kind)
        self._filtered_passages = items
        self._grouped_passages = group_reference_passages(items, self._current_group_mode())
        self._duplicate_ids_cache = self._duplicate_ids(items)
        self._refresh_group_label()

        target_group_key = self._resolve_group_key(
            self._grouped_passages,
            preferred_group_key=self._active_group_key,
            preferred_passage_id=select_id or self._current_id,
        )
        self._active_group_key = target_group_key
        self._rebuild_group_list(self._grouped_passages, selected_key=target_group_key)
        self._refresh_scope(preferred_id=select_id or self._current_id)

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
        available_keys = {group.key for group in groups}
        if preferred_group_key and preferred_group_key in available_keys:
            return preferred_group_key
        matched = find_group_key_for_passage(groups, preferred_passage_id)
        if matched:
            return matched
        return ALL_GROUP_KEY

    def _refresh_group_label(self) -> None:
        self._group_label.setText(
            TR("reflib.shelf_title_books")
            if self._is_bookshelf_mode()
            else TR("reflib.shelf_title_groups")
        )

    def _rebuild_group_list(
        self,
        groups: list[PassageGroup],
        *,
        selected_key: Optional[str],
    ) -> None:
        self._group_list.blockSignals(True)
        try:
            self._group_list.clear()
            if not groups:
                return
            self._append_group_item(
                ALL_GROUP_KEY,
                TR("reflib.all_groups"),
                subtitle=group_mode_label(self._current_group_mode()),
                count=sum(group.count for group in groups),
            )
            for group in groups:
                self._append_group_item(
                    group.key,
                    self._display_group_title(group),
                    subtitle=self._group_subtitle(group),
                    count=group.count,
                )
            if selected_key is not None:
                self._select_group_key(selected_key)
            elif self._group_list.count() > 0:
                self._group_list.setCurrentRow(0)
        finally:
            self._group_list.blockSignals(False)
        self._refresh_group_card_states()

    def _display_group_title(self, group: PassageGroup) -> str:
        if self._is_bookshelf_mode():
            return _wrap_book_title(group.title)
        return group.title

    def _group_subtitle(self, group: PassageGroup) -> str:
        subtitle = group.subtitle.strip()
        if subtitle:
            return subtitle
        if len(group.sections) > 1:
            section_titles = [section.title for section in group.sections if section.title]
            if section_titles:
                return " · ".join(section_titles[:3])
        return ""

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
        item.setData(Qt.ItemDataRole.DisplayRole, "")
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
        card = _ReferenceShelfCard(
            title,
            subtitle=subtitle,
            count=count,
            parent=self._group_list,
        )
        card.clicked.connect(lambda group_key=key: self._select_group_key(group_key))
        self._group_list.setItemWidget(item, card)
        _apply_conservative_size_hint(item, card, min_height=_SHELF_ITEM_MIN_HEIGHT)

    def _select_group_key(self, group_key: str) -> None:
        for row in range(self._group_list.count()):
            item = self._group_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == group_key:
                self._group_list.setCurrentRow(row)
                return

    def _current_group_key(self) -> Optional[str]:
        current = self._group_list.currentItem()
        if current is None:
            return None
        value = current.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    def _group_for_key(self, key: Optional[str]) -> Optional[PassageGroup]:
        if not key or key == ALL_GROUP_KEY:
            return None
        for group in self._grouped_passages:
            if group.key == key:
                return group
        return None

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

    def _refresh_scope(self, *, preferred_id: Optional[str]) -> None:
        self._visible_passages = self._visible_passages_for_group(
            self._grouped_passages,
            self._active_group_key,
        )
        self._populate_passage_list(self._visible_passages, preferred_id=preferred_id)
        self._refresh_book_header()
        self._refresh_stats()

    def _populate_passage_list(
        self,
        passages: list[ReferencePassage],
        *,
        preferred_id: Optional[str],
    ) -> None:
        self._list.blockSignals(True)
        try:
            self._list.clear()
            target_row: Optional[int] = None
            for passage in passages:
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
                            compact_text(passage.content, limit=200),
                            passage.personal_note.strip(),
                        )
                        if part
                    ),
                )
                item.setToolTip(item.data(_ITEM_AUX_TEXT_ROLE))
                self._list.addItem(item)
                card = _ReferenceListCard(
                    passage,
                    duplicate_risk=passage.id in self._duplicate_ids_cache,
                    parent=self._list,
                )
                card.clicked.connect(lambda selected_item=item: self._select_item(selected_item))
                card.delete_requested.connect(self._request_delete_passage)
                self._list.setItemWidget(item, card)
                _apply_conservative_size_hint(
                    item,
                    card,
                    min_height=_REFERENCE_CARD_MIN_HEIGHT,
                    width_hint=max(self._list.viewport().width(), 440),
                )
                if preferred_id and passage.id == preferred_id:
                    target_row = self._list.row(item)
            if target_row is not None:
                self._list.setCurrentRow(target_row)
            elif self._list.count() > 0:
                self._list.setCurrentRow(0)
            else:
                self._load_passage(None)
        finally:
            self._list.blockSignals(False)
        current = self._list.currentItem()
        if current is not None:
            passage = current.data(Qt.ItemDataRole.UserRole + 1)
            self._load_passage(passage if isinstance(passage, ReferencePassage) else None)
        elif not passages:
            self._load_passage(None)
        self._refresh_card_states()

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

    def _build_scope_stats(self, items: list[ReferencePassage]) -> _ScopeStats:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=7)
        by_kind = Counter(normalise_kind(passage.kind) for passage in items)
        by_usage_kind = Counter(
            normalise_usage_kind(passage.usage_kind) for passage in items
        )
        tags = Counter()
        total_chars = 0
        recent_7d = 0
        source_titles: set[str] = set()
        author_names: set[str] = set()
        duplicate_map: dict[str, list[ReferencePassage]] = {}

        for passage in items:
            total_chars += len(passage.content or "")
            source_titles.add(source_group_title(passage.source_title))
            author = (passage.source_author or "").strip()
            if author:
                author_names.add(author)
            for tag in split_tags(passage.tags):
                tags[tag] += 1
            created_at = _parse_timestamp(passage.created_at)
            if created_at is not None and created_at >= cutoff:
                recent_7d += 1
            normalized = normalize_reference_content(passage.content)
            if normalized:
                duplicate_map.setdefault(normalized, []).append(passage)

        duplicate_clusters = tuple(
            sorted(
                (
                    (content, tuple(passages))
                    for content, passages in duplicate_map.items()
                    if len(passages) > 1
                ),
                key=lambda item: (-len(item[1]), item[1][0].source_title.casefold()),
            )
        )
        duplicate_risk_count = sum(len(cluster) for _, cluster in duplicate_clusters)
        recent_items = tuple(
            sorted(
                items,
                key=lambda passage: (passage.updated_at or passage.created_at or ""),
                reverse=True,
            )[:6]
        )
        return _ScopeStats(
            total=len(items),
            total_chars=total_chars,
            recent_7d=recent_7d,
            source_count=len(source_titles),
            author_count=len(author_names),
            duplicate_risk_count=duplicate_risk_count,
            duplicate_clusters=duplicate_clusters,
            by_kind=dict(by_kind),
            by_usage_kind=dict(by_usage_kind),
            top_tags=tuple(tags.most_common(8)),
            recent_items=recent_items,
        )

    def _refresh_book_header(self) -> None:
        passages = self._visible_passages
        if not passages:
            self._book_header_title.setText(TR("reflib.book_empty_title"))
            self._book_header_author.setText(TR("reflib.book_empty_desc"))
            self._book_header_meta.setText("")
            self._book_header_summary.setText("")
            self._book_header_tags.setText("")
            _clear_layout(self._book_header_chip_layout)
            self._book_header_chip_layout.addStretch(1)
            return

        stats = self._build_scope_stats(passages)
        active_group = self._group_for_key(self._active_group_key)
        if active_group is not None:
            title = self._display_group_title(active_group)
            author = (
                active_group.subtitle.strip()
                or TR("reflib.book_author_unknown")
                if self._is_bookshelf_mode()
                else active_group.subtitle.strip()
            )
        else:
            title = TR("reflib.book_all_title")
            author = TR("reflib.book_all_desc").format(
                mode=group_mode_label(self._current_group_mode()),
                groups=len(self._grouped_passages),
            )

        usage_summary = _compact_counter(stats.by_usage_kind, _usage_kind_label)
        tag_summary = " · ".join(
            f"#{tag}×{count}" for tag, count in stats.top_tags[:5]
        )

        self._book_header_title.setText(title)
        self._book_header_author.setText(author)
        self._book_header_author.setVisible(bool(author))
        self._book_header_meta.setText(
            TR("reflib.book_header_meta").format(
                count=stats.total,
                chars=stats.total_chars,
                sources=stats.source_count,
            )
        )
        self._book_header_summary.setText(
            TR("reflib.book_header_usage").format(
                summary=usage_summary or TR("reflib.stats_empty")
            )
        )
        self._book_header_tags.setText(
            TR("reflib.book_header_tags").format(
                summary=tag_summary or TR("reflib.stats_empty")
            )
        )
        _clear_layout(self._book_header_chip_layout)
        for text in self._header_chip_texts(stats):
            chip = QLabel(text)
            chip.setObjectName("SpecimenSoftChip")
            self._book_header_chip_layout.addWidget(chip)
        self._book_header_chip_layout.addStretch(1)

    def _header_chip_texts(self, stats: _ScopeStats) -> list[str]:
        chips = [
            _usage_kind_label(key)
            for key, _count in sorted(
                stats.by_usage_kind.items(),
                key=lambda item: (-item[1], _usage_kind_label(item[0])),
            )[:3]
        ]
        chips.extend(f"#{tag}" for tag, _count in stats.top_tags[:3])
        return chips

    def _refresh_stats(self) -> None:
        scope_items = self._visible_passages
        stats = self._build_scope_stats(scope_items)
        self._stats_scope_label.setText(self._stats_scope_text(stats))

        self._stat_labels["total"].setText(
            TR("reflib.stats_total_value").format(
                count=stats.total,
                chars=stats.total_chars,
                recent=stats.recent_7d,
            )
        )
        self._rebuild_overview_page(stats)

        usage = _compact_counter(stats.by_usage_kind, _usage_kind_label)
        self._stat_labels["usage"].setText(usage or TR("reflib.stats_empty"))
        self._rebuild_counter_page(
            "usage",
            stats.by_usage_kind,
            _usage_kind_label,
            empty_key="reflib.stats_usage_empty",
        )

        kinds = _compact_counter(stats.by_kind, _kind_label)
        self._stat_labels["type"].setText(kinds or TR("reflib.stats_empty"))
        self._rebuild_counter_page(
            "type",
            stats.by_kind,
            _kind_label,
            empty_key="reflib.stats_type_empty",
        )

        tags_text = " · ".join(f"{tag}×{count}" for tag, count in stats.top_tags)
        self._stat_labels["tags"].setText(tags_text or TR("reflib.stats_empty"))
        self._rebuild_tags_page(stats)

        self._stat_labels["duplicates"].setText(
            TR("reflib.stats_duplicates_value").format(
                count=stats.duplicate_risk_count
            )
        )
        self._rebuild_duplicates_page(stats)

        recent_text = TR("reflib.stats_recent_value").format(count=len(stats.recent_items))
        self._stat_labels["recent"].setText(recent_text if scope_items else TR("reflib.stats_empty"))
        self._rebuild_recent_page(stats)

    def _stats_scope_text(self, stats: _ScopeStats) -> str:
        active_group = self._group_for_key(self._active_group_key)
        if active_group is not None:
            return TR("reflib.stats_scope_group").format(
                title=self._display_group_title(active_group)
            )
        return TR("reflib.stats_scope_all").format(
            count=stats.total,
            mode=group_mode_label(self._current_group_mode()),
        )

    def _rebuild_overview_page(self, stats: _ScopeStats) -> None:
        body = self._stat_body_layouts["total"]
        _clear_layout(body)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.addWidget(
            self._metric_card(
                TR("reflib.overview_metric_books"),
                str(stats.source_count),
            ),
            0,
            0,
        )
        grid.addWidget(
            self._metric_card(
                TR("reflib.overview_metric_authors"),
                str(stats.author_count),
            ),
            0,
            1,
        )
        grid.addWidget(
            self._metric_card(
                TR("reflib.overview_metric_duplicates"),
                str(stats.duplicate_risk_count),
            ),
            1,
            0,
        )
        grid.addWidget(
            self._metric_card(
                TR("reflib.overview_metric_recent"),
                str(stats.recent_7d),
            ),
            1,
            1,
        )
        body.addLayout(grid)
        body.addWidget(
            self._section_caption(
                TR("reflib.overview_usage_title")
            )
        )
        self._append_progress_rows(
            body,
            stats.by_usage_kind,
            _usage_kind_label,
            empty_key="reflib.stats_usage_empty",
        )
        body.addStretch(1)

    def _rebuild_counter_page(
        self,
        key: str,
        values: dict[str, int],
        label_fn,
        *,
        empty_key: str,
    ) -> None:
        body = self._stat_body_layouts[key]
        _clear_layout(body)
        self._append_progress_rows(body, values, label_fn, empty_key=empty_key)
        body.addStretch(1)

    def _append_progress_rows(
        self,
        layout,
        values: dict[str, int],
        label_fn,
        *,
        empty_key: str,
    ) -> None:
        if not values:
            layout.addWidget(self._empty_stat_label(TR(empty_key)))
            return
        total = max(1, sum(values.values()))
        ranked = sorted(values.items(), key=lambda item: (-item[1], label_fn(item[0])))
        for key, count in ranked:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            label = QLabel(label_fn(key))
            label.setObjectName("RefBarLabel")
            label.setMinimumWidth(110)
            bar = QProgressBar()
            bar.setObjectName("RefStatBar")
            bar.setRange(0, total)
            bar.setValue(count)
            bar.setTextVisible(False)
            value = QLabel(TR("reflib.counter_value").format(count=count))
            value.setObjectName("RefBarValue")
            row_layout.addWidget(label)
            row_layout.addWidget(bar, 1)
            row_layout.addWidget(value)
            layout.addWidget(row)

    def _rebuild_tags_page(self, stats: _ScopeStats) -> None:
        body = self._stat_body_layouts["tags"]
        _clear_layout(body)
        if not stats.top_tags:
            body.addWidget(self._empty_stat_label(TR("reflib.stats_tags_empty")))
            body.addStretch(1)
            return
        cloud = QGridLayout()
        cloud.setContentsMargins(0, 0, 0, 0)
        cloud.setHorizontalSpacing(8)
        cloud.setVerticalSpacing(8)
        for index, (tag, count) in enumerate(stats.top_tags):
            chip = QLabel(f"#{tag} × {count}")
            chip.setObjectName("RefTagCloudChip")
            cloud.addWidget(chip, index // 3, index % 3)
        body.addLayout(cloud)
        body.addStretch(1)

    def _rebuild_duplicates_page(self, stats: _ScopeStats) -> None:
        body = self._stat_body_layouts["duplicates"]
        _clear_layout(body)
        if not stats.duplicate_clusters:
            body.addWidget(self._empty_stat_label(TR("reflib.stats_duplicates_empty")))
            body.addStretch(1)
            return
        body.addWidget(
            self._metric_card(
                TR("reflib.overview_metric_duplicate_clusters"),
                str(len(stats.duplicate_clusters)),
            )
        )
        for _normalized, passages in stats.duplicate_clusters[:4]:
            card = QFrame()
            card.setObjectName("RefStatMetricCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)
            title = QLabel(
                TR("reflib.stats_duplicate_cluster_title").format(
                    count=len(passages),
                    source=source_group_title(passages[0].source_title),
                )
            )
            title.setObjectName("RefStatMetricLabel")
            title.setWordWrap(True)
            quote = QLabel(compact_text(passages[0].content, limit=180))
            quote.setObjectName("ReferenceQuoteText")
            quote.setWordWrap(True)
            meta = QLabel(
                " · ".join(
                    passage.display_label()
                    for passage in passages[:3]
                )
            )
            meta.setObjectName("ReferenceCardMeta")
            meta.setWordWrap(True)
            layout.addWidget(title)
            layout.addWidget(quote)
            layout.addWidget(meta)
            for passage in passages[:4]:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)

                locate_button = QPushButton(passage.display_label())
                locate_button.setObjectName("GhostButton")
                locate_button.setAutoDefault(False)
                locate_button.setToolTip(passage.display_label())
                locate_button.clicked.connect(
                    lambda _checked=False, passage_id=passage.id: self._select_passage_by_id(
                        passage_id
                    )
                )
                row_layout.addWidget(locate_button, 1)

                delete_button = QPushButton(TR("rlp.delete_btn"))
                delete_button.setObjectName("DangerButton")
                delete_button.setAutoDefault(False)
                delete_button.clicked.connect(
                    lambda _checked=False, passage_id=passage.id: self._request_delete_passage(
                        passage_id
                    )
                )
                row_layout.addWidget(delete_button)
                layout.addWidget(row)
            body.addWidget(card)
        body.addStretch(1)

    def _rebuild_recent_page(self, stats: _ScopeStats) -> None:
        body = self._stat_body_layouts["recent"]
        _clear_layout(body)
        if not stats.recent_items:
            body.addWidget(self._empty_stat_label(TR("reflib.stats_recent_empty")))
            body.addStretch(1)
            return
        for passage in stats.recent_items:
            card = QFrame()
            card.setObjectName("RefStatMetricCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)
            title = QLabel(source_group_title(passage.source_title))
            title.setObjectName("ReferenceCardTitle")
            meta = QLabel(
                TR("reflib.stats_recent_item_meta").format(
                    date=(passage.updated_at or passage.created_at or "")[:10]
                    or TR("context.no_value"),
                    usage=_usage_kind_label(passage.usage_kind),
                    kind=_kind_label(passage.kind),
                )
            )
            meta.setObjectName("ReferenceCardMeta")
            quote = QLabel(compact_text(passage.content, limit=160))
            quote.setObjectName("ReferenceQuoteText")
            quote.setWordWrap(True)
            layout.addWidget(title)
            layout.addWidget(meta)
            layout.addWidget(quote)
            body.addWidget(card)
        body.addStretch(1)

    def _metric_card(self, label_text: str, value_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("RefStatMetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        value = QLabel(value_text)
        value.setObjectName("RefStatMetricValue")
        label = QLabel(label_text)
        label.setObjectName("RefStatMetricLabel")
        label.setWordWrap(True)
        layout.addWidget(value)
        layout.addWidget(label)
        return card

    def _section_caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("RefStatTitle")
        label.setWordWrap(True)
        return label

    def _empty_stat_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("RefStatValue")
        label.setWordWrap(True)
        return label

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
        self._sync_category_chips_from_tags(self._tags_edit.text())

    def _on_search_changed(self, _text: str) -> None:
        self.refresh(select_id=self._current_id)

    def _on_filter_changed(self, _index: int) -> None:
        self.refresh(select_id=self._current_id)

    def _on_group_mode_changed(self, _index: int) -> None:
        self._active_group_key = ALL_GROUP_KEY
        self.refresh(select_id=self._current_id)

    def _on_group_changed(self, current, _previous) -> None:
        if current is None:
            self._active_group_key = None
            self._visible_passages = []
            self._list.clear()
            self._load_passage(None)
            self._refresh_group_card_states()
            self._refresh_stats()
            self._refresh_book_header()
            return
        self._active_group_key = current.data(Qt.ItemDataRole.UserRole)
        self._refresh_group_card_states()
        self._refresh_scope(preferred_id=self._current_id)

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            self._load_passage(None)
            self._refresh_card_states()
            return
        ref_id = current.data(Qt.ItemDataRole.UserRole)
        self._load_passage(self._repo.get(ref_id))
        self._refresh_card_states()

    def _select_item(self, item: QListWidgetItem) -> None:
        self._list.setCurrentItem(item)

    def _select_passage_by_id(self, passage_id: str) -> Optional[QListWidgetItem]:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == passage_id:
                self._list.setCurrentItem(item)
                self._list.scrollToItem(item)
                return item
        return None

    def _refresh_group_card_states(self) -> None:
        current_key = self._current_group_key()
        for row in range(self._group_list.count()):
            item = self._group_list.item(row)
            widget = self._group_list.itemWidget(item)
            if isinstance(widget, _ReferenceShelfCard):
                widget.set_current(item.data(Qt.ItemDataRole.UserRole) == current_key)

    def _refresh_card_states(self) -> None:
        current_id = self._current_id
        for row in range(self._list.count()):
            item = self._list.item(row)
            widget = self._list.itemWidget(item)
            if isinstance(widget, _ReferenceListCard):
                widget.set_current(item.data(Qt.ItemDataRole.UserRole) == current_id)

    def _tag_map(self) -> dict[str, str]:
        return {key: stored_tag for key, stored_tag in _CATEGORY_TAGS}

    def _tag_values(self) -> set[str]:
        return {stored_tag for _key, stored_tag in _CATEGORY_TAGS}

    def _on_category_chip_clicked(self, category_key: str, checked: bool) -> None:
        tags = split_tags(self._tags_edit.text())
        stored_tag = self._tag_map()[category_key]
        tag_set = set(tags)
        if checked and stored_tag not in tag_set:
            tags.append(stored_tag)
        if not checked:
            tags = [tag for tag in tags if tag != stored_tag]
        self._tags_edit.setText(", ".join(tags))

    def _sync_category_chips_from_tags(self, _text: str) -> None:
        current_tags = set(split_tags(self._tags_edit.text()))
        for key, stored_tag in _CATEGORY_TAGS:
            chip = self._category_chip_buttons[key]
            checked = stored_tag in current_tags
            if chip.isChecked() == checked:
                continue
            chip.blockSignals(True)
            chip.setChecked(checked)
            chip.blockSignals(False)
            _refresh_dynamic_style(chip)

    def _prefill_from_active_group(self) -> tuple[str, str]:
        group = self._group_for_key(self._active_group_key)
        if group is None or not self._is_bookshelf_mode():
            return "", ""
        title = group.title
        if title == TR("specimen.group_unlabeled_source"):
            title = ""
        return title, group.subtitle

    def _on_new(self) -> None:
        self._current_id = None
        default_title, default_author = self._prefill_from_active_group()
        self._title_edit.setText(default_title)
        self._author_edit.setText(default_author)
        self._tags_edit.clear()
        self._content_edit.clear()
        self._personal_note_edit.clear()
        idx = self._kind_combo.findData(REFERENCE_KIND_EXCERPT)
        self._kind_combo.setCurrentIndex(max(0, idx))
        uidx = self._usage_kind_combo.findData(USAGE_KIND_STYLE)
        self._usage_kind_combo.setCurrentIndex(max(0, uidx))
        self._delete_btn.setEnabled(False)
        self._sync_category_chips_from_tags("")
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
        self._request_delete_passage(self._current_id)

    def _request_delete_passage(self, passage_id: Optional[str]) -> None:
        target_id = (passage_id or "").strip()
        if not target_id:
            return
        self._select_passage_by_id(target_id)
        confirm = QMessageBox.question(
            self,
            TR("rlp.confirm_delete_title"),
            TR("rlp.confirm_delete_msg"),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._repo.delete(target_id)
        if self._current_id == target_id:
            self._current_id = None
        self.refresh()

    def _on_stat_tab_selected(self, index: int, checked: bool) -> None:
        if checked:
            self._stats_stack.setCurrentIndex(index)


def _compact_counter(values: dict[str, int], label_fn) -> str:
    if not values:
        return ""
    ranked = sorted(values.items(), key=lambda item: (-item[1], label_fn(item[0])))
    return " · ".join(f"{label_fn(key)}×{count}" for key, count in ranked[:4])
