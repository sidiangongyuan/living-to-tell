"""QThread workers for the M10A AI workspace.

Run task / chat calls off the UI thread; emit either ``succeeded`` or
``failed`` and finish.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal

from writer.services.ai.interfaces import AiError
from writer.services.ai.task_service import AiTaskService
from writer.services.ai.task_types import AiTaskRequest, AiTaskResponse
from writer.services.ai.thread_service import AiThreadService, ChatTurn
from writer.services.ai.task_types import AiContextAttachment
from writer.domain.enums import AiCostTier


class AiTaskWorker(QThread):
    succeeded = Signal(object)  # AiTaskResponse
    failed = Signal(str)

    def __init__(
        self,
        task_service: AiTaskService,
        request: AiTaskRequest,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = task_service
        self._request = request
        self._response: Optional[AiTaskResponse] = None

    def run(self) -> None:  # noqa: D401 — Qt slot
        if self.isInterruptionRequested():
            return
        try:
            response = self._service.generate(self._request)
        except AiError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            if not self.isInterruptionRequested():
                self.failed.emit(f"Unexpected error: {exc}")
            return
        if self.isInterruptionRequested():
            return
        self._response = response
        self.succeeded.emit(response)


class AiChatWorker(QThread):
    succeeded = Signal(object)  # ChatTurn
    failed = Signal(str)

    def __init__(
        self,
        thread_service: AiThreadService,
        thread_id: str,
        user_text: str,
        *,
        scope_attachment: Optional[AiContextAttachment],
        attachments: list,
        cost_tier: AiCostTier,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = thread_service
        self._thread_id = thread_id
        self._user_text = user_text
        self._scope_attachment = scope_attachment
        self._attachments = attachments
        self._cost_tier = cost_tier
        self._turn: Optional[ChatTurn] = None

    def run(self) -> None:  # noqa: D401
        if self.isInterruptionRequested():
            return
        try:
            turn = self._service.send(
                self._thread_id,
                self._user_text,
                scope_attachment=self._scope_attachment,
                attachments=self._attachments,
                cost_tier=self._cost_tier,
            )
        except AiError as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            if not self.isInterruptionRequested():
                self.failed.emit(f"Unexpected error: {exc}")
            return
        if self.isInterruptionRequested():
            return
        self._turn = turn
        self.succeeded.emit(turn)
