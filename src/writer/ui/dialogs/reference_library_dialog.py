"""Thin QDialog host for the reference library panel."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel


class ReferenceLibraryDialog(QDialog):
    def __init__(
        self, repo: ReferenceRepository, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reference library")
        self.resize(860, 520)
        self.panel = ReferenceLibraryPanel(repo, parent=self)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.panel)
        layout.addWidget(buttons)
