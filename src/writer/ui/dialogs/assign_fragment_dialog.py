"""Assignment dialog — pick the project (and optional chapter) for a fragment."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from writer.storage.repositories.chapter_repository import ChapterRepository
from writer.storage.repositories.project_repository import ProjectRepository


_NO_PROJECT_ID = ""
_NO_CHAPTER_ID = ""


class AssignFragmentDialog(QDialog):
    def __init__(
        self,
        project_repo: ProjectRepository,
        chapter_repo: ChapterRepository,
        *,
        current_project_id: Optional[str],
        current_chapter_id: Optional[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._projects = project_repo
        self._chapters = chapter_repo
        self.setWindowTitle("Assign fragment")

        self._project_combo = QComboBox()
        self._chapter_combo = QComboBox()

        self._project_combo.addItem("(no project)", _NO_PROJECT_ID)
        for project in self._projects.list_all():
            self._project_combo.addItem(project.name, project.id)

        form = QFormLayout()
        form.addRow("Project", self._project_combo)
        form.addRow("Chapter", self._chapter_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        # pre-select current values
        if current_project_id:
            idx = self._project_combo.findData(current_project_id)
            if idx >= 0:
                self._project_combo.setCurrentIndex(idx)
        self._project_combo.currentIndexChanged.connect(self._on_project_changed)
        self._on_project_changed()
        if current_chapter_id:
            idx = self._chapter_combo.findData(current_chapter_id)
            if idx >= 0:
                self._chapter_combo.setCurrentIndex(idx)

    # ---------- public ----------
    def selected_project_id(self) -> Optional[str]:
        value = self._project_combo.currentData(Qt.ItemDataRole.UserRole)
        return value if value else None

    def selected_chapter_id(self) -> Optional[str]:
        value = self._chapter_combo.currentData(Qt.ItemDataRole.UserRole)
        return value if value else None

    # ---------- internal ----------
    def _on_project_changed(self, *_args) -> None:
        self._chapter_combo.clear()
        self._chapter_combo.addItem("(no chapter)", _NO_CHAPTER_ID)
        project_id = self.selected_project_id()
        if project_id is None:
            self._chapter_combo.setEnabled(False)
            return
        self._chapter_combo.setEnabled(True)
        for chapter in self._chapters.list_for_project(project_id):
            self._chapter_combo.addItem(
                chapter.title or "Untitled chapter", chapter.id
            )
