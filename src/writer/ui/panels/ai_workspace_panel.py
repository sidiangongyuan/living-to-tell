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

from dataclasses import dataclass
from typing import Optional, List

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QApplication,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.app.locale import LOCALE_ZH_CN, current_locale
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
from writer.services.ai.context_budget import (
    DEFAULT_CHAT_CONTEXT_BUDGET_CHARS,
    estimate_attachment_chars,
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
from writer.ui.widgets.controls import NoWheelComboBox, NoWheelSpinBox


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


@dataclass
class AiTaskResultState:
    """Cached visible result state for one AI task type."""

    response: Optional[AiTaskResponse] = None
    request: Optional[AiTaskRequest] = None
    result_text: str = ""
    source_text: str = ""
    source_visible: bool = False
    result_header_visible: bool = False
    meta_text: str = ""
    citations_text: str = ""
    citations_visible: bool = False
    last_excerpt: str = ""


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


def _set_relaxed_vertical_sizing(
    widget: QWidget,
    *,
    minimum: int,
    maximum: int,
    policy: QSizePolicy.Policy = QSizePolicy.Policy.Preferred,
) -> None:
    widget.setMinimumHeight(minimum)
    widget.setMaximumHeight(maximum)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, policy)


def _refresh_widget_style(widget: QWidget) -> None:
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


# ---------------------------------------------------------------------------
# Task catalog (display order for the left list)
# ---------------------------------------------------------------------------

_TASK_DISPLAY_ORDER: List[AiTaskType] = [
    AiTaskType.POLISH,
    AiTaskType.EXPAND,
    AiTaskType.CONTINUE,
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

_STYLE_TASKS: set[AiTaskType] = {
    AiTaskType.POLISH,
    AiTaskType.EXPAND,
    AiTaskType.CONTINUE,
}

# Tasks that benefit from side-by-side original vs. AI result compare layout.
_COMPARE_TASKS: set[AiTaskType] = {
    AiTaskType.POLISH,
    AiTaskType.EXPAND,
    AiTaskType.CONTINUE,
}

_INTENSITY_TASKS: set[AiTaskType] = {
    AiTaskType.POLISH,
    AiTaskType.EXPAND,
}

_WRITING_NOTE_DEFAULT_TASKS: set[AiTaskType] = {
    AiTaskType.EXPAND,
    AiTaskType.CONTINUE,
}

_TASK_STYLE_HINT_KEY: dict[AiTaskType, str] = {
    AiTaskType.POLISH: "ai.params.style_hint.polish",
    AiTaskType.EXPAND: "ai.params.style_hint.expand",
    AiTaskType.CONTINUE: "ai.params.style_hint.continue",
    AiTaskType.SUMMARIZE: "ai.params.style_hint.summarize",
    AiTaskType.OUTLINE: "ai.params.style_hint.outline",
    AiTaskType.TITLE: "ai.params.style_hint.title",
    AiTaskType.STRUCTURE_DIAGNOSE: "ai.params.style_hint.structure_diagnose",
    AiTaskType.CONSISTENCY_CHECK: "ai.params.style_hint.consistency_check",
    AiTaskType.LIBRARY_QA: "ai.params.style_hint.library_qa",
}

_TASK_STYLE_PLACEHOLDER_KEY: dict[AiTaskType, str] = {
    AiTaskType.POLISH: "ai.params.style_placeholder.polish",
    AiTaskType.EXPAND: "ai.params.style_placeholder.expand",
    AiTaskType.CONTINUE: "ai.params.style_placeholder.continue",
    AiTaskType.SUMMARIZE: "ai.params.style_placeholder.summarize",
    AiTaskType.OUTLINE: "ai.params.style_placeholder.outline",
    AiTaskType.TITLE: "ai.params.style_placeholder.title",
    AiTaskType.STRUCTURE_DIAGNOSE: "ai.params.style_placeholder.structure_diagnose",
    AiTaskType.CONSISTENCY_CHECK: "ai.params.style_placeholder.consistency_check",
    AiTaskType.LIBRARY_QA: "ai.params.style_placeholder.library_qa",
}

_TASK_STYLE_PRESET_VALUES_KEY: dict[AiTaskType, str] = {
    AiTaskType.POLISH: "ai.params.style_presets.polish_values",
    AiTaskType.EXPAND: "ai.params.style_presets.expand_values",
    AiTaskType.CONTINUE: "ai.params.style_presets.continue_values",
    AiTaskType.SUMMARIZE: "ai.params.style_presets.summarize_values",
    AiTaskType.OUTLINE: "ai.params.style_presets.outline_values",
    AiTaskType.TITLE: "ai.params.style_presets.title_values",
    AiTaskType.STRUCTURE_DIAGNOSE: "ai.params.style_presets.structure_values",
    AiTaskType.CONSISTENCY_CHECK: "ai.params.style_presets.consistency_values",
    AiTaskType.LIBRARY_QA: "ai.params.style_presets.library_qa_values",
}

_TASK_DESCRIPTION_KEY: dict[AiTaskType, str] = {
    AiTaskType.POLISH: "ai.task_desc.polish",
    AiTaskType.EXPAND: "ai.task_desc.expand",
    AiTaskType.CONTINUE: "ai.task_desc.continue",
    AiTaskType.SUMMARIZE: "ai.task_desc.summarize",
    AiTaskType.OUTLINE: "ai.task_desc.outline",
    AiTaskType.TITLE: "ai.task_desc.title",
    AiTaskType.STRUCTURE_DIAGNOSE: "ai.task_desc.structure_diagnose",
    AiTaskType.CONSISTENCY_CHECK: "ai.task_desc.consistency_check",
    AiTaskType.LIBRARY_QA: "ai.task_desc.library_qa",
}

_TASK_CONTROL_LABEL_KEY: dict[AiTaskType, str] = {
    AiTaskType.POLISH: "ai.params.control.polish",
    AiTaskType.EXPAND: "ai.params.control.expand",
    AiTaskType.CONTINUE: "ai.params.control.continue",
    AiTaskType.SUMMARIZE: "ai.params.control.summarize",
    AiTaskType.OUTLINE: "ai.params.control.outline",
    AiTaskType.TITLE: "ai.params.control.title",
    AiTaskType.STRUCTURE_DIAGNOSE: "ai.params.control.structure_diagnose",
    AiTaskType.CONSISTENCY_CHECK: "ai.params.control.consistency_check",
    AiTaskType.LIBRARY_QA: "ai.params.control.library_qa",
}

_TASK_INTENSITY_LABEL_KEY: dict[AiTaskType, str] = {
    AiTaskType.POLISH: "ai.params.intensity.polish",
    AiTaskType.EXPAND: "ai.params.intensity.expand",
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


def _preset_values(key: str) -> List[str]:
    return [item.strip() for item in TR(key).split("|") if item.strip()]


def _render_outline_items(items: list, *, level: int = 0) -> str:
    lines: list[str] = []
    indent = "  " * level
    for raw in items:
        if isinstance(raw, dict):
            title = str(raw.get("title") or raw.get("text") or "").strip()
            if title:
                lines.append(f"{indent}- {title}")
            children = raw.get("children") or raw.get("items") or []
            if isinstance(children, list) and children:
                child_text = _render_outline_items(children, level=level + 1)
                if child_text:
                    lines.append(child_text)
        elif raw:
            lines.append(f"{indent}- {raw}")
    return "\n".join(lines)


def _display_provider_name(provider: str) -> str:
    key = (provider or "").strip().lower()
    if key == "gemini_cli":
        return "Gemini CLI / OAuth"
    if key == "gemini":
        return "Gemini"
    if key == "openai":
        return "GPT / OpenAI"
    return provider or ""


class _FlowLayout(QLayout):
    """Wrap preset buttons to the next row instead of squeezing text."""

    def __init__(self, parent: Optional[QWidget] = None, spacing: int = 6) -> None:
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

    def addItem(self, item) -> None:  # type: ignore[override]
        self._items.append(item)

    def count(self) -> int:  # type: ignore[override]
        return len(self._items)

    def itemAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # type: ignore[override]
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        space_x = max(self.spacing(), 0)
        space_y = max(self.spacing(), 0)
        effective_right = rect.x() + rect.width()

        for item in self._items:
            hint = item.sizeHint().expandedTo(item.minimumSize())
            next_x = x + hint.width() + space_x
            if next_x - space_x > effective_right and line_height > 0:
                x = rect.x()
                y += line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y()


# ---------------------------------------------------------------------------
# Tools tab
# ---------------------------------------------------------------------------


class AIToolsTab(QWidget):
    """Run a structured AI task and land the result safely."""

    request_save_as_fragment = Signal(str)  # new fragment id
    request_send_to_chat = Signal(str)  # text to seed chat
    request_locate_excerpt = Signal(str)
    request_locate_selection = Signal(object)
    request_focus_writing_notes = Signal()
    request_fragment_changed = Signal(str)

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("AIToolsTab")
        self._container = container
        self._scope: Optional[AiScope] = None
        self._attachments: List[AiContextAttachment] = []
        self._last_response: Optional[AiTaskResponse] = None
        self._last_request: Optional[AiTaskRequest] = None
        self._worker: Optional[AiTaskWorker] = None
        self._style_preset_buttons: dict[str, QPushButton] = {}
        self._style_author_presets = _preset_values("ai.params.style_authors_values")
        self._style_goal_presets = _preset_values("ai.params.style_goals_values")
        self._last_excerpt: str = ""
        self._last_fragment_undo: Optional[tuple[str, str]] = None
        # Per-task parameter state — isolates style/intensity/extra across tasks.
        self._task_params: dict[AiTaskType, dict] = {}
        # Per-task result state — prevents one task's output from bleeding into another.
        self._task_results: dict[AiTaskType, AiTaskResultState] = {}
        self._custom_task_presets: dict[str, list[str]] = (
            self._container.settings.load_ai_custom_task_presets()
        )

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
        right.setObjectName("AIToolsRight")
        right.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        self._scope_label = QLabel(TR("ai.scope_none"))
        self._scope_label.setObjectName("AIScopeLabel")
        self._scope_label.setWordWrap(True)
        right_layout.addWidget(self._scope_label)

        self._selection_card = QFrame()
        self._selection_card.setObjectName("AISelectionCard")
        selection_layout = QVBoxLayout(self._selection_card)
        selection_layout.setContentsMargins(12, 10, 12, 10)
        selection_layout.setSpacing(6)

        selection_header = QHBoxLayout()
        self._selection_title = QLabel(TR("ai.selection.title"))
        self._selection_title.setObjectName("AISelectionTitle")
        selection_header.addWidget(self._selection_title)
        selection_header.addStretch(1)
        self._selection_copy_btn = QPushButton(TR("ai.selection.copy"))
        self._selection_copy_btn.setObjectName("GhostButton")
        self._selection_copy_btn.clicked.connect(self._copy_selection)
        selection_header.addWidget(self._selection_copy_btn)
        self._selection_locate_btn = QPushButton(TR("ai.selection.locate"))
        self._selection_locate_btn.setObjectName("GhostButton")
        self._selection_locate_btn.clicked.connect(self._locate_selection)
        selection_header.addWidget(self._selection_locate_btn)
        selection_layout.addLayout(selection_header)

        self._selection_meta = QLabel("")
        self._selection_meta.setObjectName("AISelectionMeta")
        selection_layout.addWidget(self._selection_meta)

        self._selection_view = QPlainTextEdit()
        self._selection_view.setObjectName("AISelectionPreview")
        self._selection_view.setReadOnly(True)
        _set_relaxed_vertical_sizing(
            self._selection_view,
            minimum=96,
            maximum=220,
        )
        selection_layout.addWidget(self._selection_view)
        self._selection_card.setVisible(False)
        right_layout.addWidget(self._selection_card)

        self._task_desc_label = QLabel("")
        self._task_desc_label.setObjectName("AITaskDesc")
        self._task_desc_label.setWordWrap(True)
        right_layout.addWidget(self._task_desc_label)

        # Parameters
        params_box = QFrame()
        params_box.setObjectName("AIParamsBox")
        params_form = QFormLayout(params_box)
        params_form.setContentsMargins(0, 0, 0, 0)

        self._target_combo = NoWheelComboBox()
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

        self._tier_combo = NoWheelComboBox()
        for tier in (AiCostTier.THRIFTY, AiCostTier.BALANCED, AiCostTier.STRONG):
            self._tier_combo.addItem(TR(_TIER_LABEL_KEY[tier]), tier)
        self._tier_combo.setCurrentIndex(1)
        self._tier_field = QWidget()
        self._tier_field.setObjectName("AITierField")
        self._tier_field_layout = QVBoxLayout(self._tier_field)
        self._tier_field_layout.setContentsMargins(0, 0, 0, 0)
        self._tier_field_layout.setSpacing(4)
        self._tier_field_layout.addWidget(self._tier_combo)
        self._tier_hint_label = QLabel(TR("ai.params.cost_tier_hint"))
        self._tier_hint_label.setObjectName("AITierHint")
        self._tier_hint_label.setWordWrap(True)
        self._tier_field_layout.addWidget(self._tier_hint_label)
        params_form.addRow(TR("ai.params.cost_tier"), self._tier_field)
        self._tier_field_label = params_form.labelForField(self._tier_field)

        self._output_combo = NoWheelComboBox()
        params_form.addRow(TR("ai.output.label"), self._output_combo)

        self._style_edit = QLineEdit()
        self._style_edit.setPlaceholderText(TR("ai.params.style_placeholder.polish"))
        self._style_field = QWidget()
        self._style_field.setObjectName("AIStyleField")
        self._style_field_layout = QVBoxLayout(self._style_field)
        self._style_field_layout.setContentsMargins(0, 0, 0, 0)
        self._style_field_layout.setSpacing(4)
        self._style_field_layout.addWidget(self._style_edit)
        self._style_hint_label = QLabel("")
        self._style_hint_label.setObjectName("AIStyleHint")
        self._style_hint_label.setWordWrap(True)
        self._style_field_layout.addWidget(self._style_hint_label)
        self._style_presets_box = QWidget()
        self._style_presets_box.setObjectName("AIStylePresets")
        self._style_presets_layout = QVBoxLayout(self._style_presets_box)
        self._style_presets_layout.setContentsMargins(0, 0, 0, 0)
        self._style_presets_layout.setSpacing(4)
        self._style_field_layout.addWidget(self._style_presets_box)
        custom_preset_row = QHBoxLayout()
        custom_preset_row.setContentsMargins(0, 0, 0, 0)
        self._save_custom_preset_btn = QPushButton(TR("ai.params.save_custom_preset"))
        self._save_custom_preset_btn.setObjectName("AIStylePresetSaveButton")
        self._save_custom_preset_btn.clicked.connect(self._on_save_custom_preset)
        custom_preset_row.addWidget(self._save_custom_preset_btn)
        custom_preset_row.addStretch(1)
        self._style_field_layout.addLayout(custom_preset_row)
        params_form.addRow(TR("ai.params.style"), self._style_field)
        self._style_field_label = params_form.labelForField(self._style_field)

        self._intensity_combo = NoWheelComboBox()
        for label, value in (
            ("—", ""),
            ("light", "light"),
            ("medium", "medium"),
            ("strong", "strong"),
        ):
            self._intensity_combo.addItem(label, value)
        params_form.addRow(TR("ai.params.intensity"), self._intensity_combo)
        self._intensity_label = params_form.labelForField(self._intensity_combo)

        right_layout.addWidget(params_box)

        self._extra_edit = QPlainTextEdit()
        self._extra_edit.setObjectName("AIExtraInstructions")
        _set_relaxed_vertical_sizing(
            self._extra_edit,
            minimum=88,
            maximum=180,
        )
        self._extra_edit.setPlaceholderText(TR("ai.params.extra_placeholder.polish"))
        right_layout.addWidget(QLabel(TR("ai.params.extra_instructions")))
        right_layout.addWidget(self._extra_edit)

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
        self._max_output_spin = NoWheelSpinBox()
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
        _set_relaxed_vertical_sizing(
            self._paste_edit,
            minimum=128,
            maximum=260,
        )
        self._paste_edit.setVisible(False)
        right_layout.addWidget(self._paste_edit)
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        self._paste_edit.textChanged.connect(self._refresh_attachments_view)
        self._output_combo.currentIndexChanged.connect(self._refresh_apply_button_state)

        # Attachments
        self._include_writing_notes_check = QCheckBox()
        self._include_writing_notes_check.setObjectName("AIWritingNotesCheck")
        self._include_writing_notes_check.toggled.connect(
            self._on_include_writing_notes_toggled
        )
        self._writing_notes_status_label = QLabel("")
        self._writing_notes_status_label.setObjectName("AIWritingNotesStatus")
        self._writing_notes_status_label.setWordWrap(True)
        self._include_writing_notes_hint = QLabel(TR("ai.attachments.writing_notes_hint"))
        self._include_writing_notes_hint.setObjectName("AIAttachTotal")
        self._include_writing_notes_hint.setWordWrap(True)
        writing_notes_box = QFrame()
        writing_notes_box.setObjectName("AIWritingNotesBox")
        writing_notes_layout = QVBoxLayout(writing_notes_box)
        writing_notes_layout.setContentsMargins(10, 8, 10, 8)
        writing_notes_layout.setSpacing(6)
        writing_notes_layout.addWidget(self._include_writing_notes_check)
        writing_notes_layout.addWidget(self._writing_notes_status_label)
        writing_notes_layout.addWidget(self._include_writing_notes_hint)
        self._writing_notes_preview = QPlainTextEdit()
        self._writing_notes_preview.setObjectName("AIWritingNotesPreview")
        self._writing_notes_preview.setReadOnly(True)
        _set_relaxed_vertical_sizing(
            self._writing_notes_preview,
            minimum=84,
            maximum=180,
        )
        writing_notes_layout.addWidget(self._writing_notes_preview)
        self._manage_writing_notes_btn = QPushButton(
            TR("ai.attachments.manage_writing_notes_add")
        )
        self._manage_writing_notes_btn.setObjectName("GhostButton")
        self._manage_writing_notes_btn.clicked.connect(
            self.request_focus_writing_notes.emit
        )
        writing_notes_layout.addWidget(self._manage_writing_notes_btn)
        self._writing_notes_box = writing_notes_box
        right_layout.addWidget(self._writing_notes_box)

        attach_label = QLabel(TR("ai.attachments.title"))
        attach_label.setObjectName("AIAttachLabel")
        right_layout.addWidget(attach_label)
        self._attach_empty_label = QLabel(TR("ai.attachments.empty"))
        self._attach_empty_label.setWordWrap(True)
        self._attach_empty_label.setObjectName("AIAttachEmpty")
        right_layout.addWidget(self._attach_empty_label)
        self._attach_list = QListWidget()
        _set_relaxed_vertical_sizing(
            self._attach_list,
            minimum=96,
            maximum=220,
            policy=QSizePolicy.Policy.MinimumExpanding,
        )
        self._attach_list.setVisible(False)
        right_layout.addWidget(self._attach_list)
        attach_btn_row = QHBoxLayout()
        self._add_fragment_btn = QPushButton(TR("ai.attachments.add_fragment"))
        self._add_fragment_btn.clicked.connect(self._on_add_fragment_attachment)
        attach_btn_row.addWidget(self._add_fragment_btn)
        self._add_specimen_btn = QPushButton(TR("ai.attachments.add_specimen"))
        self._add_specimen_btn.clicked.connect(self._on_add_specimen_attachment)
        attach_btn_row.addWidget(self._add_specimen_btn)
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
            lambda *_: self._remove_attach_btn.setEnabled(
                self._attach_list.currentItem() is not None
            )
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

        # Result area — compare layout (side-by-side) for rewrite tasks,
        # single-pane for report tasks.
        #
        # Source pane (left — hidden until a compare-mode task completes).
        self._source_widget = QWidget()
        self._source_widget.setObjectName("AISourceWidget")
        source_layout_v = QVBoxLayout(self._source_widget)
        source_layout_v.setContentsMargins(0, 0, 0, 0)
        source_layout_v.setSpacing(4)
        self._source_header = QLabel(TR("ai.compare.source_label"))
        self._source_header.setObjectName("AISourceHeader")
        source_layout_v.addWidget(self._source_header)
        self._source_view = QTextEdit()
        self._source_view.setReadOnly(True)
        self._source_view.setObjectName("AISourceView")
        self._source_view.setPlaceholderText("")
        source_layout_v.addWidget(self._source_view, 1)

        # Result pane (right — always present inside splitter).
        self._result_widget = QWidget()
        self._result_widget.setObjectName("AIResultWidget")
        result_widget_layout = QVBoxLayout(self._result_widget)
        result_widget_layout.setContentsMargins(0, 0, 0, 0)
        result_widget_layout.setSpacing(4)
        self._result_header = QLabel(TR("ai.compare.result_label"))
        self._result_header.setObjectName("AIResultHeader")
        self._result_header.setVisible(False)  # only in compare mode
        result_widget_layout.addWidget(self._result_header)
        self._result_view = QTextEdit()
        self._result_view.setReadOnly(False)
        self._result_view.setObjectName("AIResultView")
        self._result_view.setPlaceholderText(TR("ai.results.empty"))
        result_widget_layout.addWidget(self._result_view, 1)

        # Splitter container (source | result)
        self._results_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._results_splitter.setObjectName("AIResultsSplitter")
        self._results_splitter.addWidget(self._source_widget)
        self._results_splitter.addWidget(self._result_widget)
        self._results_splitter.setStretchFactor(0, 1)
        self._results_splitter.setStretchFactor(1, 1)
        # Initially hide the source side.
        self._source_widget.setVisible(False)
        right_layout.addWidget(self._results_splitter, 1)

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
        self._apply_btn.setToolTip(TR("ai.results.apply_disabled_no_result"))
        self._apply_btn.clicked.connect(self._on_apply)
        action_row.addWidget(self._apply_btn)
        self._save_fragment_btn = QPushButton(TR("ai.results.save_fragment"))
        self._save_fragment_btn.setEnabled(False)
        self._save_fragment_btn.clicked.connect(self._on_save_fragment)
        action_row.addWidget(self._save_fragment_btn)
        self._send_chat_btn = QPushButton(TR("ai.results.send_to_chat"))
        self._send_chat_btn.setEnabled(False)
        self._send_chat_btn.clicked.connect(self._on_send_to_chat)
        self._send_chat_btn.setVisible(False)
        action_row.addWidget(self._send_chat_btn)
        self._locate_excerpt_btn = QPushButton(TR("ai.results.locate_excerpt"))
        self._locate_excerpt_btn.setEnabled(False)
        self._locate_excerpt_btn.clicked.connect(self._on_locate_excerpt)
        action_row.addWidget(self._locate_excerpt_btn)
        self._clear_result_btn = QPushButton(TR("ai.results.clear_current"))
        self._clear_result_btn.setEnabled(False)
        self._clear_result_btn.clicked.connect(self._on_clear_current_result)
        action_row.addWidget(self._clear_result_btn)
        self._clear_all_results_btn = QPushButton(TR("ai.results.clear_all"))
        self._clear_all_results_btn.clicked.connect(self._on_clear_all_results)
        action_row.addWidget(self._clear_all_results_btn)
        self._undo_apply_btn = QPushButton(TR("ai.results.undo_last_apply"))
        self._undo_apply_btn.setEnabled(False)
        self._undo_apply_btn.setVisible(False)
        self._undo_apply_btn.clicked.connect(self._on_undo_last_apply)
        action_row.addWidget(self._undo_apply_btn)
        action_row.addStretch(1)
        right_layout.addLayout(action_row)

        # ---- Splitter ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("AIToolsSplitter")
        splitter.addWidget(self._task_list)
        right_scroll = QScrollArea()
        right_scroll.setObjectName("AIToolsScroll")
        right_scroll.viewport().setObjectName("AIToolsViewport")
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
        self._refresh_task_params()
        self._refresh_writing_notes_option()
        self._refresh_attachments_view()
        self._refresh_apply_button_state()
        self._refresh_fragment_undo_button()

    # ---- public API ----
    def bind_scope(self, scope: AiScope) -> None:
        self._scope = scope
        self._update_scope_label()
        self._refresh_selection_card()
        self._refresh_output_combo()
        # Reset target default per scope.
        target_default = {
            AiThreadScope.FRAGMENT: (
                AiTargetKind.SELECTION
                if scope.has_selection and bool(scope.selection_text.strip())
                else AiTargetKind.FRAGMENT
            ),
            AiThreadScope.WORK: (
                AiTargetKind.SELECTION
                if scope.has_selection and bool(scope.selection_text.strip())
                else AiTargetKind.WORK
            ),
            AiThreadScope.COLLECTION: AiTargetKind.COLLECTION,
            AiThreadScope.GLOBAL: AiTargetKind.PASTE,
        }[scope.kind]
        idx = self._target_combo.findData(target_default)
        if idx >= 0:
            self._target_combo.setCurrentIndex(idx)
        self._apply_writing_notes_default_for_task(self._current_task_type())
        self._refresh_writing_notes_option()
        self._refresh_attachments_view()
        self._refresh_apply_button_state()
        self._refresh_fragment_undo_button()

    def focus_task(
        self,
        task_type: AiTaskType,
        target_kind: Optional[AiTargetKind] = None,
    ) -> None:
        """Select *task_type* in the task list and, optionally, set the target.

        Used by ``AIWorkspacePanel.focus_task`` to pre-select a task when
        entering the workspace from an external trigger (e.g. context pane).
        """
        row = next(
            (
                i
                for i in range(self._task_list.count())
                if self._task_list.item(i).data(Qt.ItemDataRole.UserRole) == task_type
            ),
            0,
        )
        self._task_list.setCurrentRow(row)
        if target_kind is not None:
            idx = self._target_combo.findData(target_kind)
            if idx >= 0:
                self._target_combo.setCurrentIndex(idx)

    def set_include_writing_notes(self, enabled: bool) -> None:
        self._include_writing_notes_check.setChecked(bool(enabled))
        self._refresh_attachments_view()

    # ---- internal ----
    def _on_include_writing_notes_toggled(self, _checked: bool) -> None:
        self._refresh_writing_notes_guidance()
        self._refresh_attachments_view()

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

    def _refresh_selection_card(self) -> None:
        scope = self._scope
        has_selection = bool(scope and scope.has_selection and scope.selection_text.strip())
        self._selection_card.setVisible(has_selection)
        if not has_selection or scope is None:
            self._selection_meta.setText(TR("ai.selection.empty"))
            self._selection_view.setPlainText("")
            return
        text = scope.selection_text
        self._selection_meta.setText(
            TR("ai.selection.source").format(name=scope.name, chars=len(text))
        )
        self._selection_view.setPlainText(text)

    def _copy_selection(self) -> None:
        if self._scope is not None and self._scope.has_selection:
            QApplication.clipboard().setText(self._scope.selection_text)

    def _locate_selection(self) -> None:
        if self._scope is not None and self._scope.has_selection:
            self.request_locate_selection.emit(self._scope)

    def _on_task_changed(self, current, previous) -> None:
        # Save params for the task we're leaving.
        if previous is not None:
            prev_val = previous.data(Qt.ItemDataRole.UserRole)
            try:
                prev_task = prev_val if isinstance(prev_val, AiTaskType) else AiTaskType(prev_val)
                self._task_params[prev_task] = self._read_current_params()
                self._task_results[prev_task] = self._capture_current_result_state()
            except (TypeError, ValueError):
                pass
        new_task: Optional[AiTaskType] = None
        # Restore params for the task we're entering.
        if current is not None:
            new_val = current.data(Qt.ItemDataRole.UserRole)
            try:
                new_task = new_val if isinstance(new_val, AiTaskType) else AiTaskType(new_val)
                self._apply_task_params(new_task)
            except (TypeError, ValueError):
                pass
        self._refresh_output_combo()
        self._refresh_task_params()
        if new_task is not None:
            self._refresh_writing_notes_option()
            self._apply_result_state(
                self._task_results.get(new_task, AiTaskResultState())
            )

    # ---- task parameter isolation ----

    def _read_current_params(self) -> dict:
        return {
            "style": self._style_edit.text(),
            "intensity_data": self._intensity_combo.currentData(),
            "extra": self._extra_edit.toPlainText(),
            "max_output": self._max_output_spin.value(),
            "preserve_meaning": self._preserve_meaning_check.isChecked(),
            "preserve_voice": self._preserve_voice_check.isChecked(),
            "must_keep": self._must_keep_edit.text(),
            "forbid": self._forbid_edit.text(),
            "include_writing_notes": self._include_writing_notes_check.isChecked(),
        }

    def _apply_task_params(self, task: AiTaskType) -> None:
        """Restore saved params for *task*, or reset to defaults."""
        params = self._task_params.get(task)
        if params is None:
            # First visit — reset to defaults.
            self._style_edit.clear()
            idx0 = self._intensity_combo.findData("")
            self._intensity_combo.setCurrentIndex(max(idx0, 0))
            self._extra_edit.clear()
            self._max_output_spin.setValue(0)
            self._preserve_meaning_check.setChecked(True)
            self._preserve_voice_check.setChecked(True)
            self._must_keep_edit.clear()
            self._forbid_edit.clear()
            self._apply_writing_notes_default_for_task(task)
            return
        self._style_edit.setText(params.get("style", ""))
        intensity_data = params.get("intensity_data", "")
        idx = self._intensity_combo.findData(intensity_data or "")
        self._intensity_combo.setCurrentIndex(max(idx, 0))
        self._extra_edit.setPlainText(params.get("extra", ""))
        self._max_output_spin.setValue(params.get("max_output", 0))
        self._preserve_meaning_check.setChecked(params.get("preserve_meaning", True))
        self._preserve_voice_check.setChecked(params.get("preserve_voice", True))
        self._must_keep_edit.setText(params.get("must_keep", ""))
        self._forbid_edit.setText(params.get("forbid", ""))
        self._include_writing_notes_check.setChecked(
            params.get(
                "include_writing_notes",
                self._writing_notes_default_enabled(task),
            )
        )

    def _writing_notes_default_enabled(self, task: AiTaskType) -> bool:
        return task in _WRITING_NOTE_DEFAULT_TASKS

    def _apply_writing_notes_default_for_task(self, task: AiTaskType) -> None:
        self._include_writing_notes_check.setChecked(
            self._writing_notes_default_enabled(task)
        )

    def _refresh_task_params(self) -> None:
        task = self._current_task_type()
        show_style = True
        self._style_field.setVisible(show_style)
        self._save_custom_preset_btn.setVisible(show_style)
        if self._style_field_label is not None:
            self._style_field_label.setVisible(show_style)
            self._style_field_label.setText(
                TR(_TASK_CONTROL_LABEL_KEY.get(task, "ai.params.style"))
            )
        self._task_desc_label.setText(
            TR(_TASK_DESCRIPTION_KEY.get(task, "ai.params.style_hint.default"))
        )

        show_intensity = task in _INTENSITY_TASKS
        self._intensity_combo.setVisible(show_intensity)
        if self._intensity_label is not None:
            self._intensity_label.setVisible(show_intensity)
            self._intensity_label.setText(
                TR(_TASK_INTENSITY_LABEL_KEY.get(task, "ai.params.intensity"))
            )
        if self._tier_field_label is not None:
            self._tier_field_label.setText(TR("ai.params.cost_tier"))

        if not show_style:
            self._rebuild_style_preset_sections([])
            return

        self._style_edit.setPlaceholderText(
            TR(_TASK_STYLE_PLACEHOLDER_KEY.get(task, "ai.params.style_placeholder"))
        )
        self._extra_edit.setPlaceholderText(TR(f"ai.params.extra_placeholder.{task.value}"))
        self._style_hint_label.setText(
            TR(_TASK_STYLE_HINT_KEY.get(task, "ai.params.style_hint.default"))
        )
        self._rebuild_style_preset_sections(self._style_sections_for_task(task))

    def _style_sections_for_task(self, task: AiTaskType) -> List[tuple[str, List[str], bool]]:
        sections: List[tuple[str, List[str], bool]]
        if task is AiTaskType.POLISH:
            sections = [
                (
                    TR("ai.params.quick_presets"),
                    _preset_values("ai.params.style_presets.polish_values"),
                    False,
                ),
                (TR("ai.params.style_authors"), self._style_author_presets, False),
                (TR("ai.params.style_goals"), self._style_goal_presets, False),
            ]
        else:
            values_key = _TASK_STYLE_PRESET_VALUES_KEY.get(task)
            sections = (
                [(TR("ai.params.quick_presets"), _preset_values(values_key), False)]
                if values_key
                else []
            )
        custom = self._custom_presets_for_task(task)
        if custom:
            sections.append((TR("ai.params.my_presets"), custom, True))
        return sections

    def _rebuild_style_preset_sections(
        self, sections: List[tuple[str, List[str], bool]]
    ) -> None:
        self._style_preset_buttons = {}
        while self._style_presets_layout.count():
            item = self._style_presets_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for title, values, custom in sections:
            if values:
                self._style_presets_layout.addWidget(
                    self._build_style_preset_section(title, values, custom=custom)
                )
        self._style_presets_box.setVisible(bool(sections))

    def _build_style_preset_section(
        self, title: str, values: List[str], *, custom: bool = False
    ) -> QWidget:
        section = QWidget()
        section.setObjectName("AIStylePresetSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(title)
        label.setObjectName("AIStylePresetLabel")
        layout.addWidget(label)

        buttons_layout = _FlowLayout(spacing=6)
        layout.addLayout(buttons_layout)
        for value in values:
            if custom:
                chip = QWidget()
                chip.setObjectName("AIStyleCustomPresetChip")
                chip_layout = QHBoxLayout(chip)
                chip_layout.setContentsMargins(0, 0, 0, 0)
                chip_layout.setSpacing(2)
            else:
                chip = None
                chip_layout = None
            button = QPushButton(value)
            button.setObjectName("AIStylePresetButton")
            button.setFlat(True)
            button.ensurePolished()
            text_width = button.fontMetrics().horizontalAdvance(value)
            text_height = button.fontMetrics().height()
            button.setMinimumWidth(max(button.sizeHint().width(), text_width + 48))
            button.setMinimumHeight(max(button.sizeHint().height(), text_height + 16, 36))
            button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            button.setToolTip(value)
            button.clicked.connect(
                lambda _checked=False, preset=value: self._append_style_preset(preset)
            )
            self._style_preset_buttons[value] = button
            if custom and chip is not None and chip_layout is not None:
                chip_layout.addWidget(button)
                delete_btn = QPushButton("×")
                delete_btn.setObjectName("AIStylePresetDeleteButton")
                delete_btn.setFlat(True)
                delete_btn.setToolTip(TR("ai.params.delete_custom_preset"))
                delete_btn.setMinimumSize(28, 28)
                delete_btn.clicked.connect(
                    lambda _checked=False, preset=value: self._delete_custom_preset(preset)
                )
                chip_layout.addWidget(delete_btn)
                buttons_layout.addWidget(chip)
            else:
                buttons_layout.addWidget(button)
        return section

    def _append_style_preset(self, value: str) -> None:
        current = self._style_edit.text().strip()
        if not current:
            self._style_edit.setText(value)
        elif value not in {
            part.strip() for part in current.replace(",", "，").split("，") if part.strip()
        }:
            separator = "，" if current_locale() == LOCALE_ZH_CN else ", "
            self._style_edit.setText(current + separator + value)
        self._style_edit.setFocus()

    def _custom_presets_for_task(self, task: AiTaskType) -> List[str]:
        return list(self._custom_task_presets.get(task.value, []))

    def _built_in_presets_for_task(self, task: AiTaskType) -> set[str]:
        values: list[str] = []
        for _title, section_values, custom in self._style_sections_for_task_without_custom(task):
            if not custom:
                values.extend(section_values)
        return {value.lower() for value in values}

    def _style_sections_for_task_without_custom(
        self, task: AiTaskType
    ) -> List[tuple[str, List[str], bool]]:
        if task is AiTaskType.POLISH:
            return [
                (
                    TR("ai.params.quick_presets"),
                    _preset_values("ai.params.style_presets.polish_values"),
                    False,
                ),
                (TR("ai.params.style_authors"), self._style_author_presets, False),
                (TR("ai.params.style_goals"), self._style_goal_presets, False),
            ]
        values_key = _TASK_STYLE_PRESET_VALUES_KEY.get(task)
        if values_key:
            return [(TR("ai.params.quick_presets"), _preset_values(values_key), False)]
        return []

    def _on_save_custom_preset(self) -> None:
        value = self._style_edit.text().strip()
        if not value:
            return
        task = self._current_task_type()
        existing = self._built_in_presets_for_task(task) | {
            item.lower() for item in self._custom_presets_for_task(task)
        }
        if value.lower() in existing:
            return
        task_values = self._custom_task_presets.setdefault(task.value, [])
        task_values.append(value)
        self._container.settings.save_ai_custom_task_presets(self._custom_task_presets)
        self._refresh_task_params()

    def _delete_custom_preset(self, value: str) -> None:
        task = self._current_task_type()
        presets = [
            item
            for item in self._custom_presets_for_task(task)
            if item.lower() != value.strip().lower()
        ]
        if presets:
            self._custom_task_presets[task.value] = presets
        else:
            self._custom_task_presets.pop(task.value, None)
        self._container.settings.save_ai_custom_task_presets(self._custom_task_presets)
        self._refresh_task_params()

    def _on_toggle_advanced(self, checked: bool) -> None:
        self._advanced_box.setVisible(checked)
        arrow = "▴" if checked else "▾"
        self._advanced_toggle.setText(TR("ai.params.advanced") + " " + arrow)

    def _on_target_changed(self) -> None:
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)
        self._paste_edit.setVisible(target == AiTargetKind.PASTE)
        self._refresh_output_combo()
        self._refresh_attachments_view()

    def _refresh_output_combo(self) -> None:
        prev = self._output_combo.currentData()
        self._output_combo.clear()
        scope = self._scope or AiScope(AiThreadScope.GLOBAL, None, "", "")
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)

        # Allowed outputs depend on both scope & target. We start from
        # scope-allowed and additionally restrict by target kind.
        allowed = set(_allowed_outputs(scope))
        if target == AiTargetKind.SELECTION:
            # Fragment and focused work-section selections can be replaced
            # safely; other selection-like targets degrade to preview/save-as.
            if scope.kind is AiThreadScope.FRAGMENT or (
                scope.kind is AiThreadScope.WORK and scope.has_section
            ):
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
            AiTaskType.SUMMARIZE,
            AiTaskType.OUTLINE,
            AiTaskType.TITLE,
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
        self._refresh_apply_button_state()

    def _refresh_apply_button_state(self) -> None:
        out = _combo_enum(self._output_combo, AiOutputAction, AiOutputAction.PREVIEW_ONLY)
        has_result = self._last_response is not None and bool(
            self._result_view.toPlainText().strip()
        )
        can_apply = has_result and out in {
            AiOutputAction.REPLACE_FRAGMENT,
            AiOutputAction.REPLACE_SELECTION,
            AiOutputAction.REPLACE_SECTION,
        }
        # Specific button text based on the destructive action.
        _action_text: dict[AiOutputAction, str] = {
            AiOutputAction.REPLACE_SELECTION: TR("ai.results.apply_replace_selection"),
            AiOutputAction.REPLACE_FRAGMENT: TR("ai.results.apply_replace_fragment"),
            AiOutputAction.REPLACE_SECTION: TR("ai.results.apply_replace_section"),
        }
        self._apply_btn.setText(_action_text.get(out, TR("ai.results.apply")))
        self._apply_btn.setEnabled(can_apply)
        if can_apply:
            self._apply_btn.setToolTip(TR("ai.results.apply_ready"))
        elif not has_result:
            self._apply_btn.setToolTip(TR("ai.results.apply_disabled_no_result"))
        else:
            self._apply_btn.setToolTip(TR("ai.results.apply_disabled_preview"))
        self._save_fragment_btn.setEnabled(has_result)
        self._clear_result_btn.setEnabled(has_result)

    def _clear_fragment_undo(self) -> None:
        self._last_fragment_undo = None
        self._refresh_fragment_undo_button()

    def _remember_fragment_undo(self, entry_id: str, restore_version_id: str) -> None:
        self._last_fragment_undo = (entry_id, restore_version_id)
        self._undo_apply_btn.setToolTip(TR("ai.results.undo_last_apply_hint"))
        self._refresh_fragment_undo_button()

    def _refresh_fragment_undo_button(self) -> None:
        if self._last_fragment_undo is None or self._scope is None:
            self._undo_apply_btn.setEnabled(False)
            self._undo_apply_btn.setVisible(False)
            return
        entry_id, _version_id = self._last_fragment_undo
        visible = (
            self._scope.kind is AiThreadScope.FRAGMENT
            and self._scope.ref_id == entry_id
        )
        self._undo_apply_btn.setVisible(visible)
        self._undo_apply_btn.setEnabled(visible)

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

    def _capture_current_result_state(self) -> AiTaskResultState:
        return AiTaskResultState(
            response=self._last_response,
            request=self._last_request,
            result_text=self._result_view.toPlainText(),
            source_text=self._source_view.toPlainText(),
            source_visible=not self._source_widget.isHidden(),
            result_header_visible=not self._result_header.isHidden(),
            meta_text=self._meta_label.text(),
            citations_text=self._citations_label.text(),
            citations_visible=not self._citations_label.isHidden(),
            last_excerpt=self._last_excerpt,
        )

    def _apply_result_state(self, state: AiTaskResultState) -> None:
        self._last_response = state.response
        self._last_request = state.request
        self._last_excerpt = state.last_excerpt
        self._result_view.setPlainText(state.result_text)
        self._source_view.setPlainText(state.source_text)
        self._source_widget.setVisible(state.source_visible)
        self._result_header.setVisible(state.result_header_visible)
        self._meta_label.setText(state.meta_text)
        self._citations_label.setText(state.citations_text)
        self._citations_label.setVisible(state.citations_visible)
        self._refresh_apply_button_state()
        self._refresh_send_to_chat_button()
        self._locate_excerpt_btn.setEnabled(bool(self._last_excerpt.strip()))

    def _empty_result_state(self, *, request: Optional[AiTaskRequest] = None) -> AiTaskResultState:
        return AiTaskResultState(request=request)

    def _pending_result_request(self) -> Optional[AiTaskRequest]:
        for state in self._task_results.values():
            if state.request is not None and state.response is None:
                return state.request
        return None

    def _on_clear_current_result(self) -> None:
        task = self._current_task_type()
        self._task_results.pop(task, None)
        self._apply_result_state(AiTaskResultState())
        self._status_label.setText("")

    def _on_clear_all_results(self) -> None:
        choice = QMessageBox.question(
            self,
            TR("ai.results.clear_all_confirm_title"),
            TR("ai.results.clear_all_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        self._task_results.clear()
        self._apply_result_state(AiTaskResultState())
        self._status_label.setText("")

    def _writing_note_count(self) -> int:
        return len(self._open_writing_notes())

    def _open_writing_notes(self):
        if self._scope is None or self._scope.kind is not AiThreadScope.FRAGMENT:
            return []
        if not self._scope.ref_id:
            return []
        try:
            notes = self._container.entry_writing_note_repository.list_for_entry(
                self._scope.ref_id
            )
            return sorted(
                notes,
                key=lambda note: (
                    not note.pinned,
                    int(note.board_y if note.board_y is not None else 999999),
                    int(note.board_x if note.board_x is not None else 999999),
                    int(note.sort_order or 0),
                ),
            )
        except Exception:  # noqa: BLE001
            return []

    def _writing_note_attachments(self) -> list[AiContextAttachment]:
        if not self._include_writing_notes_check.isChecked():
            return []
        notes = self._open_writing_notes()
        attachments: list[AiContextAttachment] = []
        for index, note in enumerate(notes, start=1):
            attachments.append(
                AiContextAttachment(
                    kind="writing_note",
                    ref_id=note.id,
                    name=TR("ai.attachments.writing_note_name").format(index=index),
                    body=TR("ai.attachments.writing_note_body").format(body=note.body),
                )
            )
        return attachments

    def _refresh_writing_notes_guidance(self, count: Optional[int] = None) -> None:
        if count is None:
            count = self._writing_note_count()
        task = self._current_task_type()
        task_label = TR(_TASK_LABEL_KEY.get(task, "ai.task.continue"))
        if count <= 0:
            key = "ai.attachments.writing_notes_status_empty"
        else:
            default_enabled = self._writing_notes_default_enabled(task)
            checked = self._include_writing_notes_check.isChecked()
            if checked and default_enabled:
                key = "ai.attachments.writing_notes_status_default_on"
            elif checked:
                key = "ai.attachments.writing_notes_status_manual_on"
            elif default_enabled:
                key = "ai.attachments.writing_notes_status_default_off"
            else:
                key = "ai.attachments.writing_notes_status_optional_off"
        self._writing_notes_status_label.setText(TR(key).format(task=task_label))

    def _refresh_writing_notes_option(self) -> None:
        notes = self._open_writing_notes()
        count = len(notes)
        visible = bool(
            self._scope is not None
            and self._scope.kind is AiThreadScope.FRAGMENT
        )
        self._writing_notes_box.setVisible(visible)
        self._include_writing_notes_check.setText(
            TR("ai.attachments.include_writing_notes").format(count=count)
        )
        self._include_writing_notes_check.setEnabled(count > 0)
        if count <= 0:
            self._include_writing_notes_check.setChecked(False)
            self._writing_notes_preview.setPlainText(
                TR("ai.attachments.writing_notes_empty")
            )
            self._manage_writing_notes_btn.setText(
                TR("ai.attachments.manage_writing_notes_add")
            )
        else:
            preview_lines = []
            for index, note in enumerate(notes[:4], start=1):
                clean = " ".join(note.body.split())
                if len(clean) > 70:
                    clean = clean[:67] + "..."
                preview_lines.append(f"{index}. {clean}")
            if len(notes) > 4:
                preview_lines.append(f"... +{len(notes) - 4}")
            self._writing_notes_preview.setPlainText(
                TR("ai.attachments.writing_notes_preview").format(
                    notes="\n".join(preview_lines)
                )
            )
            self._manage_writing_notes_btn.setText(
                TR("ai.attachments.manage_writing_notes_edit")
            )
        self._refresh_writing_notes_guidance(count)
        self._writing_notes_preview.setVisible(visible)
        self._manage_writing_notes_btn.setVisible(visible)
        self._refresh_attachments_view()

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
        total = self._estimated_context_chars()
        self._attach_total_label.setText(TR("ai.attachments.total").format(chars=total))
        over_budget = total > SOFT_CONTEXT_BUDGET_CHARS
        self._attach_total_label.setProperty("overBudget", over_budget)
        _refresh_widget_style(self._attach_total_label)
        if over_budget:
            self._attach_total_label.setToolTip(TR("ai.attachments.heavy_warning"))
        else:
            self._attach_total_label.setToolTip("")
        self._remove_attach_btn.setEnabled(self._attach_list.currentItem() is not None)

    def _estimated_context_chars(self) -> int:
        total = sum(a.size_chars for a in self._attachments)
        total += sum(a.size_chars for a in self._writing_note_attachments())
        scope = self._scope
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)
        if target == AiTargetKind.PASTE:
            total += len(self._paste_edit.toPlainText())
        elif scope is not None and target == AiTargetKind.SELECTION:
            total += len(scope.selection_text if scope.has_selection else "")
        elif scope is not None and target == AiTargetKind.WORK_SECTION:
            total += len(scope.body if scope.has_section else "")
        elif scope is not None:
            total += len(scope.body)
        return total

    def _current_target_uses_fragment(self, entry_id: str) -> bool:
        if self._scope is None or self._scope.kind is not AiThreadScope.FRAGMENT:
            return False
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)
        return (
            target in {AiTargetKind.FRAGMENT, AiTargetKind.SELECTION}
            and self._scope.ref_id == entry_id
        )

    def _has_attachment(self, *, kind: str, ref_id: str) -> bool:
        return any(att.kind == kind and att.ref_id == ref_id for att in self._attachments)

    def _try_add_fragment_attachment(self, entry) -> bool:
        if self._current_target_uses_fragment(entry.id):
            QMessageBox.information(
                self,
                TR("ai.attachments.title"),
                TR("ai.attachments.current_target"),
            )
            return False
        if self._has_attachment(kind="fragment", ref_id=entry.id):
            QMessageBox.information(
                self,
                TR("ai.attachments.title"),
                TR("ai.attachments.already_added"),
            )
            return False
        self._attachments.append(
            AiContextAttachment(
                kind="fragment",
                ref_id=entry.id,
                name=(entry.title or "(untitled)") + f" [{entry.id[:8]}]",
                body=entry.body or "",
            )
        )
        self._refresh_attachments_view()
        return True

    def _on_add_fragment_attachment(self) -> None:
        from writer.ui.dialogs.fragment_picker_dialog import FragmentPickerDialog  # lazy

        dlg = FragmentPickerDialog(self._container, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        entry = dlg.selected_entry
        if entry is None:
            return
        self._try_add_fragment_attachment(entry)

    def _on_add_specimen_attachment(self) -> None:
        from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog  # lazy

        repo = self._container.reference_repository
        preselected_ids = [
            att.ref_id
            for att in self._attachments
            if att.kind == "style_specimen" and att.ref_id
        ]
        dlg = SpecimenPickerDialog(
            repo,
            recommended_text=self._current_subject_text_for_recommendation(),
            preselected_ids=preselected_ids,
            settings=self._container.settings,
            parent=self,
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        passages = dlg.selected_passages
        preserved = [att for att in self._attachments if att.kind != "style_specimen"]
        selected_attachments: list[AiContextAttachment] = []
        for passage in passages:
            from writer.ui.panels.reference_library_panel import _usage_kind_label

            note_part = f"\n备注：{passage.personal_note}" if passage.personal_note else ""
            tags_part = f"\n标签：{passage.tags}" if passage.tags.strip() else ""
            body = (
                f"{passage.content}\n\n"
                f"作品名：{passage.source_title or TR('search.untitled')}"
                + (f"\n作者：{passage.source_author}" if passage.source_author else "")
                + f"\n用途：{_usage_kind_label(passage.usage_kind)}"
                + f"\n类型：{passage.kind}"
                + tags_part
                + note_part
            )
            selected_attachments.append(
                AiContextAttachment(
                    kind="style_specimen",
                    ref_id=passage.id,
                    name=passage.display_label(),
                    body=body,
                )
            )
        self._attachments = preserved + selected_attachments
        self._refresh_attachments_view()

    def _current_subject_text_for_recommendation(self) -> str:
        scope = self._scope
        target = _combo_enum(self._target_combo, AiTargetKind, AiTargetKind.PASTE)
        if target == AiTargetKind.PASTE:
            return self._paste_edit.toPlainText()
        if scope is None:
            return ""
        if target == AiTargetKind.SELECTION:
            return scope.selection_text if scope.has_selection else self._paste_edit.toPlainText()
        return scope.body

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
        output = _combo_enum(self._output_combo, AiOutputAction, AiOutputAction.PREVIEW_ONLY)

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
        intensity_val = (
            self._intensity_combo.currentData() or None
            if self._intensity_combo.isVisible()
            else None
        )

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
            AiTaskType.SUMMARIZE,
            AiTaskType.OUTLINE,
            AiTaskType.TITLE,
            AiTaskType.STRUCTURE_DIAGNOSE,
            AiTaskType.CONSISTENCY_CHECK,
            AiTaskType.LIBRARY_QA,
        }

        request = AiTaskRequest(
            task_type=task,
            target_kind=target,
            text=text,
            target_ref_id=target_ref,
            style=(
                self._style_edit.text().strip() or None if self._style_field.isVisible() else None
            ),
            intensity=intensity_val,
            extra_instructions=extra,
            max_output_chars=max_out,
            preserve_meaning=self._preserve_meaning_check.isChecked(),
            preserve_voice=self._preserve_voice_check.isChecked(),
            forbid_terms=forbid,
            must_keep_terms=must_keep,
            attachments=list(self._attachments) + self._writing_note_attachments(),
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
        provider = self._container.settings.load_ai_config().provider_key()
        self._status_label.setText(
            TR("ai.status.running_provider").format(provider=_display_provider_name(provider))
        )
        self._apply_result_state(self._empty_result_state(request=request))
        self._last_request = request
        self._task_results[request.task_type] = self._capture_current_result_state()

        worker = AiTaskWorker(self._container.ai_task_service, request, parent=self)
        worker.succeeded.connect(
            lambda response, request=request: self._on_task_succeeded(response, request)
        )
        worker.failed.connect(self._on_task_failed)
        worker.finished.connect(lambda: self._run_btn.setEnabled(True))
        self._worker = worker
        worker.start()

    def _on_task_succeeded(
        self,
        response: AiTaskResponse,
        request: Optional[AiTaskRequest] = None,
    ) -> None:
        request = request or self._last_request or self._pending_result_request()
        task_type = request.task_type if request is not None else self._current_task_type()
        last_excerpt = self._extract_excerpt(response)
        self._clear_fragment_undo()
        self._status_label.setText("")
        rendered = (
            self._render_structured(response, task_type=task_type) if response.structured else None
        )
        result_text = rendered if rendered is not None else response.content

        # Compare layout — show source pane for rewrite tasks.
        if task_type in _COMPARE_TASKS and request is not None:
            source_text = request.text
            source_visible = True
            result_header_visible = True
        else:
            source_text = ""
            source_visible = False
            result_header_visible = False

        meta_parts = []
        if response.provider:
            meta_parts.append(
                f"{TR('ai.results.provider_label')}: {_display_provider_name(response.provider)}"
            )
        if response.model:
            meta_parts.append(f"{TR('ai.results.model_label')}: {response.model}")
        if response.input_tokens is not None or response.output_tokens is not None:
            tokens = f"{response.input_tokens or 0}/{response.output_tokens or 0}"
            meta_parts.append(f"{TR('ai.results.tokens_label')}: {tokens}")
        meta_text = "  ·  ".join(meta_parts)

        if response.citations:
            cite_lines = [TR("ai.results.citations_label") + ":"]
            for c in response.citations:
                tag = TR("ai.results.unresolved") + " " if c.kind == "unresolved" else ""
                cite_lines.append(f"  • {tag}{c.name}")
            citations_text = "\n".join(cite_lines)
            citations_visible = True
        else:
            citations_text = ""
            citations_visible = False

        state = AiTaskResultState(
            response=response,
            request=request,
            result_text=result_text,
            source_text=source_text,
            source_visible=source_visible,
            result_header_visible=result_header_visible,
            meta_text=meta_text,
            citations_text=citations_text,
            citations_visible=citations_visible,
            last_excerpt=last_excerpt,
        )
        self._task_results[task_type] = state
        if self._current_task_type() == task_type:
            self._apply_result_state(state)

    def _result_task_type(self) -> AiTaskType:
        if self._last_request is not None:
            return self._last_request.task_type
        return self._current_task_type()

    def _refresh_send_to_chat_button(self) -> None:
        can_send = self._last_response is not None and bool(self._result_view.toPlainText().strip())
        self._send_chat_btn.setVisible(can_send)
        self._send_chat_btn.setEnabled(can_send)

    def _extract_excerpt(self, response: AiTaskResponse) -> str:
        data = response.structured or {}
        issues = data.get("issues") or []
        if isinstance(issues, list):
            for raw in issues:
                if not isinstance(raw, dict):
                    continue
                excerpt = str(raw.get("excerpt") or "").strip()
                if excerpt:
                    return excerpt
        excerpt = str(data.get("excerpt") or "").strip()
        return excerpt

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
        if task == AiTaskType.SUMMARIZE:
            lines: List[str] = []
            summary = str(data.get("summary") or data.get("core_summary") or "").strip()
            if summary:
                lines.append(TR("ai.render.summary") + "\n" + summary)
            for key, label_key in (
                ("key_facts", "ai.render.key_facts"),
                ("themes", "ai.render.themes"),
                ("keeper_lines", "ai.render.keeper_lines"),
            ):
                values = data.get(key) or []
                if isinstance(values, str):
                    values = [values]
                if isinstance(values, list) and values:
                    lines.append(TR(label_key) + "\n" + "\n".join(f"- {v}" for v in values))
            return "\n\n".join(lines) if lines else response.content
        if task == AiTaskType.OUTLINE:
            items = data.get("outline") or data.get("items") or []
            if isinstance(items, str):
                return items
            if isinstance(items, list):
                rendered = _render_outline_items(items)
                return rendered or response.content
            return response.content
        if task == AiTaskType.TITLE:
            groups = data.get("groups") or data.get("titles") or []
            if isinstance(groups, str):
                return groups
            if isinstance(groups, list):
                lines: List[str] = []
                for raw in groups:
                    if not isinstance(raw, dict):
                        lines.append(f"- {raw}")
                        continue
                    category = str(raw.get("category") or raw.get("type") or "").strip()
                    if category:
                        lines.append(category)
                    titles = raw.get("titles") or []
                    if isinstance(titles, str):
                        titles = [{"title": titles}]
                    for item in titles:
                        if isinstance(item, dict):
                            title = str(item.get("title") or "").strip()
                            reason = str(item.get("reason") or "").strip()
                            if title and reason:
                                lines.append(f"- {title}：{reason}")
                            elif title:
                                lines.append(f"- {title}")
                        elif item:
                            lines.append(f"- {item}")
                return "\n".join(lines) if lines else response.content
        if task == AiTaskType.LIBRARY_QA:
            answer = (data.get("answer") or "").strip()
            unconfirmed = data.get("unconfirmed") or []
            if isinstance(unconfirmed, str):
                unconfirmed = [unconfirmed]
            if unconfirmed:
                answer += (
                    "\n\n"
                    + TR("ai.render.unconfirmed")
                    + "\n"
                    + "\n".join(f"- {item}" for item in unconfirmed)
                )
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
                what = str(raw.get("what") or raw.get("issue") or raw.get("problem") or "").strip()
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
        out = _combo_enum(self._output_combo, AiOutputAction, AiOutputAction.PREVIEW_ONLY)
        text = self._result_view.toPlainText()  # honour any user edits
        if not self._confirm_destructive_apply(out, text):
            return
        if not self._validate_live_fragment_before_apply(out):
            return
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
                and self._scope.kind is AiThreadScope.FRAGMENT
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
                out == AiOutputAction.REPLACE_SELECTION
                and self._scope.has_section
                and self._scope.has_selection
            ):
                outcome = apply_to_section(
                    self._container,
                    work_id=self._scope.work_id,
                    section_id=self._scope.section_id,
                    generated_text=text,
                    original_section_body=self._scope.body,
                    selection_start=self._scope.selection_start,
                    selection_end=self._scope.selection_end,
                )
            elif out == AiOutputAction.REPLACE_SECTION and self._scope.has_section:
                outcome = apply_to_section(
                    self._container,
                    work_id=self._scope.work_id,
                    section_id=self._scope.section_id,
                    generated_text=text,
                )
            else:
                QMessageBox.warning(self, TR("ai.dlg.run_failed"), TR("ai.dlg.cannot_apply"))
                return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, TR("ai.dlg.run_failed"), str(exc))
            return
        self._after_apply(outcome)
        QMessageBox.information(
            self,
            TR("ai.results.apply"),
            TR("ai.dlg.applied").format(target=outcome.target_label),
        )

    def _confirm_destructive_apply(self, out: AiOutputAction, text: str) -> bool:
        if out not in {
            AiOutputAction.REPLACE_FRAGMENT,
            AiOutputAction.REPLACE_SELECTION,
            AiOutputAction.REPLACE_SECTION,
        }:
            return True
        scope = self._scope
        target_name = scope.name if scope is not None else ""
        source_chars = (
            len(scope.selection_text)
            if scope is not None and out == AiOutputAction.REPLACE_SELECTION
            else len(scope.body if scope is not None else "")
        )
        key = {
            AiOutputAction.REPLACE_SELECTION: "ai.confirm_apply.selection",
            AiOutputAction.REPLACE_FRAGMENT: "ai.confirm_apply.fragment",
            AiOutputAction.REPLACE_SECTION: "ai.confirm_apply.section",
        }[out]
        msg = TR(key).format(
            target=target_name or TR("ai.confirm_apply.unknown_target"),
            source_chars=source_chars,
            output_chars=len(text),
        )
        choice = QMessageBox.question(
            self,
            TR("ai.confirm_apply.title"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return choice == QMessageBox.StandardButton.Yes

    def _validate_live_fragment_before_apply(self, out: AiOutputAction) -> bool:
        if self._scope is None or self._scope.kind is not AiThreadScope.FRAGMENT:
            return True
        if out not in {
            AiOutputAction.REPLACE_FRAGMENT,
            AiOutputAction.REPLACE_SELECTION,
        }:
            return True
        if self._scope.ref_id is None:
            return False
        entry = self._container.entry_repository.get(self._scope.ref_id)
        if entry is None:
            QMessageBox.warning(
                self,
                TR("ai.dlg.cannot_apply_title"),
                TR("ai.dlg.target_missing"),
            )
            return False
        if (entry.body or "") != (self._scope.body or ""):
            QMessageBox.warning(
                self,
                TR("ai.dlg.cannot_apply_title"),
                TR("ai.dlg.target_changed"),
            )
            return False
        return True

    def _after_apply(self, outcome) -> None:
        if (
            self._scope is not None
            and self._scope.kind is AiThreadScope.FRAGMENT
            and self._scope.ref_id is not None
        ):
            if outcome.restore_version_id:
                self._remember_fragment_undo(
                    self._scope.ref_id,
                    outcome.restore_version_id,
                )
            if outcome.new_body is not None:
                self._scope.body = outcome.new_body
                self._scope.selection_start = None
                self._scope.selection_end = None
                self._scope.selection_text = ""
                self._refresh_selection_card()
                self._refresh_output_combo()
                self._refresh_attachments_view()
                self._refresh_apply_button_state()
            self.request_fragment_changed.emit(self._scope.ref_id)
        else:
            self._clear_fragment_undo()

    def _on_undo_last_apply(self) -> None:
        if self._last_fragment_undo is None:
            return
        entry_id, version_id = self._last_fragment_undo
        choice = QMessageBox.question(
            self,
            TR("ai.undo.title"),
            TR("ai.undo.confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            outcome = self._container.version_history_service.restore(entry_id, version_id)
        except ValueError as exc:
            QMessageBox.critical(self, TR("ai.undo.title"), str(exc))
            return
        if self._scope is not None and self._scope.ref_id == entry_id:
            self._scope.body = outcome.new_body
            self._scope.selection_start = None
            self._scope.selection_end = None
            self._scope.selection_text = ""
            self._refresh_selection_card()
            self._refresh_output_combo()
            self._refresh_attachments_view()
            self._refresh_apply_button_state()
        self._clear_fragment_undo()
        self.request_fragment_changed.emit(entry_id)
        QMessageBox.information(self, TR("ai.undo.title"), TR("ai.undo.done"))

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

    def _on_locate_excerpt(self) -> None:
        excerpt = self._last_excerpt.strip()
        if not excerpt:
            QMessageBox.information(
                self,
                TR("ai.results.locate_excerpt"),
                TR("ai.results.locate_excerpt_missing"),
            )
            return
        self.request_locate_excerpt.emit(excerpt)


# ---------------------------------------------------------------------------
# Chat tab
# ---------------------------------------------------------------------------


class AIChatTab(QWidget):
    """Free-form conversation persisted per scope."""

    request_save_as_fragment = Signal(str)  # new fragment id

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("AIChatTab")
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

        self._thread_info_label = QLabel("")
        self._thread_info_label.setObjectName("AIChatThreadInfo")
        self._thread_info_label.setWordWrap(True)
        layout.addWidget(self._thread_info_label)

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
        self._tier_combo = NoWheelComboBox()
        for tier in (AiCostTier.THRIFTY, AiCostTier.BALANCED, AiCostTier.STRONG):
            self._tier_combo.addItem(TR(_TIER_LABEL_KEY[tier]), tier)
        self._tier_combo.setCurrentIndex(1)
        self._tier_combo.currentIndexChanged.connect(self._refresh_thread_info)
        attach_row.addWidget(self._tier_combo)
        layout.addLayout(attach_row)

        self._input = QPlainTextEdit()
        self._input.setPlaceholderText(TR("ai.chat.input_placeholder").format(scope="object"))
        _set_relaxed_vertical_sizing(
            self._input,
            minimum=96,
            maximum=180,
        )
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
        self._refresh_thread_info()

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
        self._refresh_thread_info()

    def seed_input(self, text: str) -> None:
        self._input.setPlainText(text)

    # ---- internal ----
    def _update_scope_label(self) -> None:
        if self._scope is None or self._scope.is_global:
            self._scope_label.setText(TR("ai.scope_global"))
            self._input.setPlaceholderText(TR("ai.chat.input_placeholder").format(scope="object"))
            self._refresh_thread_info()
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
        self._refresh_thread_info()

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
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _refresh_attachments_label(self) -> None:
        if not self._attachments:
            self._attach_label.setText("")
            self._refresh_thread_info()
            return
        names = [a.name for a in self._attachments]
        self._attach_label.setText(TR("ai.chat.attachment_added").format(name=", ".join(names)))
        self._refresh_thread_info()

    def _refresh_thread_info(self) -> None:
        tier = _combo_enum(self._tier_combo, AiCostTier, AiCostTier.BALANCED)
        model = self._container.ai_task_service.model_for_tier(tier)
        if not model:
            model = self._container.settings.load_ai_config().model
        history_count = 0
        if self._thread_id is not None:
            history_count = len(self._container.ai_thread_service.history(self._thread_id))
        scope_chars = len(self._scope.body) if self._scope and not self._scope.is_global else 0
        attachment_chars = estimate_attachment_chars(self._attachments)
        estimated = scope_chars + attachment_chars
        self._thread_info_label.setText(
            TR("ai.chat.thread_info").format(
                model=model or TR("context.no_value"),
                messages=history_count,
                chars=estimated,
                budget=DEFAULT_CHAT_CONTEXT_BUDGET_CHARS,
            )
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
        omitted = turn.context_breakdown.omitted_history_count
        self._status_label.setText(
            TR("ai.chat.context_trimmed").format(count=omitted) if omitted else ""
        )
        self._append_message("assistant", turn.assistant_message.content)
        self._refresh_thread_info()

    def _on_chat_failed(self, message: str) -> None:
        self._status_label.setText("")
        QMessageBox.critical(self, TR("ai.dlg.run_failed"), message)

    def _on_save_last_assistant_as_fragment(self) -> None:
        if self._thread_id is None:
            return
        history = self._container.ai_thread_service.history(self._thread_id)
        last_assistant = next((m for m in reversed(history) if m.role == "assistant"), None)
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
    request_locate_excerpt = Signal(str)
    request_locate_selection = Signal(object)
    request_focus_writing_notes = Signal()
    request_fragment_changed = Signal(str)

    def __init__(self, container: AppContainer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("AIWorkspacePanel")
        self._container = container
        self._scope: Optional[AiScope] = None

        self._tools_tab = AIToolsTab(container, self)
        self._chat_tab = AIChatTab(container, self)
        self._tabs = QTabWidget()
        self._tabs.setObjectName("AIWorkspaceTabs")
        self._tabs.addTab(self._tools_tab, TR("ai.tab_tools"))
        self._tabs.addTab(self._chat_tab, TR("ai.tab_chat"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

        # Wire send-to-chat from tools to chat tab.
        self._tools_tab.request_send_to_chat.connect(self._on_send_to_chat)
        self._tools_tab.request_save_as_fragment.connect(self.request_save_as_fragment.emit)
        self._tools_tab.request_locate_excerpt.connect(self.request_locate_excerpt.emit)
        self._tools_tab.request_locate_selection.connect(
            self.request_locate_selection.emit
        )
        self._tools_tab.request_focus_writing_notes.connect(
            self.request_focus_writing_notes.emit
        )
        self._tools_tab.request_fragment_changed.connect(
            self.request_fragment_changed.emit
        )
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

    @property
    def scope(self) -> Optional[AiScope]:
        return self._scope

    def focus_task(
        self,
        task_type: AiTaskType,
        target_kind: Optional[AiTargetKind] = None,
    ) -> None:
        """Switch to the Tools tab, select *task_type*, and optionally set target."""
        self._tabs.setCurrentWidget(self._tools_tab)
        self._tools_tab.focus_task(task_type, target_kind=target_kind)

    def set_include_writing_notes(self, enabled: bool) -> None:
        self._tools_tab.set_include_writing_notes(enabled)
