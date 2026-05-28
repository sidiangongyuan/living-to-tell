"""Include-fragment dialog (M8).

Lets the user pick a target work + section, edit the text to be inserted,
and confirm. The text defaults to the *selected text* from the source
fragment when the caller provides one (otherwise the full body). The
insertion point is *explicit*: the dialog shows a read-only preview of
the chosen section and the user clicks where the text should go.

If the target section combo is set to "(append as new section)", the
cursor preview is hidden and a brand-new body section is created instead.

The fragment's curation status flips to ``included`` automatically on
success.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.enums import SectionType
from writer.domain.models.entry import Entry
from writer.ui.i18n import TR
from writer.ui.widgets.controls import NoWheelComboBox

NEW_SECTION_SENTINEL = "__new__"


class IncludeFragmentDialog(QDialog):
    """Pick a work/section, choose insertion point, confirm inclusion."""

    def __init__(
        self,
        container: AppContainer,
        entry: Entry,
        *,
        default_text: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._entry = entry
        self.included_outcome = None  # type: ignore[assignment]

        # Resolve default text: caller-provided selection wins; fall back
        # to the entry body. Strip pure-empty selections back to the body
        # so we never seed the editor with a blank string.
        if default_text and default_text.strip():
            initial_text = default_text
        else:
            initial_text = entry.body or ""

        self.setWindowTitle(TR("include.title"))
        self.resize(600, 540)

        self._work_combo = NoWheelComboBox()
        self._work_combo.currentIndexChanged.connect(self._reload_sections)

        self._section_combo = NoWheelComboBox()
        self._section_combo.currentIndexChanged.connect(self._reload_preview)

        self._editor = QTextEdit()
        self._editor.setPlainText(initial_text)

        # Section preview — read-only but cursor-movable so the user can
        # click to place the insertion point. End-of-content by default.
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText(TR("include.preview_placeholder"))

        self._position_hint = QLabel("")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(TR("include.confirm"))
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel(TR("include.work")))
        row1.addWidget(self._work_combo, 1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(TR("include.section")))
        row2.addWidget(self._section_combo, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addWidget(QLabel(TR("include.text")))
        layout.addWidget(self._editor, 1)
        layout.addWidget(QLabel(TR("include.preview_label")))
        layout.addWidget(self._preview, 1)
        layout.addWidget(self._position_hint)
        layout.addWidget(buttons)

        # React to cursor moves in the preview to update the position hint.
        self._preview.cursorPositionChanged.connect(self._update_position_hint)

        self._populate_works()

    # ------------------------------------------------------------------
    def _populate_works(self) -> None:
        works = self._container.work_repository.list_recent(limit=500)
        self._work_combo.clear()
        for w in works:
            self._work_combo.addItem(w.title or TR("works.untitled"), w.id)
        if not works:
            self._section_combo.addItem(
                TR("include.no_works"), NEW_SECTION_SENTINEL
            )
            self._section_combo.setEnabled(False)
            self._preview.setEnabled(False)

    def _reload_sections(self) -> None:
        wid = self._work_combo.currentData()
        self._section_combo.clear()
        if not wid:
            return
        self._section_combo.setEnabled(True)
        sections = self._container.work_section_repository.list_for_work(wid)
        for s in sections:
            preview = (
                (s.content or "").strip().splitlines()[0]
                if s.content.strip()
                else TR("work.empty_body")
            )
            if len(preview) > 50:
                preview = preview[:47] + "…"
            prefix = "#" if s.section_type == SectionType.HEADING.value else "¶"
            self._section_combo.addItem(f"{prefix} {preview}", s.id)
        self._section_combo.addItem(TR("include.new_section"), NEW_SECTION_SENTINEL)

    def _reload_preview(self) -> None:
        section_value = self._section_combo.currentData()
        if section_value is None or section_value == NEW_SECTION_SENTINEL:
            self._preview.setPlainText("")
            self._preview.setEnabled(False)
            self._position_hint.setText(TR("include.position_new_section"))
            return
        self._preview.setEnabled(True)
        section = self._container.work_section_repository.get(section_value)
        body = section.content if section else ""
        self._preview.setPlainText(body)
        # Default the cursor to the end of the section so "just press OK"
        # keeps the previous append behaviour — but the user can click
        # anywhere else to set an explicit insertion point.
        cursor = self._preview.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._preview.setTextCursor(cursor)
        self._update_position_hint()

    def _update_position_hint(self) -> None:
        section_value = self._section_combo.currentData()
        if section_value == NEW_SECTION_SENTINEL:
            return
        pos = self._preview.textCursor().position()
        total = len(self._preview.toPlainText())
        self._position_hint.setText(
            TR("include.position_at").format(pos=pos, total=total)
        )

    # ------------------------------------------------------------------
    # Test / automation hook: explicitly set the insertion position in
    # the preview without simulating a click.
    # ------------------------------------------------------------------
    def set_insert_position(self, position: int) -> None:
        cursor = self._preview.textCursor()
        clamped = max(0, min(position, len(self._preview.toPlainText())))
        cursor.setPosition(clamped)
        self._preview.setTextCursor(cursor)

    def current_insert_position(self) -> Optional[int]:
        section_value = self._section_combo.currentData()
        if section_value == NEW_SECTION_SENTINEL:
            return None
        return self._preview.textCursor().position()

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        wid = self._work_combo.currentData()
        if not wid:
            QMessageBox.warning(self, TR("include.title"), TR("include.no_works"))
            return
        text = self._editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, TR("include.title"), TR("include.empty_text"))
            return
        section_value = self._section_combo.currentData()
        if section_value == NEW_SECTION_SENTINEL:
            section_id: Optional[str] = None
            position: Optional[int] = None
        else:
            section_id = section_value
            position = self._preview.textCursor().position()
        try:
            self.included_outcome = self._container.work_service.include_fragment(
                work_id=wid,
                section_id=section_id,
                position=position,
                edited_text=text,
                entry_id=self._entry.id,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, TR("include.title"), str(exc))
            return
        self.accept()
