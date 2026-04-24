"""Project workspace panel (M5C).

A three-column layout — projects · sections · entries — plus a simple
project description editor and inline export buttons. Intentionally
plain: no drag-drop, no kanban, no board. Every mutation goes through
the repository layer; the panel is pure coordination + widgets.

The "Sections" column always has a sentinel "Unchaptered" row at the
top representing the project-level unchaptered bucket; real chapters
follow.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.chapter import Chapter
from writer.domain.models.project import Project
from writer.services.export.markdown_exporter import MarkdownExporter
from writer.services.export.text_exporter import TextExporter
from writer.storage.repositories.chapter_repository import ChapterRepository
from writer.storage.repositories.entry_repository import EntryRepository
from writer.storage.repositories.project_repository import ProjectRepository


_UNCHAPTERED_SENTINEL = "__unchaptered__"


class ProjectPanel(QWidget):
    """Emits :pyattr:`data_changed` whenever projects, chapters, or entry
    assignments mutate, so the host window can refresh dependent views.
    """

    data_changed = Signal()

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
        self._projects = project_repo
        self._chapters = chapter_repo
        self._entries = entry_repo
        self._markdown_exporter = markdown_exporter
        self._text_exporter = text_exporter

        # ----- column 1: projects -----
        self._project_list = QListWidget()
        self._new_project_btn = QPushButton("New")
        self._rename_project_btn = QPushButton("Rename")
        self._delete_project_btn = QPushButton("Delete")
        project_btn_row = QHBoxLayout()
        project_btn_row.addWidget(self._new_project_btn)
        project_btn_row.addWidget(self._rename_project_btn)
        project_btn_row.addWidget(self._delete_project_btn)
        project_btn_row.addStretch(1)
        left = QVBoxLayout()
        left.addWidget(QLabel("Projects"))
        left.addWidget(self._project_list, 1)
        left.addLayout(project_btn_row)

        # ----- column 2: sections (Unchaptered + chapters) -----
        self._chapter_list = QListWidget()
        self._new_chapter_btn = QPushButton("New")
        self._rename_chapter_btn = QPushButton("Rename")
        self._delete_chapter_btn = QPushButton("Delete")
        self._up_btn = QPushButton("↑")
        self._down_btn = QPushButton("↓")
        chapter_btn_row = QHBoxLayout()
        chapter_btn_row.addWidget(self._new_chapter_btn)
        chapter_btn_row.addWidget(self._rename_chapter_btn)
        chapter_btn_row.addWidget(self._delete_chapter_btn)
        chapter_btn_row.addWidget(self._up_btn)
        chapter_btn_row.addWidget(self._down_btn)
        chapter_btn_row.addStretch(1)
        middle = QVBoxLayout()
        middle.addWidget(QLabel("Sections"))
        middle.addWidget(self._chapter_list, 1)
        middle.addLayout(chapter_btn_row)

        # ----- column 3: entries in current section -----
        self._entry_list = QListWidget()
        self._entry_up_btn = QPushButton("↑")
        self._entry_down_btn = QPushButton("↓")
        self._move_to_unch_btn = QPushButton("→ Unchaptered")
        self._move_to_chapter_btn = QPushButton("→ Chapter…")
        self._remove_entry_btn = QPushButton("Remove from project")
        entry_btn_row = QHBoxLayout()
        entry_btn_row.addWidget(self._entry_up_btn)
        entry_btn_row.addWidget(self._entry_down_btn)
        entry_btn_row.addWidget(self._move_to_unch_btn)
        entry_btn_row.addWidget(self._move_to_chapter_btn)
        entry_btn_row.addWidget(self._remove_entry_btn)
        entry_btn_row.addStretch(1)
        right = QVBoxLayout()
        right.addWidget(QLabel("Entries"))
        right.addWidget(self._entry_list, 1)
        right.addLayout(entry_btn_row)

        # ----- columns row -----
        columns = QHBoxLayout()
        columns.addLayout(left, 2)
        columns.addLayout(middle, 2)
        columns.addLayout(right, 3)

        # ----- bottom: description + export -----
        self._description_edit = QPlainTextEdit()
        self._description_edit.setPlaceholderText(
            "Project description — shown in exported manuscripts."
        )
        self._description_edit.setFixedHeight(80)
        self._save_description_btn = QPushButton("Save description")
        self._export_md_btn = QPushButton("Export Markdown…")
        self._export_txt_btn = QPushButton("Export Text…")
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self._save_description_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self._export_md_btn)
        bottom_row.addWidget(self._export_txt_btn)

        # ----- assemble -----
        outer = QVBoxLayout(self)
        outer.addLayout(columns, 1)
        outer.addWidget(QLabel("Description"))
        outer.addWidget(self._description_edit)
        outer.addLayout(bottom_row)

        # wiring
        self._project_list.currentItemChanged.connect(self._on_project_changed)
        self._chapter_list.currentItemChanged.connect(self._on_section_changed)

        self._new_project_btn.clicked.connect(self._on_new_project)
        self._rename_project_btn.clicked.connect(self._on_rename_project)
        self._delete_project_btn.clicked.connect(self._on_delete_project)
        self._new_chapter_btn.clicked.connect(self._on_new_chapter)
        self._rename_chapter_btn.clicked.connect(self._on_rename_chapter)
        self._delete_chapter_btn.clicked.connect(self._on_delete_chapter)
        self._up_btn.clicked.connect(lambda: self._move_chapter(-1))
        self._down_btn.clicked.connect(lambda: self._move_chapter(1))

        self._entry_up_btn.clicked.connect(lambda: self._move_entry(-1))
        self._entry_down_btn.clicked.connect(lambda: self._move_entry(1))
        self._move_to_unch_btn.clicked.connect(self._on_move_entry_to_unchaptered)
        self._move_to_chapter_btn.clicked.connect(self._on_move_entry_to_chapter)
        self._remove_entry_btn.clicked.connect(self._on_remove_entry)

        self._save_description_btn.clicked.connect(self._on_save_description)
        self._export_md_btn.clicked.connect(lambda: self._on_export("markdown"))
        self._export_txt_btn.clicked.connect(lambda: self._on_export("text"))

        self.refresh_projects()

    # -------------------- refresh helpers --------------------
    def refresh_projects(self, *, select_id: Optional[str] = None) -> None:
        self._project_list.blockSignals(True)
        try:
            self._project_list.clear()
            for project in self._projects.list_all():
                item = QListWidgetItem(project.name)
                item.setData(Qt.ItemDataRole.UserRole, project.id)
                self._project_list.addItem(item)
        finally:
            self._project_list.blockSignals(False)

        if select_id is not None:
            for row in range(self._project_list.count()):
                if (
                    self._project_list.item(row).data(Qt.ItemDataRole.UserRole)
                    == select_id
                ):
                    self._project_list.setCurrentRow(row)
                    return
        if self._project_list.count() > 0:
            self._project_list.setCurrentRow(0)
        else:
            self._chapter_list.clear()
            self._entry_list.clear()
            self._description_edit.clear()
            self._description_edit.setEnabled(False)

    def _refresh_chapters(
        self, project_id: str, *, select_id: Optional[str] = None
    ) -> None:
        """Populate the sections column.

        The pseudo-section ``Unchaptered`` always sits at row 0. ``select_id``
        can be ``None`` (default), a real chapter id, or the unchaptered
        sentinel string.
        """
        self._chapter_list.blockSignals(True)
        try:
            self._chapter_list.clear()
            unchaptered_item = QListWidgetItem("Unchaptered")
            unchaptered_item.setData(
                Qt.ItemDataRole.UserRole, _UNCHAPTERED_SENTINEL
            )
            self._chapter_list.addItem(unchaptered_item)
            for chapter in self._chapters.list_for_project(project_id):
                item = QListWidgetItem(chapter.title or "Untitled chapter")
                item.setData(Qt.ItemDataRole.UserRole, chapter.id)
                self._chapter_list.addItem(item)
        finally:
            self._chapter_list.blockSignals(False)

        target_row = 0
        if select_id is not None:
            for row in range(self._chapter_list.count()):
                if (
                    self._chapter_list.item(row).data(Qt.ItemDataRole.UserRole)
                    == select_id
                ):
                    target_row = row
                    break
        self._chapter_list.setCurrentRow(target_row)

    def _refresh_entries(self) -> None:
        self._entry_list.clear()
        project = self.current_project()
        if project is None:
            return
        section_data = self._current_section_data()
        if section_data is None:
            return
        if section_data == _UNCHAPTERED_SENTINEL:
            entries = self._entries.list_unchaptered_for_project(project.id)
        else:
            entries = self._entries.list_for_chapter(section_data)
        for entry in entries:
            item = QListWidgetItem(entry.title.strip() or "Untitled fragment")
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._entry_list.addItem(item)
        if self._entry_list.count() > 0:
            self._entry_list.setCurrentRow(0)

    def _refresh_description(self) -> None:
        project = self.current_project()
        if project is None:
            self._description_edit.clear()
            self._description_edit.setEnabled(False)
            return
        self._description_edit.setEnabled(True)
        self._description_edit.blockSignals(True)
        try:
            self._description_edit.setPlainText(project.description)
        finally:
            self._description_edit.blockSignals(False)

    # -------------------- accessors --------------------
    def current_project(self) -> Optional[Project]:
        item = self._project_list.currentItem()
        if item is None:
            return None
        return self._projects.get(item.data(Qt.ItemDataRole.UserRole))

    def current_chapter(self) -> Optional[Chapter]:
        data = self._current_section_data()
        if data is None or data == _UNCHAPTERED_SENTINEL:
            return None
        return self._chapters.get(data)

    def _current_section_data(self) -> Optional[str]:
        item = self._chapter_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _current_entry_id(self) -> Optional[str]:
        item = self._entry_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # -------------------- slots --------------------
    def _on_project_changed(self, current, _previous) -> None:
        if current is None:
            self._chapter_list.clear()
            self._entry_list.clear()
            self._description_edit.clear()
            self._description_edit.setEnabled(False)
            return
        self._refresh_chapters(current.data(Qt.ItemDataRole.UserRole))
        self._refresh_entries()
        self._refresh_description()

    def _on_section_changed(self, _current, _previous) -> None:
        self._refresh_entries()

    def _on_new_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New project", "Project name:")
        if not ok or not name.strip():
            return
        project = self._projects.create(name.strip())
        self.refresh_projects(select_id=project.id)
        self.data_changed.emit()

    def _on_rename_project(self) -> None:
        project = self.current_project()
        if project is None:
            return
        name, ok = QInputDialog.getText(
            self, "Rename project", "Project name:", text=project.name
        )
        if not ok or not name.strip():
            return
        self._projects.rename(project.id, name.strip())
        self.refresh_projects(select_id=project.id)
        self.data_changed.emit()

    def _on_delete_project(self) -> None:
        project = self.current_project()
        if project is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete project",
            f"Delete project '{project.name}' and all its chapters?"
            " Fragments will be detached but kept.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._projects.delete(project.id)
        self.refresh_projects()
        self.data_changed.emit()

    def _on_new_chapter(self) -> None:
        project = self.current_project()
        if project is None:
            return
        title, ok = QInputDialog.getText(self, "New chapter", "Chapter title:")
        if not ok:
            return
        chapter = self._chapters.create(project.id, title.strip())
        self._refresh_chapters(project.id, select_id=chapter.id)
        self._refresh_entries()
        self.data_changed.emit()

    def _on_rename_chapter(self) -> None:
        chapter = self.current_chapter()
        project = self.current_project()
        if chapter is None or project is None:
            return
        title, ok = QInputDialog.getText(
            self, "Rename chapter", "Chapter title:", text=chapter.title
        )
        if not ok:
            return
        self._chapters.rename(chapter.id, title.strip())
        self._refresh_chapters(project.id, select_id=chapter.id)
        self.data_changed.emit()

    def _on_delete_chapter(self) -> None:
        chapter = self.current_chapter()
        project = self.current_project()
        if chapter is None or project is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete chapter",
            f"Delete chapter '{chapter.title or 'Untitled'}'?"
            " Its fragments will remain in the project as unchaptered.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._chapters.delete(chapter.id)
        self._refresh_chapters(project.id, select_id=_UNCHAPTERED_SENTINEL)
        self._refresh_entries()
        self.data_changed.emit()

    def _move_chapter(self, delta: int) -> None:
        project = self.current_project()
        chapter = self.current_chapter()
        if project is None or chapter is None:
            return
        current_ids = [
            ch.id for ch in self._chapters.list_for_project(project.id)
        ]
        try:
            idx = current_ids.index(chapter.id)
        except ValueError:
            return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(current_ids):
            return
        current_ids[idx], current_ids[new_idx] = (
            current_ids[new_idx],
            current_ids[idx],
        )
        self._chapters.reorder(project.id, current_ids)
        self._refresh_chapters(project.id, select_id=chapter.id)
        self.data_changed.emit()

    # -------------------- entry slots --------------------
    def _move_entry(self, delta: int) -> None:
        project = self.current_project()
        section_data = self._current_section_data()
        entry_id = self._current_entry_id()
        if project is None or section_data is None or entry_id is None:
            return
        chapter_id = (
            None if section_data == _UNCHAPTERED_SENTINEL else section_data
        )
        if chapter_id is None:
            ids = [e.id for e in self._entries.list_unchaptered_for_project(project.id)]
        else:
            ids = [e.id for e in self._entries.list_for_chapter(chapter_id)]
        try:
            idx = ids.index(entry_id)
        except ValueError:
            return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(ids):
            return
        ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
        self._entries.reorder_container(project.id, chapter_id, ids)
        self._refresh_entries()
        self._select_entry(entry_id)
        self.data_changed.emit()

    def _on_move_entry_to_unchaptered(self) -> None:
        entry_id = self._current_entry_id()
        if entry_id is None:
            return
        self._entries.assign_to_chapter(entry_id, None)
        project = self.current_project()
        if project is not None:
            self._refresh_chapters(project.id, select_id=_UNCHAPTERED_SENTINEL)
        self._refresh_entries()
        self._select_entry(entry_id)
        self.data_changed.emit()

    def _on_move_entry_to_chapter(self) -> None:
        project = self.current_project()
        entry_id = self._current_entry_id()
        if project is None or entry_id is None:
            return
        chapters = self._chapters.list_for_project(project.id)
        if not chapters:
            QMessageBox.information(
                self,
                "No chapters",
                "This project has no chapters yet. Create one first.",
            )
            return

        # Build disambiguated display labels: if two chapters share a title,
        # append a 1-based counter "(2)", "(3)" … to duplicates so each item
        # maps unambiguously to exactly one chapter id.
        seen: dict[str, int] = {}
        counts: dict[str, int] = {}
        for ch in chapters:
            label = ch.title.strip() if ch.title and ch.title.strip() else "Untitled chapter"
            counts[label] = counts.get(label, 0) + 1
        seq: dict[str, int] = {}
        labels: list[str] = []
        for ch in chapters:
            base = ch.title.strip() if ch.title and ch.title.strip() else "Untitled chapter"
            if counts[base] > 1:
                seq[base] = seq.get(base, 0) + 1
                label = f"{base} ({seq[base]})"
            else:
                label = base
            labels.append(label)

        pick, ok = QInputDialog.getItem(
            self, "Move to chapter", "Chapter:", labels, 0, False
        )
        if not ok:
            return
        # Use index to get the exact chapter object — labels are now unique.
        target = chapters[labels.index(pick)]
        try:
            self._entries.assign_to_chapter(entry_id, target.id)
        except ValueError as err:
            QMessageBox.warning(self, "Move failed", str(err))
            return
        self._refresh_chapters(project.id, select_id=target.id)
        self._refresh_entries()
        self._select_entry(entry_id)
        self.data_changed.emit()

    def _on_remove_entry(self) -> None:
        entry_id = self._current_entry_id()
        if entry_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Remove from project",
            "Detach this fragment from the project? The fragment itself is"
            " kept and stays editable from the main window.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._entries.assign_to_project(entry_id, None)
        self._refresh_entries()
        self.data_changed.emit()

    def _select_entry(self, entry_id: str) -> None:
        for row in range(self._entry_list.count()):
            if (
                self._entry_list.item(row).data(Qt.ItemDataRole.UserRole)
                == entry_id
            ):
                self._entry_list.setCurrentRow(row)
                return

    # -------------------- description --------------------
    def _on_save_description(self) -> None:
        project = self.current_project()
        if project is None:
            return
        text = self._description_edit.toPlainText()
        self._projects.update_description(project.id, text)
        self.data_changed.emit()

    # -------------------- export --------------------
    def _on_export(self, fmt: str) -> None:
        project = self.current_project()
        if project is None:
            QMessageBox.information(
                self, "No project", "Select a project to export."
            )
            return
        exporter = (
            self._markdown_exporter if fmt == "markdown" else self._text_exporter
        )
        text = exporter.export_project(project)
        ext = "md" if fmt == "markdown" else "txt"
        filter_label = (
            "Markdown (*.md)" if fmt == "markdown" else "Text files (*.txt)"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Export project", f"{project.name}.{ext}", filter_label
        )
        if not path:
            return
        try:
            Path(path).write_text(text, encoding="utf-8", newline="\n")
        except OSError as err:
            QMessageBox.critical(self, "Export failed", str(err))
