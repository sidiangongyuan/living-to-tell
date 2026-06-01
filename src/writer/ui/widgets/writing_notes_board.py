"""Floating sticky-note board for fragment-bound writing notes."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from writer.domain.models.entry_writing_note import (
    NOTE_STATUS_DONE,
    NOTE_STATUS_OPEN,
    EntryWritingNote,
)
from writer.ui.i18n import TR

NOTE_COLOR_KEYS = ("cream", "amber", "mist", "blue", "rose", "paper")
DEFAULT_NOTE_COLOR_KEY = "cream"
DEFAULT_NOTE_WIDTH = 248
MIN_NOTE_WIDTH = 220
MAX_NOTE_WIDTH = 340
BOARD_GRID = 8
BOARD_PADDING = 12
BOARD_COLUMN_GAP = 14
BOARD_ROW_GAP = 14
BOARD_MIN_WIDTH = 260
BOARD_MAX_WIDTH = 320
COLLAPSED_WIDTH = 104
COLLAPSED_HEIGHT = 42
NOTE_HEADER_HEIGHT = 28
NOTE_ACTIONS_HEIGHT = 30
NOTE_WALL_TOP_OFFSET = 88


class WritingNoteCard(QFrame):
    edit_requested = Signal(str, str)
    done_requested = Signal(str, bool)
    delete_requested = Signal(str)
    pin_requested = Signal(str, bool)
    layout_changed = Signal(str, int, int, int, str, int)

    def __init__(
        self,
        note: EntryWritingNote,
        *,
        display_font_family: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.note = note
        self._drag_start: Optional[QPoint] = None
        self._drag_origin: Optional[QPoint] = None
        self._drag_bounds = QRect(0, 0, 0, 0)
        self.setObjectName("WritingNoteSticky")
        self.setProperty("color", _color_key(note))
        self.setProperty("pinned", note.pinned)
        self.setProperty("done", note.status == NOTE_STATUS_DONE)
        note_size = _note_width(note)
        self.setFixedSize(note_size, note_size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(4)
        pin_btn = QPushButton("●" if note.pinned else "○")
        pin_btn.setObjectName("WritingNotePinButton")
        pin_btn.setFixedSize(24, 22)
        pin_btn.setToolTip(
            TR("editor.writing_notes.unpin" if note.pinned else "editor.writing_notes.pin")
        )
        pin_btn.clicked.connect(
            lambda _checked=False, note_id=note.id, pinned=note.pinned: (
                self.pin_requested.emit(note_id, not pinned)
            )
        )
        top.addWidget(pin_btn)
        state = QLabel(_state_text(note))
        state.setObjectName("WritingNoteState")
        top.addWidget(state, 1)
        menu_btn = QPushButton("⋯")
        menu_btn.setObjectName("WritingNoteMenuButton")
        menu_btn.setFixedSize(24, 22)
        menu_btn.clicked.connect(lambda _checked=False: self._open_menu(menu_btn))
        top.addWidget(menu_btn)
        layout.addLayout(top)

        self._body = QPlainTextEdit(note.body)
        self._body.setObjectName("WritingNoteBody")
        self._body.setReadOnly(True)
        self._body.setFrameShape(QFrame.Shape.NoFrame)
        self._body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._body.setToolTip(note.body)
        self._body.setPlainText(note.body)
        body_font = QFont()
        if display_font_family:
            body_font.setFamilies(_font_families(display_font_family))
        body_font.setPointSizeF(12.2)
        body_font.setStrikeOut(note.status == NOTE_STATUS_DONE)
        self._body.setFont(body_font)
        if note.status == NOTE_STATUS_DONE:
            self._body.setStyleSheet(
                f"color: {self.palette().color(QPalette.ColorRole.PlaceholderText).name()};"
            )
        layout.addWidget(self._body, 1)

        self._edit_input = QPlainTextEdit(note.body)
        self._edit_input.setObjectName("WritingNoteInput")
        self._edit_input.setVisible(False)
        self._edit_input.setFrameShape(QFrame.Shape.NoFrame)
        self._edit_input.setMinimumHeight(90)
        layout.addWidget(self._edit_input, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(4)
        done_btn = QPushButton("↺" if note.status == NOTE_STATUS_DONE else "✓")
        done_btn.setObjectName("WritingNoteDoneToggle")
        done_btn.setToolTip(
            TR("editor.writing_notes.restore_hint")
            if note.status == NOTE_STATUS_DONE
            else TR("editor.writing_notes.done_hint")
        )
        done_btn.clicked.connect(
            lambda _checked=False, note_id=note.id, done=note.status != NOTE_STATUS_DONE: (
                self.done_requested.emit(note_id, done)
            )
        )
        actions.addWidget(done_btn)
        edit_btn = QPushButton(TR("editor.writing_notes.edit"))
        edit_btn.setObjectName("WritingNoteMiniButton")
        edit_btn.clicked.connect(self._start_edit)
        actions.addWidget(edit_btn)
        save_btn = QPushButton(TR("editor.writing_notes.save"))
        save_btn.setObjectName("WritingNoteMiniButton")
        save_btn.setVisible(False)
        save_btn.clicked.connect(lambda _checked=False, note_id=note.id: self._commit_edit(note_id))
        actions.addWidget(save_btn)
        self._save_btn = save_btn
        actions.addStretch(1)
        layout.addLayout(actions)

    def set_drag_bounds(self, bounds: QRect) -> None:
        self._drag_bounds = bounds

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self.note.pinned:
            self._drag_start = event.globalPosition().toPoint()
            self._drag_origin = self.pos()
            self.raise_()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_start is None or self._drag_origin is None:
            super().mouseMoveEvent(event)
            return
        delta = event.globalPosition().toPoint() - self._drag_start
        self.move(self._bounded_position(self._drag_origin + delta))
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_start is not None:
            self._drag_start = None
            self._drag_origin = None
            pos = self._bounded_position(self.pos())
            self.move(pos)
            self.layout_changed.emit(
                self.note.id,
                pos.x(),
                pos.y(),
                self.width(),
                _color_key(self.note),
                max(_z_index(self.note), 0),
            )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _bounded_position(self, point: QPoint) -> QPoint:
        bounds = self._drag_bounds
        if bounds.isNull() or not bounds.isValid():
            bounds = self.parentWidget().rect() if self.parentWidget() else QRect(0, 0, 0, 0)
        max_x = max(BOARD_PADDING, bounds.right() - self.width())
        max_y = max(BOARD_PADDING, bounds.bottom() - self.height())
        return QPoint(
            min(max(point.x(), bounds.left()), max_x),
            min(max(point.y(), bounds.top()), max_y),
        )

    def _start_edit(self) -> None:
        self._body.setVisible(False)
        self._edit_input.setVisible(True)
        self._save_btn.setVisible(True)
        self._edit_input.setFocus()
        self._edit_input.selectAll()

    def _commit_edit(self, note_id: str) -> None:
        text = self._edit_input.toPlainText().strip()
        if not text:
            self._edit_input.setFocus()
            return
        self._body.setVisible(True)
        self._edit_input.setVisible(False)
        self._save_btn.setVisible(False)
        if text != self.note.body:
            self.edit_requested.emit(note_id, text)

    def _open_menu(self, button: QPushButton) -> None:
        menu = QMenu(self)
        menu.addAction(
            TR("editor.writing_notes.unpin" if self.note.pinned else "editor.writing_notes.pin"),
            lambda: self.pin_requested.emit(self.note.id, not self.note.pinned),
        )
        color_menu = menu.addMenu(TR("editor.writing_notes.color"))
        for color in NOTE_COLOR_KEYS:
            color_menu.addAction(
                TR(f"editor.writing_notes.color_{color}"),
                lambda checked=False, selected=color: self._set_color(selected),
            )
        width_menu = menu.addMenu(TR("editor.writing_notes.width"))
        for label_key, width in (
            ("editor.writing_notes.width_small", MIN_NOTE_WIDTH),
            ("editor.writing_notes.width_medium", DEFAULT_NOTE_WIDTH),
            ("editor.writing_notes.width_large", 310),
        ):
            width_menu.addAction(
                TR(label_key),
                lambda checked=False, selected=width: self._set_width(selected),
            )
        menu.addSeparator()
        menu.addAction(TR("editor.writing_notes.delete"), lambda: self.delete_requested.emit(self.note.id))
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _set_color(self, color_key: str) -> None:
        pos = self._current_layout_point()
        self.layout_changed.emit(
            self.note.id,
            pos.x(),
            pos.y(),
            self.width(),
            _normalize_color_key(color_key),
            max(_z_index(self.note), 0),
        )

    def _set_width(self, width: int) -> None:
        pos = self._current_layout_point()
        self.layout_changed.emit(
            self.note.id,
            pos.x(),
            pos.y(),
            max(MIN_NOTE_WIDTH, min(MAX_NOTE_WIDTH, int(width))),
            _color_key(self.note),
            max(_z_index(self.note), 0),
        )

    def _current_layout_point(self) -> QPoint:
        return self.pos()


class WritingNoteFloatingWindow(WritingNoteCard):
    """A sticky note as a small tool window tied to the Writer main window."""

    def __init__(
        self,
        note: EntryWritingNote,
        *,
        host_window: QWidget,
        display_font_family: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(note, display_font_family=display_font_family, parent=parent)
        self._host_window: QWidget = host_window
        self._relative_position = QPoint(0, 0)
        self._apply_tool_flags()

    def _apply_tool_flags(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def set_host_window(self, host_window: QWidget) -> None:
        self._host_window = host_window
        if self.parentWidget() is not host_window:
            self.setParent(host_window)
            self._apply_tool_flags()
        self.sync_to_host()

    def set_relative_position(self, x: int, y: int) -> None:
        self._relative_position = QPoint(int(x), int(y))
        self.sync_to_host()

    def relative_position(self) -> QPoint:
        return QPoint(self._relative_position)

    def sync_to_host(self) -> None:
        if self._host_window is None:
            return
        self.move(self._host_origin() + self._relative_position)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self.note.pinned:
            self._drag_start = event.globalPosition().toPoint()
            self._drag_origin = self.pos()
            self.raise_()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_start is None or self._drag_origin is None:
            super().mouseMoveEvent(event)
            return
        delta = event.globalPosition().toPoint() - self._drag_start
        self.move(self._drag_origin + delta)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_start is not None:
            self._drag_start = None
            self._drag_origin = None
            self._relative_position = self.pos() - self._host_origin()
            self.layout_changed.emit(
                self.note.id,
                self._relative_position.x(),
                self._relative_position.y(),
                self.width(),
                _color_key(self.note),
                max(_z_index(self.note), 0),
            )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _bounded_position(self, point: QPoint) -> QPoint:
        return point

    def _current_layout_point(self) -> QPoint:
        return self.relative_position()

    def _host_origin(self) -> QPoint:
        host = self._host_window.window() if self._host_window is not None else None
        if host is None:
            return QPoint(0, 0)
        return host.frameGeometry().topLeft()


class WritingNotesBoard(QFrame):
    add_requested = Signal(str)
    edit_requested = Signal(str, str)
    done_requested = Signal(str, bool)
    delete_requested = Signal(str)
    pin_requested = Signal(str, bool)
    layout_changed = Signal(str, int, int, int, str, int)
    continue_requested = Signal()
    collapsed_changed = Signal(bool)
    show_done_changed = Signal(bool)

    def __init__(
        self,
        *,
        note_layer: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("WritingNotesBoard")
        self.setMinimumWidth(BOARD_MIN_WIDTH)
        self.setMaximumWidth(BOARD_MAX_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._notes: list[EntryWritingNote] = []
        self._cards: dict[str, WritingNoteFloatingWindow] = {}
        self._entry_id: Optional[str] = None
        self._show_done = True
        self._collapsed = False
        self._active = True
        self._display_font_family = ""
        self._note_layer = note_layer
        self._host_window: Optional[QWidget] = None
        self._drag_bounds = QRect()

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._collapsed_button = QPushButton(TR("editor.writing_notes.tab"))
        self._collapsed_button.setObjectName("WritingNotesCollapsedTab")
        self._collapsed_button.clicked.connect(self.toggle_collapsed)
        root.addWidget(self._collapsed_button)

        self._content = QWidget()
        content = QVBoxLayout(self._content)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel(TR("editor.writing_notes.title"))
        self._title.setObjectName("WritingNotesTitle")
        header.addWidget(self._title)
        self._count = QLabel("")
        self._count.setObjectName("WritingNotesCount")
        header.addWidget(self._count)
        header.addStretch(1)
        self._collapse_btn = QPushButton(TR("editor.writing_notes.collapse"))
        self._collapse_btn.setObjectName("GhostButton")
        self._collapse_btn.clicked.connect(self.toggle_collapsed)
        header.addWidget(self._collapse_btn)
        content.addLayout(header)

        add_row = QHBoxLayout()
        add_row.setContentsMargins(0, 0, 0, 0)
        self._input = QLineEdit()
        self._input.setObjectName("WritingNoteInput")
        self._input.setPlaceholderText(TR("editor.writing_notes.placeholder"))
        self._input.returnPressed.connect(self._on_add)
        add_row.addWidget(self._input, 1)
        self._add_btn = QPushButton(TR("editor.writing_notes.add"))
        self._add_btn.setObjectName("PrimaryButton")
        self._add_btn.clicked.connect(self._on_add)
        add_row.addWidget(self._add_btn)
        content.addLayout(add_row)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        self._arrange_btn = QPushButton(TR("editor.writing_notes.arrange"))
        self._arrange_btn.setObjectName("GhostButton")
        self._arrange_btn.clicked.connect(self.arrange_notes)
        action_row.addWidget(self._arrange_btn)
        self._done_toggle_btn = QPushButton(TR("editor.writing_notes.hide_done"))
        self._done_toggle_btn.setObjectName("GhostButton")
        self._done_toggle_btn.clicked.connect(self.toggle_done)
        action_row.addWidget(self._done_toggle_btn)
        action_row.addStretch(1)
        self._continue_btn = QPushButton(TR("editor.writing_notes.use_for_continue"))
        self._continue_btn.setObjectName("PrimaryButton")
        self._continue_btn.clicked.connect(self.continue_requested.emit)
        action_row.addWidget(self._continue_btn)
        content.addLayout(action_row)

        self._empty = QLabel(TR("editor.writing_notes.empty_board"))
        self._empty.setObjectName("WritingNotesHint")
        self._empty.setWordWrap(True)
        content.addWidget(self._empty)

        root.addWidget(self._content, 1)
        self._refresh_visibility()

    def set_note_layer(self, layer: QWidget) -> None:
        self._note_layer = layer
        self._host_window = layer.window()
        for card in self._cards.values():
            card.set_host_window(self._host_window)
        self._sync_card_bounds()

    def set_display_font_family(self, family: str) -> None:
        self._display_font_family = family
        self._rebuild_cards(force=True)

    def set_notes(self, notes: list[EntryWritingNote]) -> None:
        self._notes = list(notes)
        self._rebuild_cards()

    def set_entry_id(self, entry_id: Optional[str]) -> None:
        self._entry_id = entry_id
        self.setVisible(entry_id is not None and self._active)
        if entry_id is None:
            self._input.clear()
            self._notes = []
            self._rebuild_cards()

    def set_active(self, active: bool) -> None:
        self._active = bool(active)
        self.setVisible(bool(self._entry_id) and self._active)
        self._sync_card_visibility()

    def set_drag_bounds(self, bounds: QRect) -> None:
        self._drag_bounds = bounds
        self._sync_card_bounds()

    def sync_floating_windows(self) -> None:
        for card in self._cards.values():
            card.sync_to_host()

    def focus_input(self) -> None:
        self.set_collapsed(False, emit_signal=True)
        self._input.setFocus()

    def set_collapsed(self, collapsed: bool, *, emit_signal: bool = False) -> None:
        collapsed = bool(collapsed)
        changed = self._collapsed != collapsed
        self._collapsed = collapsed
        self._refresh_visibility()
        self._sync_card_visibility()
        if changed and emit_signal:
            self.collapsed_changed.emit(self._collapsed)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed, emit_signal=True)

    def set_show_done(self, show_done: bool, *, emit_signal: bool = False) -> None:
        show_done = bool(show_done)
        changed = self._show_done != show_done
        self._show_done = show_done
        self._rebuild_cards()
        if changed and emit_signal:
            self.show_done_changed.emit(self._show_done)

    def show_done(self) -> bool:
        return self._show_done

    def toggle_done(self) -> None:
        self.set_show_done(not self._show_done, emit_signal=True)

    def arrange_notes(self) -> None:
        visible = sorted(
            (note for note in self._visible_notes() if not note.pinned),
            key=_arrange_sort_key,
        )
        if not visible:
            return
        x, y, direction, vertical_limit = self._wall_start(visible)
        for note in visible:
            note_width = _note_width(note)
            if y + note_width > vertical_limit:
                y = NOTE_WALL_TOP_OFFSET
                x += direction * (note_width + BOARD_COLUMN_GAP)
            self.layout_changed.emit(
                note.id,
                x,
                y,
                note_width,
                _color_key(note),
                _z_index(note),
            )
            y += note_width + BOARD_ROW_GAP

    def _on_add(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_requested.emit(text)

    def _visible_notes(self) -> list[EntryWritingNote]:
        return [
            note
            for note in self._notes
            if note.status == NOTE_STATUS_OPEN or self._show_done
        ]

    def _rebuild_cards(self, *, force: bool = False) -> None:
        parent = self._host_parent()
        if parent is None:
            self._clear_cards()
            self._refresh_visibility()
            return
        visible_notes = self._visible_notes()
        visible_ids = {note.id for note in visible_notes}
        for note_id in list(self._cards):
            if note_id not in visible_ids or force:
                self._remove_card(note_id)
        for index, note in enumerate(visible_notes):
            existing = self._cards.get(note.id)
            if existing is not None and existing.note != note:
                self._remove_card(note.id)
                existing = None
            if existing is None:
                x, y = self._note_position(note, index, visible_notes)
                card = WritingNoteFloatingWindow(
                    note,
                    host_window=parent,
                    display_font_family=self._display_font_family,
                    parent=parent,
                )
                card.set_relative_position(x, y)
                card.edit_requested.connect(self.edit_requested)
                card.done_requested.connect(self.done_requested)
                card.delete_requested.connect(self.delete_requested)
                card.pin_requested.connect(self.pin_requested)
                card.layout_changed.connect(self.layout_changed)
                self._cards[note.id] = card
            else:
                x, y = self._note_position(note, index, visible_notes)
                existing.set_relative_position(x, y)
                existing.set_host_window(parent)
            card = self._cards[note.id]
            card.set_drag_bounds(QRect())
            card.raise_()
        self._sync_card_visibility()
        self._refresh_visibility()

    def _clear_cards(self) -> None:
        for note_id in list(self._cards):
            self._remove_card(note_id)

    def _remove_card(self, note_id: str) -> None:
        card = self._cards.pop(note_id, None)
        if card is None:
            return
        card.hide()
        card.deleteLater()

    def _host_parent(self) -> Optional[QWidget]:
        if self._host_window is not None:
            return self._host_window.window()
        if self._note_layer is not None:
            return self._note_layer.window()
        parent = self.window()
        return parent if parent is not None else None

    def _sync_card_bounds(self) -> None:
        for card in self._cards.values():
            card.set_drag_bounds(QRect())
            card.sync_to_host()

    def _sync_card_visibility(self) -> None:
        visible = bool(self._entry_id) and self._active and not self._collapsed
        for card in self._cards.values():
            card.setVisible(visible)
            if visible:
                card.sync_to_host()
                card.raise_()
        if visible:
            self.raise_()

    def _effective_bounds(self) -> QRect:
        parent = self._note_layer
        host = self._host_parent()
        if parent is None or host is None:
            if self._drag_bounds.isValid() and not self._drag_bounds.isNull():
                return self._drag_bounds
            return QRect(BOARD_PADDING, BOARD_PADDING, 640, 420)
        top_left = parent.mapToGlobal(parent.rect().topLeft()) - host.frameGeometry().topLeft()
        return QRect(top_left, parent.size()).adjusted(
            BOARD_PADDING,
            BOARD_PADDING,
            -BOARD_PADDING,
            -BOARD_PADDING,
        )

    def _wall_start(self, notes: list[EntryWritingNote]) -> tuple[int, int, int, int]:
        host = self._host_parent()
        widest = max((_note_width(note) for note in notes), default=DEFAULT_NOTE_WIDTH)
        if host is None:
            return BOARD_PADDING, NOTE_WALL_TOP_OFFSET, 1, 720
        frame = host.frameGeometry()
        screen = host.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else frame
        right_space = available.right() - frame.right()
        left_space = frame.left() - available.left()
        if right_space >= widest + BOARD_COLUMN_GAP:
            x = frame.width() + BOARD_COLUMN_GAP
            direction = 1
        elif left_space >= widest + BOARD_COLUMN_GAP:
            x = -widest - BOARD_COLUMN_GAP
            direction = -1
        else:
            bounds = self._effective_bounds()
            x = max(BOARD_PADDING, min(bounds.left(), frame.width() - widest - BOARD_PADDING))
            direction = 1
        vertical_limit = max(
            NOTE_WALL_TOP_OFFSET + widest,
            min(available.bottom() - frame.top() - BOARD_PADDING, frame.height() - BOARD_PADDING),
        )
        return x, NOTE_WALL_TOP_OFFSET, direction, vertical_limit

    def _note_position(
        self,
        note: EntryWritingNote,
        index: int,
        visible_notes: list[EntryWritingNote],
    ) -> tuple[int, int]:
        stored = _stored_note_position(note)
        if stored is not None:
            return stored
        x, y, direction, vertical_limit = self._wall_start(visible_notes)
        for previous in visible_notes[:index]:
            previous_width = _note_width(previous)
            if y + previous_width > vertical_limit:
                y = NOTE_WALL_TOP_OFFSET
                x += direction * (previous_width + BOARD_COLUMN_GAP)
            y += previous_width + BOARD_ROW_GAP
        width = _note_width(note)
        if y + width > vertical_limit:
            y = NOTE_WALL_TOP_OFFSET
            x += direction * (width + BOARD_COLUMN_GAP)
        return x, y

    def _refresh_visibility(self) -> None:
        if self._collapsed:
            self.setFixedSize(COLLAPSED_WIDTH, COLLAPSED_HEIGHT)
        else:
            self.setMinimumWidth(BOARD_MIN_WIDTH)
            self.setMaximumWidth(BOARD_MAX_WIDTH)
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.adjustSize()
        self._content.setVisible(not self._collapsed)
        self._collapsed_button.setVisible(self._collapsed)
        open_count = sum(1 for note in self._notes if note.status == NOTE_STATUS_OPEN)
        done_count = sum(1 for note in self._notes if note.status == NOTE_STATUS_DONE)
        self._collapsed_button.setText(
            f"{TR('editor.writing_notes.tab')} · {open_count}"
            if open_count
            else TR("editor.writing_notes.tab")
        )
        self._count.setText(TR("editor.writing_notes.count").format(count=open_count))
        self._done_toggle_btn.setVisible(done_count > 0)
        self._done_toggle_btn.setText(
            TR("editor.writing_notes.hide_done" if self._show_done else "editor.writing_notes.show_done").format(
                count=done_count
            )
        )
        self._continue_btn.setVisible(open_count > 0)
        self._empty.setVisible(open_count == 0 and done_count == 0)


def _state_text(note: EntryWritingNote) -> str:
    if note.status == NOTE_STATUS_DONE:
        return TR("editor.writing_notes.state_done")
    if note.pinned:
        return TR("editor.writing_notes.state_pinned")
    return TR("editor.writing_notes.state_open")


def _font_families(value: str) -> list[str]:
    families = [part.strip() for part in (value or "").split(",") if part.strip()]
    return families or ["Georgia", "Cambria"]


def _normalize_color_key(value: object) -> str:
    key = str(value or "").strip().lower()
    return key if key in NOTE_COLOR_KEYS else DEFAULT_NOTE_COLOR_KEY


def _color_key(note: EntryWritingNote) -> str:
    return _normalize_color_key(getattr(note, "color_key", DEFAULT_NOTE_COLOR_KEY))


def _note_width(note: EntryWritingNote) -> int:
    return max(
        MIN_NOTE_WIDTH,
        min(MAX_NOTE_WIDTH, int(getattr(note, "board_width", DEFAULT_NOTE_WIDTH) or DEFAULT_NOTE_WIDTH)),
    )


def _z_index(note: EntryWritingNote) -> int:
    return int(getattr(note, "z_index", 0) or 0)


def _arrange_sort_key(note: EntryWritingNote) -> tuple[int, int, str, str]:
    return (
        1 if note.status == NOTE_STATUS_DONE else 0,
        int(getattr(note, "sort_order", 0) or 0),
        str(getattr(note, "created_at", "") or ""),
        note.id,
    )


def _stored_note_position(note: EntryWritingNote) -> Optional[tuple[int, int]]:
    x = getattr(note, "board_x", None)
    y = getattr(note, "board_y", None)
    if x is not None and y is not None:
        try:
            return int(x), int(y)
        except (TypeError, ValueError):
            return None
    return None


def _note_position(note: EntryWritingNote, index: int, bounds: QRect) -> tuple[int, int]:
    stored = _stored_note_position(note)
    if stored is not None:
        return stored
    note_width = _note_width(note)
    columns = max(1, max(note_width, bounds.width()) // (note_width + BOARD_COLUMN_GAP))
    column = index % columns
    row = index // columns
    return _bounded_point(
        QPoint(
            bounds.right() - note_width - column * (note_width + BOARD_COLUMN_GAP),
            bounds.top() + row * (note_width + BOARD_ROW_GAP),
        ),
        bounds,
        note_width,
    )


def _bounded_point(point: QPoint, bounds: QRect, width: int) -> tuple[int, int]:
    return (
        min(max(point.x(), bounds.left()), max(bounds.left(), bounds.right() - width)),
        min(max(point.y(), bounds.top()), max(bounds.top(), bounds.bottom() - width)),
    )
