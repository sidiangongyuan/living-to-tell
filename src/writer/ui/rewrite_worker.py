"""QThread worker that runs a single AI rewrite call off the UI thread.

Keeps Qt from freezing while the OpenAI SDK call is in flight. The worker
emits exactly one of :attr:`succeeded` or :attr:`failed` and then finishes.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal

from writer.services.ai.interfaces import (
    AiError,
    RewriteRequest,
    RewriteResponse,
)
from writer.services.ai.rewrite_service import RewriteService


class RewriteWorker(QThread):
    succeeded = Signal(object)  # RewriteResponse
    failed = Signal(str)

    def __init__(
        self,
        rewrite_service: RewriteService,
        request: RewriteRequest,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = rewrite_service
        self._request = request
        self._response: Optional[RewriteResponse] = None

    def run(self) -> None:  # noqa: D401 — Qt slot
        if self.isInterruptionRequested():
            return
        try:
            response = self._service.generate(self._request)
        except AiError as exc:
            if self.isInterruptionRequested():
                return
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            if self.isInterruptionRequested():
                return
            self.failed.emit(f"Unexpected error: {exc}")
            return
        if self.isInterruptionRequested():
            # User cancelled while the provider call was in flight; drop the
            # result so the UI never sees a stale success after cancel.
            return
        self._response = response
        self.succeeded.emit(response)
