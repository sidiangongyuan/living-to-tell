"""Collections panel (M8): manage collections and their work order."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
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
from writer.ui.dialogs.work_picker_dialog import WorkPickerDialog
from writer.ui.i18n import TR
from writer.ui.widgets.empty_state import EmptyStateCard


class CollectionsPanel(QWidget):
    collection_selected = Signal(str)
    # M9A: emitted by the empty-state "Go organise a work first" CTA so
    # the parent can switch the active mode to Works without the panel
    # needing a back-reference.
    switch_to_works_requested = Signal()

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container

        # Left: collection list
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
        for b in (self._new_btn, self._rename_btn, self._delete_btn):
            coll_btns.addWidget(b)
        coll_btns.addStretch(1)

        self._collections_empty = EmptyStateCard(
            TR("empty.collections_title"),
            TR("empty.collections_desc"),
            primary_label=TR("empty.collections_primary"),
            primary_callback=self._on_new_collection,
            secondary_label=TR("empty.collections_secondary"),
            secondary_callback=self.switch_to_works_requested.emit,
        )
        coll_empty_wrap = QWidget()
        cew = QVBoxLayout(coll_empty_wrap)
        cew.setContentsMargins(8, 16, 8, 16)
        cew.addWidget(self._collections_empty)
        cew.addStretch(1)

        self._collections_stack = QStackedWidget()
        self._collections_stack.addWidget(self._collections)   # 0
        self._collections_stack.addWidget(coll_empty_wrap)      # 1

        self._column_title = QLabel(TR("column.collections"))
        self._column_title.setObjectName("ColumnTitle")

        left = QWidget()
        left.setObjectName("WriterListColumn")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 16, 16, 16)
        ll.setSpacing(8)
        ll.addWidget(self._column_title)
        ll.addLayout(coll_btns)
        ll.addWidget(QLabel(TR("collections.label")))
        ll.addWidget(self._collections_stack, 1)

        # Right: works in selected collection
        self._works = QListWidget()
        self._works.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._works.model().rowsMoved.connect(self._on_works_reordered)

        self._add_work_btn = QPushButton(TR("collections.add_work"))
        self._add_work_btn.clicked.connect(self._on_add_work)
        self._remove_work_btn = QPushButton(TR("collections.remove_work"))
        self._remove_work_btn.clicked.connect(self._on_remove_work)
        self._up_btn = QPushButton("↑")
        self._up_btn.clicked.connect(lambda: self._move_work(-1))
        self._down_btn = QPushButton("↓")
        self._down_btn.clicked.connect(lambda: self._move_work(1))
        self._export_btn = QPushButton(TR("collections.export"))
        self._export_btn.clicked.connect(self._on_export_collection)

        work_btns = QHBoxLayout()
        for b in (
            self._add_work_btn,
            self._remove_work_btn,
            self._up_btn,
            self._down_btn,
            self._export_btn,
        ):
            work_btns.addWidget(b)
        work_btns.addStretch(1)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.addLayout(work_btns)
        rl.addWidget(QLabel(TR("collections.works_label")))
        rl.addWidget(self._works, 1)

        # M9A: right-side "no collection picked" card.
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
        self._right_stack = QStackedWidget()
        self._right_stack.addWidget(right)             # 0 — works area
        self._right_stack.addWidget(unselected_wrap)    # 1 — unselected card

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self._right_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 700])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.refresh_collections()

    # ------------------------------------------------------------------
    def refresh_collections(self) -> None:
        previous = self._current_collection_id()
        self._collections.blockSignals(True)
        self._collections.clear()
        for c in self._container.collection_repository.list_all():
            item = QListWidgetItem(c.name or TR("collections.untitled"))
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self._collections.addItem(item)
        self._collections.blockSignals(False)
        if self._collections.count() == 0:
            self._collections_stack.setCurrentIndex(1)
        else:
            self._collections_stack.setCurrentIndex(0)
        # M9A: only restore an explicit previous selection. Do NOT auto-pick
        # row 0 — leaves the "pick a collection first" empty state reachable.
        if previous is not None:
            for i in range(self._collections.count()):
                if self._collections.item(i).data(Qt.ItemDataRole.UserRole) == previous:
                    self._collections.setCurrentRow(i)
                    self._update_right_stack()
                    return
        self._collections.clearSelection()
        self._collections.setCurrentRow(-1)
        self._refresh_works()
        self._update_right_stack()

    def _update_right_stack(self) -> None:
        if self._current_collection_id():
            self._right_stack.setCurrentIndex(0)
        else:
            self._right_stack.setCurrentIndex(1)

    def _refresh_works(self) -> None:
        self._works.blockSignals(True)
        self._works.clear()
        cid = self._current_collection_id()
        if cid is not None:
            for w in self._container.collection_repository.list_works(cid):
                wc = self._container.work_service.compute_word_count(w.id)
                title = w.title or TR("works.untitled")
                item = QListWidgetItem(f"{title}  [{w.status} · {wc}]")
                item.setData(Qt.ItemDataRole.UserRole, w.id)
                self._works.addItem(item)
        self._works.blockSignals(False)

    # ------------------------------------------------------------------
    def _current_collection_id(self) -> Optional[str]:
        item = self._collections.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _current_work_id(self) -> Optional[str]:
        item = self._works.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_collection_changed(self) -> None:
        self._refresh_works()
        self._update_right_stack()
        cid = self._current_collection_id()
        if cid:
            self.collection_selected.emit(cid)

    # ------------------------------------------------------------------
    def _on_new_collection(self) -> None:
        name, ok = QInputDialog.getText(
            self, TR("collections.new"), TR("collections.new_name_prompt")
        )
        if not ok:
            return
        c = self._container.collection_repository.create(name=name.strip())
        self.refresh_collections()
        for i in range(self._collections.count()):
            if self._collections.item(i).data(Qt.ItemDataRole.UserRole) == c.id:
                self._collections.setCurrentRow(i)
                break
        self._update_right_stack()

    def _on_rename_collection(self) -> None:
        cid = self._current_collection_id()
        if cid is None:
            return
        c = self._container.collection_repository.get(cid)
        if c is None:
            return
        name, ok = QInputDialog.getText(
            self, TR("collections.rename"), TR("collections.new_name_prompt"), text=c.name
        )
        if not ok:
            return
        self._container.collection_repository.rename(cid, name.strip())
        self.refresh_collections()

    def _on_delete_collection(self) -> None:
        cid = self._current_collection_id()
        if cid is None:
            return
        ans = QMessageBox.question(
            self,
            TR("collections.delete"),
            TR("collections.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._container.collection_repository.delete(cid)
        self.refresh_collections()

    # ------------------------------------------------------------------
    def _on_add_work(self) -> None:
        cid = self._current_collection_id()
        if cid is None:
            return
        dlg = WorkPickerDialog(self._container, self)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.selected_work_id:
            self._container.collection_repository.add_work(cid, dlg.selected_work_id)
            self._refresh_works()

    def _on_remove_work(self) -> None:
        cid = self._current_collection_id()
        wid = self._current_work_id()
        if cid is None or wid is None:
            return
        self._container.collection_repository.remove_work(cid, wid)
        self._refresh_works()

    def _move_work(self, delta: int) -> None:
        cid = self._current_collection_id()
        if cid is None:
            return
        row = self._works.currentRow()
        if row < 0:
            return
        new_row = max(0, min(self._works.count() - 1, row + delta))
        if new_row == row:
            return
        ids = [
            self._works.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._works.count())
        ]
        ids.insert(new_row, ids.pop(row))
        self._container.collection_repository.reorder_works(cid, ids)
        self._refresh_works()
        self._works.setCurrentRow(new_row)

    def _on_works_reordered(self, *args) -> None:
        cid = self._current_collection_id()
        if cid is None:
            return
        ids = [
            self._works.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._works.count())
        ]
        self._container.collection_repository.reorder_works(cid, ids)

    # ------------------------------------------------------------------
    def _on_export_collection(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        cid = self._current_collection_id()
        if cid is None:
            return
        path, selected = QFileDialog.getSaveFileName(
            self,
            TR("collections.export"),
            "",
            TR("export.filter_all"),
        )
        if not path:
            return
        svc = self._container.work_export_service
        try:
            if path.lower().endswith(".docx"):
                svc.export_collection_docx(cid, path)
            elif path.lower().endswith(".md"):
                from pathlib import Path

                Path(path).write_text(svc.export_collection_md(cid), encoding="utf-8")
            else:
                from pathlib import Path

                Path(path).write_text(svc.export_collection_txt(cid), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, TR("dlg.export_failed"), str(exc))
            return
        QMessageBox.information(
            self, TR("collections.export"), TR("collections.export_done").format(path=path)
        )
