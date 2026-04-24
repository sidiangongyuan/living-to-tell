"""Version History dialog — lets the user inspect and restore prior bodies.

Layout (M5D):
  Left  — version list (newest first):  type label | timestamp | provider/model
  Right — two read-only panes stacked vertically:
            top:    currently live body  (labelled "Current")
            bottom: selected version body (labelled by version type + timestamp)
  Bottom row — [Restore Selected Version]  [Close]

Restore is disabled when:
  * No version is selected, or
  * The entry has no version history at all (empty state).

This dialog never edits text directly; all mutation goes through
VersionHistoryService.restore().
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from writer.services.version_history_service import VersionHistoryService
from writer.ui.i18n import TR


class VersionHistoryDialog(QDialog):
    """Browse and restore the version history of a single entry.

    Parameters
    ----------
    entry_id:
        The entry whose history is shown.
    live_body:
        The current live body to display in the "Current" pane.
    service:
        ``VersionHistoryService`` instance that owns the restore logic.
    """

    def __init__(
        self,
        entry_id: str,
        live_body: str,
        service: VersionHistoryService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._entry_id = entry_id
        self._service = service
        self._live_body = live_body
        # Will be set to the new body after a successful restore so the
        # caller can reload the editor.
        self._restored_body: Optional[str] = None

        self.setWindowTitle(TR("vhd.title"))
        self.resize(860, 520)

        self._build_ui()
        self._load_versions()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def restored_body(self) -> Optional[str]:
        """Return the restored body text, or None if no restore was done."""
        return self._restored_body

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Left: version list
        self._version_list = QListWidget()
        self._version_list.currentItemChanged.connect(self._on_selection_changed)

        left = QVBoxLayout()
        left.addWidget(QLabel(TR("vhd.history_label")))
        left.addWidget(self._version_list, 1)
        left_widget = QWidget()
        left_widget.setLayout(left)

        # Right: current pane + selected pane
        self._current_label = QLabel(TR("vhd.current_body_label"))
        self._current_edit = QPlainTextEdit(self._live_body)
        self._current_edit.setReadOnly(True)

        self._selected_label = QLabel(TR("vhd.no_version_selected"))
        self._selected_edit = QPlainTextEdit()
        self._selected_edit.setReadOnly(True)
        self._selected_edit.setPlaceholderText(TR("vhd.no_version_selected_placeholder"))

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        current_widget = QWidget()
        current_layout = QVBoxLayout(current_widget)
        current_layout.setContentsMargins(0, 0, 0, 0)
        current_layout.addWidget(self._current_label)
        current_layout.addWidget(self._current_edit)

        selected_widget = QWidget()
        selected_layout = QVBoxLayout(selected_widget)
        selected_layout.setContentsMargins(0, 0, 0, 0)
        selected_layout.addWidget(self._selected_label)
        selected_layout.addWidget(self._selected_edit)

        right_splitter.addWidget(current_widget)
        right_splitter.addWidget(selected_widget)
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 1)

        # Main horizontal split
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)

        # Restore button (separate from the dialog button box so we can
        # control its enabled state and keep Close independent).
        self._restore_btn = QPushButton(TR("vhd.restore_btn"))
        self._restore_btn.setEnabled(False)
        self._restore_btn.clicked.connect(self._on_restore)

        close_btn = QPushButton(TR("vhd.close_btn"))
        close_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._restore_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)

        root = QVBoxLayout(self)
        root.addWidget(main_splitter, 1)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_versions(self) -> None:
        self._version_list.clear()
        versions = self._service.list_history(self._entry_id)
        if not versions:
            placeholder = QListWidgetItem(TR("vhd.no_history"))
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self._version_list.addItem(placeholder)
            self._restore_btn.setEnabled(False)
            return

        for v in versions:
            label = self._service.version_type_label(v.version_type)
            ts = (v.created_at or "")[:19].replace("T", " ")
            display = f"{label}  ·  {ts}"
            if v.provider:
                display += f"  ·  {v.provider}"
                if v.model:
                    display += f" / {v.model}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, v.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, v.content)
            self._version_list.addItem(item)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_selection_changed(
        self, current: Optional[QListWidgetItem], _prev
    ) -> None:
        if current is None or not current.data(Qt.ItemDataRole.UserRole):
            self._selected_label.setText(TR("vhd.no_version_selected"))
            self._selected_edit.setPlainText("")
            self._restore_btn.setEnabled(False)
            return
        version_id = current.data(Qt.ItemDataRole.UserRole)
        content = current.data(Qt.ItemDataRole.UserRole + 1)
        self._selected_label.setText(current.text())
        self._selected_edit.setPlainText(content or "")
        self._restore_btn.setEnabled(bool(version_id))

    def _on_restore(self) -> None:
        item = self._version_list.currentItem()
        if item is None:
            return
        version_id = item.data(Qt.ItemDataRole.UserRole)
        if not version_id:
            return

        confirm = QMessageBox.question(
            self,
            TR("vhd.restore_confirm_title"),
            TR("vhd.restore_confirm_msg"),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            outcome = self._service.restore(self._entry_id, version_id)
        except ValueError as err:
            QMessageBox.critical(self, TR("vhd.restore_failed"), str(err))
            return

        if outcome.was_noop:
            QMessageBox.information(
                self,
                TR("vhd.nothing_changed_title"),
                TR("vhd.nothing_changed_msg"),
            )
            return

        self._restored_body = outcome.new_body
        self._current_edit.setPlainText(outcome.new_body)
        self._live_body = outcome.new_body
        self._load_versions()
        QMessageBox.information(
            self,
            TR("vhd.restored_title"),
            TR("vhd.restored_msg"),
        )
