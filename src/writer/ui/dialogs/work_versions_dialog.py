"""Work versions dialog (M8): list snapshots and restore one."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.ui.i18n import TR


class WorkVersionsDialog(QDialog):
    def __init__(
        self,
        container: AppContainer,
        work_id: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._work_id = work_id
        self.restored = False

        self.setWindowTitle(TR("work_versions.title"))
        self.resize(420, 380)

        self._list = QListWidget()

        restore_btn = QPushButton(TR("work_versions.restore"))
        restore_btn.clicked.connect(self._on_restore)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list, 1)
        layout.addWidget(restore_btn)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        versions = self._container.work_version_repository.list_for_work(self._work_id)
        for v in versions:
            label_parts = [v.created_at or "", v.version_type]
            if v.label:
                label_parts.append(v.label)
            self._list.addItem(QListWidgetItem("  ·  ".join(label_parts)))
            self._list.item(self._list.count() - 1).setData(
                Qt.ItemDataRole.UserRole, v.id
            )

    def _on_restore(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        version_id = item.data(Qt.ItemDataRole.UserRole)
        ans = QMessageBox.question(
            self,
            TR("work_versions.restore"),
            TR("work_versions.restore_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._container.work_service.restore_version(self._work_id, version_id)
        self.restored = True
        self.accept()
