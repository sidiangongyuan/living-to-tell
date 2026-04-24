"""Thin QDialog host around ProjectPanel."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from writer.services.export.markdown_exporter import MarkdownExporter
from writer.services.export.text_exporter import TextExporter
from writer.storage.repositories.chapter_repository import ChapterRepository
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.project_repository import ProjectRepository
from writer.ui.panels.project_panel import ProjectPanel
from writer.ui.i18n import TR


class ProjectsDialog(QDialog):
    def __init__(
        self,
        project_repo: ProjectRepository,
        chapter_repo: ChapterRepository,
        entry_repo: EntryRepository,
        markdown_exporter: MarkdownExporter,
        text_exporter: TextExporter,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TR("projects.title"))
        self.resize(960, 560)
        self.panel = ProjectPanel(
            project_repo,
            chapter_repo,
            entry_repo,
            markdown_exporter,
            text_exporter,
            parent=self,
        )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.panel)
        layout.addWidget(buttons)

