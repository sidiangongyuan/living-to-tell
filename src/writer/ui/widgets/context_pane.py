"""Right-hand context pane (M9A scaffolding).

Per-mode metadata + secondary actions surface. M9A keeps this lightweight
on purpose: the structure is in place but only displays read-only meta and
a couple of buttons. Richer wiring is intentionally deferred to M9B.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from writer.ui.widgets.empty_state import EmptyStateCard


class _MetaRow(QWidget):
    """A label/value row used inside ContextPane."""

    def __init__(self, label: str, value: str = "—", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._label = QLabel(label)
        self._label.setObjectName("ContextLabel")
        self._value = QLabel(value)
        self._value.setObjectName("ContextValue")
        self._value.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(value or "—")


class ContextPane(QWidget):
    """Right-hand info pane.

    Its content is picked from one of three internal layouts based on the
    active mode. Selection inside each list-column updates the rows via
    ``update_*`` calls.
    """

    DEFAULT_WIDTH = 280

    def __init__(
        self,
        *,
        empty_title: str,
        empty_description: str,
        meta_labels: dict,
        action_labels: dict,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("WriterContext")
        self.setMinimumWidth(220)

        self._title = QLabel("")
        self._title.setObjectName("ContextTitle")
        self._title.setWordWrap(True)

        self._stack = QStackedWidget()
        self._empty = EmptyStateCard(empty_title, empty_description)

        # Three content layouts -- shared label widgets per mode.
        # Fragment context
        self._frag_widget = QWidget()
        frag_layout = QVBoxLayout(self._frag_widget)
        frag_layout.setContentsMargins(0, 0, 0, 0)
        frag_layout.setSpacing(12)
        self._frag_words = _MetaRow(meta_labels["words"])
        self._frag_chars = _MetaRow(meta_labels["chars"])
        self._frag_tags = _MetaRow(meta_labels["tags"])
        self._frag_created = _MetaRow(meta_labels["created"])
        self._frag_updated = _MetaRow(meta_labels["updated"])
        self._frag_status = _MetaRow(meta_labels["status"])
        for row in (
            self._frag_words,
            self._frag_chars,
            self._frag_tags,
            self._frag_status,
            self._frag_created,
            self._frag_updated,
        ):
            frag_layout.addWidget(row)
        self._frag_actions_row = QHBoxLayout()
        self._frag_polish_btn = QPushButton(action_labels["polish"])
        self._frag_polish_btn.setObjectName("GhostButton")
        self._frag_include_btn = QPushButton(action_labels["include"])
        self._frag_include_btn.setObjectName("GhostButton")
        self._frag_actions_row.addWidget(self._frag_polish_btn)
        self._frag_actions_row.addWidget(self._frag_include_btn)
        self._frag_actions_row.addStretch(1)
        frag_layout.addLayout(self._frag_actions_row)
        frag_layout.addStretch(1)

        # Work context
        self._work_widget = QWidget()
        work_layout = QVBoxLayout(self._work_widget)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(12)
        self._work_summary = _MetaRow(meta_labels["summary"])
        self._work_status = _MetaRow(meta_labels["status"])
        self._work_words = _MetaRow(meta_labels["words"])
        self._work_target = _MetaRow(meta_labels["target"])
        self._work_updated = _MetaRow(meta_labels["updated"])
        for row in (
            self._work_summary,
            self._work_status,
            self._work_words,
            self._work_target,
            self._work_updated,
        ):
            work_layout.addWidget(row)
        self._work_actions_row = QHBoxLayout()
        self._work_versions_btn = QPushButton(action_labels["versions"])
        self._work_versions_btn.setObjectName("GhostButton")
        self._work_export_btn = QPushButton(action_labels["export_work"])
        self._work_export_btn.setObjectName("GhostButton")
        self._work_actions_row.addWidget(self._work_versions_btn)
        self._work_actions_row.addWidget(self._work_export_btn)
        self._work_actions_row.addStretch(1)
        work_layout.addLayout(self._work_actions_row)
        work_layout.addStretch(1)

        # Collection context
        self._coll_widget = QWidget()
        coll_layout = QVBoxLayout(self._coll_widget)
        coll_layout.setContentsMargins(0, 0, 0, 0)
        coll_layout.setSpacing(12)
        self._coll_count = _MetaRow(meta_labels["work_count"])
        self._coll_words = _MetaRow(meta_labels["words"])
        for row in (self._coll_count, self._coll_words):
            coll_layout.addWidget(row)
        self._coll_actions_row = QHBoxLayout()
        self._coll_export_btn = QPushButton(action_labels["export_collection"])
        self._coll_export_btn.setObjectName("GhostButton")
        self._coll_actions_row.addWidget(self._coll_export_btn)
        self._coll_actions_row.addStretch(1)
        coll_layout.addLayout(self._coll_actions_row)
        coll_layout.addStretch(1)

        self._stack.addWidget(self._empty)        # 0
        self._stack.addWidget(self._frag_widget)   # 1
        self._stack.addWidget(self._work_widget)   # 2
        self._stack.addWidget(self._coll_widget)   # 3

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(self._title)
        layout.addWidget(self._stack, 1)

        self.show_empty()

    # ------------------------------------------------------------------
    # State setters used by MainWindow.
    # ------------------------------------------------------------------
    def show_empty(self, title: str = "", description: str = "") -> None:
        if title:
            self._empty.set_text(title, description)
        self._title.setText("")
        self._stack.setCurrentIndex(0)

    def show_fragment(
        self,
        *,
        title: str,
        words: str,
        chars: str,
        tags: str,
        created: str,
        updated: str,
        status: str,
    ) -> None:
        self._title.setText(title)
        self._frag_words.set_value(words)
        self._frag_chars.set_value(chars)
        self._frag_tags.set_value(tags)
        self._frag_created.set_value(created)
        self._frag_updated.set_value(updated)
        self._frag_status.set_value(status)
        self._stack.setCurrentIndex(1)

    def show_work(
        self,
        *,
        title: str,
        summary: str,
        status: str,
        words: str,
        target: str,
        updated: str,
    ) -> None:
        self._title.setText(title)
        self._work_summary.set_value(summary)
        self._work_status.set_value(status)
        self._work_words.set_value(words)
        self._work_target.set_value(target)
        self._work_updated.set_value(updated)
        self._stack.setCurrentIndex(2)

    def show_collection(
        self,
        *,
        title: str,
        work_count: str,
        words: str,
    ) -> None:
        self._title.setText(title)
        self._coll_count.set_value(work_count)
        self._coll_words.set_value(words)
        self._stack.setCurrentIndex(3)

    # ------------------------------------------------------------------
    # Action button accessors so MainWindow can wire callbacks.
    # ------------------------------------------------------------------
    @property
    def fragment_polish_button(self) -> QPushButton:
        return self._frag_polish_btn

    @property
    def fragment_include_button(self) -> QPushButton:
        return self._frag_include_btn

    @property
    def work_versions_button(self) -> QPushButton:
        return self._work_versions_btn

    @property
    def work_export_button(self) -> QPushButton:
        return self._work_export_btn

    @property
    def collection_export_button(self) -> QPushButton:
        return self._coll_export_btn
