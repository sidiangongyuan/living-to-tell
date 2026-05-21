"""Right pane: title + body editor for the active fragment."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QKeyEvent,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.app.settings import (
    DEFAULT_EDITOR_DISPLAY_SETTINGS,
    DEFAULT_EDITOR_FONT_FAMILY,
    EditorDisplaySettings,
)
from writer.domain.models.entry import Entry
from writer.services.epigraph import detect_epigraph
from writer.storage.repositories.entry_repository import serialize_tags
from writer.ui.i18n import TR
from writer.ui.motion import cancel_scrollbar_animation, smooth_scrollbar_to
from writer.ui.tag_colors import tag_style_sheet
from writer.ui.widgets.editor_find import EditorFindBar, PaperPlainTextEdit


FOCUS_MODE_CONTENT_WIDTH = 1180
EDITOR_RESPONSIVE_SIDE_MARGIN = 24
EDITOR_RESPONSIVE_MAX_WIDTH = 1600
FOCUS_MODE_RESPONSIVE_SIDE_MARGIN = 32
FOCUS_MODE_RESPONSIVE_MAX_WIDTH = 1800
PARAGRAPH_INDENT_TEXT = "\u3000\u3000"


class _WriterBodyEdit(PaperPlainTextEdit):
    """Plain-text body editor with view-only layout formatting.

    Paragraph indentation and spacing are applied through block formats so the
    stored plain text stays clean. We join the previous edit block before
    reapplying formats so visual refreshes do not create separate undo steps.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._display_settings = DEFAULT_EDITOR_DISPLAY_SETTINGS
        self._typewriter_override = False
        self._focus_paragraph_enabled = False
        self._reduced_motion = False
        self._applying_formats = False
        self._typewriter_adjust_allowed = False
        self._typewriter_adjust_suppressed = False
        self._find_selections: list[QTextEdit.ExtraSelection] = []

        self._format_timer = QTimer(self)
        self._format_timer.setSingleShot(True)
        self._format_timer.timeout.connect(self._reapply_paragraph_formatting)

        self._typewriter_timer = QTimer(self)
        self._typewriter_timer.setSingleShot(True)
        self._typewriter_timer.timeout.connect(self._adjust_typewriter_scroll)

        self.textChanged.connect(self._schedule_paragraph_formatting)
        self.cursorPositionChanged.connect(self._refresh_focus_paragraph)

    def set_reduced_motion(self, enabled: bool) -> None:
        self._reduced_motion = bool(enabled)
        super().set_reduced_motion(enabled)

    def apply_display_settings(self, settings: EditorDisplaySettings) -> None:
        self._display_settings = settings
        font = QFont()
        font.setFamilies(_font_families(settings.font_family))
        font.setPointSizeF(settings.font_size)
        self.setFont(font)
        self.document().setDefaultFont(font)
        self._schedule_paragraph_formatting()
        self._refresh_focus_paragraph()

    def display_settings(self) -> EditorDisplaySettings:
        return self._display_settings

    def set_typewriter_override(self, enabled: bool) -> None:
        self._typewriter_override = enabled
        self._focus_paragraph_enabled = enabled
        self._refresh_focus_paragraph()

    def effective_typewriter_enabled(self) -> bool:
        return self._typewriter_override or self._display_settings.typewriter_mode_enabled

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._schedule_typewriter_adjust(force=True)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._cancel_typewriter_follow()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._cancel_typewriter_follow()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._cancel_typewriter_follow()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            self._cancel_typewriter_follow()
            super().keyPressEvent(event)
            return
        if self._should_auto_indent_return(event):
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.insertBlock()
            if not cursor.block().text().startswith(PARAGRAPH_INDENT_TEXT):
                cursor.insertText(PARAGRAPH_INDENT_TEXT)
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            event.accept()
            self._schedule_typewriter_adjust(force=True)
            return
        is_delete_key = self._is_delete_key(event)
        if is_delete_key:
            self._typewriter_adjust_suppressed = True
            self._cancel_typewriter_follow()
        super().keyPressEvent(event)
        if is_delete_key:
            self._cancel_typewriter_follow()
            QTimer.singleShot(80, self._clear_typewriter_adjust_suppression)
            return
        if self._should_typewriter_follow_key(event):
            self._schedule_typewriter_adjust(force=True)

    def _schedule_paragraph_formatting(self) -> None:
        if self._applying_formats:
            return
        self._format_timer.start(0)

    def _reapply_paragraph_formatting(self) -> None:
        if self._applying_formats:
            return
        self._applying_formats = True
        try:
            document = self.document()
            controller = QTextCursor(document)
            controller.joinPreviousEditBlock()
            metrics = self.fontMetrics()
            line_height = max(100, int(round(self._display_settings.line_height * 100)))
            paragraph_spacing_px = metrics.lineSpacing() * self._display_settings.paragraph_spacing
            visual_indent_px = (
                metrics.horizontalAdvance("汉汉")
                if self._display_settings.visual_first_line_indent_enabled
                else 0.0
            )

            block = document.firstBlock()
            is_first = True
            while block.isValid():
                block_cursor = QTextCursor(block)
                block_format = block.blockFormat()
                block_format.setLineHeight(
                    float(line_height),
                    QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
                )
                block_format.setTextIndent(visual_indent_px)
                block_format.setTopMargin(0.0 if is_first else paragraph_spacing_px)
                block_format.setBottomMargin(0.0)
                block_cursor.setBlockFormat(block_format)
                block = block.next()
                is_first = False
            controller.endEditBlock()
        finally:
            self._applying_formats = False
        self._refresh_focus_paragraph()

    def _schedule_typewriter_adjust(self, *, force: bool = False) -> None:
        if self._typewriter_adjust_suppressed:
            return
        if force:
            self._typewriter_adjust_allowed = True
        if self.effective_typewriter_enabled() and self._typewriter_adjust_allowed:
            self._typewriter_timer.start(0)

    def _clear_typewriter_adjust_suppression(self) -> None:
        self._typewriter_adjust_suppressed = False

    def _cancel_typewriter_follow(self) -> None:
        self._typewriter_adjust_allowed = False
        self._typewriter_timer.stop()
        cancel_scrollbar_animation(self.verticalScrollBar())

    def _adjust_typewriter_scroll(self) -> None:
        self._typewriter_adjust_allowed = False
        if not self.effective_typewriter_enabled() or not self.isVisible():
            return
        viewport_height = self.viewport().height()
        if viewport_height <= 0:
            return
        cursor_rect = self.cursorRect()
        desired_top = int(viewport_height * 0.4)
        delta = cursor_rect.top() - desired_top
        threshold = max(cursor_rect.height(), self.fontMetrics().lineSpacing()) // 2
        if abs(delta) <= threshold:
            return
        scrollbar = self.verticalScrollBar()
        smoothed_delta = int(delta * 0.7)
        target = scrollbar.value() + smoothed_delta
        target = max(scrollbar.minimum(), min(scrollbar.maximum(), target))
        smooth_scrollbar_to(scrollbar, target, reduced=self._reduced_motion)

    def _should_auto_indent_return(self, event: QKeyEvent) -> bool:
        if not self._display_settings.auto_paragraph_indent_enabled:
            return False
        if event.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return False
        return not event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
        )

    def _should_typewriter_follow_key(self, event: QKeyEvent) -> bool:
        if self._is_delete_key(event):
            return False
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
        ):
            return True
        return bool(event.text())

    @staticmethod
    def _is_delete_key(event: QKeyEvent) -> bool:
        return event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)

    def _refresh_focus_paragraph(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = list(self._find_selections)
        if self._focus_paragraph_enabled:
            current_block = self.textCursor().block()

            muted_format = QTextCharFormat()
            muted_format.setForeground(QColor(120, 128, 140))
            block = self.document().firstBlock()
            while block.isValid():
                if block != current_block and block.text().strip():
                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = QTextCursor(block)
                    selection.cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    selection.format = muted_format
                    selections.append(selection)
                block = block.next()

            current_format = QTextCharFormat()
            current_format.setBackground(QColor(30, 143, 149, 22))
            current_selection = QTextEdit.ExtraSelection()
            current_selection.cursor = QTextCursor(current_block)
            current_selection.cursor.clearSelection()
            current_selection.format = current_format
            current_selection.format.setProperty(
                QTextCharFormat.Property.FullWidthSelection, True
            )
            selections.append(current_selection)
        self.setExtraSelections(selections)

    def set_find_selections(self, selections: list[QTextEdit.ExtraSelection]) -> None:
        self._find_selections = list(selections)
        self._refresh_focus_paragraph()

    def focusNextPrevChild(self, next: bool) -> bool:  # noqa: A002, N802
        result = super().focusNextPrevChild(next)
        self._schedule_paragraph_formatting()
        return result


class EditorPanel(QWidget):
    content_changed = Signal()
    save_specimen_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._entry_id: Optional[str] = None
        self._display_settings = DEFAULT_EDITOR_DISPLAY_SETTINGS
        self._focus_mode_enabled = False
        self._find_bar = EditorFindBar()

        self._title = QLineEdit()
        self._title.setPlaceholderText(TR("editor.title_placeholder"))
        self._title.textChanged.connect(self._on_changed)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText(TR("editor.tags_placeholder"))
        self._tags.textChanged.connect(self._on_changed)
        self._tags.textChanged.connect(self._update_tag_chips)

        # Tag chip row — hidden when no tags
        self._tag_chips_widget = QWidget()
        self._tag_chips_layout = QHBoxLayout(self._tag_chips_widget)
        self._tag_chips_layout.setContentsMargins(0, 2, 0, 2)
        self._tag_chips_layout.setSpacing(4)
        self._tag_chips_layout.addStretch(1)
        self._tag_chips_widget.setVisible(False)

        self._body = _WriterBodyEdit()
        self._body.setPlaceholderText(TR("editor.body_placeholder"))
        self._body.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._body.textChanged.connect(self._on_changed)
        self._body.textChanged.connect(self._refresh_epigraph_card)
        self._body.textChanged.connect(self._update_word_count)
        self._body.textChanged.connect(self._refresh_save_specimen_state)
        self._body.selectionChanged.connect(self._update_word_count)
        self._body.customContextMenuRequested.connect(self._on_body_context_menu)

        self._epigraph_card = QFrame()
        self._epigraph_card.setObjectName("EpigraphCard")
        self._epigraph_card.setVisible(False)
        epigraph_layout = QVBoxLayout(self._epigraph_card)
        epigraph_layout.setContentsMargins(20, 18, 20, 18)
        epigraph_layout.setSpacing(8)

        self._epigraph_label = QLabel(TR("editor.epigraph_label"))
        self._epigraph_label.setObjectName("EpigraphCardLabel")
        epigraph_layout.addWidget(self._epigraph_label)

        self._epigraph_quote = QLabel("")
        self._epigraph_quote.setObjectName("EpigraphQuote")
        self._epigraph_quote.setWordWrap(True)
        self._epigraph_quote.setTextFormat(Qt.TextFormat.PlainText)
        epigraph_layout.addWidget(self._epigraph_quote)

        self._epigraph_attr = QLabel("")
        self._epigraph_attr.setObjectName("EpigraphAttribution")
        self._epigraph_attr.setWordWrap(True)
        self._epigraph_attr.setTextFormat(Qt.TextFormat.PlainText)
        self._epigraph_attr.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        epigraph_layout.addWidget(self._epigraph_attr)

        self._meta = QLabel("")
        self._meta.setObjectName("MetaLabel")

        self._save_specimen_btn = QPushButton(TR("context.action_save_specimen"))
        self._save_specimen_btn.setObjectName("GhostButton")
        self._save_specimen_btn.clicked.connect(self.save_specimen_requested.emit)

        self._word_count = QLabel("")
        self._word_count.setObjectName("MetaLabel")
        self._word_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.addWidget(self._meta, 1)
        bottom_row.addWidget(self._save_specimen_btn, 0)
        bottom_row.addWidget(self._word_count, 0)

        self._content_wrap = QWidget()
        self._content_wrap.setObjectName("EditorContentWrap")
        self._content_wrap.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        content_layout = QVBoxLayout(self._content_wrap)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)
        content_layout.addWidget(self._title)
        content_layout.addWidget(self._tags)
        content_layout.addWidget(self._tag_chips_widget)
        content_layout.addWidget(self._epigraph_card)
        content_layout.addWidget(self._body, 1)
        content_layout.addLayout(bottom_row)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        editor_column = QWidget()
        editor_column_layout = QVBoxLayout(editor_column)
        editor_column_layout.setContentsMargins(0, 0, 0, 0)
        editor_column_layout.setSpacing(8)
        editor_column_layout.addWidget(self._find_bar)
        editor_column_layout.addWidget(self._content_wrap, 1)
        layout.addWidget(editor_column, 1)
        layout.setAlignment(self._content_wrap, Qt.AlignmentFlag.AlignHCenter)

        self._loading = False
        self._find_bar.set_editor(self._body)
        self._find_bar.install_on(self, self._title, self._tags, self._body, self._body.viewport())
        self._body.textChanged.connect(self._find_bar.refresh_matches)
        self.apply_display_settings(DEFAULT_EDITOR_DISPLAY_SETTINGS)
        self.set_entry(None)
        self._update_word_count()
        self._refresh_save_specimen_state()

    def apply_display_settings(self, settings: EditorDisplaySettings) -> None:
        self._display_settings = settings
        self._apply_content_width()
        title_font = QFont()
        title_font.setFamilies(_font_families(settings.font_family))
        title_font.setPointSizeF(max(settings.font_size + 2, 18))
        self._title.setFont(title_font)

        tags_font = QFont(self._tags.font())
        tags_font.setPointSizeF(max(settings.font_size - 3, 12))
        self._tags.setFont(tags_font)

        epigraph_label_font = QFont()
        epigraph_label_font.setFamilies(_font_families(settings.font_family))
        epigraph_label_font.setPointSizeF(max(settings.font_size - 5, 11))
        self._epigraph_label.setFont(epigraph_label_font)

        epigraph_quote_font = QFont()
        epigraph_quote_font.setFamilies(_serif_font_families(settings.font_family))
        epigraph_quote_font.setPointSizeF(max(settings.font_size - 1, 14))
        self._epigraph_quote.setFont(epigraph_quote_font)

        epigraph_attr_font = QFont(epigraph_quote_font)
        epigraph_attr_font.setPointSizeF(max(settings.font_size - 3, 12))
        self._epigraph_attr.setFont(epigraph_attr_font)

        self._body.apply_display_settings(settings)
        self._body.set_soft_page_guides_enabled(settings.soft_page_guides_enabled)
        self.updateGeometry()

    def set_reduced_motion(self, enabled: bool) -> None:
        self._body.set_reduced_motion(enabled)

    def display_settings(self) -> EditorDisplaySettings:
        return self._display_settings

    def set_focus_mode_enabled(self, enabled: bool) -> None:
        self._focus_mode_enabled = bool(enabled)
        self._body.set_typewriter_override(bool(enabled))
        self._body.setProperty("focusMode", bool(enabled))
        self._body.style().unpolish(self._body)
        self._body.style().polish(self._body)
        self._apply_content_width()
        self._body._schedule_paragraph_formatting()  # noqa: SLF001

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_content_width()

    def _target_content_width(self) -> int:
        base_width = self._display_settings.content_width
        max_width = EDITOR_RESPONSIVE_MAX_WIDTH

        if self._focus_mode_enabled:
            base_width = max(base_width, FOCUS_MODE_CONTENT_WIDTH)
            max_width = FOCUS_MODE_RESPONSIVE_MAX_WIDTH

        available_width = max(0, self.width())
        if available_width > 0:
            base_width = max(base_width, available_width - self._responsive_side_margin())
        return min(base_width, max_width)

    def _responsive_side_margin(self) -> int:
        if self._focus_mode_enabled:
            return FOCUS_MODE_RESPONSIVE_SIDE_MARGIN
        return EDITOR_RESPONSIVE_SIDE_MARGIN

    def _apply_content_width(self) -> None:
        width = self._target_content_width()
        available_width = max(0, self.width())
        minimum_width = 0
        if available_width > 0:
            minimum_width = min(
                width,
                max(0, available_width - self._responsive_side_margin()),
            )
        if (
            self._content_wrap.maximumWidth() == width
            and self._content_wrap.minimumWidth() == minimum_width
        ):
            return
        self._content_wrap.setMinimumWidth(minimum_width)
        self._content_wrap.setMaximumWidth(width)
        self.updateGeometry()

    def set_entry(self, entry: Optional[Entry]) -> None:
        self._loading = True
        try:
            if entry is None:
                self._entry_id = None
                self._title.clear()
                self._tags.clear()
                self._body.clear()
                self._meta.setText("")
                self._update_tag_chips("")
                self._refresh_epigraph_card()
                self._find_bar.close_bar(clear_query=True)
                self._find_bar.clear_matches()
                self.setEnabled(False)
            else:
                self._entry_id = entry.id
                self._title.setText(entry.title)
                self._tags.setText(serialize_tags(entry.tags))
                self._body.setPlainText(entry.body)
                self._meta.setText(self._format_meta(entry))
                self._update_tag_chips(serialize_tags(entry.tags))
                self._refresh_epigraph_card()
                self._find_bar.refresh_matches()
                self.setEnabled(True)
        finally:
            self._loading = False
        self._refresh_save_specimen_state()

    def focus_body(self) -> None:
        """Move keyboard focus to the body editor and place cursor at end."""
        self._body.setFocus()
        cursor = self._body.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._body.setTextCursor(cursor)

    def update_meta(self, text: str) -> None:
        self._meta.setText(text)

    def current_entry_id(self) -> Optional[str]:
        return self._entry_id

    def title_text(self) -> str:
        return self._title.text()

    def tags_text(self) -> str:
        """Return the raw tags string from the QLineEdit."""
        return self._tags.text()

    def body_text(self) -> str:
        return self._body.toPlainText()

    def selection_range(self) -> Optional[tuple[int, int]]:
        """Return ``(start, end)`` of the body selection, or None if empty."""
        cursor = self._body.textCursor()
        if not cursor.hasSelection():
            return None
        return cursor.selectionStart(), cursor.selectionEnd()

    def selected_body_text(self) -> str:
        cursor = self._body.textCursor()
        return cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else ""

    @property
    def save_specimen_button(self) -> QPushButton:
        return self._save_specimen_btn

    def replace_body(self, new_body: str) -> None:
        self._loading = True
        try:
            self._body.setPlainText(new_body)
        finally:
            self._loading = False
        self._refresh_epigraph_card()
        self._find_bar.refresh_matches()

    def activate_excerpt_find(self, excerpt: str) -> bool:
        return self._find_bar.activate_excerpt(excerpt)

    def _on_changed(self) -> None:
        if self._loading or self._entry_id is None:
            return
        self.content_changed.emit()

    def _can_save_specimen(self) -> bool:
        return self._entry_id is not None and bool(self._body.toPlainText().strip())

    def _refresh_save_specimen_state(self) -> None:
        self._save_specimen_btn.setEnabled(self._can_save_specimen())

    def _create_body_context_menu(self, pos):
        menu = self._body.createStandardContextMenu(pos)
        menu.addSeparator()
        action = menu.addAction(TR("context.action_save_specimen"))
        action.setEnabled(self._can_save_specimen())
        action.triggered.connect(self.save_specimen_requested.emit)
        return menu

    def _on_body_context_menu(self, pos) -> None:
        menu = self._create_body_context_menu(pos)
        menu.exec(self._body.mapToGlobal(pos))

    def _update_tag_chips(self, text: str = "") -> None:
        """Rebuild tag chip labels from the tags QLineEdit."""
        # Remove all existing chip labels (leave the trailing stretch)
        while self._tag_chips_layout.count() > 1:
            item = self._tag_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        raw = self._tags.text() if not text and hasattr(self, "_tags") else text
        tags = [t.strip() for t in raw.split(",") if t.strip()]
        for tag in tags:
            chip = QLabel(tag)
            chip.setStyleSheet(tag_style_sheet(tag))
            self._tag_chips_layout.insertWidget(self._tag_chips_layout.count() - 1, chip)
        self._tag_chips_widget.setVisible(bool(tags))

    def _format_meta(self, entry: Entry) -> str:
        parts: list[str] = []
        created_label = TR("editor.meta_created")
        updated_label = TR("editor.meta_updated")
        if entry.created_at:
            parts.append(f"{created_label} {entry.created_at}")
        if entry.updated_at:
            parts.append(f"{updated_label} {entry.updated_at}")
        return "  |  ".join(parts)

    # ------------------------------------------------------------------
    # M7B: live word / character count
    # ------------------------------------------------------------------

    def _update_word_count(self) -> None:
        body = self._body.toPlainText()
        words = _count_words(body)
        chars = len(body)
        selected = self.selected_body_text()
        if selected:
            self._word_count.setText(
                TR("editor.word_count_with_sel").format(
                    words=words,
                    chars=chars,
                    sel_words=_count_words(selected),
                    sel_chars=len(selected),
                )
            )
        else:
            self._word_count.setText(TR("editor.word_count").format(words=words, chars=chars))

    def _refresh_epigraph_card(self) -> None:
        epigraph = detect_epigraph(self._body.toPlainText())
        if epigraph is None:
            self._epigraph_quote.clear()
            self._epigraph_attr.clear()
            self._epigraph_card.setVisible(False)
            return
        self._epigraph_quote.setText(epigraph.quote)
        self._epigraph_attr.setText(epigraph.attribution)
        self._epigraph_card.setVisible(True)


def _count_words(text: str) -> int:
    """Word count that treats CJK characters individually and splits
    non-CJK runs on whitespace (matches the intuition for mixed CN/EN
    drafts)."""
    if not text:
        return 0
    total = 0
    buffer: list[str] = []
    for ch in text:
        if _is_cjk(ch):
            if buffer:
                total += len("".join(buffer).split())
                buffer.clear()
            total += 1
        else:
            buffer.append(ch)
    if buffer:
        total += len("".join(buffer).split())
    return total


def _font_families(raw: str) -> list[str]:
    parts = [part.strip().strip("'\"") for part in (raw or "").split(",")]
    families = [part for part in parts if part]
    if _has_installed_family(families):
        return families
    fallback = [
        part.strip().strip("'\"") for part in DEFAULT_EDITOR_FONT_FAMILY.split(",") if part.strip()
    ]
    return fallback


def _serif_font_families(raw: str) -> list[str]:
    families = _font_families(raw)
    preferred = [
        "Source Han Serif SC",
        "Noto Serif CJK SC",
        "Songti SC",
        "STSong",
        "SimSun",
        "Georgia",
        "Cambria",
    ]
    merged = preferred + families
    deduped: list[str] = []
    seen: set[str] = set()
    for family in merged:
        key = family.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(family)
    if _has_installed_family(deduped):
        return deduped
    return families


def _has_installed_family(families: list[str]) -> bool:
    try:
        installed = {name.casefold() for name in QFontDatabase.families()}
    except Exception:  # noqa: BLE001
        return True
    return any(family.casefold() in installed for family in families)


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
        or 0x3040 <= code <= 0x309F  # Hiragana
        or 0x30A0 <= code <= 0x30FF  # Katakana
        or 0xAC00 <= code <= 0xD7AF  # Hangul Syllables
        or 0x3400 <= code <= 0x4DBF  # CJK Unified Ideographs Extension A
    )
