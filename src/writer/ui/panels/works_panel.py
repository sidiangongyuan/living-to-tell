"""Works panel (M8): list of works on the left, editor on the right.

The list shows each work's title plus a compact status/word-count badge.
Selecting a work loads it into the embedded :class:`WorkEditorPanel`.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.enums import WorkStatus
from writer.domain.models.work import Work
from writer.ui.i18n import TR
from writer.ui.panels.work_editor_panel import WorkEditorPanel
from writer.ui.widgets.empty_state import EmptyStateCard


class WorksPanel(QWidget):
    """Two-pane works browser: list + editor."""

    work_selected = Signal(str)  # work_id
    # M9A: emitted by the empty-state "Include current fragment in a work"
    # CTA so the parent can route it to the existing include-fragment flow.
    include_fragment_requested = Signal()

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container

        self._column_title = QLabel(TR("column.works"))
        self._column_title.setObjectName("ColumnTitle")

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._on_selection_changed)

        self._new_btn = QPushButton(TR("works.new"))
        self._new_btn.setObjectName("PrimaryButton")
        self._new_btn.clicked.connect(self._on_new_work)
        self._archive_btn = QPushButton(TR("works.archive"))
        self._archive_btn.clicked.connect(self._on_toggle_archive)
        self._export_btn = QPushButton(TR("works.export"))
        self._export_btn.clicked.connect(self._on_export_work)
        self._delete_btn = QPushButton(TR("works.delete"))
        self._delete_btn.setObjectName("DangerButton")
        self._delete_btn.clicked.connect(self._on_delete_work)
        self._show_archived = QCheckBox(TR("works.show_archived"))
        self._show_archived.toggled.connect(self.refresh)

        top_row = QHBoxLayout()
        top_row.addWidget(self._new_btn)
        top_row.addWidget(self._archive_btn)
        top_row.addWidget(self._export_btn)
        top_row.addWidget(self._delete_btn)
        top_row.addStretch(1)

        # Empty state for the works list (shown when no works exist).
        self._empty_card = EmptyStateCard(
            TR("empty.works_title"),
            TR("empty.works_desc"),
            primary_label=TR("empty.works_primary"),
            primary_callback=self._on_new_work,
            secondary_label=TR("empty.works_secondary"),
            secondary_callback=self.include_fragment_requested.emit,
        )
        empty_wrap = QWidget()
        ew = QVBoxLayout(empty_wrap)
        ew.setContentsMargins(8, 16, 8, 16)
        ew.addWidget(self._empty_card)
        ew.addStretch(1)

        self._list_stack = QStackedWidget()
        self._list_stack.addWidget(self._list)       # 0
        self._list_stack.addWidget(empty_wrap)        # 1

        left = QWidget()
        left.setObjectName("WriterListColumn")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._column_title)
        left_layout.addLayout(top_row)
        left_layout.addWidget(self._list_stack, 1)
        left_layout.addWidget(self._show_archived)

        self._editor = WorkEditorPanel(container)
        self._editor.work_changed.connect(lambda _: self.refresh(preserve_selection=True))

        # ── Right-side "no work selected" card ────────────────────────────
        # When works exist but the user hasn't picked one yet (or just
        # cleared their selection), the editor pane is empty and confusing.
        # Replace it with a real empty state so the user knows what to do.
        self._unselected_card = EmptyStateCard(
            TR("empty.work_unselected_title"),
            TR("empty.work_unselected_desc"),
            primary_label=TR("empty.work_unselected_primary"),
            primary_callback=self._on_new_work,
        )
        unselected_wrap = QWidget()
        uw = QVBoxLayout(unselected_wrap)
        uw.setContentsMargins(32, 48, 32, 32)
        uw.addWidget(self._unselected_card)
        uw.addStretch(1)

        self._right_stack = QStackedWidget()
        self._right_stack.addWidget(self._editor)         # 0 — editor
        self._right_stack.addWidget(unselected_wrap)       # 1 — unselected card

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self._right_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 720])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self, *, preserve_selection: bool = False) -> None:
        previous_id: Optional[str] = None
        if preserve_selection:
            previous_id = self._current_work_id()
        self._list.blockSignals(True)
        self._list.clear()
        works = self._container.work_repository.list_recent(
            limit=500, include_archived=self._show_archived.isChecked()
        )
        for w in works:
            wc = self._container.work_service.compute_word_count(w.id)
            archived_badge = (
                f" · {TR('works.archived_badge')}" if w.archived_at else ""
            )
            label = (
                f"{w.title or TR('works.untitled')}  "
                f"[{w.status} · {wc}{archived_badge}]"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, w.id)
            self._list.addItem(item)
        self._list.blockSignals(False)

        if self._list.count() == 0:
            self._list_stack.setCurrentIndex(1)
        else:
            self._list_stack.setCurrentIndex(0)

        # M9A: only restore an explicit previous selection. Do NOT auto-pick
        # row 0, otherwise the "pick a work, or start a new one" empty
        # state can never appear in real usage.
        if previous_id is not None:
            self._select_id(previous_id)
        else:
            self._list.clearSelection()
            self._list.setCurrentRow(-1)
        self._update_right_stack()
        self._update_archive_button()

    def select_work(self, work_id: str) -> None:
        self._select_id(work_id)

    def select_work_section(self, work_id: str, section_id: Optional[str]) -> None:
        self._select_id(work_id)
        if section_id:
            self._editor.focus_section(section_id)

    # ------------------------------------------------------------------
    def _on_selection_changed(self) -> None:
        wid = self._current_work_id()
        if wid:
            self._editor.load_work(wid)
            self.work_selected.emit(wid)
        else:
            self._editor.load_work(None)
        self._update_right_stack()
        self._update_archive_button()

    def _update_right_stack(self) -> None:
        """Show the editor when a work is selected, otherwise the empty card."""
        if self._current_work_id():
            self._right_stack.setCurrentIndex(0)
        else:
            self._right_stack.setCurrentIndex(1)

    def _on_new_work(self) -> None:
        work = self._container.work_repository.create(title=TR("works.untitled"))
        self.refresh()
        self._select_id(work.id)
        self._update_right_stack()

    def _on_delete_work(self) -> None:
        wid = self._current_work_id()
        if not wid:
            return
        from PySide6.QtWidgets import QMessageBox

        ans = QMessageBox.question(
            self,
            TR("works.delete"),
            TR("works.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._container.work_repository.delete(wid)
        self.refresh()

    # ------------------------------------------------------------------
    def _current_work_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _select_id(self, work_id: str) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == work_id:
                self._list.setCurrentRow(i)
                return

    # ------------------------------------------------------------------
    def _update_archive_button(self) -> None:
        wid = self._current_work_id()
        if not wid:
            self._archive_btn.setEnabled(False)
            self._export_btn.setEnabled(False)
            self._archive_btn.setText(TR("works.archive"))
            return
        self._archive_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        w = self._container.work_repository.get(wid)
        if w is not None and w.archived_at:
            self._archive_btn.setText(TR("works.unarchive"))
        else:
            self._archive_btn.setText(TR("works.archive"))

    def _on_toggle_archive(self) -> None:
        wid = self._current_work_id()
        if not wid:
            return
        w = self._container.work_repository.get(wid)
        if w is None:
            return
        currently_archived = bool(w.archived_at)
        self._container.work_repository.set_archived(wid, not currently_archived)
        self.refresh(preserve_selection=True)

    def _on_export_work(self) -> None:
        wid = self._current_work_id()
        if not wid:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            TR("works.export"),
            "",
            TR("export.filter_all"),
        )
        if not path:
            return
        from pathlib import Path

        svc = self._container.work_export_service
        try:
            lower = path.lower()
            if lower.endswith(".docx"):
                svc.export_work_docx(wid, path)
            elif lower.endswith(".md"):
                Path(path).write_text(svc.export_work_md(wid), encoding="utf-8")
            else:
                Path(path).write_text(svc.export_work_txt(wid), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            QMessageBox.critical(self, TR("dlg.export_failed"), str(exc))
            return
        QMessageBox.information(
            self,
            TR("works.export"),
            TR("works.export_done").format(path=path),
        )
