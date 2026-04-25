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
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.enums import WorkStatus
from writer.domain.models.work import Work
from writer.ui.i18n import TR
from writer.ui.panels.work_editor_panel import WorkEditorPanel


class WorksPanel(QWidget):
    """Two-pane works browser: list + editor."""

    work_selected = Signal(str)  # work_id

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._on_selection_changed)

        self._new_btn = QPushButton(TR("works.new"))
        self._new_btn.clicked.connect(self._on_new_work)
        self._archive_btn = QPushButton(TR("works.archive"))
        self._archive_btn.clicked.connect(self._on_toggle_archive)
        self._export_btn = QPushButton(TR("works.export"))
        self._export_btn.clicked.connect(self._on_export_work)
        self._delete_btn = QPushButton(TR("works.delete"))
        self._delete_btn.clicked.connect(self._on_delete_work)
        self._show_archived = QCheckBox(TR("works.show_archived"))
        self._show_archived.toggled.connect(self.refresh)

        top_row = QHBoxLayout()
        top_row.addWidget(self._new_btn)
        top_row.addWidget(self._archive_btn)
        top_row.addWidget(self._export_btn)
        top_row.addWidget(self._delete_btn)
        top_row.addStretch(1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addLayout(top_row)
        left_layout.addWidget(self._list, 1)
        left_layout.addWidget(self._show_archived)

        self._editor = WorkEditorPanel(container)
        self._editor.work_changed.connect(lambda _: self.refresh(preserve_selection=True))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self._editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 720])

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

        if previous_id is not None:
            self._select_id(previous_id)
        elif self._list.count() > 0:
            self._list.setCurrentRow(0)
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
        self._update_archive_button()

    def _on_new_work(self) -> None:
        work = self._container.work_repository.create(title=TR("works.untitled"))
        self.refresh()
        self._select_id(work.id)

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
