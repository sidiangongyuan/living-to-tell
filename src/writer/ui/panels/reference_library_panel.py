"""Embeddable reference-library panel (M4A).

Minimal CRUD UI for reference passages: search box, list on the left,
detail editor on the right, and New / Save / Delete buttons. Kept thin
so it can be dropped into a dialog or future side panel.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from writer.domain.models.reference_passage import ReferencePassage
from writer.storage.repositories.reference_repository import ReferenceRepository


class ReferenceLibraryPanel(QWidget):
    def __init__(
        self, repo: ReferenceRepository, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._current_id: Optional[str] = None

        # left side: search + list + buttons
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search references…")
        self._list = QListWidget()
        self._new_btn = QPushButton("New")
        self._delete_btn = QPushButton("Delete")

        left_buttons = QHBoxLayout()
        left_buttons.addWidget(self._new_btn)
        left_buttons.addWidget(self._delete_btn)
        left_buttons.addStretch(1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._search)
        left_layout.addWidget(self._list, 1)
        left_layout.addLayout(left_buttons)

        # right side: form
        self._title_edit = QLineEdit()
        self._author_edit = QLineEdit()
        self._tags_edit = QLineEdit()
        self._content_edit = QPlainTextEdit()
        self._save_btn = QPushButton("Save")

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Source title *"))
        right_layout.addWidget(self._title_edit)
        right_layout.addWidget(QLabel("Author"))
        right_layout.addWidget(self._author_edit)
        right_layout.addWidget(QLabel("Tags (free text)"))
        right_layout.addWidget(self._tags_edit)
        right_layout.addWidget(QLabel("Passage content *"))
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
        self._list.currentItemChanged.connect(self._on_current_changed)
        self._new_btn.clicked.connect(self._on_new)
        self._delete_btn.clicked.connect(self._on_delete)
        self._save_btn.clicked.connect(self._on_save)

        self.refresh()

    # ---------------- behaviour ----------------
    def refresh(self, *, select_id: Optional[str] = None) -> None:
        query = self._search.text().strip()
        items = (
            self._repo.search(query) if query else self._repo.list_recent()
        )
        self._list.blockSignals(True)
        try:
            self._list.clear()
            for passage in items:
                item = QListWidgetItem(passage.display_label())
                item.setData(Qt.ItemDataRole.UserRole, passage.id)
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
        self._delete_btn.setEnabled(False)
        self._title_edit.setFocus()

    def _on_save(self) -> None:
        title = self._title_edit.text().strip()
        content = self._content_edit.toPlainText()
        if not title:
            QMessageBox.warning(self, "Missing title", "Source title is required.")
            return
        if not content.strip():
            QMessageBox.warning(self, "Missing content", "Passage content is required.")
            return
        author = self._author_edit.text()
        tags = self._tags_edit.text()
        try:
            if self._current_id is None:
                passage = self._repo.create(
                    source_title=title,
                    source_author=author,
                    content=content,
                    tags=tags,
                )
            else:
                passage = self._repo.update(
                    self._current_id,
                    source_title=title,
                    source_author=author,
                    content=content,
                    tags=tags,
                )
        except ValueError as err:
            QMessageBox.warning(self, "Invalid reference", str(err))
            return
        if passage is None:
            QMessageBox.warning(self, "Not found", "Reference no longer exists.")
            self.refresh()
            return
        self.refresh(select_id=passage.id)

    def _on_delete(self) -> None:
        if self._current_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete reference",
            "Delete this reference passage?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._repo.delete(self._current_id)
        self._current_id = None
        self.refresh()
