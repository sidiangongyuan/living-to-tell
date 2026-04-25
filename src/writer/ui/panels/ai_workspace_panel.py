"""AI Workspace panel (M10A).

Top-level workspace mode that hosts two tabs:

* **Tools tab** — pick a structured task, fill parameters, attach extra
  context, run, and land the result back into a fragment / section / new
  fragment via the safe write-back helpers.
* **Chat tab** — free-form conversation bound to whatever object is
  currently selected (fragment / work / collection / global), persisted
  across sessions via the ``ai_threads`` / ``ai_messages`` tables.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.domain.enums import (
    AiCostTier,
    AiOutputAction,
    AiTargetKind,
    AiTaskType,
    AiThreadScope,
)
from writer.services.ai.task_types import (
    AiContextAttachment,
    AiTaskRequest,
    AiTaskResponse,
)
from writer.services.ai.task_service import SOFT_CONTEXT_BUDGET_CHARS
from writer.services.ai.thread_service import ChatTurn
from writer.ui.ai_workers import AiTaskWorker, AiChatWorker
from writer.ui.i18n import TR
from writer.ui.services.ai_apply import (
    apply_to_fragment,
    apply_to_section,
    save_as_new_fragment,
)


# ---------------------------------------------------------------------------
# Scope binding
# ---------------------------------------------------------------------------


@dataclass
class AiScope:
    """Currently bound object for the AI workspace."""

    kind: AiThreadScope
    ref_id: Optional[str]
    name: str  # display label
    body: str  # full text (for default attachment)
    work_id: Optional[str] = None  # for sections, points to parent work
    section_id: Optional[str] = None  # focused work-section id, when applicable
    selection_start: Optional[int] = None  # body-coordinate, inclusive
    selection_end: Optional[int] = None  # body-coordinate, exclusive
    selection_text: str = ""  # the currently-selected text inside the body

    @property
    def is_global(self) -> bool:
        return self.kind is AiThreadScope.GLOBAL

    @property
    def has_selection(self) -> bool:
        return (
            self.selection_start is not None
            and self.selection_end is not None
            and self.selection_end > self.selection_start
        )

    @property
    def has_section(self) -> bool:
        return bool(self.section_id) and bool(self.work_id)


def _combo_enum(combo: QComboBox, enum_cls, default):
    """Return ``combo.currentData()`` normalised back to ``enum_cls``.

    ``QComboBox.setItemData`` round-trips str-Enums through Qt's QVariant
    and hands them back as plain strings, so identity (``is``) checks
    against enum values silently fail. This helper restores the enum so
    callers can compare with either ``is`` or ``==``.
    """
    value = combo.currentData()
    if isinstance(value, enum_cls):
        return value
    if value is None:
        return default
    try:
        return enum_cls(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Task catalog (display order for the left list)
# ---------------------------------------------------------------------------

_TASK_DISPLAY_ORDER: List[AiTaskType] = [
    AiTaskType.POLISH,
    AiTaskType.EXPAND,
    AiTaskType.CONTINUE,
    AiTaskType.STYLE_TRANSFER,
    AiTaskType.SUMMARIZE,
    AiTaskType.OUTLINE,
    AiTaskType.TITLE,
    AiTaskType.STRUCTURE_DIAGNOSE,
    AiTaskType.CONSISTENCY_CHECK,
    AiTaskType.LIBRARY_QA,
]

_TASK_LABEL_KEY: dict[AiTaskType, str] = {
    AiTaskType.POLISH: "ai.task.polish",
    AiTaskType.EXPAND: "ai.task.expand",
    AiTaskType.CONTINUE: "ai.task.continue",
    AiTaskType.STYLE_TRANSFER: "ai.task.style_transfer",
    AiTaskType.SUMMARIZE: "ai.task.summarize",
    AiTaskType.OUTLINE: "ai.task.outline",
    AiTaskType.TITLE: "ai.task.title",
    AiTaskType.STRUCTURE_DIAGNOSE: "ai.task.structure_diagnose",
    AiTaskType.CONSISTENCY_CHECK: "ai.task.consistency_check",
    AiTaskType.LIBRARY_QA: "ai.task.library_qa",
}

_TIER_LABEL_KEY: dict[AiCostTier, str] = {
    AiCostTier.THRIFTY: "ai.tier.thrifty",
    AiCostTier.BALANCED: "ai.tier.balanced",
    AiCostTier.STRONG: "ai.tier.strong",
}

_OUTPUT_LABEL_KEY: dict[AiOutputAction, str] = {
    AiOutputAction.PREVIEW_ONLY: "ai.output.preview_only",
    AiOutputAction.REPLACE_SELECTION: "ai.output.replace_selection",
    AiOutputAction.REPLACE_FRAGMENT: "ai.output.replace_fragment",
    AiOutputAction.REPLACE_SECTION: "ai.output.replace_section",
    AiOutputAction.SAVE_AS_FRAGMENT: "ai.output.save_as_fragment",
    AiOutputAction.REPORT: "ai.output.report",
}


# Output destinations available per scope kind (UI-side filter; service
# layer does no enforcement on this).
def _allowed_outputs(scope: AiScope) -> List[AiOutputAction]:
    if scope.kind is AiThreadScope.FRAGMENT:
        return [
            AiOutputAction.PREVIEW_ONLY,
            AiOutputAction.REPLACE_FRAGMENT,
            AiOutputAction.SAVE_AS_FRAGMENT,
        ]
    if scope.kind is AiThreadScope.WORK:
        return [
            AiOutputAction.PREVIEW_ONLY,
            AiOutputAction.SAVE_AS_FRAGMENT,
            AiOutputAction.REPORT,
        ]
    if scope.kind is AiThreadScope.COLLECTION:
        return [AiOutputAction.PREVIEW_ONLY, AiOutputAction.REPORT]
    return [AiOutputAction.PREVIEW_ONLY, AiOutputAction.SAVE_AS_FRAGMENT]


def _scope_to_attachment_kind(scope: AiScope) -> str:
    return {
        AiThreadScope.FRAGMENT: "fragment",
        AiThreadScope.WORK: "work",
        AiThreadScope.COLLECTION: "collection",
        AiThreadScope.GLOBAL: "global",
    }[scope.kind]


# ---------------------------------------------------------------------------
# Tools tab
# ---------------------------------------------------------------------------


class AIToolsTab(QWidget):
    """Run a structured AI task and land the result safely."""

    request_save_as_fragment = Signal(str)  # new fragment id
    request_send_to_chat = Signal(str)  # text to seed chat

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._scope: Optional[AiScope] = None
        self._attachments: List[AiContextAttachment] = []
        self._last_response: Optional[AiTaskResponse] = None
        self._last_request: Optional[AiTaskRequest] = None
        self._worker: Optional[AiTaskWorker] = None

        # ---- Left: task list ----
        self._task_list = QListWidget()
        self._task_list.setObjectName("AITaskList")
        self._task_list.setMinimumWidth(150)
        for task in _TASK_DISPLAY_ORDER:
            item = QListWidgetItem(TR(_TASK_LABEL_KEY[task]))
            item.setData(Qt.ItemDataRole.UserRole, task)
            self._task_list.addItem(item)
        self._task_list.setCurrentRow(0)
        self._task_list.currentItemChanged.connect(self._on_task_changed)

        # ---- Right: form + results ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        self._scope_label = QLabel(TR("ai.scope_none"))
        self._scope_label.setObjectName("AIScopeLabel")
        self._scope_label.setWordWrap(True)
        right_layout.addWidget(self._scope_label)

        # Parameters
        params_box = QFrame()
        params_box.setObjectName("AIParamsBox")
        params_form = QFormLayout(params_box)
        params_form.setContentsMargins(0, 0, 0, 0)

        self._target_combo = QComboBox()
        for kind, key in (
            (AiTargetKind.SELECTION, "ai.target.selection"),
            (AiTargetKind.FRAGMENT, "ai.target.fragment"),
            (AiTargetKind.WORK_SECTION, "ai.target.section"),
            (AiTargetKind.WORK, "ai.target.work"),
            (AiTargetKind.COLLECTION, "ai.target.collection"),
            (AiTargetKind.PASTE, "ai.target.paste"),
        ):
            self._target_combo.addItem(TR(key), kind)
        params_form.addRow(TR("ai.target.label"), self._target_combo)

        self._tier_combo = QComboBox()
        for tier in (AiCostTier.THRIFTY, AiCostTier.BALANCED, AiCostTier.STRONG):
            self._tier_combo.addItem(TR(_TIER_LABEL_KEY[tier]), tier)
        self._tier_combo.setCurrentIndex(1)
        params_form.addRow(TR("ai.params.cost_tier"), self._tier_combo)

        self._output_combo = QComboBox()
        params_form.addRow(TR("ai.output.label"), self._output_combo)

        self._style_edit = QLineEdit()
        params_form.addRow(TR("ai.params.style"), self._style_edit)

        self._intensity_combo = QComboBox()
        for label, value in (("—", ""), ("light", "light"), ("medium", "medium"), ("strong", "strong")):
            self._intensity_combo.addItem(label, value)
        params_form.addRow(TR("ai.params.intensity"), self._intensity_combo)

        right_layout.addWidget(params_box)

        # Advanced toggle
        self._advanced_toggle = QPushButton(TR("ai.params.advanced") + " ▾")
        self._advanced_toggle.setCheckable(True)
        self._advanced_toggle.setFlat(True)
        self._advanced_toggle.toggled.connect(self._on_toggle_advanced)
        right_layout.addWidget(self._advanced_toggle)

        self._advanced_box = QFrame()
        self._advanced_box.setObjectName("AIAdvancedBox")
        adv_form = QFormLayout(self._advanced_box)
        adv_form.setContentsMargins(0, 0, 0, 0)
        self._extra_edit = QPlainTextEdit()
        self._extra_edit.setMaximumHeight(60)
        adv_form.addRow(TR("ai.params.extra_instructions"), self._extra_edit)
        self._max_output_spin = QSpinBox()
        self._max_output_spin.setRange(0, 100_000)
        self._max_output_spin.setSingleStep(200)
        self._max_output_spin.setSpecialValueText("—")
        adv_form.addRow(TR("ai.params.max_output"), self._max_output_spin)
        self._preserve_meaning_check = QCheckBox()
        self._preserve_meaning_check.setChecked(True)
        adv_form.addRow(TR("ai.params.preserve_meaning"), self._preserve_meaning_check)
        self._preserve_voice_check = QCheckBox()
        self._preserve_voice_check.setChecked(True)
        adv_form.addRow(TR("ai.params.preserve_voice"), self._preserve_voice_check)
        self._must_keep_edit = QLineEdit()
        adv_form.addRow(TR("ai.params.must_keep"), self._must_keep_edit)
        self._forbid_edit = QLineEdit()
        adv_form.addRow(TR("ai.params.forbid"), self._forbid_edit)
        self._advanced_box.setVisible(False)
        right_layout.addWidget(self._advanced_box)

        # Pasted-text input (shown only when target=PASTE)
        self._paste_edit = QPlainTextEdit()
        self._paste_edit.setPlaceholderText(TR("ai.target.paste"))
        self._paste_edit.setMaximumHeight(120)
        self._paste_edit.setVisible(False)
        right_layout.addWidget(self._paste_edit)
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)

        # Attachments
        attach_label = QLabel(TR("ai.attachments.title"))
        attach_label.setObjectName("AIAttachLabel")
        right_layout.addWidget(attach_label)
        self._attach_empty_label = QLabel(TR("ai.attachments.empty"))
        self._attach_empty_label.setWordWrap(True)
        self._attach_empty_label.setObjectName("AIAttachEmpty")
        right_layout.addWidget(self._attach_empty_label)
        self._attach_list = QListWidget()
        self._attach_list.setMaximumHeight(110)
        self._attach_list.setVisible(False)
        right_layout.addWidget(self._attach_list)
        attach_btn_row = QHBoxLayout()
        self._add_fragment_btn = QPushButton(TR("ai.attachments.add_fragment"))
        self._add_fragment_btn.clicked.connect(self._on_add_fragment_attachment)
        attach_btn_row.addWidget(self._add_fragment_btn)
        self._remove_attach_btn = QPushButton(TR("ai.attachments.remove"))
        self._remove_attach_btn.clicked.connect(self._on_remove_attachment)
        self._remove_attach_btn.setEnabled(False)
        attach_btn_row.addWidget(self._remove_attach_btn)
        attach_btn_row.addStretch(1)
        self._attach_total_label = QLabel("")
        self._attach_total_label.setObjectName("AIAttachTotal")
        attach_btn_row.addWidget(self._attach_total_label)
        right_layout.addLayout(attach_btn_row)
        self._attach_list.currentItemChanged.connect(
            lambda *_: self._remove_attach_btn.setEnabled(self._attach_list.currentItem() is not None)
        )

        # Run button + status
        run_row = QHBoxLayout()
        self._run_btn = QPushButton(TR("ai.results.run"))
        self._run_btn.setObjectName("AIRunButton")
        self._run_btn.clicked.connect(self._on_run)
        run_row.addWidget(self._run_btn)
        self._status_label = QLabel("")
        self._status_label.setObjectName("AIStatusLabel")
        run_row.addWidget(self._status_label, 1)
        right_layout.addLayout(run_row)

        # Result area
        result_label = QLabel(TR("ai.results.title"))
        result_label.setObjectName("AIResultLabel")
        right_layout.addWidget(result_label)
        self._result_view = QTextEdit()
        self._result_view.setReadOnly(False)
        self._result_view.setObjectName("AIResultView")
        self._result_view.setPlaceholderText(TR("ai.results.empty"))
        right_layout.addWidget(self._result_view, 1)

        self._meta_label = QLabel("")
        self._meta_label.setObjectName("AIResultMeta")
        self._meta_label.setWordWrap(True)
        right_layout.addWidget(self._meta_label)

        self._citations_label = QLabel("")
        self._citations_label.setObjectName("AICitationsLabel")
        self._citations_label.setWordWrap(True)
        self._citations_label.setVisible(False)
        right_layout.addWidget(self._citations_label)

        action_row = QHBoxLayout()
        self._apply_btn = QPushButton(TR("ai.results.apply"))
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        action_row.addWidget(self._apply_btn)
        self._save_fragment_btn = QPushButton(TR("ai.results.save_fragment"))
        self._save_fragment_btn.setEnabled(False)
        self._save_fragment_btn.clicked.connect(self._on_save_fragment)
        action_row.addWidget(self._save_fragment_btn)
        self._send_chat_btn = QPushButton(TR("ai.results.send_to_chat"))
        self._send_chat_btn.setEnabled(False)
        self._send_chat_btn.clicked.connect(self._on_send_to_chat)
        action_row.addWidget(self._send_chat_btn)
        action_row.addStretch(1)
        right_layout.addLayout(action_row)

        # ---- Splitter ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._task_list)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([180, 600])

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)

        self._refresh_output_combo()
        self._refresh_attachments_view()

    # ---- public API ----
    def bind_scope(self, scope: AiScope) -> None:
        self._scope = scope
        self._update_scope_label()
        self._refresh_output_combo()
        # Reset target default per scope.
        target_default = {
            AiThreadScope.FRAGMENT: AiTargetKind.FRAGMENT,
            AiThreadScope.WORK: AiTargetKind.WORK,
            AiThreadScope.COLLECTION: AiTargetKind.COLLECTION,
            AiThreadScope.GLOBAL: AiTargetKind.PASTE,
        }[scope.kind]
        idx = self._target_combo.findData(target_default)
        if idx >= 0:
            self._target_combo.setCurrentIndex(idx)

    # ---- internal ----
    def _update_scope_label(self) -> None:
        if self._scope is None or self._scope.is_global:
            self._scope_label.setText(TR("ai.scope_global"))
            return
        key = {
            AiThreadScope.FRAGMENT: "ai.scope_fragment",
            AiThreadScope.WORK: "ai.scope_work",
            AiThreadScope.COLLECTION: "ai.scope_collection",
        }.get(self._scope.kind, "ai.scope_global")
        self._scope_label.setText(TR(key).format(name=self._scope.name))

    def _on_task_changed(self, *_args) -> None:
        self._refresh_output_combo()

    def _on_toggle_advanced(self, checked: bool) -> None:
        self._advanced_box.setVisible(checked)
        arrow = "▴" if checked else "▾"
        self._advanced_toggle.setText(TR("ai.params.advanced") + " " + arrow)

    def _on_target_changed(self) -> None:
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)
        self._paste_edit.setVisible(target == AiTargetKind.PASTE)
        self._refresh_output_combo()

    def _refresh_output_combo(self) -> None:
        prev = self._output_combo.currentData()
        self._output_combo.clear()
        scope = self._scope or AiScope(AiThreadScope.GLOBAL, None, "", "")
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)

        # Allowed outputs depend on both scope & target. We start from
        # scope-allowed and additionally restrict by target kind.
        allowed = set(_allowed_outputs(scope))
        if target == AiTargetKind.SELECTION:
            # Selection inside a fragment unlocks REPLACE_SELECTION; for
            # other scopes the request degrades to preview / save-as.
            if scope.kind is AiThreadScope.FRAGMENT:
                allowed.add(AiOutputAction.REPLACE_SELECTION)
            allowed &= {
                AiOutputAction.PREVIEW_ONLY,
                AiOutputAction.REPLACE_SELECTION,
                AiOutputAction.SAVE_AS_FRAGMENT,
            }
        elif target == AiTargetKind.WORK_SECTION:
            allowed.add(AiOutputAction.REPLACE_SECTION)
        elif target == AiTargetKind.PASTE:
            allowed = {AiOutputAction.PREVIEW_ONLY, AiOutputAction.SAVE_AS_FRAGMENT}

        # Always allow REPORT for diagnostic/QA tasks.
        cur_task = self._current_task_type()
        if cur_task in {
            AiTaskType.STRUCTURE_DIAGNOSE,
            AiTaskType.CONSISTENCY_CHECK,
            AiTaskType.LIBRARY_QA,
        }:
            allowed = {AiOutputAction.REPORT, AiOutputAction.SAVE_AS_FRAGMENT}

        # Stable display order:
        order = [
            AiOutputAction.PREVIEW_ONLY,
            AiOutputAction.REPLACE_SELECTION,
            AiOutputAction.REPLACE_FRAGMENT,
            AiOutputAction.REPLACE_SECTION,
            AiOutputAction.SAVE_AS_FRAGMENT,
            AiOutputAction.REPORT,
        ]
        for act in order:
            if act in allowed:
                self._output_combo.addItem(TR(_OUTPUT_LABEL_KEY[act]), act)
        # Restore previous if still allowed; else first item.
        idx = self._output_combo.findData(prev)
        if idx < 0:
            idx = 0
        self._output_combo.setCurrentIndex(idx)

    def _current_task_type(self) -> AiTaskType:
        item = self._task_list.currentItem()
        if item is None:
            return AiTaskType.POLISH
        value = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(value, AiTaskType):
            return value
        try:
            return AiTaskType(value)
        except (TypeError, ValueError):
            return AiTaskType.POLISH

    def _refresh_attachments_view(self) -> None:
        self._attach_list.clear()
        for att in self._attachments:
            label = f"{att.name}  ({att.size_chars} chars)"
            item = QListWidgetItem(label)
            self._attach_list.addItem(item)
        has_any = bool(self._attachments)
        self._attach_list.setVisible(has_any)
        self._attach_empty_label.setVisible(not has_any)
        # total
        total = sum(a.size_chars for a in self._attachments)
        if self._scope is not None:
            total += len(self._scope.body)
        self._attach_total_label.setText(
            TR("ai.attachments.total").format(chars=total)
        )
        if total > SOFT_CONTEXT_BUDGET_CHARS:
            self._attach_total_label.setStyleSheet("color: #c1440e;")
            self._attach_total_label.setToolTip(TR("ai.attachments.heavy_warning"))
        else:
            self._attach_total_label.setStyleSheet("")
            self._attach_total_label.setToolTip("")
        self._remove_attach_btn.setEnabled(self._attach_list.currentItem() is not None)

    def _on_add_fragment_attachment(self) -> None:
        from writer.ui.dialogs.fragment_picker_dialog import FragmentPickerDialog  # lazy
        dlg = FragmentPickerDialog(self._container, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        entry = dlg.selected_entry
        if entry is None:
            return
        self._attachments.append(
            AiContextAttachment(
                kind="fragment",
                ref_id=entry.id,
                name=(entry.title or "(untitled)") + f" [{entry.id[:8]}]",
                body=entry.body or "",
            )
        )
        self._refresh_attachments_view()

    def _on_remove_attachment(self) -> None:
        row = self._attach_list.currentRow()
        if 0 <= row < len(self._attachments):
            del self._attachments[row]
            self._refresh_attachments_view()

    # ---- run ----
    def _build_request(self) -> Optional[AiTaskRequest]:
        if self._scope is None:
            self._scope = AiScope(AiThreadScope.GLOBAL, None, "", "")

        task = self._current_task_type()
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)
        tier = _combo_enum(self._tier_combo, AiCostTier, AiCostTier.BALANCED)
        output = _combo_enum(
            self._output_combo, AiOutputAction, AiOutputAction.PREVIEW_ONLY
        )

        # Determine subject text based on target.
        if target == AiTargetKind.PASTE:
            text = self._paste_edit.toPlainText()
        elif target == AiTargetKind.SELECTION:
            # Prefer the live selection captured by main_window when the AI
            # workspace was activated. Fall back to paste only when the user
            # explicitly typed something (we never silently degrade to the
            # whole body, which would surprise the user).
            if self._scope.has_selection and self._scope.selection_text:
                text = self._scope.selection_text
            else:
                text = self._paste_edit.toPlainText()
        elif target == AiTargetKind.WORK_SECTION:
            # Section body has been packed into scope.body by main_window
            # whenever a section is focused.
            text = self._scope.body if self._scope.has_section else ""
        else:
            text = self._scope.body

        if not text.strip() and task is not AiTaskType.LIBRARY_QA:
            QMessageBox.warning(
                self,
                TR("ai.dlg.no_target"),
                TR("ai.dlg.no_target_msg"),
            )
            return None

        max_out = self._max_output_spin.value() or None
        intensity_val = self._intensity_combo.currentData() or None

        must_keep = [t.strip() for t in self._must_keep_edit.text().split(",") if t.strip()]
        forbid = [t.strip() for t in self._forbid_edit.text().split(",") if t.strip()]
        extra = self._extra_edit.toPlainText().strip() or None

        if target == AiTargetKind.WORK_SECTION:
            target_ref = self._scope.section_id or self._scope.ref_id
        elif target in {
            AiTargetKind.FRAGMENT,
            AiTargetKind.WORK,
            AiTargetKind.COLLECTION,
        }:
            target_ref = self._scope.ref_id
        else:
            target_ref = None

        is_structured = task in {
            AiTaskType.STRUCTURE_DIAGNOSE,
            AiTaskType.CONSISTENCY_CHECK,
            AiTaskType.LIBRARY_QA,
        }

        request = AiTaskRequest(
            task_type=task,
            target_kind=target,
            text=text,
            target_ref_id=target_ref,
            style=self._style_edit.text().strip() or None,
            intensity=intensity_val,
            extra_instructions=extra,
            max_output_chars=max_out,
            preserve_meaning=self._preserve_meaning_check.isChecked(),
            preserve_voice=self._preserve_voice_check.isChecked(),
            forbid_terms=forbid,
            must_keep_terms=must_keep,
            attachments=list(self._attachments),
            cost_tier=tier,
            desired_output=output,
            expect_structured=is_structured,
        )
        return request

    def _on_run(self) -> None:
        request = self._build_request()
        if request is None:
            return
        # Disable run button while in flight.
        self._run_btn.setEnabled(False)
        self._status_label.setText("…")
        self._last_request = request

        worker = AiTaskWorker(self._container.ai_task_service, request, parent=self)
        worker.succeeded.connect(self._on_task_succeeded)
        worker.failed.connect(self._on_task_failed)
        worker.finished.connect(lambda: self._run_btn.setEnabled(True))
        self._worker = worker
        worker.start()

    def _on_task_succeeded(self, response: AiTaskResponse) -> None:
        self._last_response = response
        self._status_label.setText("")
        task_type = self._result_task_type()
        rendered = (
            self._render_structured(response, task_type=task_type)
            if response.structured else None
        )
        self._result_view.setPlainText(rendered if rendered is not None else response.content)
        meta_parts = []
        if response.model:
            meta_parts.append(f"{TR('ai.results.model_label')}: {response.model}")
        if response.input_tokens is not None or response.output_tokens is not None:
            tokens = f"{response.input_tokens or 0}/{response.output_tokens or 0}"
            meta_parts.append(f"{TR('ai.results.tokens_label')}: {tokens}")
        self._meta_label.setText("  ·  ".join(meta_parts))

        if response.citations:
            cite_lines = [TR("ai.results.citations_label") + ":"]
            for c in response.citations:
                tag = TR("ai.results.unresolved") + " " if c.kind == "unresolved" else ""
                cite_lines.append(f"  • {tag}{c.name}")
            self._citations_label.setText("\n".join(cite_lines))
            self._citations_label.setVisible(True)
        else:
            self._citations_label.setVisible(False)

        # Apply button enablement.
        out = _combo_enum(
            self._output_combo, AiOutputAction, AiOutputAction.PREVIEW_ONLY
        )
        can_apply = out in {
            AiOutputAction.REPLACE_FRAGMENT,
            AiOutputAction.REPLACE_SELECTION,
            AiOutputAction.REPLACE_SECTION,
        }
        self._apply_btn.setEnabled(can_apply)
        self._save_fragment_btn.setEnabled(True)
        self._send_chat_btn.setEnabled(True)

    def _result_task_type(self) -> AiTaskType:
        if self._last_request is not None:
            return self._last_request.task_type
        return self._current_task_type()

    def _render_structured(
        self,
        response: AiTaskResponse,
        *,
        task_type: Optional[AiTaskType] = None,
    ) -> Optional[str]:
        """Render structured task results as readable text.

        Returns ``None`` when the structure isn't recognised; the caller
        then falls back to the raw assistant content.
        """
        data = response.structured or {}
        task = task_type or self._result_task_type()
        if task == AiTaskType.LIBRARY_QA:
            answer = (data.get("answer") or "").strip()
            return answer or response.content
        if task in {AiTaskType.STRUCTURE_DIAGNOSE, AiTaskType.CONSISTENCY_CHECK}:
            issues = data.get("issues") or []
            if not isinstance(issues, list):
                return None
            if not issues:
                return TR("ai.results.no_issues")
            lines: List[str] = []
            for idx, raw in enumerate(issues, start=1):
                if not isinstance(raw, dict):
                    lines.append(f"{idx}. {raw}")
                    continue
                severity = str(raw.get("severity") or "").strip()
                where = str(raw.get("where") or raw.get("location") or "").strip()
                what = str(
                    raw.get("what") or raw.get("issue") or raw.get("problem") or ""
                ).strip()
                suggestion = str(raw.get("suggestion") or raw.get("fix") or "").strip()
                header = f"{idx}."
                if severity:
                    header += f" [{severity}]"
                if where:
                    header += f" {where}"
                lines.append(header)
                if what:
                    lines.append(f"   - {what}")
                if suggestion:
                    lines.append(f"   → {suggestion}")
            return "\n".join(lines)
        return None

    def _on_task_failed(self, message: str) -> None:
        self._status_label.setText("")
        QMessageBox.critical(self, TR("ai.dlg.run_failed"), message)

    # ---- result actions ----
    def _on_apply(self) -> None:
        if self._last_response is None or self._last_request is None or self._scope is None:
            return
        out = _combo_enum(
            self._output_combo, AiOutputAction, AiOutputAction.PREVIEW_ONLY
        )
        text = self._result_view.toPlainText()  # honour any user edits
        try:
            if out == AiOutputAction.REPLACE_FRAGMENT and self._scope.ref_id is not None:
                outcome = apply_to_fragment(
                    self._container,
                    entry_id=self._scope.ref_id,
                    task_type=self._last_request.task_type,
                    original_full_body=self._scope.body,
                    selection_start=None,
                    selection_end=None,
                    generated_text=text,
                    title=self._scope.name,
                    provider_name=self._last_response.provider or "openai",
                    model=self._last_response.model or "",
                )
            elif (
                out == AiOutputAction.REPLACE_SELECTION
                and self._scope.ref_id is not None
                and self._scope.has_selection
            ):
                outcome = apply_to_fragment(
                    self._container,
                    entry_id=self._scope.ref_id,
                    task_type=self._last_request.task_type,
                    original_full_body=self._scope.body,
                    selection_start=self._scope.selection_start,
                    selection_end=self._scope.selection_end,
                    generated_text=text,
                    title=self._scope.name,
                    provider_name=self._last_response.provider or "openai",
                    model=self._last_response.model or "",
                )
            elif (
                out == AiOutputAction.REPLACE_SECTION
                and self._scope.has_section
            ):
                outcome = apply_to_section(
                    self._container,
                    work_id=self._scope.work_id,
                    section_id=self._scope.section_id,
                    generated_text=text,
                )
            else:
                QMessageBox.warning(
                    self, TR("ai.dlg.run_failed"), TR("ai.dlg.cannot_apply")
                )
                return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, TR("ai.dlg.run_failed"), str(exc))
            return
        QMessageBox.information(
            self,
            TR("ai.results.apply"),
            TR("ai.dlg.applied").format(target=outcome.target_label),
        )

    def _on_save_fragment(self) -> None:
        text = self._result_view.toPlainText()
        if not text.strip():
            return
        title = "AI: " + TR(_TASK_LABEL_KEY[self._result_task_type()])
        outcome = save_as_new_fragment(self._container, title=title, body=text)
        QMessageBox.information(
            self, TR("ai.results.save_fragment"), TR("ai.dlg.saved_as_fragment")
        )
        if outcome.new_fragment_id:
            self.request_save_as_fragment.emit(outcome.new_fragment_id)

    def _on_send_to_chat(self) -> None:
        text = self._result_view.toPlainText()
        if text.strip():
            self.request_send_to_chat.emit(text)


# ---------------------------------------------------------------------------
# Chat tab
# ---------------------------------------------------------------------------


class AIChatTab(QWidget):
    """Free-form conversation persisted per scope."""

    request_save_as_fragment = Signal(str)  # new fragment id

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._scope: Optional[AiScope] = None
        self._thread_id: Optional[str] = None
        self._worker: Optional[AiChatWorker] = None
        self._attachments: List[AiContextAttachment] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._scope_label = QLabel(TR("ai.scope_none"))
        self._scope_label.setObjectName("AIChatScope")
        self._scope_label.setWordWrap(True)
        layout.addWidget(self._scope_label)

        self._messages_view = QTextEdit()
        self._messages_view.setReadOnly(True)
        self._messages_view.setObjectName("AIChatMessages")
        layout.addWidget(self._messages_view, 1)

        # Attachments mini-list
        self._attach_label = QLabel("")
        self._attach_label.setObjectName("AIChatAttach")
        self._attach_label.setWordWrap(True)
        layout.addWidget(self._attach_label)

        attach_row = QHBoxLayout()
        self._add_frag_btn = QPushButton(TR("ai.attachments.add_fragment"))
        self._add_frag_btn.clicked.connect(self._on_add_attachment)
        attach_row.addWidget(self._add_frag_btn)
        self._clear_attach_btn = QPushButton(TR("ai.attachments.remove"))
        self._clear_attach_btn.clicked.connect(self._on_clear_attachments)
        attach_row.addWidget(self._clear_attach_btn)
        attach_row.addStretch(1)
        self._tier_combo = QComboBox()
        for tier in (AiCostTier.THRIFTY, AiCostTier.BALANCED, AiCostTier.STRONG):
            self._tier_combo.addItem(TR(_TIER_LABEL_KEY[tier]), tier)
        self._tier_combo.setCurrentIndex(1)
        attach_row.addWidget(self._tier_combo)
        layout.addLayout(attach_row)

        self._input = QPlainTextEdit()
        self._input.setPlaceholderText(TR("ai.chat.input_placeholder").format(scope="object"))
        self._input.setMaximumHeight(110)
        layout.addWidget(self._input)

        send_row = QHBoxLayout()
        self._send_btn = QPushButton(TR("ai.chat.send"))
        self._send_btn.clicked.connect(self._on_send)
        send_row.addWidget(self._send_btn)
        self._save_fragment_btn = QPushButton(TR("ai.chat.save_as_fragment"))
        self._save_fragment_btn.clicked.connect(self._on_save_last_assistant_as_fragment)
        send_row.addWidget(self._save_fragment_btn)
        send_row.addStretch(1)
        self._status_label = QLabel("")
        send_row.addWidget(self._status_label)
        layout.addLayout(send_row)

        self._refresh_attachments_label()

    # ---- public API ----
    def bind_scope(self, scope: AiScope) -> None:
        self._scope = scope
        self._update_scope_label()
        # Resolve thread for this scope.
        thread = self._container.ai_thread_service.get_or_create_for_scope(
            scope.kind,
            scope.ref_id,
            title=scope.name or "Global",
        )
        self._thread_id = thread.id
        self._render_history()

    def seed_input(self, text: str) -> None:
        self._input.setPlainText(text)

    # ---- internal ----
    def _update_scope_label(self) -> None:
        if self._scope is None or self._scope.is_global:
            self._scope_label.setText(TR("ai.scope_global"))
            self._input.setPlaceholderText(
                TR("ai.chat.input_placeholder").format(scope="object")
            )
            return
        key = {
            AiThreadScope.FRAGMENT: "ai.scope_fragment",
            AiThreadScope.WORK: "ai.scope_work",
            AiThreadScope.COLLECTION: "ai.scope_collection",
        }.get(self._scope.kind, "ai.scope_global")
        self._scope_label.setText(TR(key).format(name=self._scope.name))
        self._input.setPlaceholderText(
            TR("ai.chat.input_placeholder").format(scope=self._scope.name or "object")
        )

    def _render_history(self) -> None:
        self._messages_view.clear()
        if self._thread_id is None:
            return
        history = self._container.ai_thread_service.history(self._thread_id)
        if not history:
            self._messages_view.setPlaceholderText(TR("ai.chat.empty"))
            return
        for msg in history:
            self._append_message(msg.role, msg.content)

    def _append_message(self, role: str, content: str) -> None:
        if role == "user":
            label = TR("ai.chat.role_user")
            color = "#2b6cb0"
        else:
            label = TR("ai.chat.role_assistant")
            color = "#2f855a"
        html = (
            f'<div style="margin: 4px 0;"><b style="color:{color};">{label}:</b><br>'
            f'<span style="white-space: pre-wrap;">{self._escape(content)}</span></div>'
        )
        self._messages_view.append(html)

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _refresh_attachments_label(self) -> None:
        if not self._attachments:
            self._attach_label.setText("")
            return
        names = [a.name for a in self._attachments]
        self._attach_label.setText(
            TR("ai.chat.attachment_added").format(name=", ".join(names))
        )

    def _on_add_attachment(self) -> None:
        from writer.ui.dialogs.fragment_picker_dialog import FragmentPickerDialog  # lazy
        dlg = FragmentPickerDialog(self._container, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        entry = dlg.selected_entry
        if entry is None:
            return
        self._attachments.append(
            AiContextAttachment(
                kind="fragment",
                ref_id=entry.id,
                name=(entry.title or "(untitled)") + f" [{entry.id[:8]}]",
                body=entry.body or "",
            )
        )
        self._refresh_attachments_label()

    def _on_clear_attachments(self) -> None:
        self._attachments.clear()
        self._refresh_attachments_label()

    def _on_send(self) -> None:
        if self._thread_id is None or self._scope is None:
            return
        user_text = self._input.toPlainText().strip()
        if not user_text:
            return
        scope_attachment = None
        if self._scope.body and not self._scope.is_global:
            scope_attachment = AiContextAttachment(
                kind=_scope_to_attachment_kind(self._scope),
                ref_id=self._scope.ref_id or "",
                name=self._scope.name,
                body=self._scope.body,
            )
        self._send_btn.setEnabled(False)
        self._status_label.setText("…")
        self._append_message("user", user_text)
        self._input.clear()

        worker = AiChatWorker(
            self._container.ai_thread_service,
            self._thread_id,
            user_text,
            scope_attachment=scope_attachment,
            attachments=list(self._attachments),
            cost_tier=self._tier_combo.currentData() or AiCostTier.BALANCED,
            parent=self,
        )
        worker.succeeded.connect(self._on_chat_succeeded)
        worker.failed.connect(self._on_chat_failed)
        worker.finished.connect(lambda: self._send_btn.setEnabled(True))
        self._worker = worker
        worker.start()

    def _on_chat_succeeded(self, turn: ChatTurn) -> None:
        self._status_label.setText("")
        self._append_message("assistant", turn.assistant_message.content)

    def _on_chat_failed(self, message: str) -> None:
        self._status_label.setText("")
        QMessageBox.critical(self, TR("ai.dlg.run_failed"), message)

    def _on_save_last_assistant_as_fragment(self) -> None:
        if self._thread_id is None:
            return
        history = self._container.ai_thread_service.history(self._thread_id)
        last_assistant = next(
            (m for m in reversed(history) if m.role == "assistant"), None
        )
        if last_assistant is None:
            return
        outcome = save_as_new_fragment(
            self._container,
            title="AI chat: " + (self._scope.name if self._scope else "global"),
            body=last_assistant.content,
        )
        QMessageBox.information(
            self, TR("ai.results.save_fragment"), TR("ai.dlg.saved_as_fragment")
        )
        if outcome.new_fragment_id:
            self.request_save_as_fragment.emit(outcome.new_fragment_id)


# ---------------------------------------------------------------------------
# Top-level panel
# ---------------------------------------------------------------------------


class AIWorkspacePanel(QWidget):
    """The mode-3 panel: a tabbed AI workspace (Tools + Chat)."""

    request_save_as_fragment = Signal(str)

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._scope: Optional[AiScope] = None

        self._tools_tab = AIToolsTab(container, self)
        self._chat_tab = AIChatTab(container, self)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._tools_tab, TR("ai.tab_tools"))
        self._tabs.addTab(self._chat_tab, TR("ai.tab_chat"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

        # Wire send-to-chat from tools to chat tab.
        self._tools_tab.request_send_to_chat.connect(self._on_send_to_chat)
        self._tools_tab.request_save_as_fragment.connect(self.request_save_as_fragment.emit)
        self._chat_tab.request_save_as_fragment.connect(self.request_save_as_fragment.emit)

        # Default global scope until bound.
        self.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))

    def bind_scope(self, scope: AiScope) -> None:
        self._scope = scope
        self._tools_tab.bind_scope(scope)
        self._chat_tab.bind_scope(scope)

    def _on_send_to_chat(self, text: str) -> None:
        self._tabs.setCurrentWidget(self._chat_tab)
        self._chat_tab.seed_input(text)

    # Helpers used by tests / main_window.
    @property
    def tools_tab(self) -> AIToolsTab:
        return self._tools_tab

    @property
    def chat_tab(self) -> AIChatTab:
        return self._chat_tab

    @property
    def tabs(self) -> QTabWidget:
        return self._tabs
