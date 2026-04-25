"""Debounced autosave for the active fragment.

Owns a single ``QTimer``. ``mark_dirty`` schedules a save; if more dirty
events arrive before the timer fires, the timer restarts. ``flush`` writes
immediately (used on entry switch and on close).
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from writer.storage.repositories.entry_repository import (
    EntryRepository,
    parse_tags,
)


# Snapshot is (entry_id, title, body, tags_text) — tags_text is the raw
# comma-separated string coming directly from the editor QLineEdit.
SnapshotProvider = Callable[[], Optional[tuple[str, str, str, str]]]


class AutosaveService(QObject):
    saved = Signal(str)
    # Emitted when the user has unsaved edits pending the debounce timer.
    # M7B: lets the UI show a "Unsaved changes" indicator.
    dirty = Signal()
    # Emitted right before a write hits the DB so the UI can show "Saving…".
    saving = Signal(str)

    def __init__(
        self,
        repository: EntryRepository,
        snapshot_provider: SnapshotProvider,
        *,
        debounce_ms: int = 800,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repository
        self._snapshot = snapshot_provider
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self.flush)
        self._last_saved: dict[str, tuple[str, str, str]] = {}

    def mark_dirty(self) -> None:
        self._timer.start()
        self.dirty.emit()

    def flush(self) -> None:
        snap = self._snapshot()
        if snap is None:
            return
        entry_id, title, body, tags_text = snap
        prev = self._last_saved.get(entry_id)
        if prev == (title, body, tags_text):
            return
        tags = parse_tags(tags_text)
        self.saving.emit(entry_id)
        if self._repo.update(entry_id, title=title, body=body, tags=tags) is not None:
            self._last_saved[entry_id] = (title, body, tags_text)
            self.saved.emit(entry_id)

    def remember_clean(
        self, entry_id: str, title: str, body: str, tags_text: str = ""
    ) -> None:
        self._last_saved[entry_id] = (title, body, tags_text)

    def stop(self) -> None:
        self._timer.stop()
