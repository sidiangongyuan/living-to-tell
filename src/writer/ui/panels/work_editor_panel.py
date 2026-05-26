"""Work editor panel (M8): edit a work's header + ordered sections.

Layout:
- top: title / summary / tags / status / target word count + Save snapshot.
- middle row: sections list (with Add body / Add heading / Up / Down /
  Delete / Toggle type buttons) on the left; the focused section's
  content editor on the right.
- bottom: word count + manual save button.

The panel emits ``work_changed(work_id)`` whenever the data has been
modified so the parent (works panel) can refresh its row.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.app.settings import DEFAULT_EDITOR_DISPLAY_SETTINGS, EditorDisplaySettings
from writer.app.container import AppContainer
from writer.domain.enums import SectionType, WorkStatus
from writer.domain.models.work_section import WorkSection
from writer.ui.dialogs.work_versions_dialog import WorkVersionsDialog
from writer.ui.i18n import TR
from writer.ui.panels.editor_panel import _font_families
from writer.ui.widgets.editor_find import (
    EditorFindBar,
    EditorPageControls,
    PaperRichTextEdit,
)


_AUTOSAVE_DEBOUNCE_MS = 600


class WorkEditorPanel(QWidget):
    work_changed = Signal(str)
    section_changed = Signal(str)  # work_id

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._work_id: Optional[str] = None
        self._current_section_id: Optional[str] = None
        self._loading = False
        self._display_settings = DEFAULT_EDITOR_DISPLAY_SETTINGS
        self._find_bar = EditorFindBar()
        self._page_controls = EditorPageControls()

        # ---- header fields ----
        self._title = QLineEdit()
        self._title.setPlaceholderText(TR("work.title_placeholder"))
        self._summary = QLineEdit()
        self._summary.setPlaceholderText(TR("work.summary_placeholder"))
        self._tags = QLineEdit()
        self._tags.setPlaceholderText(TR("work.tags_placeholder"))
        self._status = QComboBox()
        for s in WorkStatus.values():
            self._status.addItem(TR(f"work.status.{s}"), s)
        self._target_wc = QSpinBox()
        self._target_wc.setRange(0, 10_000_000)
        self._target_wc.setSpecialValueText(TR("work.no_target"))

        for w in (self._title, self._summary, self._tags):
            w.editingFinished.connect(self._save_header)
        self._status.currentIndexChanged.connect(self._save_status)
        self._target_wc.editingFinished.connect(self._save_target)

        header_row1 = QHBoxLayout()
        header_row1.addWidget(QLabel(TR("work.title")))
        header_row1.addWidget(self._title, 1)

        header_row2 = QHBoxLayout()
        header_row2.addWidget(QLabel(TR("work.summary")))
        header_row2.addWidget(self._summary, 1)

        header_row3 = QHBoxLayout()
        header_row3.addWidget(QLabel(TR("work.tags")))
        header_row3.addWidget(self._tags, 1)
        header_row3.addWidget(QLabel(TR("work.status")))
        header_row3.addWidget(self._status)
        header_row3.addWidget(QLabel(TR("work.target_wc")))
        header_row3.addWidget(self._target_wc)

        # ---- sections list + buttons ----
        self._sections = QListWidget()
        self._sections.itemSelectionChanged.connect(self._on_section_selected)

        self._add_body_btn = QPushButton(TR("work.add_body"))
        self._add_body_btn.clicked.connect(lambda: self._add_section(SectionType.BODY.value))
        self._add_heading_btn = QPushButton(TR("work.add_heading"))
        self._add_heading_btn.clicked.connect(lambda: self._add_section(SectionType.HEADING.value))
        self._toggle_type_btn = QPushButton(TR("work.toggle_type"))
        self._toggle_type_btn.clicked.connect(self._toggle_section_type)
        self._up_btn = QPushButton("↑")
        self._up_btn.clicked.connect(lambda: self._move_section(-1))
        self._down_btn = QPushButton("↓")
        self._down_btn.clicked.connect(lambda: self._move_section(1))
        self._del_btn = QPushButton(TR("work.delete_section"))
        self._del_btn.clicked.connect(self._delete_section)

        section_btns = QHBoxLayout()
        for b in (
            self._add_body_btn,
            self._add_heading_btn,
            self._toggle_type_btn,
            self._up_btn,
            self._down_btn,
            self._del_btn,
        ):
            section_btns.addWidget(b)
        section_btns.addStretch(1)

        section_left = QWidget()
        sl = QVBoxLayout(section_left)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addLayout(section_btns)
        sl.addWidget(self._sections, 1)

        self._editor = PaperRichTextEdit()
        self._editor.setPlaceholderText(TR("work.body_placeholder"))
        self._editor.textChanged.connect(self._on_editor_changed)
        self._editor.textChanged.connect(self._find_bar.refresh_matches)

        section_split = QSplitter(Qt.Orientation.Horizontal)
        section_split.addWidget(section_left)
        section_split.addWidget(self._editor)
        section_split.setStretchFactor(0, 0)
        section_split.setStretchFactor(1, 1)
        section_split.setSizes([260, 540])

        # ---- bottom row: word count + snapshot/restore ----
        self._wc_label = QLabel("")
        self._snapshot_btn = QPushButton(TR("work.save_snapshot"))
        self._snapshot_btn.clicked.connect(self._on_save_snapshot)
        self._versions_btn = QPushButton(TR("work.versions"))
        self._versions_btn.clicked.connect(self._on_open_versions)

        bottom = QHBoxLayout()
        bottom.addWidget(self._wc_label)
        bottom.addStretch(1)
        bottom.addWidget(self._snapshot_btn)
        bottom.addWidget(self._versions_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._find_bar)
        layout.addLayout(header_row1)
        layout.addLayout(header_row2)
        layout.addLayout(header_row3)
        layout.addWidget(section_split, 1)
        layout.addWidget(self._page_controls)
        layout.addLayout(bottom)

        self._editor_save_timer = QTimer(self)
        self._editor_save_timer.setSingleShot(True)
        self._editor_save_timer.setInterval(_AUTOSAVE_DEBOUNCE_MS)
        self._editor_save_timer.timeout.connect(self._flush_section_content)

        self._find_bar.set_editor(self._editor)
        self._page_controls.set_editor(self._editor)
        self._find_bar.install_on(
            self,
            self._title,
            self._summary,
            self._tags,
            self._sections,
            self._editor,
            self._editor.viewport(),
        )
        self._set_enabled(False)
        self.apply_display_settings(DEFAULT_EDITOR_DISPLAY_SETTINGS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_work(self, work_id: Optional[str]) -> None:
        # Flush any pending text edits before switching.
        if self._editor_save_timer.isActive():
            self._editor_save_timer.stop()
            self._flush_section_content()

        self._work_id = work_id
        self._current_section_id = None
        if work_id is None:
            self._set_enabled(False)
            self._loading = True
            self._title.setText("")
            self._summary.setText("")
            self._tags.setText("")
            self._sections.clear()
            self._editor.setPlainText("")
            self._wc_label.setText("")
            self._loading = False
            self._find_bar.close_bar(clear_query=True)
            self._page_controls.schedule_refresh()
            return

        work = self._container.work_repository.get(work_id)
        if work is None:
            self.load_work(None)
            return

        self._loading = True
        self._set_enabled(True)
        self._title.setText(work.title)
        self._summary.setText(work.summary)
        self._tags.setText(", ".join(work.tags))
        idx = self._status.findData(work.status)
        self._status.setCurrentIndex(max(0, idx))
        self._target_wc.setValue(int(work.target_word_count or 0))

        self._reload_sections()
        self._loading = False
        self._update_word_count()
        self._find_bar.refresh_matches()
        self._page_controls.schedule_refresh()

    def focus_section(self, section_id: str) -> None:
        for i in range(self._sections.count()):
            item = self._sections.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == section_id:
                self._sections.setCurrentRow(i)
                return

    def current_work_id(self) -> Optional[str]:
        """Return the work being edited, or ``None`` if no work is loaded."""
        return self._work_id

    def current_section_id(self) -> Optional[str]:
        """Return the focused section id, or ``None`` if nothing is selected."""
        return self._current_section_id

    def current_section_content(self) -> str:
        """Return the live editor text for the focused section."""
        if self._current_section_id is None:
            return ""
        return self._editor.toPlainText()

    def selection_range(self) -> Optional[tuple[int, int]]:
        cursor = self._editor.textCursor()
        if not cursor.hasSelection():
            return None
        return cursor.selectionStart(), cursor.selectionEnd()

    def selected_section_text(self) -> str:
        cursor = self._editor.textCursor()
        return cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else ""

    def select_current_section_range(self, start: int, end: int) -> None:
        text = self._editor.toPlainText()
        lower = max(0, min(len(text), int(start)))
        upper = max(lower, min(len(text), int(end)))
        cursor = self._editor.textCursor()
        cursor.setPosition(lower)
        cursor.setPosition(upper, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(cursor)
        self._editor.ensureCursorVisible()
        self._editor.setFocus()

    def flush_pending(self) -> None:
        """Force any debounced text edit to be persisted immediately.

        Used by callers (e.g. AI workspace binding) that need the freshest
        section body before reading it.
        """
        if self._editor_save_timer.isActive():
            self._editor_save_timer.stop()
            self._flush_section_content()

    def activate_excerpt_find(self, excerpt: str) -> bool:
        return self._find_bar.activate_excerpt(excerpt)

    def apply_display_settings(self, settings: EditorDisplaySettings) -> None:
        self._display_settings = settings
        title_font = QFont()
        title_font.setFamilies(_font_families(settings.font_family))
        title_font.setPointSizeF(max(settings.font_size + 2, 18))
        self._title.setFont(title_font)

        body_font = QFont()
        body_font.setFamilies(_font_families(settings.font_family))
        body_font.setPointSizeF(settings.font_size)
        self._editor.setFont(body_font)
        self._editor.document().setDefaultFont(body_font)
        self._editor.set_soft_page_guides_enabled(settings.soft_page_guides_enabled)
        self._editor.set_paper_layout(settings.page_vertical_padding, settings.page_gap)
        self._page_controls.refresh()

    # ------------------------------------------------------------------
    # Section list management
    # ------------------------------------------------------------------
    def _reload_sections(self) -> None:
        if self._work_id is None:
            return
        previous = self._current_section_id
        self._sections.blockSignals(True)
        self._sections.clear()
        sections = self._container.work_section_repository.list_for_work(self._work_id)
        for s in sections:
            self._sections.addItem(self._make_section_item(s))
        self._sections.blockSignals(False)

        if previous is not None:
            for i in range(self._sections.count()):
                if self._sections.item(i).data(Qt.ItemDataRole.UserRole) == previous:
                    self._sections.setCurrentRow(i)
                    return
        if self._sections.count() > 0:
            self._sections.setCurrentRow(0)
        else:
            self._current_section_id = None
            self._editor.blockSignals(True)
            self._editor.setPlainText("")
            self._editor.blockSignals(False)
            self._find_bar.refresh_matches()
            self._page_controls.schedule_refresh()

    @staticmethod
    def _make_section_item(section: WorkSection) -> QListWidgetItem:
        if section.section_type == SectionType.HEADING.value:
            preview = section.content.strip() or TR("work.untitled_heading")
            label = f"# {preview}"
        else:
            preview = section.content.strip().splitlines()[0] if section.content.strip() else TR("work.empty_body")
            if len(preview) > 60:
                preview = preview[:57] + "…"
            label = f"¶ {preview}"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, section.id)
        item.setData(Qt.ItemDataRole.UserRole + 1, section.section_type)
        return item

    def _on_section_selected(self) -> None:
        if self._editor_save_timer.isActive():
            self._editor_save_timer.stop()
            self._flush_section_content()
        item = self._sections.currentItem()
        if item is None:
            self._current_section_id = None
            self._editor.blockSignals(True)
            self._editor.setPlainText("")
            self._editor.blockSignals(False)
            self._find_bar.refresh_matches()
            return
        section_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_section_id = section_id
        section = self._container.work_section_repository.get(section_id)
        self._editor.blockSignals(True)
        self._editor.setPlainText(section.content if section else "")
        self._editor.blockSignals(False)
        self._find_bar.refresh_matches()
        self._page_controls.schedule_refresh()

    def _add_section(self, section_type: str) -> None:
        if self._work_id is None:
            return
        section = self._container.work_section_repository.create(
            self._work_id, section_type=section_type
        )
        self._current_section_id = section.id
        self._reload_sections()
        self.work_changed.emit(self._work_id)
        self._update_word_count()

    def _delete_section(self) -> None:
        if self._work_id is None or self._current_section_id is None:
            return
        self._container.work_section_repository.delete(self._current_section_id)
        self._current_section_id = None
        self._reload_sections()
        self.work_changed.emit(self._work_id)
        self._update_word_count()

    def _toggle_section_type(self) -> None:
        if self._work_id is None or self._current_section_id is None:
            return
        section = self._container.work_section_repository.get(self._current_section_id)
        if section is None:
            return
        new_type = (
            SectionType.BODY.value
            if section.section_type == SectionType.HEADING.value
            else SectionType.HEADING.value
        )
        self._container.work_section_repository.set_section_type(
            self._current_section_id, new_type
        )
        self._reload_sections()
        self.work_changed.emit(self._work_id)

    def _move_section(self, delta: int) -> None:
        if self._work_id is None or self._current_section_id is None:
            return
        self._container.work_section_repository.move(
            self._current_section_id, delta
        )
        self._reload_sections()
        self.work_changed.emit(self._work_id)

    # ------------------------------------------------------------------
    # Editor body autosave
    # ------------------------------------------------------------------
    def _on_editor_changed(self) -> None:
        if self._loading or self._current_section_id is None:
            return
        self._editor_save_timer.start()

    def _flush_section_content(self) -> None:
        if self._current_section_id is None:
            return
        text = self._editor.toPlainText()
        try:
            self._container.work_section_repository.update_content(
                self._current_section_id, text
            )
        except Exception:  # noqa: BLE001
            # Connection may have been closed (e.g. during teardown).
            return
        # Refresh the list label for the saved section without losing focus.
        for i in range(self._sections.count()):
            item = self._sections.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == self._current_section_id:
                section = self._container.work_section_repository.get(
                    self._current_section_id
                )
                if section is not None:
                    new_item = self._make_section_item(section)
                    item.setText(new_item.text())
                break
        if self._work_id:
            self.work_changed.emit(self._work_id)
            self.section_changed.emit(self._work_id)
        self._update_word_count()

    # ------------------------------------------------------------------
    # Header autosave
    # ------------------------------------------------------------------
    def _save_header(self) -> None:
        if self._loading or self._work_id is None:
            return
        tags = [t.strip() for t in self._tags.text().split(",") if t.strip()]
        self._container.work_repository.update(
            self._work_id,
            title=self._title.text(),
            summary=self._summary.text(),
            tags=tags,
        )
        self.work_changed.emit(self._work_id)

    def _save_status(self) -> None:
        if self._loading or self._work_id is None:
            return
        status = self._status.currentData()
        if isinstance(status, str):
            self._container.work_repository.set_status(self._work_id, status)
            self.work_changed.emit(self._work_id)

    def _save_target(self) -> None:
        if self._loading or self._work_id is None:
            return
        val = self._target_wc.value()
        self._container.work_repository.set_target_word_count(
            self._work_id, val if val > 0 else None
        )
        self.work_changed.emit(self._work_id)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
    def _on_save_snapshot(self) -> None:
        if self._work_id is None:
            return
        if self._editor_save_timer.isActive():
            self._editor_save_timer.stop()
            self._flush_section_content()
        self._container.work_service.save_manual_snapshot(self._work_id)
        QMessageBox.information(
            self, TR("work.snapshot_saved"), TR("work.snapshot_saved_msg")
        )

    def _on_open_versions(self) -> None:
        if self._work_id is None:
            return
        if self._editor_save_timer.isActive():
            self._editor_save_timer.stop()
            self._flush_section_content()
        dlg = WorkVersionsDialog(self._container, self._work_id, self)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.restored:
            self.load_work(self._work_id)
            self.work_changed.emit(self._work_id)

    # ------------------------------------------------------------------
    def _set_enabled(self, on: bool) -> None:
        for w in (
            self._title,
            self._summary,
            self._tags,
            self._status,
            self._target_wc,
            self._sections,
            self._editor,
            self._add_body_btn,
            self._add_heading_btn,
            self._toggle_type_btn,
            self._up_btn,
            self._down_btn,
            self._del_btn,
            self._snapshot_btn,
            self._versions_btn,
        ):
            w.setEnabled(on)

    def _update_word_count(self) -> None:
        if self._work_id is None:
            self._wc_label.setText("")
            return
        wc = self._container.work_service.compute_word_count(self._work_id)
        target = self._container.work_repository.get(self._work_id)
        if target and target.target_word_count:
            self._wc_label.setText(
                TR("work.word_count_with_target").format(
                    words=wc, target=target.target_word_count
                )
            )
        else:
            self._wc_label.setText(
                TR("work.word_count").format(words=wc)
            )
