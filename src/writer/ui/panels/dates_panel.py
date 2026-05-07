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

import hashlib
from datetime import date
from typing import Dict, Iterable, List, Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.models.reference_passage import ReferencePassage, USAGE_KIND_QUOTE
from writer.storage.repositories.entry_repository import (
    DailyStat,
    EntryRepository,
)
from writer.storage.repositories.reference_repository import ReferenceRepository
from writer.ui.i18n import TR


DAILY_QUOTE_MIN_LENGTH = 10
DAILY_QUOTE_MAX_LENGTH = 160
DAILY_QUOTE_PREVIEW_LIMIT = 96


def _quote_text(content: str) -> str:
    return " ".join(line.strip() for line in content.splitlines() if line.strip()).strip()


def eligible_daily_quotes(
    passages: Iterable[ReferencePassage],
) -> list[ReferencePassage]:
    candidates = []
    for passage in passages:
        text = _quote_text(passage.content)
        if DAILY_QUOTE_MIN_LENGTH <= len(text) <= DAILY_QUOTE_MAX_LENGTH:
            candidates.append(passage)
    return sorted(
        candidates,
        key=lambda passage: (
            (passage.source_title or "").casefold(),
            (passage.source_author or "").casefold(),
            _quote_text(passage.content).casefold(),
            passage.id,
        ),
    )


def choose_default_daily_quote(
    passages: Iterable[ReferencePassage], selected_day: date
) -> Optional[ReferencePassage]:
    candidates = eligible_daily_quotes(passages)
    if not candidates:
        return None
    seed = int(
        hashlib.sha256(selected_day.isoformat().encode("utf-8")).hexdigest()[:16],
        16,
    )
    return candidates[seed % len(candidates)]


def format_daily_quote_preview(content: str, *, limit: int = DAILY_QUOTE_PREVIEW_LIMIT) -> str:
    text = _quote_text(content)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


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
    manage_quotes_requested = Signal()

    def __init__(
        self,
        container: AppContainer,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DatesPanel")
        self._container = container
        self._repo: EntryRepository = container.entry_repository
        self._reference_repo: ReferenceRepository = container.reference_repository
        self._selected_date: date = date.today()
        self._temporary_daily_quote_id: Optional[str] = None
        self._displayed_daily_quote_id: Optional[str] = None

        self._quote_card = QFrame()
        self._quote_card.setObjectName("DailyQuoteCard")
        self._quote_card.setMaximumWidth(780)

        quote_header = QHBoxLayout()
        quote_header.setContentsMargins(0, 0, 0, 0)
        quote_header.addWidget(QLabel(TR("dates.daily_quote_title")))
        quote_header.addStretch(1)

        self._replace_quote_btn = QPushButton(TR("dates.daily_quote_replace"))
        self._replace_quote_btn.setObjectName("GhostButton")
        self._manage_quotes_btn = QPushButton(TR("dates.daily_quote_manage"))
        self._manage_quotes_btn.setObjectName("GhostButton")
        self._copy_quote_btn = QPushButton(TR("dates.daily_quote_copy"))
        self._copy_quote_btn.setObjectName("GhostButton")
        quote_header.addWidget(self._replace_quote_btn)
        quote_header.addWidget(self._manage_quotes_btn)
        quote_header.addWidget(self._copy_quote_btn)

        self._quote_stack = QStackedWidget()

        quote_content = QWidget()
        quote_content_layout = QVBoxLayout(quote_content)
        quote_content_layout.setContentsMargins(0, 0, 0, 0)
        quote_content_layout.setSpacing(8)
        self._quote_body = QLabel("")
        self._quote_body.setObjectName("DailyQuoteBody")
        self._quote_body.setWordWrap(True)
        self._quote_meta = QLabel("")
        self._quote_meta.setObjectName("DailyQuoteMeta")
        self._quote_meta.setWordWrap(True)
        quote_content_layout.addWidget(self._quote_body)
        quote_content_layout.addWidget(self._quote_meta)

        quote_empty = QWidget()
        quote_empty_layout = QVBoxLayout(quote_empty)
        quote_empty_layout.setContentsMargins(0, 0, 0, 0)
        quote_empty_layout.setSpacing(6)
        self._quote_empty_title = QLabel(TR("dates.daily_quote_empty_title"))
        self._quote_empty_title.setObjectName("DailyQuoteEmptyTitle")
        self._quote_empty_desc = QLabel(TR("dates.daily_quote_empty_desc"))
        self._quote_empty_desc.setObjectName("DailyQuoteEmptyDesc")
        self._quote_empty_desc.setWordWrap(True)
        quote_empty_layout.addWidget(self._quote_empty_title)
        quote_empty_layout.addWidget(self._quote_empty_desc)

        self._quote_stack.addWidget(quote_content)
        self._quote_stack.addWidget(quote_empty)

        quote_layout = QVBoxLayout(self._quote_card)
        quote_layout.setContentsMargins(16, 14, 16, 14)
        quote_layout.setSpacing(10)
        quote_layout.addLayout(quote_header)
        quote_layout.addWidget(self._quote_stack)

        quote_wrap = QWidget()
        quote_wrap_layout = QHBoxLayout(quote_wrap)
        quote_wrap_layout.setContentsMargins(12, 12, 12, 0)
        quote_wrap_layout.setSpacing(0)
        quote_wrap_layout.addWidget(self._quote_card, 0)
        quote_wrap_layout.addStretch(1)

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

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(quote_wrap)
        root.addWidget(splitter, 1)

        # ---- Wiring --------------------------------------------------
        self._calendar.selectionChanged.connect(self._on_calendar_changed)
        self._calendar.currentPageChanged.connect(self._on_page_changed)
        self._today_btn.clicked.connect(self._on_go_today)
        self._new_btn.clicked.connect(self.new_today_requested.emit)
        self._tag_btn.clicked.connect(self._on_tag_clicked)
        self._merge_btn.clicked.connect(self._on_merge_clicked)
        self._replace_quote_btn.clicked.connect(self._on_replace_daily_quote)
        self._manage_quotes_btn.clicked.connect(self.manage_quotes_requested.emit)
        self._copy_quote_btn.clicked.connect(self._on_copy_daily_quote)
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
        self.refresh_daily_quote()
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

    def refresh_daily_quote(self) -> None:
        quotes = eligible_daily_quotes(
            self._reference_repo.list_recent(usage_kind=USAGE_KIND_QUOTE, limit=500)
        )
        if not quotes:
            self._displayed_daily_quote_id = None
            self._temporary_daily_quote_id = None
            self._quote_stack.setCurrentIndex(1)
            self._replace_quote_btn.setEnabled(False)
            self._copy_quote_btn.setEnabled(False)
            self._quote_body.clear()
            self._quote_meta.clear()
            return

        default_quote = choose_default_daily_quote(quotes, date.today())
        selected_quote = default_quote
        if self._temporary_daily_quote_id is not None:
            selected_quote = next(
                (quote for quote in quotes if quote.id == self._temporary_daily_quote_id),
                default_quote,
            )
        if selected_quote is None:
            self._quote_stack.setCurrentIndex(1)
            self._replace_quote_btn.setEnabled(False)
            self._copy_quote_btn.setEnabled(False)
            return

        self._displayed_daily_quote_id = selected_quote.id
        self._quote_stack.setCurrentIndex(0)
        self._quote_body.setText(format_daily_quote_preview(selected_quote.content))
        self._quote_body.setToolTip(_quote_text(selected_quote.content))
        meta_parts = [selected_quote.source_title.strip() or TR("context.no_value")]
        if selected_quote.source_author.strip():
            meta_parts.append(selected_quote.source_author.strip())
        if selected_quote.tags.strip():
            meta_parts.append(selected_quote.tags.strip())
        self._quote_meta.setText(" · ".join(meta_parts))
        self._quote_meta.setToolTip(self._quote_meta.text())
        self._replace_quote_btn.setEnabled(len(quotes) > 1)
        self._copy_quote_btn.setEnabled(True)

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

    def _on_replace_daily_quote(self) -> None:
        quotes = eligible_daily_quotes(
            self._reference_repo.list_recent(usage_kind=USAGE_KIND_QUOTE, limit=500)
        )
        if len(quotes) < 2:
            return
        current_id = self._displayed_daily_quote_id
        current_index = next(
            (index for index, quote in enumerate(quotes) if quote.id == current_id),
            -1,
        )
        next_quote = quotes[(current_index + 1) % len(quotes)]
        self._temporary_daily_quote_id = next_quote.id
        self.refresh_daily_quote()

    def _on_copy_daily_quote(self) -> None:
        if not self._displayed_daily_quote_id:
            return
        quote = self._reference_repo.get(self._displayed_daily_quote_id)
        if quote is None:
            return
        QApplication.clipboard().setText(_quote_text(quote.content))

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
