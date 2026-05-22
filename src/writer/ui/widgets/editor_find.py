"""Shared in-editor find bar and paper-like editor helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.ui.i18n import TR
from writer.ui.motion import cancel_scrollbar_animation, smooth_scrollbar_to

EditorWidget = QPlainTextEdit | QTextEdit

_MATCH_BG = QColor("#E8D9AA")
_MATCH_FG = QColor("#54411E")
_CURRENT_BG = QColor("#D29C43")
_CURRENT_FG = QColor("#FFFDF7")
_CURRENT_BORDER = QColor("#B97828")
_WHEEL_LINES_PER_NOTCH = 3
_WHEEL_ANIMATION_MS = 90


def _selection_type() -> type:
    return QTextEdit.ExtraSelection


@dataclass
class _MatchRange:
    start: int
    end: int


class EditorFindController(QObject):
    """Query matching/highlighting/navigation for text editors."""

    state_changed = Signal(int, int, bool)  # current_index(1-based), total, has_results

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._editor: Optional[EditorWidget] = None
        self._query = ""
        self._matches: list[_MatchRange] = []
        self._current_index = -1

    def set_editor(self, widget: Optional[EditorWidget]) -> None:
        if self._editor is widget:
            return
        self.clear()
        self._editor = widget
        self.refresh_matches()

    def set_query(self, text: str) -> None:
        query = text or ""
        if self._query == query:
            self.refresh_matches()
            return
        self._query = query
        self.refresh_matches()

    def query(self) -> str:
        return self._query

    def current_index(self) -> int:
        return self._current_index

    def match_count(self) -> int:
        return len(self._matches)

    def refresh_matches(self) -> None:
        editor = self._editor
        if editor is None:
            self.clear()
            return
        text = editor.toPlainText()
        if not self._query:
            self._matches = []
            self._current_index = -1
            self._apply_highlights()
            self._emit_state()
            return
        folded_query = self._query.casefold()
        folded_text = text.casefold()
        matches: list[_MatchRange] = []
        pos = 0
        while True:
            idx = folded_text.find(folded_query, pos)
            if idx < 0:
                break
            end = idx + len(self._query)
            matches.append(_MatchRange(idx, end))
            pos = max(end, idx + 1)
        previous_anchor = self._match_anchor()
        self._matches = matches
        self._current_index = self._find_best_index(previous_anchor)
        if self._matches:
            self._select_current_match(scroll=False)
        self._apply_highlights()
        self._emit_state()

    def go_next(self) -> bool:
        if not self._matches:
            self._emit_state()
            return False
        if self._current_index < 0:
            self._current_index = self._find_best_index(self._match_anchor())
        else:
            self._current_index = (self._current_index + 1) % len(self._matches)
        self._activate_current_match()
        return True

    def go_previous(self) -> bool:
        if not self._matches:
            self._emit_state()
            return False
        if self._current_index < 0:
            self._current_index = self._find_best_index(self._match_anchor())
        else:
            self._current_index = (self._current_index - 1) % len(self._matches)
        self._activate_current_match()
        return True

    def activate_first(self) -> bool:
        if not self._matches:
            self._emit_state()
            return False
        self._current_index = 0
        self._activate_current_match()
        return True

    def clear(self) -> None:
        self._matches = []
        self._current_index = -1
        self._apply_highlights()
        self._emit_state()

    def set_active_query(self, text: str) -> bool:
        self._query = text or ""
        self.refresh_matches()
        return self.activate_first()

    def _match_anchor(self) -> int:
        editor = self._editor
        if editor is None:
            return 0
        cursor = editor.textCursor()
        if cursor.hasSelection():
            return cursor.selectionStart()
        return cursor.position()

    def _find_best_index(self, anchor: int) -> int:
        if not self._matches:
            return -1
        for index, match in enumerate(self._matches):
            if anchor <= match.start:
                return index
        return 0

    def _activate_current_match(self) -> None:
        if not self._select_current_match(scroll=True):
            self._apply_highlights()
            self._emit_state()
            return
        self._apply_highlights()
        self._emit_state()

    def _select_current_match(self, *, scroll: bool) -> bool:
        editor = self._editor
        if editor is None or not (0 <= self._current_index < len(self._matches)):
            return False
        match = self._matches[self._current_index]
        cursor = editor.textCursor()
        cursor.setPosition(match.start)
        cursor.setPosition(match.end, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        if scroll:
            self._scroll_current_match_into_view()
        return True

    def _scroll_current_match_into_view(self) -> None:
        editor = self._editor
        if editor is None:
            return
        rect = editor.cursorRect(editor.textCursor())
        viewport = editor.viewport()
        viewport_height = viewport.height()
        if viewport_height <= 0:
            return
        desired_center = max(0, int(viewport_height / 2 - rect.height() / 2))
        delta = rect.top() - desired_center
        scrollbar = editor.verticalScrollBar()
        target = scrollbar.value() + delta
        target = max(scrollbar.minimum(), min(scrollbar.maximum(), target))
        smooth_scrollbar_to(scrollbar, target)

    def _apply_highlights(self) -> None:
        editor = self._editor
        if editor is None:
            return
        selections = []
        current_range = (
            self._matches[self._current_index]
            if 0 <= self._current_index < len(self._matches)
            else None
        )
        for match in self._matches:
            selection = _selection_type()()
            selection.cursor = QTextCursor(editor.document())
            selection.cursor.setPosition(match.start)
            selection.cursor.setPosition(match.end, QTextCursor.MoveMode.KeepAnchor)
            selection.format = QTextCharFormat()
            selection.format.setBackground(_CURRENT_BG if match == current_range else _MATCH_BG)
            selection.format.setForeground(_CURRENT_FG if match == current_range else _MATCH_FG)
            if match == current_range:
                selection.format.setFontUnderline(True)
                selection.format.setUnderlineColor(_CURRENT_BORDER)
            selections.append(selection)
        try:
            if hasattr(editor, "set_find_selections"):
                editor.set_find_selections(selections)
            else:
                editor.setExtraSelections(selections)
        except RuntimeError:
            return

    def _emit_state(self) -> None:
        total = len(self._matches)
        current = self._current_index + 1 if 0 <= self._current_index < total else 0
        self.state_changed.emit(current, total, total > 0)


class _FindShortcutFilter(QObject):
    """Shared key handling for in-editor find shortcuts."""

    def __init__(self, host: "EditorFindBar", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._host = host

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() != QEvent.Type.KeyPress:
            return False
        key_event = event if isinstance(event, QKeyEvent) else None
        if key_event is None:
            return False
        key = key_event.key()
        modifiers = key_event.modifiers()
        if key == Qt.Key.Key_F and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._host.open_and_focus()
            return True
        if key == Qt.Key.Key_Escape and self._host.isVisible():
            self._host.close_bar()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._host.isVisible():
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                self._host.go_previous()
            else:
                self._host.go_next()
            return True
        return False


class EditorFindBar(QFrame):
    """Compact warm-toned find bar shared by fragment/work editors."""

    locate_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorFindBar")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._editor: Optional[EditorWidget] = None
        self._controller = EditorFindController(self)
        self._controller.state_changed.connect(self._on_state_changed)
        self._shortcut_filter = _FindShortcutFilter(self, self)
        self._installed_widgets: list[QObject] = []

        self._input = QLineEdit()
        self._input.setObjectName("EditorFindInput")
        self._input.setPlaceholderText(TR("editor.find.placeholder"))
        self._input.textChanged.connect(self.set_query)
        self._input.installEventFilter(self._shortcut_filter)
        self.installEventFilter(self._shortcut_filter)

        self._count_label = QLabel(TR("editor.find.empty_count"))
        self._count_label.setObjectName("EditorFindCount")

        self._prev_btn = QPushButton(TR("editor.find.previous"))
        self._prev_btn.setObjectName("GhostButton")
        self._prev_btn.clicked.connect(self.go_previous)

        self._next_btn = QPushButton(TR("editor.find.next"))
        self._next_btn.setObjectName("GhostButton")
        self._next_btn.clicked.connect(self.go_next)

        self._close_btn = QPushButton(TR("editor.find.close"))
        self._close_btn.setObjectName("GhostButton")
        self._close_btn.clicked.connect(self.close_bar)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(self._input, 1)
        layout.addWidget(self._count_label)
        layout.addWidget(self._prev_btn)
        layout.addWidget(self._next_btn)
        layout.addWidget(self._close_btn)

        self.setVisible(False)

    def set_editor(self, widget: Optional[EditorWidget]) -> None:
        self._editor = widget
        self._controller.set_editor(widget)
        self._reinstall_shortcuts()
        if widget is None:
            self.close_bar(clear_query=True)

    def install_on(self, *widgets: QObject) -> None:
        self._installed_widgets = [w for w in widgets if w is not None]
        self._reinstall_shortcuts()

    def set_query(self, text: str) -> None:
        if self._input.text() != text:
            self._input.blockSignals(True)
            try:
                self._input.setText(text)
            finally:
                self._input.blockSignals(False)
        self._controller.set_query(text)

    def query(self) -> str:
        return self._input.text()

    def refresh_matches(self) -> None:
        self._controller.refresh_matches()

    def go_next(self) -> None:
        if not self._controller.go_next():
            self._flash_no_results()

    def go_previous(self) -> None:
        if not self._controller.go_previous():
            self._flash_no_results()

    def open_and_focus(self) -> None:
        self.setVisible(True)
        self.raise_()
        self._input.setFocus()
        self._input.selectAll()
        self.refresh_matches()

    def close_bar(self, *, clear_query: bool = False) -> None:
        self.setVisible(False)
        if clear_query:
            self._input.clear()
        else:
            self._controller.clear()
        if self._editor is not None:
            self._editor.setFocus()

    def clear_matches(self) -> None:
        self._controller.clear()

    def activate_excerpt(self, text: str) -> bool:
        excerpt = (text or "").strip()
        self.setVisible(True)
        self.set_query(excerpt)
        self._input.setFocus()
        if not excerpt:
            self._flash_no_results()
            return False
        found = self._controller.activate_first()
        if not found:
            self._flash_no_results()
        return found

    def _flash_no_results(self) -> None:
        self._count_label.setProperty("noResults", True)
        self.style().unpolish(self._count_label)
        self.style().polish(self._count_label)

    def _on_state_changed(self, current: int, total: int, has_results: bool) -> None:
        if not self.query():
            self._count_label.setText(TR("editor.find.empty_count"))
        elif total == 0:
            self._count_label.setText(TR("editor.find.no_results"))
        else:
            self._count_label.setText(
                TR("editor.find.count").format(current=current, total=total)
            )
        self._count_label.setProperty("noResults", bool(self.query()) and not has_results)
        self.style().unpolish(self._count_label)
        self.style().polish(self._count_label)

    def _reinstall_shortcuts(self) -> None:
        for widget in self._installed_widgets:
            try:
                widget.removeEventFilter(self._shortcut_filter)
            except RuntimeError:
                pass
        for widget in self._installed_widgets:
            widget.installEventFilter(self._shortcut_filter)
        if self._editor is not None:
            self._editor.installEventFilter(self._shortcut_filter)
        self._input.installEventFilter(self._shortcut_filter)
        self.installEventFilter(self._shortcut_filter)


class PaperTextEditMixin:
    """Shared paper-guide drawing and smooth page-step scrolling."""

    def _init_paper_behavior(self) -> None:
        self._soft_page_guides_enabled = True
        self._paper_margin_h = 36
        self._paper_margin_v = 28
        self._page_gap = 34
        self._reduced_motion = False

    def set_reduced_motion(self, enabled: bool) -> None:
        self._reduced_motion = bool(enabled)

    def set_soft_page_guides_enabled(self, enabled: bool) -> None:
        self._soft_page_guides_enabled = bool(enabled)
        self.viewport().update()

    def soft_page_guides_enabled(self) -> bool:
        return bool(self._soft_page_guides_enabled)

    def pageStepTarget(self, *, direction: int) -> int:  # noqa: N802
        scrollbar = self.verticalScrollBar()
        page_step = max(1, int(self.viewport().height() * 0.84))
        gap = int(self._page_gap * 0.7)
        delta = direction * (page_step - gap)
        target = scrollbar.value() + delta
        return max(scrollbar.minimum(), min(scrollbar.maximum(), target))

    def animatePageStep(self, *, direction: int) -> None:  # noqa: N802
        target = self.pageStepTarget(direction=direction)
        smooth_scrollbar_to(
            self.verticalScrollBar(),
            target,
            duration_ms=220,
            reduced=self._reduced_motion,
        )

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            return
        pixel_delta = event.pixelDelta().y()
        angle = event.angleDelta().y()
        if pixel_delta or angle:
            event.accept()
            scrollbar = self.verticalScrollBar()
            single_step = max(1, scrollbar.singleStep())
            if pixel_delta:
                # Trackpads report actual pixels. Keep the motion proportional
                # and restrained. QPlainTextEdit scrollbars are line-based,
                # while QTextEdit scrollbars are usually pixel-based.
                if single_step <= 3:
                    delta = -int(round(pixel_delta / max(1, self.fontMetrics().lineSpacing())))
                else:
                    delta = -pixel_delta
            else:
                steps = angle / 120.0
                delta = -int(round(steps * single_step * _WHEEL_LINES_PER_NOTCH))
            if delta == 0:
                delta = -1 if angle > 0 else 1
            target = scrollbar.value() + delta
            smooth_scrollbar_to(
                scrollbar,
                target,
                duration_ms=_WHEEL_ANIMATION_MS,
                reduced=self._reduced_motion,
            )
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_PageDown:
            event.accept()
            self.animatePageStep(direction=1)
            return
        if event.key() == Qt.Key.Key_PageUp:
            event.accept()
            self.animatePageStep(direction=-1)
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        cancel_scrollbar_animation(self.verticalScrollBar())
        super().focusOutEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        self._paint_soft_page_guides()

    def _paint_soft_page_guides(self) -> None:
        if not self._soft_page_guides_enabled:
            return
        document: QTextDocument = self.document()
        page_height = self._page_height_px()
        if page_height <= 0:
            return
        viewport_rect = self.viewport().rect()
        scrollbar_value = self.verticalScrollBar().value()
        paper_rect = viewport_rect.adjusted(20, 12, -20, -12)
        painter = QPainter(self.viewport())
        if not painter.isActive():
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor("#D8CCB7"))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        doc_height = max(document.size().height(), float(viewport_rect.height()))
        guide_top = 0
        while guide_top < doc_height + page_height:
            y = int(guide_top - scrollbar_value + self._paper_margin_v + page_height)
            if y >= viewport_rect.top() - 60 and y <= viewport_rect.bottom() + 60:
                left = paper_rect.left() + 20
                right = paper_rect.right() - 20
                if right > left:
                    painter.drawLine(left, y, right, y)
                dot_y = y + int(self._page_gap / 2)
                if dot_y < viewport_rect.bottom():
                    dot_radius = 2
                    center = QPoint(paper_rect.center().x(), dot_y)
                    painter.setBrush(QColor("#C9B796"))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(center, dot_radius, dot_radius)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QColor("#D8CCB7"))
            guide_top += page_height + self._page_gap

    def _page_height_px(self) -> int:
        metrics = self.fontMetrics()
        line_spacing = max(metrics.lineSpacing(), 1)
        return max(380, int(round(line_spacing * 26 + self._paper_margin_v * 2)))


class PaperPlainTextEdit(PaperTextEditMixin, QPlainTextEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_paper_behavior()


class PaperRichTextEdit(PaperTextEditMixin, QTextEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_paper_behavior()


class FindBarHost(QWidget):
    """Simple vertical host layout helper for find bar + editor content."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._find_bar = EditorFindBar(self)
        layout.addWidget(self._find_bar)
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        layout.addWidget(self._content_container, 1)

    @property
    def find_bar(self) -> EditorFindBar:
        return self._find_bar

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout
