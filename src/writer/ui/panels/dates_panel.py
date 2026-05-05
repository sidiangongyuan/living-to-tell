"""Dates / daily-writing view (M-Dates).

Top-level rail mode that lets the user navigate fragments by their
creation day (in the local timezone). Layout::

    [ Calendar | day entry list + actions ]

The calendar shows a small badge per day with the entry count and a
discreet dot when at least one fragment from that day has been curated
(any status other than ``unsorted``). Selecting a date refreshes the
right-hand list. Clicking a list row emits :pyattr:`entry_picked` so the
shell can switch to Fragments mode and load the entry into the editor.

This panel deliberately depends only on ``EntryRepository`` for reads —
the multi-select toolbar emits :pyattr:`append_tags_requested` and
:pyattr:`merge_requested` for the host shell to process via dialogs.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPalette, QTextCharFormat
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.models.entry import Entry
from writer.storage.repositories.entry_repository import (
    DailyStat,
    EntryRepository,
)
from writer.ui.i18n import TR


def _qdate_to_pydate(q: QDate) -> date:
    return date(q.year(), q.month(), q.day())


def _pydate_to_qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


class _DatesCalendar(QCalendarWidget):
    """A QCalendarWidget that paints per-day fragment counts."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DatesCalendar")
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._stats: Dict[date, DailyStat] = {}

    def set_stats(self, stats: Dict[date, DailyStat]) -> None:
        self._stats = stats
        # Force a repaint of all visible cells.
        self.updateCells()

    def paintCell(self, painter, rect, qdate):  # noqa: N802 — Qt override
        super().paintCell(painter, rect, qdate)
        try:
            d = _qdate_to_pydate(qdate)
        except ValueError:
            return
        stat = self._stats.get(d)
        if stat is None or stat.entry_count == 0:
            return
        # Draw a small count badge in the bottom-right corner. We use the
        # palette accent so light/dark themes both stay readable.
        painter.save()
        try:
            count_text = str(stat.entry_count)
            font = painter.font()
            font.setPointSizeF(max(7.5, font.pointSizeF() - 1.5))
            font.setBold(True)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            text_w = metrics.horizontalAdvance(count_text)
            text_h = metrics.height()
            pad_x = 4
            pad_y = 1
            badge_w = text_w + pad_x * 2
            badge_h = text_h + pad_y * 2
            x = rect.right() - badge_w - 2
            y = rect.bottom() - badge_h - 2
            accent = self.palette().color(QPalette.ColorRole.Highlight)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(x, y, badge_w, badge_h, 4, 4)
            text_color = self.palette().color(QPalette.ColorRole.HighlightedText)
            painter.setPen(text_color)
            painter.drawText(
                x + pad_x,
                y + pad_y + metrics.ascent(),
                count_text,
            )
            if stat.has_curated:
                # Tiny dot in the top-left.
                dot_r = 3
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(accent)
                painter.drawEllipse(rect.left() + 3, rect.top() + 3, dot_r * 2, dot_r * 2)
        finally:
            painter.restore()


class DatesPanel(QWidget):
    """Calendar + day-entry list with quick-create and batch actions."""

    entry_picked = Signal(str)  # entry_id
    new_today_requested = Signal()  # host should create + open
    append_tags_requested = Signal(list)  # list[str] entry_ids
    merge_requested = Signal(list)  # list[str] entry_ids

    def __init__(
        self,
        container: AppContainer,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DatesPanel")
        self._container = container
        self._repo: EntryRepository = container.entry_repository
        self._selected_date: date = date.today()

        # ---- Calendar (left) -----------------------------------------
        self._calendar = _DatesCalendar()
        self._calendar.setSelectedDate(_pydate_to_qdate(self._selected_date))

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(8, 8, 8, 8)
        left_l.addWidget(self._calendar)

        self._today_btn = QPushButton(TR("dates.go_today"))
        self._today_btn.setObjectName("DatesGoTodayBtn")
        left_l.addWidget(self._today_btn)
        left_l.addStretch(0)

        # ---- Day list (right) ----------------------------------------
        right = QWidget()
        right.setObjectName("DatesRight")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(12, 12, 12, 12)
        right_l.setSpacing(6)

        self._date_header = QLabel("")
        self._date_header.setObjectName("DatesHeader")
        right_l.addWidget(self._date_header)

        self._summary = QLabel("")
        self._summary.setObjectName("DatesSummary")
        right_l.addWidget(self._summary)

        self._entry_list = QListWidget()
        self._entry_list.setObjectName("DatesEntryList")
        self._entry_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        right_l.addWidget(self._entry_list, 1)

        actions = QHBoxLayout()
        self._new_btn = QPushButton(TR("dates.new_today_btn"))
        self._new_btn.setObjectName("DatesNewTodayBtn")
        self._tag_btn = QPushButton(TR("dates.append_tags_btn"))
        self._merge_btn = QPushButton(TR("dates.merge_btn"))
        actions.addWidget(self._new_btn)
        actions.addStretch(1)
        actions.addWidget(self._tag_btn)
        actions.addWidget(self._merge_btn)
        right_l.addLayout(actions)

        # ---- Splitter -----------------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 600])

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(splitter)

        # ---- Wiring --------------------------------------------------
        self._calendar.selectionChanged.connect(self._on_calendar_changed)
        self._calendar.currentPageChanged.connect(self._on_page_changed)
        self._today_btn.clicked.connect(self._on_go_today)
        self._new_btn.clicked.connect(self.new_today_requested.emit)
        self._tag_btn.clicked.connect(self._on_tag_clicked)
        self._merge_btn.clicked.connect(self._on_merge_clicked)
        self._entry_list.itemActivated.connect(self._on_item_activated)
        self._entry_list.itemDoubleClicked.connect(self._on_item_activated)
        self._entry_list.itemSelectionChanged.connect(self._update_buttons)

        self.refresh()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def selected_date(self) -> date:
        return self._selected_date

    def selected_entry_ids(self) -> List[str]:
        return [
            it.data(Qt.ItemDataRole.UserRole)
            for it in self._entry_list.selectedItems()
        ]

    def refresh(self, *, select_entry_id: Optional[str] = None) -> None:
        # Reload month stats based on whatever the calendar currently shows
        # so the calendar badges remain in sync.
        page_year = self._calendar.yearShown()
        page_month = self._calendar.monthShown()
        try:
            stats = self._repo.daily_stats_for_month(page_year, page_month)
        except Exception:  # noqa: BLE001 — UI must not crash on bad data
            stats = {}
        self._calendar.set_stats(stats)

        entries = self._repo.list_by_local_date(self._selected_date)
        self._entry_list.clear()
        for entry in entries:
            label = entry.title.strip() or TR("list.empty_fragment")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._entry_list.addItem(item)

        if select_entry_id is not None:
            for row in range(self._entry_list.count()):
                if self._entry_list.item(row).data(Qt.ItemDataRole.UserRole) == select_entry_id:
                    self._entry_list.setCurrentRow(row)
                    break

        # ---- Header / summary -----
        self._date_header.setText(self._selected_date.isoformat())
        stat = stats.get(self._selected_date)
        if stat is None or stat.entry_count == 0:
            self._summary.setText(TR("dates.empty_day"))
        else:
            count_str = (
                TR("dates.day_count_one")
                if stat.entry_count == 1
                else TR("dates.day_count_format").format(count=stat.entry_count)
            )
            words_str = TR("dates.day_words_format").format(words=stat.total_word_count)
            self._summary.setText(f"{count_str} · {words_str}")
        self._update_buttons()

    def refresh_today(self) -> None:
        """Public hook: jump to today and reload."""
        self._selected_date = date.today()
        self._calendar.setSelectedDate(_pydate_to_qdate(self._selected_date))
        self.refresh()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_calendar_changed(self) -> None:
        new_date = _qdate_to_pydate(self._calendar.selectedDate())
        if new_date != self._selected_date:
            self._selected_date = new_date
            self.refresh()

    def _on_page_changed(self, _year: int, _month: int) -> None:
        # Calendar paged to a different month — refresh its badge stats
        # without changing the selected date.
        try:
            stats = self._repo.daily_stats_for_month(_year, _month)
        except Exception:  # noqa: BLE001
            stats = {}
        self._calendar.set_stats(stats)

    def _on_go_today(self) -> None:
        self.refresh_today()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        if entry_id:
            self.entry_picked.emit(entry_id)

    def _on_tag_clicked(self) -> None:
        ids = self.selected_entry_ids()
        if ids:
            self.append_tags_requested.emit(ids)

    def _on_merge_clicked(self) -> None:
        ids = self.selected_entry_ids()
        if ids:
            self.merge_requested.emit(ids)

    def _update_buttons(self) -> None:
        has_sel = bool(self._entry_list.selectedItems())
        self._tag_btn.setEnabled(has_sel)
        self._merge_btn.setEnabled(has_sel)
