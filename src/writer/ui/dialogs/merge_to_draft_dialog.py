"""Dialog: turn N selected fragments into one merged AI draft (M-Dates).

Flow: user picks an output type, clicks "Run AI", waits for the provider
to return, then reviews the result. "Save as new fragment" persists the
draft via :func:`save_merged_draft_as_fragment` without touching any of
the source entries.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.models.entry import Entry
from writer.services.ai.interfaces import AiError
from writer.services.ai.task_types import AiTaskResponse
from writer.services.dates_merge_service import (
    MergeOutputType,
    MergeRequestPlan,
    build_merge_plan,
    save_merged_draft_as_fragment,
)
from writer.ui.i18n import TR


class _MergeWorker(QThread):
    """Runs ``AiTaskService.generate`` off the UI thread."""

    succeeded = Signal(object)  # AiTaskResponse
    failed = Signal(str)

    def __init__(self, service, plan: MergeRequestPlan, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._plan = plan

    def run(self) -> None:  # noqa: D401 — Qt slot
        try:
            response = self._service.generate(self._plan.request)
        except AiError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Unexpected error: {exc}")
            return
        self.succeeded.emit(response)


class MergeToDraftDialog(QDialog):
    """Preview & save UI for the daily AI-merge feature."""

    saved = Signal(str)  # new entry_id

    def __init__(
        self,
        container: AppContainer,
        entries: Sequence[Entry],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MergeToDraftDialog")
        self.setWindowTitle(TR("dates.merge_title"))
        self._container = container
        self._entries: List[Entry] = list(entries)
        self._last_response: Optional[AiTaskResponse] = None
        self._worker: Optional[_MergeWorker] = None

        layout = QVBoxLayout(self)

        # Sources summary
        names = ", ".join(
            (e.title or "").strip() or TR("list.empty_fragment") for e in entries
        )
        layout.addWidget(QLabel(f"{TR('dates.merge_sources_label')}: {names}"))

        # Output type radio group
        layout.addWidget(QLabel(TR("dates.merge_output_label")))
        self._output_group = QButtonGroup(self)
        self._radio_prose = QRadioButton(TR("dates.merge_output_prose"))
        self._radio_section = QRadioButton(TR("dates.merge_output_section"))
        self._radio_outline = QRadioButton(TR("dates.merge_output_outline"))
        self._radio_prose.setChecked(True)
        for rb, key in (
            (self._radio_prose, MergeOutputType.PROSE),
            (self._radio_section, MergeOutputType.SECTION),
            (self._radio_outline, MergeOutputType.OUTLINE),
        ):
            self._output_group.addButton(rb)
            layout.addWidget(rb)

        # Preview pane
        self._preview = QPlainTextEdit()
        self._preview.setObjectName("MergePreview")
        self._preview.setPlaceholderText(TR("dates.merge_preview_placeholder"))
        layout.addWidget(self._preview, 1)

        # Buttons
        bar = QHBoxLayout()
        self._run_btn = QPushButton(TR("dates.merge_run"))
        self._save_btn = QPushButton(TR("dates.merge_save_as_fragment"))
        self._save_btn.setEnabled(False)
        self._close_btn = QPushButton(TR("dates.merge_close"))
        bar.addWidget(self._run_btn)
        bar.addStretch(1)
        bar.addWidget(self._save_btn)
        bar.addWidget(self._close_btn)
        layout.addLayout(bar)

        self._run_btn.clicked.connect(self._on_run)
        self._save_btn.clicked.connect(self._on_save)
        self._close_btn.clicked.connect(self.reject)

        self.resize(640, 520)

    # ------------------------------------------------------------------
    def selected_output_type(self) -> MergeOutputType:
        if self._radio_section.isChecked():
            return MergeOutputType.SECTION
        if self._radio_outline.isChecked():
            return MergeOutputType.OUTLINE
        return MergeOutputType.PROSE

    def build_plan(self) -> MergeRequestPlan:
        """Test hook — returns the plan that *would* be sent to AI."""
        return build_merge_plan(self._entries, self.selected_output_type())

    # ------------------------------------------------------------------
    def _on_run(self) -> None:
        if not self._entries:
            QMessageBox.warning(
                self,
                TR("dates.merge_title"),
                TR("dates.merge_select_msg"),
            )
            return
        plan = self.build_plan()
        self._run_btn.setEnabled(False)
        self._run_btn.setText(TR("dates.merge_running"))
        self._save_btn.setEnabled(False)

        self._worker = _MergeWorker(
            self._container.ai_task_service, plan, parent=self
        )
        self._worker.succeeded.connect(self._on_ai_ok)
        self._worker.failed.connect(self._on_ai_err)
        self._worker.finished.connect(self._reset_run_btn)
        self._worker.start()

    def _reset_run_btn(self) -> None:
        self._run_btn.setEnabled(True)
        self._run_btn.setText(TR("dates.merge_run"))

    def _on_ai_ok(self, response: AiTaskResponse) -> None:
        self._last_response = response
        self._preview.setPlainText(response.content or "")
        self._save_btn.setEnabled(bool(response.content and response.content.strip()))

    def _on_ai_err(self, message: str) -> None:
        QMessageBox.warning(
            self,
            TR("dates.merge_title"),
            TR("dates.merge_failed").format(error=message),
        )

    def _on_save(self) -> None:
        body = self._preview.toPlainText()
        if not body.strip():
            return
        entry = save_merged_draft_as_fragment(
            self._container.entry_repository,
            body,
            source_ids=[e.id for e in self._entries],
        )
        self.saved.emit(entry.id)
        QMessageBox.information(
            self, TR("dates.merge_title"), TR("dates.merge_saved")
        )
        self.accept()
