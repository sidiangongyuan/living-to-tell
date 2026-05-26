"""Shared in-editor find bar and paper-like editor helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QTextCharFormat, QTextCursor
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


class EditorPageControls(QFrame):
    """Small page navigation strip for soft-page editor browsing."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorPageControls")
        self._editor: Optional[EditorWidget] = None
        self._pending_refresh = False

        self._prev_btn = QPushButton(TR("editor.page.previous"))
        self._prev_btn.setObjectName("EditorPageButton")
        self._prev_btn.clicked.connect(self.previous_page)

        self._page_label = QLabel(TR("editor.page.count").format(current=1, total=1))
        self._page_label.setObjectName("EditorPageLabel")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._next_btn = QPushButton(TR("editor.page.next"))
        self._next_btn.setObjectName("EditorPageButton")
        self._next_btn.clicked.connect(self.next_page)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)
        layout.addStretch(1)
        layout.addWidget(self._prev_btn)
        layout.addWidget(self._page_label)
        layout.addWidget(self._next_btn)
        layout.addStretch(1)

    def set_editor(self, widget: Optional[EditorWidget]) -> None:
        if self._editor is widget:
            self.refresh()
            return
        if self._editor is not None:
            scrollbar = self._editor.verticalScrollBar()
            try:
                scrollbar.valueChanged.disconnect(self.refresh)
                scrollbar.rangeChanged.disconnect(self.schedule_refresh)
                self._editor.textChanged.disconnect(self.schedule_refresh)
            except (RuntimeError, TypeError):
                pass
        self._editor = widget
        if widget is not None:
            scrollbar = widget.verticalScrollBar()
            scrollbar.valueChanged.connect(self.refresh)
            scrollbar.rangeChanged.connect(self.schedule_refresh)
            widget.textChanged.connect(self.schedule_refresh)
        self.schedule_refresh()

    def previous_page(self) -> None:
        if self._editor is not None and hasattr(self._editor, "previous_soft_page"):
            self._editor.previous_soft_page()
            self.schedule_refresh()

    def next_page(self) -> None:
        if self._editor is not None and hasattr(self._editor, "next_soft_page"):
            self._editor.next_soft_page()
            self.schedule_refresh()

    def schedule_refresh(self, *_args) -> None:
        if self._pending_refresh:
            return
        self._pending_refresh = True
        QTimer.singleShot(0, self._refresh_later)

    def _refresh_later(self) -> None:
        self._pending_refresh = False
        self.refresh()

    def refresh(self, *_args) -> None:
        editor = self._editor
        enabled = bool(
            editor is not None
            and hasattr(editor, "soft_page_guides_enabled")
            and editor.soft_page_guides_enabled()
        )
        self.setVisible(enabled)
        if not enabled or editor is None:
            return
        total = editor.soft_page_count() if hasattr(editor, "soft_page_count") else 1
        current = editor.current_soft_page() if hasattr(editor, "current_soft_page") else 1
        self._page_label.setText(
            TR("editor.page.count").format(current=current, total=total)
        )
        self._prev_btn.setEnabled(current > 1)
        self._next_btn.setEnabled(current < total)


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

    def set_paper_layout(self, page_vertical_padding: int, page_gap: int) -> None:
        self._paper_margin_v = max(12, min(96, int(page_vertical_padding)))
        self._page_gap = max(0, min(96, int(page_gap)))
        self.viewport().update()

    def _soft_page_step(self) -> int:
        scrollbar = self.verticalScrollBar()
        page_step = int(scrollbar.pageStep())
        if page_step <= 1:
            return max(1, int(self.viewport().height() * 0.82))
        return max(1, int(page_step * 0.92))

    def _soft_page_positions(self) -> list[int]:
        scrollbar = self.verticalScrollBar()
        minimum = int(scrollbar.minimum())
        maximum = int(scrollbar.maximum())
        step = self._soft_page_step()
        positions = [minimum]
        current = minimum
        while current < maximum:
            next_position = min(maximum, current + step)
            if next_position <= current:
                break
            positions.append(next_position)
            current = next_position
        return positions

    def soft_page_count(self) -> int:
        return len(self._soft_page_positions())

    def current_soft_page(self) -> int:
        scrollbar = self.verticalScrollBar()
        value = int(scrollbar.value())
        current = 1
        for index, position in enumerate(self._soft_page_positions(), start=1):
            if value < position:
                break
            current = index
        return current

    def go_to_soft_page(self, page_index: int) -> None:
        scrollbar = self.verticalScrollBar()
        positions = self._soft_page_positions()
        requested_page = max(1, min(len(positions), int(page_index)))
        target = positions[requested_page - 1]
        if target == int(scrollbar.value()):
            return
        smooth_scrollbar_to(
            scrollbar,
            target,
            duration_ms=120,
            reduced=self._reduced_motion,
        )

    def next_soft_page(self) -> None:
        self.go_to_soft_page(self.current_soft_page() + 1)

    def previous_soft_page(self) -> None:
        self.go_to_soft_page(self.current_soft_page() - 1)

    def pageStepTarget(self, *, direction: int) -> int:  # noqa: N802
        scrollbar = self.verticalScrollBar()
        delta = direction * self._soft_page_step()
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
        # Deliberately do not draw page guides inside the text viewport.
        # In-body lines can overlap wrapped text and opening epigraphs; paging
        # is represented by the external EditorPageControls instead.

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
