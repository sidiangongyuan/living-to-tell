"""Embeddable reference-library panel (M4A).

Minimal CRUD UI for reference passages: search box, list on the left,
detail editor on the right, and New / Save / Delete buttons. Kept thin
so it can be dropped into a dialog or future side panel.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.reference_passage import (
    REFERENCE_KIND_CHARACTER,
    REFERENCE_KIND_EXCERPT,
    REFERENCE_KIND_LOCATION,
    REFERENCE_KIND_SETTING,
    REFERENCE_KINDS,
    ReferencePassage,
    normalise_kind,
)
from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.ui.i18n import TR
from writer.ui.tag_colors import get_tag_color


_KIND_LABEL_KEYS = {
    REFERENCE_KIND_CHARACTER: "reflib.kind_character",
    REFERENCE_KIND_LOCATION: "reflib.kind_location",
    REFERENCE_KIND_SETTING: "reflib.kind_setting",
    REFERENCE_KIND_EXCERPT: "reflib.kind_excerpt",
}


def _kind_label(kind: str) -> str:
    return TR(_KIND_LABEL_KEYS.get(normalise_kind(kind), "reflib.kind_excerpt"))


class _RefTagDotDelegate(QStyledItemDelegate):
    """Draws a small colored dot for the first tag of a reference passage."""

    _DOT_SIZE = 8
    _DOT_MARGIN = 6

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        tags_raw: str = index.data(Qt.ItemDataRole.UserRole + 1) or ""
        first_tag = tags_raw.split(",")[0].strip() if tags_raw.strip() else ""
        if not first_tag:
            return
        bg_hex, _ = get_tag_color(first_tag)
        r = option.rect
        cx = r.right() - self._DOT_MARGIN - self._DOT_SIZE // 2
        cy = r.center().y()
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setBrush(QColor(bg_hex))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            cx - self._DOT_SIZE // 2,
            cy - self._DOT_SIZE // 2,
            self._DOT_SIZE,
            self._DOT_SIZE,
        )
        painter.restore()


class ReferenceLibraryPanel(QWidget):
    def __init__(
        self, repo: ReferenceRepository, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._current_id: Optional[str] = None

        # left side: search + kind filter + list + buttons
        self._search = QLineEdit()
        self._search.setPlaceholderText(TR("rlp.search_placeholder"))

        self._kind_filter_combo = QComboBox()
        self._kind_filter_combo.setObjectName("RefKindFilter")
        # Index 0 = "All"; userData=None signals "no kind filter".
        self._kind_filter_combo.addItem(TR("reflib.kind_filter_all"), None)
        for kind in REFERENCE_KINDS:
            self._kind_filter_combo.addItem(_kind_label(kind), kind)

        self._list = QListWidget()
        self._list.setItemDelegate(_RefTagDotDelegate(self._list))
        self._new_btn = QPushButton(TR("rlp.new_btn"))
        self._delete_btn = QPushButton(TR("rlp.delete_btn"))

        left_buttons = QHBoxLayout()
        left_buttons.addWidget(self._new_btn)
        left_buttons.addWidget(self._delete_btn)
        left_buttons.addStretch(1)

        kind_filter_row = QHBoxLayout()
        kind_filter_row.addWidget(QLabel(TR("reflib.kind_filter_label")))
        kind_filter_row.addWidget(self._kind_filter_combo, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._search)
        left_layout.addLayout(kind_filter_row)
        left_layout.addWidget(self._list, 1)
        left_layout.addLayout(left_buttons)

        # right side: form
        self._title_edit = QLineEdit()
        self._author_edit = QLineEdit()
        self._tags_edit = QLineEdit()
        self._kind_combo = QComboBox()
        self._kind_combo.setObjectName("RefKindCombo")
        for kind in REFERENCE_KINDS:
            self._kind_combo.addItem(_kind_label(kind), kind)
        self._content_edit = QPlainTextEdit()
        self._save_btn = QPushButton(TR("rlp.save_btn"))

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel(TR("rlp.source_title_label")))
        right_layout.addWidget(self._title_edit)
        right_layout.addWidget(QLabel(TR("rlp.author_label")))
        right_layout.addWidget(self._author_edit)
        right_layout.addWidget(QLabel(TR("reflib.kind_label")))
        right_layout.addWidget(self._kind_combo)
        right_layout.addWidget(QLabel(TR("rlp.tags_label")))
        right_layout.addWidget(self._tags_edit)
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
        splitter.setSizes([260, 540])

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        # wiring
        self._search.textChanged.connect(self._on_search_changed)
        self._kind_filter_combo.currentIndexChanged.connect(self._on_search_changed)
        self._list.currentItemChanged.connect(self._on_current_changed)
        self._new_btn.clicked.connect(self._on_new)
        self._delete_btn.clicked.connect(self._on_delete)
        self._save_btn.clicked.connect(self._on_save)

        self.refresh()

    # ---------------- behaviour ----------------
    def _current_kind_filter(self) -> Optional[str]:
        return self._kind_filter_combo.currentData()

    def refresh(self, *, select_id: Optional[str] = None) -> None:
        query = self._search.text().strip()
        kind = self._current_kind_filter()
        if query:
            items = self._repo.search(query, kind=kind)
        else:
            items = self._repo.list_recent(kind=kind)
        self._list.blockSignals(True)
        try:
            self._list.clear()
            for passage in items:
                item = QListWidgetItem(passage.display_label())
                item.setData(Qt.ItemDataRole.UserRole, passage.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, passage.tags or "")
                self._list.addItem(item)
        finally:
            self._list.blockSignals(False)

        if select_id is not None:
            for row in range(self._list.count()):
                if self._list.item(row).data(Qt.ItemDataRole.UserRole) == select_id:
                    self._list.setCurrentRow(row)
                    return
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        else:
            self._load_passage(None)

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
        self._content_edit.setPlainText(passage.content if passage else "")
        self._delete_btn.setEnabled(passage is not None)

    # ---------------- slots ----------------
    def _on_search_changed(self, _text: str) -> None:
        self.refresh()

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            self._load_passage(None)
            return
        ref_id = current.data(Qt.ItemDataRole.UserRole)
        self._load_passage(self._repo.get(ref_id))

    def _on_new(self) -> None:
        self._current_id = None
        self._title_edit.clear()
        self._author_edit.clear()
        self._tags_edit.clear()
        self._content_edit.clear()
        idx = self._kind_combo.findData(REFERENCE_KIND_EXCERPT)
        self._kind_combo.setCurrentIndex(max(0, idx))
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
        try:
            if self._current_id is None:
                passage = self._repo.create(
                    source_title=title,
                    source_author=author,
                    content=content,
                    tags=tags,
                    kind=kind,
                )
            else:
                passage = self._repo.update(
                    self._current_id,
                    source_title=title,
                    source_author=author,
                    content=content,
                    tags=tags,
                    kind=kind,
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
