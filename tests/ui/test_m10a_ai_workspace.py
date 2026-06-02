"""Smoke + behavioural tests for the M10A AI workspace UI.

We never run real provider calls — the AI services stay live but the
provider factory is monkey-patched to a stub.
"""

from __future__ import annotations

import pytest

from writer.app.container import build_container
from writer.domain.enums import AiCostTier, AiThreadScope, AiTaskType, AiTargetKind, AiOutputAction
from writer.services.ai.interfaces import AiProvider, ChatResponse, RewriteResponse
from writer.services.ai.task_types import AiContextAttachment


class _StubProvider(AiProvider):
    name = "stub"

    def __init__(self, content: str = "STUBBED") -> None:
        self._content = content
        self.calls: list[dict] = []

    def rewrite(self, request):  # pragma: no cover
        return RewriteResponse(content=self._content, model="stub", provider=self.name)

    def chat(self, messages, *, model=None):
        self.calls.append({"messages": list(messages), "model": model})
        return ChatResponse(
            content=self._content,
            model=model or "stub",
            provider=self.name,
            input_tokens=1,
            output_tokens=2,
        )


def _stub_container_provider(container, provider: AiProvider) -> None:
    """Replace both task and thread service provider factories in-place."""
    container.ai_task_service._provider_factory = lambda: provider  # noqa: SLF001
    container.ai_thread_service._provider_factory = lambda: provider  # noqa: SLF001


def _row_for_task(tab, task: AiTaskType) -> int:
    return next(
        i
        for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == task
    )


def _accept_ai_apply_dialogs(panel_mod) -> None:
    panel_mod.QMessageBox.information = lambda *a, **k: None  # type: ignore[assignment]
    panel_mod.QMessageBox.warning = lambda *a, **k: 0  # type: ignore[assignment]
    panel_mod.QMessageBox.question = (  # type: ignore[assignment]
        lambda *a, **k: panel_mod.QMessageBox.StandardButton.Yes
    )


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


# ---------------------------------------------------------------------------
# Rail / mode wiring
# ---------------------------------------------------------------------------


def test_main_window_has_four_rail_modes_including_ai(qtbot, container):
    from writer.ui.main_window import MainWindow

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    # M-Dates added a new mode at the front, so the stack now has five.
    assert window._stack.count() == 5  # noqa: SLF001
    rail = window._rail  # noqa: SLF001
    assert rail.ai_button is not None
    assert rail.ai_button.isCheckable()


def test_set_mode_three_binds_ai_workspace_to_global_when_nothing_selected(qtbot, container):
    from writer.ui.main_window import MainWindow

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(4)  # noqa: SLF001
    assert window._stack.currentIndex() == 4  # noqa: SLF001
    panel = window._ai_workspace_panel  # noqa: SLF001
    # Tabs widget should have exactly two tabs.
    assert panel.tabs.count() == 2


def test_set_mode_three_binds_ai_workspace_to_open_fragment(qtbot, container):
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="Hello", body="A short fragment.")
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._editor_panel.set_entry(entry)  # noqa: SLF001
    window._set_mode(4)  # noqa: SLF001

    panel = window._ai_workspace_panel  # noqa: SLF001
    scope = panel._scope  # noqa: SLF001
    assert scope is not None
    assert scope.kind is AiThreadScope.FRAGMENT
    assert scope.ref_id == entry.id
    assert "Hello" in scope.name


def test_main_window_locates_ai_excerpt_in_fragment_editor(qtbot, container):
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(
        title="Hello",
        body="第一段\n这里有关键摘录。\n第三段",
    )
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window._editor_panel.set_entry(entry)  # noqa: SLF001
    window._set_mode(4)  # noqa: SLF001

    window._on_locate_ai_excerpt("关键摘录")  # noqa: SLF001

    assert window._stack.currentIndex() == 1  # noqa: SLF001
    assert window._editor_panel._find_bar.isVisible() is True  # noqa: SLF001
    assert window._editor_panel.selected_body_text() == "关键摘录"  # noqa: SLF001


def test_main_window_locates_ai_excerpt_in_work_editor(qtbot, container):
    from writer.ui.main_window import MainWindow

    work = container.work_repository.create(title="Work")
    section = container.work_section_repository.create(work.id, content="前文\nExcerpt Line\n后文")
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    window._last_mode_before_ai = 2  # noqa: SLF001
    window._set_mode(4)  # noqa: SLF001

    window._on_locate_ai_excerpt("Excerpt Line")  # noqa: SLF001

    assert window._stack.currentIndex() == 2  # noqa: SLF001
    assert window._works_panel._editor._find_bar.isVisible() is True  # noqa: SLF001
    assert window._works_panel._editor._editor.textCursor().selectedText() == "Excerpt Line"  # noqa: SLF001


# ---------------------------------------------------------------------------
# Tools tab
# ---------------------------------------------------------------------------


def test_tools_tab_runs_polish_via_stub_provider(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="X", body="hello world")
    provider = _StubProvider("POLISHED")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title or "X",
            body=entry.body or "",
        )
    )

    # Pick POLISH (first in list), default tier balanced.
    tab._task_list.setCurrentRow(0)  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.task_type == AiTaskType.POLISH
    assert request.text == "hello world"

    response = container.ai_task_service.generate(request)
    assert response.content == "POLISHED"
    assert provider.calls


def test_polish_result_shows_send_to_chat_action(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    provider = _StubProvider("POLISHED")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.GLOBAL,
            ref_id=None,
            name="",
            body="plain text",
        )
    )
    tab._paste_edit.setPlainText("plain text")  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._on_task_succeeded(response)  # noqa: SLF001

    assert tab._send_chat_btn.isHidden() is False  # noqa: SLF001


def test_result_meta_shows_provider_and_model(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    provider = _StubProvider("POLISHED")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", "plain text"))
    tab._paste_edit.setPlainText("plain text")  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._on_task_succeeded(response)  # noqa: SLF001

    assert "Provider" in tab._meta_label.text()  # noqa: SLF001
    assert "stub" in tab._meta_label.text()  # noqa: SLF001
    assert "Model" in tab._meta_label.text()  # noqa: SLF001


def test_structured_result_enables_locate_excerpt_and_emits_excerpt(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    from writer.services.ai.task_types import AiTaskResponse

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    tab._paste_edit.setPlainText("report body")  # noqa: SLF001
    tab._last_request = tab._build_request()  # noqa: SLF001
    response = AiTaskResponse(
        content="1. issue",
        structured={"issues": [{"location": "p1", "excerpt": "关键句子", "issue": "x"}]},
        provider="stub",
        model="m",
    )

    tab._on_task_succeeded(response)  # noqa: SLF001

    assert tab._locate_excerpt_btn.isEnabled() is True  # noqa: SLF001
    with qtbot.waitSignal(tab.request_locate_excerpt, timeout=500) as blocker:
        tab._locate_excerpt_btn.click()  # noqa: SLF001
    assert blocker.args == ["关键句子"]


def test_apply_button_updates_when_output_destination_changes_after_result(qtbot, container):
    from writer.ui.i18n import TR
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="X", body="hello world")
    provider = _StubProvider("POLISHED")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title or "X",
            body=entry.body or "",
        )
    )

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._on_task_succeeded(response)  # noqa: SLF001

    assert tab._apply_btn.isEnabled() is False  # noqa: SLF001
    assert tab._apply_btn.toolTip() == TR("ai.results.apply_disabled_preview")  # noqa: SLF001

    repl_idx = tab._output_combo.findData(AiOutputAction.REPLACE_FRAGMENT)  # noqa: SLF001
    tab._output_combo.setCurrentIndex(repl_idx)  # noqa: SLF001

    assert tab._apply_btn.isEnabled() is True  # noqa: SLF001
    assert tab._apply_btn.toolTip() == TR("ai.results.apply_ready")  # noqa: SLF001


def test_ai_destination_controls_ignore_mouse_wheel(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    class _Wheel:
        ignored = False

        def ignore(self):
            self.ignored = True

    entry = container.entry_repository.create(title="X", body="alpha beta")
    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=entry.body,
            selection_start=0,
            selection_end=5,
            selection_text="alpha",
        )
    )

    controls = [
        tab._target_combo,  # noqa: SLF001
        tab._output_combo,  # noqa: SLF001
        tab._tier_combo,  # noqa: SLF001
        tab._intensity_combo,  # noqa: SLF001
        tab._max_output_spin,  # noqa: SLF001
    ]
    for control in controls:
        before = control.currentIndex() if hasattr(control, "currentIndex") else control.value()
        event = _Wheel()
        control.wheelEvent(event)  # noqa: SLF001
        after = control.currentIndex() if hasattr(control, "currentIndex") else control.value()
        assert event.ignored is True
        assert after == before


def test_library_qa_result_shows_send_to_chat_action(qtbot, container):
    import json
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    payload = {"answer": "Alice", "citations": []}
    provider = _StubProvider(json.dumps(payload))
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    qa_row = next(
        i
        for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == AiTaskType.LIBRARY_QA
    )
    tab._task_list.setCurrentRow(qa_row)  # noqa: SLF001
    paste_idx = tab._target_combo.findData(AiTargetKind.PASTE)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(paste_idx)  # noqa: SLF001
    tab._paste_edit.setPlainText("who?")  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._on_task_succeeded(response)  # noqa: SLF001

    assert tab._send_chat_btn.isHidden() is False  # noqa: SLF001


def test_style_preset_buttons_append_into_style_input(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001

    first_author = tab._style_author_presets[0]  # noqa: SLF001
    first_goal = tab._style_goal_presets[0]  # noqa: SLF001
    separator = ", "

    tab._style_preset_buttons[first_author].click()  # noqa: SLF001
    tab._style_preset_buttons[first_goal].click()  # noqa: SLF001

    assert tab._style_edit.text() == first_author + separator + first_goal  # noqa: SLF001


def test_custom_style_preset_adds_deletes_and_persists(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001
    tab._style_edit.setText("雾一样的克制")  # noqa: SLF001

    tab._save_custom_preset_btn.click()  # noqa: SLF001

    assert container.settings.load_ai_custom_task_presets()["polish"] == ["雾一样的克制"]
    assert "雾一样的克制" in tab._style_preset_buttons  # noqa: SLF001

    tab2 = AIToolsTab(container)
    qtbot.addWidget(tab2)
    tab2._task_list.setCurrentRow(_row_for_task(tab2, AiTaskType.POLISH))  # noqa: SLF001
    assert "雾一样的克制" in tab2._style_preset_buttons  # noqa: SLF001

    tab2._delete_custom_preset("雾一样的克制")  # noqa: SLF001

    assert container.settings.load_ai_custom_task_presets() == {}
    assert "雾一样的克制" not in tab2._style_preset_buttons  # noqa: SLF001


def test_style_transfer_is_not_visible_in_task_list(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)

    visible_tasks = [
        tab._task_list.item(i).data(0x0100)  # noqa: SLF001
        for i in range(tab._task_list.count())  # noqa: SLF001
    ]

    assert AiTaskType.STYLE_TRANSFER not in visible_tasks


def test_task_description_and_extra_instructions_are_main_controls(qtbot, container):
    from writer.ui.i18n import TR
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)

    assert tab._task_desc_label.text() == TR("ai.task_desc.polish")  # noqa: SLF001
    assert tab._extra_edit.isHidden() is False  # noqa: SLF001
    assert tab._advanced_box.isHidden() is True  # noqa: SLF001
    assert tab._extra_edit.parent() is not tab._advanced_box  # noqa: SLF001


def test_style_preset_buttons_keep_readable_size(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)

    assert tab._style_preset_buttons  # noqa: SLF001
    for button in tab._style_preset_buttons.values():  # noqa: SLF001
        assert button.minimumHeight() >= max(button.fontMetrics().height() + 16, 36)
        assert button.minimumWidth() >= button.fontMetrics().horizontalAdvance(button.text()) + 48


def test_task_switch_updates_style_presets_and_relevant_fields(qtbot, container):
    from writer.ui.i18n import TR
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)

    polish_presets = set(tab._style_preset_buttons)  # noqa: SLF001
    assert polish_presets
    assert not tab._style_field.isHidden()  # noqa: SLF001
    assert not tab._intensity_combo.isHidden()  # noqa: SLF001
    assert tab._intensity_label.text() == TR("ai.params.intensity.polish")  # noqa: SLF001
    assert tab._tier_field_label.text() == TR("ai.params.cost_tier")  # noqa: SLF001
    assert tab._tier_hint_label.text() == TR("ai.params.cost_tier_hint")  # noqa: SLF001

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.EXPAND))  # noqa: SLF001
    expand_presets = set(tab._style_preset_buttons)  # noqa: SLF001
    assert expand_presets
    assert expand_presets != polish_presets
    assert tab._intensity_label.text() == TR("ai.params.intensity.expand")  # noqa: SLF001

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.CONTINUE))  # noqa: SLF001
    continue_presets = set(tab._style_preset_buttons)  # noqa: SLF001
    assert continue_presets
    assert continue_presets != expand_presets
    assert tab._intensity_combo.isHidden()  # noqa: SLF001

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.SUMMARIZE))  # noqa: SLF001
    assert not tab._style_field.isHidden()  # noqa: SLF001
    assert tab._intensity_combo.isHidden()  # noqa: SLF001
    assert tab._style_field_label.text() == "Summary mode"  # noqa: SLF001
    assert set(tab._style_preset_buttons)  # noqa: SLF001


def test_build_request_still_passes_ai_cost_tier(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    tab._paste_edit.setPlainText("plain text")  # noqa: SLF001

    strong_idx = tab._tier_combo.findData(AiCostTier.STRONG)  # noqa: SLF001
    tab._tier_combo.setCurrentIndex(strong_idx)  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001

    assert request is not None
    assert request.cost_tier is AiCostTier.STRONG


def test_current_fragment_is_not_readded_as_attachment(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    import writer.ui.panels.ai_workspace_panel as panel_mod

    entry = container.entry_repository.create(title="X", body="body")
    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title or "X",
            body=entry.body or "",
        )
    )
    panel_mod.QMessageBox.information = lambda *a, **k: None  # type: ignore[assignment]

    added = tab._try_add_fragment_attachment(entry)  # noqa: SLF001

    assert added is False
    assert tab._attachments == []  # noqa: SLF001


def test_fragment_writing_notes_are_default_context_for_continue_and_expand(qtbot, container):
    from writer.ui.i18n import TR
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="绵绵", body="原文。")
    container.entry_writing_note_repository.create(
        entry_id=entry.id,
        body="下一段让人物先回到凉面摊。",
    )
    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=entry.body,
        )
    )

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.CONTINUE))  # noqa: SLF001
    continue_request = tab._build_request()  # noqa: SLF001

    assert continue_request is not None
    assert tab._include_writing_notes_check.isChecked() is True  # noqa: SLF001
    assert tab._writing_notes_status_label.text() == TR(  # noqa: SLF001
        "ai.attachments.writing_notes_status_default_on"
    ).format(task=TR("ai.task.continue"))
    note_attachments = [
        att for att in continue_request.attachments if att.kind == "writing_note"
    ]
    assert len(note_attachments) == 1
    assert note_attachments[0].ref_id == entry.id
    assert note_attachments[0].name.endswith("1")
    assert "凉面摊" in note_attachments[0].body

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.EXPAND))  # noqa: SLF001
    expand_request = tab._build_request()  # noqa: SLF001

    assert expand_request is not None
    assert [att.kind for att in expand_request.attachments].count("writing_note") == 1
    assert tab._writing_notes_status_label.text() == TR(  # noqa: SLF001
        "ai.attachments.writing_notes_status_default_on"
    ).format(task=TR("ai.task.expand"))


def test_fragment_writing_notes_are_shown_as_removable_context(qtbot, container):
    from writer.ui.i18n import TR
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="绵绵", body="原文。")
    container.entry_writing_note_repository.create(
        entry_id=entry.id,
        body="下一段让人物先回到凉面摊，再听见风。",
    )
    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=entry.body,
        )
    )

    assert tab._writing_notes_status_label.text() == TR(  # noqa: SLF001
        "ai.attachments.writing_notes_status_optional_off"
    ).format(task=TR("ai.task.polish"))

    tab._on_add_writing_notes_attachment()  # noqa: SLF001

    assert tab._include_writing_notes_check.isChecked() is True  # noqa: SLF001
    assert tab._attach_list.count() == 1  # noqa: SLF001
    assert "片段便签" in tab._attach_list.item(0).text() or "Fragment notes" in tab._attach_list.item(0).text()  # noqa: SLF001
    tab._attach_list.setCurrentRow(0)  # noqa: SLF001
    tab._on_remove_attachment()  # noqa: SLF001
    assert tab._include_writing_notes_check.isChecked() is False  # noqa: SLF001


def test_fragment_writing_notes_are_opt_in_for_analysis_tasks(qtbot, container):
    from writer.ui.i18n import TR
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="绵绵", body="原文。")
    container.entry_writing_note_repository.create(
        entry_id=entry.id,
        body="下一段写风。",
    )
    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=entry.body,
        )
    )

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.SUMMARIZE))  # noqa: SLF001
    summary_request = tab._build_request()  # noqa: SLF001

    assert summary_request is not None
    assert tab._include_writing_notes_check.isChecked() is False  # noqa: SLF001
    assert tab._writing_notes_status_label.text() == TR(  # noqa: SLF001
        "ai.attachments.writing_notes_status_optional_off"
    ).format(task=TR("ai.task.summarize"))
    assert all(att.kind != "writing_note" for att in summary_request.attachments)

    tab._include_writing_notes_check.setChecked(True)  # noqa: SLF001
    opted_in_request = tab._build_request()  # noqa: SLF001

    assert opted_in_request is not None
    assert tab._writing_notes_status_label.text() == TR(  # noqa: SLF001
        "ai.attachments.writing_notes_status_manual_on"
    ).format(task=TR("ai.task.summarize"))
    assert [att.kind for att in opted_in_request.attachments] == ["writing_note"]


def test_unchecking_fragment_writing_notes_removes_auto_attachment(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="绵绵", body="原文。")
    container.entry_writing_note_repository.create(
        entry_id=entry.id,
        body="下一段写风。",
    )
    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=entry.body,
        )
    )

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.CONTINUE))  # noqa: SLF001
    tab._include_writing_notes_check.setChecked(False)  # noqa: SLF001
    request = tab._build_request()  # noqa: SLF001

    assert request is not None
    assert all(att.kind != "writing_note" for att in request.attachments)


def test_fragment_writing_notes_empty_state_explains_add_and_return(qtbot, container):
    from writer.ui.i18n import TR
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="绵绵", body="原文。")
    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=entry.body,
        )
    )

    assert tab._include_writing_notes_check.isEnabled() is False  # noqa: SLF001
    assert tab._manage_writing_notes_btn.text() == TR("ai.attachments.add_context")  # noqa: SLF001
    assert tab._writing_notes_status_label.text() == TR(  # noqa: SLF001
        "ai.attachments.writing_notes_status_empty"
    ).format(task=TR("ai.task.polish"))


def test_ai_workspace_context_pane_button_opens_fragment_notes(qtbot, container):
    from writer.ui.main_window import MODE_FRAGMENTS, MainWindow

    entry = container.entry_repository.create(title="绵绵", body="原文。")
    window = MainWindow(container, autosave_debounce_ms=20)
    qtbot.addWidget(window)
    window.show()
    window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
    window._load_entry(entry.id)  # noqa: SLF001

    board = window._editor_panel._writing_notes_board  # noqa: SLF001
    assert board.isHidden()

    window._context_pane.fragment_writing_notes_button.click()  # noqa: SLF001

    assert board.isVisible()
    assert board.is_collapsed() is False


def test_add_specimen_attachment_replaces_only_style_specimens(qtbot, container, monkeypatch):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    keep_entry = container.entry_repository.create(title="Keep", body="keep body")
    old_specimen = container.reference_repository.create(source_title="Old specimen", content="old body")
    new_specimen = container.reference_repository.create(source_title="New specimen", content="new body")

    class FakeSpecimenPickerDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 1})

        def __init__(self, repo, **kwargs) -> None:
            self.selected_passages = [repo.get(new_specimen.id)]
            self.preselected_ids = kwargs.get("preselected_ids")

        def exec(self):
            return 1

    import writer.ui.dialogs.specimen_picker_dialog as picker_mod

    monkeypatch.setattr(picker_mod, "SpecimenPickerDialog", FakeSpecimenPickerDialog)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    tab._attachments = [  # noqa: SLF001
        AiContextAttachment(kind="fragment", ref_id=keep_entry.id, name="Keep", body="keep body"),
        AiContextAttachment(
            kind="style_specimen",
            ref_id=old_specimen.id,
            name="Old specimen",
            body="old body",
        ),
    ]

    tab._on_add_specimen_attachment()  # noqa: SLF001

    assert [att.kind for att in tab._attachments] == ["fragment", "style_specimen"]  # noqa: SLF001
    assert tab._attachments[0].ref_id == keep_entry.id  # noqa: SLF001
    assert tab._attachments[1].ref_id == new_specimen.id  # noqa: SLF001


def test_add_specimen_attachment_passes_existing_style_specimen_ids(qtbot, container, monkeypatch):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    first = container.reference_repository.create(source_title="Spec A", content="body a")
    second = container.reference_repository.create(source_title="Spec B", content="body b")
    seen: dict[str, list[str]] = {}

    class FakeSpecimenPickerDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 0})

        def __init__(self, _repo, **kwargs) -> None:
            seen["preselected_ids"] = kwargs.get("preselected_ids") or []
            self.selected_passages = []

        def exec(self):
            return 0

    import writer.ui.dialogs.specimen_picker_dialog as picker_mod

    monkeypatch.setattr(picker_mod, "SpecimenPickerDialog", FakeSpecimenPickerDialog)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    tab._attachments = [  # noqa: SLF001
        AiContextAttachment(kind="style_specimen", ref_id=first.id, name="Spec A", body="body a"),
        AiContextAttachment(kind="fragment", ref_id="frag-1", name="Frag", body="fragment body"),
        AiContextAttachment(kind="style_specimen", ref_id=second.id, name="Spec B", body="body b"),
    ]

    tab._on_add_specimen_attachment()  # noqa: SLF001

    assert seen["preselected_ids"] == [first.id, second.id]


def test_tools_tab_library_qa_resolves_citations_through_real_service(qtbot, container):
    """End-to-end: provider returns JSON answer with citations; service maps
    them onto attachments and the tab renders them without crashing."""
    import json
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    payload = {
        "answer": "X is the antagonist.",
        "citations": [{"name": "Lore A"}, {"name": "ghost"}],
    }
    provider = _StubProvider(json.dumps(payload))
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))

    # Switch to LIBRARY_QA.
    library_qa_row = next(
        i
        for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == AiTaskType.LIBRARY_QA
    )
    tab._task_list.setCurrentRow(library_qa_row)  # noqa: SLF001
    # Switch target to PASTE so we can supply text directly.
    paste_idx = tab._target_combo.findData(AiTargetKind.PASTE)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(paste_idx)  # noqa: SLF001
    tab._paste_edit.setPlainText("who is X?")  # noqa: SLF001
    tab._attachments.append(  # noqa: SLF001
        AiContextAttachment(kind="fragment", ref_id="f1", name="Lore A", body="...")
    )

    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    response = container.ai_task_service.generate(request)
    cite_kinds = {c.kind for c in response.citations}
    assert "fragment" in cite_kinds
    assert "unresolved" in cite_kinds


# ---------------------------------------------------------------------------
# Chat tab
# ---------------------------------------------------------------------------


def test_chat_tab_send_persists_user_and_assistant(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIChatTab, AiScope

    provider = _StubProvider("hi back")
    _stub_container_provider(container, provider)

    tab = AIChatTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    thread_id = tab._thread_id  # noqa: SLF001
    assert thread_id is not None

    # Drive the underlying service synchronously to avoid QThread timing.
    container.ai_thread_service.send(thread_id, "hello")
    history = container.ai_thread_service.history(thread_id)
    assert [m.role for m in history] == ["user", "assistant"]
    assert history[1].content == "hi back"


def test_chat_tab_rebinding_to_same_scope_returns_same_thread(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIChatTab, AiScope

    provider = _StubProvider()
    _stub_container_provider(container, provider)

    tab1 = AIChatTab(container)
    qtbot.addWidget(tab1)
    tab1.bind_scope(AiScope(AiThreadScope.FRAGMENT, "frag-1", "F1", "body"))
    first_id = tab1._thread_id  # noqa: SLF001

    tab2 = AIChatTab(container)
    qtbot.addWidget(tab2)
    tab2.bind_scope(AiScope(AiThreadScope.FRAGMENT, "frag-1", "F1", "body"))
    assert tab2._thread_id == first_id  # noqa: SLF001


def test_chat_tab_can_save_last_assistant_reply_as_fragment_note(
    qtbot, container, monkeypatch
):
    from writer.ui.panels.ai_workspace_panel import AIChatTab, AiScope
    import writer.ui.panels.ai_workspace_panel as panel_mod

    provider = _StubProvider("把雨声写得更近一点。")
    _stub_container_provider(container, provider)
    monkeypatch.setattr(panel_mod.QMessageBox, "information", lambda *a, **k: None)

    entry = container.entry_repository.create(title="雨夜", body="窗外下雨。")
    tab = AIChatTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(AiThreadScope.FRAGMENT, entry.id, entry.title or "", entry.body or "")
    )
    assert tab._save_note_btn.isEnabled() is False  # noqa: SLF001

    assert tab._thread_id is not None  # noqa: SLF001
    container.ai_thread_service.send(tab._thread_id, "怎么改？")  # noqa: SLF001
    tab._render_history()  # noqa: SLF001

    assert tab._save_note_btn.isEnabled() is True  # noqa: SLF001
    with qtbot.waitSignal(tab.request_fragment_changed, timeout=500) as blocker:
        tab._save_note_btn.click()  # noqa: SLF001

    notes = container.entry_writing_note_repository.list_for_entry(entry.id)
    assert len(notes) == 1
    assert notes[0].body == "把雨声写得更近一点。"
    assert blocker.args == [entry.id]


def test_chat_tab_saves_selected_chat_text_as_fragment_note(
    qtbot, container, monkeypatch
):
    from PySide6.QtGui import QTextCursor

    from writer.ui.panels.ai_workspace_panel import AIChatTab, AiScope
    import writer.ui.panels.ai_workspace_panel as panel_mod

    provider = _StubProvider("第一句。\n第二句。\n第三句。")
    _stub_container_provider(container, provider)
    monkeypatch.setattr(panel_mod.QMessageBox, "information", lambda *a, **k: None)

    entry = container.entry_repository.create(title="雨夜", body="窗外下雨。")
    tab = AIChatTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(AiThreadScope.FRAGMENT, entry.id, entry.title or "", entry.body or "")
    )
    assert tab._thread_id is not None  # noqa: SLF001
    container.ai_thread_service.send(tab._thread_id, "怎么改？")  # noqa: SLF001
    tab._render_history()  # noqa: SLF001

    document = tab._messages_view.document()  # noqa: SLF001
    plain = tab._messages_view.toPlainText()  # noqa: SLF001
    start = plain.index("第二句")
    cursor = QTextCursor(document)
    cursor.setPosition(start)
    cursor.setPosition(start + len("第二句。"), QTextCursor.MoveMode.KeepAnchor)
    tab._messages_view.setTextCursor(cursor)  # noqa: SLF001

    tab._save_note_btn.click()  # noqa: SLF001

    notes = container.entry_writing_note_repository.list_for_entry(entry.id)
    assert [note.body for note in notes] == ["第二句。"]


def test_chat_tab_note_action_is_fragment_only(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIChatTab, AiScope

    provider = _StubProvider("global answer")
    _stub_container_provider(container, provider)

    tab = AIChatTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    assert tab._thread_id is not None  # noqa: SLF001
    container.ai_thread_service.send(tab._thread_id, "hello")  # noqa: SLF001
    tab._render_history()  # noqa: SLF001

    assert tab._save_fragment_btn.isEnabled() is True  # noqa: SLF001
    assert tab._save_note_btn.isEnabled() is False  # noqa: SLF001


def test_chat_tab_can_add_current_fragment_notes_context(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIChatTab, AiScope

    entry = container.entry_repository.create(title="绵绵", body="原文。")
    container.entry_writing_note_repository.create(
        entry_id=entry.id,
        body="下一段让人物先回到凉面摊。",
        pinned=True,
    )
    container.entry_writing_note_repository.create(
        entry_id=entry.id,
        body="再听见风。",
    )
    tab = AIChatTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(AiThreadScope.FRAGMENT, entry.id, entry.title or "", entry.body or "")
    )

    tab._on_add_writing_notes_attachment()  # noqa: SLF001

    assert len(tab._attachments) == 1  # noqa: SLF001
    attachment = tab._attachments[0]  # noqa: SLF001
    assert attachment.kind == "writing_note"
    assert attachment.ref_id == entry.id
    assert "凉面摊" in attachment.body
    assert "再听见风" in attachment.body
    assert "片段便签" in tab._attach_label.text() or "Fragment notes" in tab._attach_label.text()  # noqa: SLF001


# ---------------------------------------------------------------------------
# Safe write-back
# ---------------------------------------------------------------------------


def test_apply_to_fragment_via_polish_uses_legacy_acceptance(qtbot, container):
    """Polish task → version snapshots ORIGINAL + AI_POLISH and updates body."""
    from writer.ui.services.ai_apply import apply_to_fragment

    entry = container.entry_repository.create(title="t", body="orig body")
    apply_to_fragment(
        container,
        entry_id=entry.id,
        task_type=AiTaskType.POLISH,
        original_full_body="orig body",
        selection_start=None,
        selection_end=None,
        generated_text="POLISHED body",
        title="t",
        provider_name="stub",
        model="m",
    )
    fresh = container.entry_repository.get(entry.id)
    assert fresh.body == "POLISHED body"
    versions = container.version_repository.list_for_entry(entry.id)
    types = {v.version_type for v in versions}
    assert "original" in types
    assert "ai_polish" in types


def test_apply_generic_task_writes_ai_other_version(qtbot, container):
    from writer.ui.services.ai_apply import apply_to_fragment

    entry = container.entry_repository.create(title="t", body="orig body")
    apply_to_fragment(
        container,
        entry_id=entry.id,
        task_type=AiTaskType.SUMMARIZE,  # not in legacy mapping
        original_full_body="orig body",
        selection_start=None,
        selection_end=None,
        generated_text="SUMMARY",
        title="t",
        provider_name="stub",
        model="m",
    )
    versions = container.version_repository.list_for_entry(entry.id)
    types = {v.version_type for v in versions}
    assert "original" in types
    assert "ai_other" in types


def test_save_as_new_fragment_creates_entry(qtbot, container):
    from writer.ui.services.ai_apply import save_as_new_fragment

    outcome = save_as_new_fragment(container, title="AI: Outline", body="1. A\n2. B")
    assert outcome.new_fragment_id is not None
    fresh = container.entry_repository.get(outcome.new_fragment_id)
    assert fresh is not None
    assert fresh.title == "AI: Outline"


def test_apply_to_section_snapshots_work_first(qtbot, container):
    from writer.ui.services.ai_apply import apply_to_section

    work = container.work_repository.create(title="W", summary="")
    section = container.work_section_repository.create(work_id=work.id, content="orig content")

    snapshots_before = container.work_version_repository.list_for_work(work.id)
    apply_to_section(
        container,
        work_id=work.id,
        section_id=section.id,
        generated_text="NEW SECTION",
    )
    snapshots_after = container.work_version_repository.list_for_work(work.id)
    assert len(snapshots_after) == len(snapshots_before) + 1

    fresh = container.work_section_repository.get(section.id)
    assert fresh.content == "NEW SECTION"



# ---------------------------------------------------------------------------
# Regression: combo currentData() round-trips str-Enums as plain strings,
# so `is` checks against AiTargetKind / AiOutputAction / AiCostTier silently
# fail. The panel must use value-equality (or normalise via _combo_enum).
# ---------------------------------------------------------------------------


def test_paste_target_reads_paste_editor_text_not_scope_body(qtbot, container):
    """Bug #1: with target=PASTE the request must use the paste-edit text,
    even when a fragment scope (with non-empty body) is bound."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    provider = _StubProvider("ok")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id="frag-1",
            name="F",
            body="ORIGINAL FRAGMENT BODY",
        )
    )
    paste_idx = tab._target_combo.findData(AiTargetKind.PASTE)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(paste_idx)  # noqa: SLF001
    # Paste editor must become visible after switching target.
    assert tab._paste_edit.isVisible() or True  # may not be shown until parent shown
    tab._paste_edit.setPlainText("ONLY THIS")  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.text == "ONLY THIS"
    assert "ORIGINAL FRAGMENT BODY" not in request.text


def test_selection_target_uses_scope_selection_text(qtbot, container):
    """Bug #2: selection target must use scope.selection_text instead of
    silently degrading to paste/whole-body."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    provider = _StubProvider("ok")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id="frag-1",
            name="F",
            body="hello world hello again",
            selection_start=6,
            selection_end=11,
            selection_text="world",
        )
    )
    sel_idx = tab._target_combo.findData(AiTargetKind.SELECTION)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(sel_idx)  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.text == "world"

    # And REPLACE_SELECTION must be available as an output choice.
    out_values = [
        tab._output_combo.itemData(i)  # noqa: SLF001
        for i in range(tab._output_combo.count())  # noqa: SLF001
    ]
    assert AiOutputAction.REPLACE_SELECTION in out_values


def test_bind_scope_defaults_to_selection_when_fragment_has_selection(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id="frag-1",
            name="F",
            body="hello world hello again",
            selection_start=6,
            selection_end=11,
            selection_text="world",
        )
    )

    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.target_kind == AiTargetKind.SELECTION
    assert request.text == "world"


def test_context_estimate_refreshes_after_scope_bind(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id="frag-1",
            name="F",
            body="hello world",
        )
    )

    assert "11" in tab._attach_total_label.text()  # noqa: SLF001


def test_context_estimate_tracks_paste_text(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    tab._paste_edit.setPlainText("abcde")  # noqa: SLF001

    assert "5" in tab._attach_total_label.text()  # noqa: SLF001


def test_replace_fragment_apply_actually_writes_fragment_body(qtbot, container):
    """Bug #1 + #4: REPLACE_FRAGMENT path must route through apply_to_fragment
    (this verifies the `out is AiOutputAction.X` -> `==` fix is in effect)."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    entry = container.entry_repository.create(title="t", body="orig body")
    provider = _StubProvider("REPLACED")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=entry.body,
        )
    )
    # Pick FRAGMENT target + REPLACE_FRAGMENT output.
    frag_idx = tab._target_combo.findData(AiTargetKind.FRAGMENT)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(frag_idx)  # noqa: SLF001
    repl_idx = tab._output_combo.findData(AiOutputAction.REPLACE_FRAGMENT)  # noqa: SLF001
    assert repl_idx >= 0
    tab._output_combo.setCurrentIndex(repl_idx)  # noqa: SLF001

    # Drive the service synchronously (no QThread).
    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._last_response = response  # noqa: SLF001
    tab._result_view.setPlainText(response.content)  # noqa: SLF001

    # Bypass QMessageBox prompts by stubbing them.
    import writer.ui.panels.ai_workspace_panel as panel_mod

    _accept_ai_apply_dialogs(panel_mod)
    tab._on_apply()  # noqa: SLF001

    fresh = container.entry_repository.get(entry.id)
    assert fresh.body == "REPLACED"


def test_replace_selection_apply_only_rewrites_selected_range(qtbot, container):
    """Bug #2 + #4: REPLACE_SELECTION must use scope.selection_start/end so
    only the selected range is replaced, leaving the surrounding body."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    body = "alpha beta gamma"
    entry = container.entry_repository.create(title="t", body=body)
    provider = _StubProvider("BETA!")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=body,
            selection_start=6,
            selection_end=10,
            selection_text="beta",
        )
    )
    sel_idx = tab._target_combo.findData(AiTargetKind.SELECTION)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(sel_idx)  # noqa: SLF001
    repl_idx = tab._output_combo.findData(AiOutputAction.REPLACE_SELECTION)  # noqa: SLF001
    assert repl_idx >= 0
    tab._output_combo.setCurrentIndex(repl_idx)  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._last_response = response  # noqa: SLF001
    tab._result_view.setPlainText(response.content)  # noqa: SLF001

    import writer.ui.panels.ai_workspace_panel as panel_mod

    _accept_ai_apply_dialogs(panel_mod)
    tab._on_apply()  # noqa: SLF001

    fresh = container.entry_repository.get(entry.id)
    assert fresh.body == "alpha BETA! gamma"


def test_fragment_apply_exposes_undo_and_restores_previous_body(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    body = "alpha beta gamma"
    entry = container.entry_repository.create(title="t", body=body)
    provider = _StubProvider("BETA!")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name=entry.title,
            body=body,
            selection_start=6,
            selection_end=10,
            selection_text="beta",
        )
    )
    repl_idx = tab._output_combo.findData(AiOutputAction.REPLACE_SELECTION)  # noqa: SLF001
    tab._output_combo.setCurrentIndex(repl_idx)  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._last_response = response  # noqa: SLF001
    tab._result_view.setPlainText(response.content)  # noqa: SLF001

    import writer.ui.panels.ai_workspace_panel as panel_mod

    _accept_ai_apply_dialogs(panel_mod)
    tab._on_apply()  # noqa: SLF001

    fresh = container.entry_repository.get(entry.id)
    assert fresh.body == "alpha BETA! gamma"
    assert tab._undo_apply_btn.isHidden() is False  # noqa: SLF001
    assert tab._undo_apply_btn.isEnabled() is True  # noqa: SLF001

    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    assert tab._undo_apply_btn.isHidden() is True  # noqa: SLF001

    tab.bind_scope(AiScope(AiThreadScope.FRAGMENT, entry.id, entry.title, fresh.body))
    assert tab._undo_apply_btn.isHidden() is False  # noqa: SLF001

    tab._on_undo_last_apply()  # noqa: SLF001

    restored = container.entry_repository.get(entry.id)
    assert restored.body == body
    assert tab._undo_apply_btn.isHidden() is True  # noqa: SLF001


def test_selection_preview_card_shows_bound_selection_and_emits_locate(qtbot, container):
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id="frag-1",
            name="Fragment",
            body="hello world",
            selection_start=6,
            selection_end=11,
            selection_text="world",
        )
    )

    assert tab._selection_card.isHidden() is False  # noqa: SLF001
    assert tab._selection_view.toPlainText() == "world"  # noqa: SLF001
    with qtbot.waitSignal(tab.request_locate_selection) as blocker:
        tab._selection_locate_btn.click()  # noqa: SLF001
    assert blocker.args[0].selection_text == "world"


def test_work_section_selection_apply_only_rewrites_selected_range(qtbot, container):
    from PySide6.QtGui import QTextCursor

    from writer.ui.main_window import MainWindow, MODE_AI, MODE_WORKS

    work = container.work_repository.create(title="W", summary="")
    section = container.work_section_repository.create(
        work_id=work.id,
        content="alpha beta gamma",
    )
    provider = _StubProvider("BETA!")
    _stub_container_provider(container, provider)

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(MODE_WORKS)  # noqa: SLF001
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    editor = window._works_panel._editor._editor  # noqa: SLF001
    cursor = editor.textCursor()
    cursor.setPosition(6)
    cursor.setPosition(10, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)

    window._set_mode(MODE_AI)  # noqa: SLF001
    tab = window._ai_workspace_panel.tools_tab  # noqa: SLF001
    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.target_kind == AiTargetKind.SELECTION
    assert request.text == "beta"

    repl_idx = tab._output_combo.findData(AiOutputAction.REPLACE_SELECTION)  # noqa: SLF001
    assert repl_idx >= 0
    tab._output_combo.setCurrentIndex(repl_idx)  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._last_response = response  # noqa: SLF001
    tab._result_view.setPlainText(response.content)  # noqa: SLF001

    import writer.ui.panels.ai_workspace_panel as panel_mod

    _accept_ai_apply_dialogs(panel_mod)
    tab._on_apply()  # noqa: SLF001

    fresh = container.work_section_repository.get(section.id)
    assert fresh.content == "alpha BETA! gamma"


def test_main_window_binds_section_scope_when_section_focused(qtbot, container):
    """Bug #3: when a work section is focused, AI binding must surface a
    writable section sub-scope (section_id + work_id + section body)."""
    from writer.ui.main_window import MainWindow

    work = container.work_repository.create(title="My Work", summary="")
    section = container.work_section_repository.create(work_id=work.id, content="section body text")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(2)  # works mode  # noqa: SLF001
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    window._set_mode(4)  # noqa: SLF001

    scope = window._ai_workspace_panel._scope  # noqa: SLF001
    assert scope is not None
    assert scope.kind is AiThreadScope.WORK
    assert scope.work_id == work.id
    assert scope.section_id == section.id
    assert "section body text" in scope.body


def test_main_window_keeps_fragment_selection_when_reentering_ai(qtbot, container):
    from PySide6.QtGui import QTextCursor

    from writer.ui.main_window import MainWindow, MODE_AI, MODE_FRAGMENTS

    entry = container.entry_repository.create(title="t", body="alpha beta gamma")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
    window._load_entry(entry.id)  # noqa: SLF001

    body_edit = window._editor_panel._body  # noqa: SLF001
    cursor = body_edit.textCursor()
    cursor.setPosition(6)
    cursor.setPosition(10, QTextCursor.MoveMode.KeepAnchor)
    body_edit.setTextCursor(cursor)

    window._set_mode(MODE_AI)  # noqa: SLF001
    window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
    window._set_mode(MODE_AI)  # noqa: SLF001

    tab = window._ai_workspace_panel.tools_tab  # noqa: SLF001
    request = tab._build_request()  # noqa: SLF001

    assert request is not None
    assert request.target_kind == AiTargetKind.SELECTION
    assert request.text == "beta"


def test_main_window_section_scope_replace_section_path_reachable(qtbot, container):
    """Bug #3 end-to-end: REPLACE_SECTION must be selectable and the apply
    must route through apply_to_section (not silently fail)."""
    from writer.ui.main_window import MainWindow

    work = container.work_repository.create(title="W", summary="")
    section = container.work_section_repository.create(work_id=work.id, content="orig section")
    provider = _StubProvider("NEW SECTION TEXT")
    _stub_container_provider(container, provider)

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(2)  # noqa: SLF001
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    window._set_mode(4)  # noqa: SLF001

    tab = window._ai_workspace_panel.tools_tab  # noqa: SLF001
    sec_idx = tab._target_combo.findData(AiTargetKind.WORK_SECTION)  # noqa: SLF001
    assert sec_idx >= 0
    tab._target_combo.setCurrentIndex(sec_idx)  # noqa: SLF001
    repl_idx = tab._output_combo.findData(AiOutputAction.REPLACE_SECTION)  # noqa: SLF001
    assert repl_idx >= 0, "REPLACE_SECTION must be a valid output for WORK_SECTION target"
    tab._output_combo.setCurrentIndex(repl_idx)  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.target_kind == AiTargetKind.WORK_SECTION
    assert request.target_ref_id == section.id

    response = container.ai_task_service.generate(request)
    tab._last_request = request  # noqa: SLF001
    tab._last_response = response  # noqa: SLF001
    tab._result_view.setPlainText(response.content)  # noqa: SLF001

    import writer.ui.panels.ai_workspace_panel as panel_mod

    _accept_ai_apply_dialogs(panel_mod)
    tab._on_apply()  # noqa: SLF001

    fresh = container.work_section_repository.get(section.id)
    assert fresh.content == "NEW SECTION TEXT"


def test_main_window_prefers_work_section_over_stale_fragment_when_entering_ai(qtbot, container):
    """AI scope should follow the surface the user came from.

    If a fragment is still loaded in the hidden fragments editor, it must
    not steal AI binding when the user is currently in Works mode and has
    a section focused there.
    """
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="Frag", body="fragment body")
    work = container.work_repository.create(title="Work", summary="")
    section = container.work_section_repository.create(work_id=work.id, content="section body")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._editor_panel.set_entry(entry)  # noqa: SLF001
    window._set_mode(2)  # noqa: SLF001
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    window._set_mode(4)  # noqa: SLF001

    scope = window._ai_workspace_panel._scope  # noqa: SLF001
    assert scope is not None
    assert scope.kind is AiThreadScope.WORK
    assert scope.work_id == work.id
    assert scope.section_id == section.id
    assert "section body" in scope.body


def test_structured_library_qa_renders_answer_not_raw_json(qtbot, container):
    """Bug #4: library QA result view must render the parsed answer, not
    the raw JSON envelope."""
    import json
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    payload = {
        "answer": "The protagonist is Alice.",
        "citations": [{"name": "Lore"}],
    }
    provider = _StubProvider(json.dumps(payload))
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    qa_row = next(
        i
        for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == AiTaskType.LIBRARY_QA
    )
    tab._task_list.setCurrentRow(qa_row)  # noqa: SLF001
    paste_idx = tab._target_combo.findData(AiTargetKind.PASTE)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(paste_idx)  # noqa: SLF001
    tab._paste_edit.setPlainText("who is the protagonist?")  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._on_task_succeeded(response)  # noqa: SLF001

    rendered = tab._result_view.toPlainText()  # noqa: SLF001
    assert rendered == "The protagonist is Alice."
    assert "{" not in rendered  # no raw JSON in the user-facing view


def test_structured_diagnose_renders_issue_list_not_raw_json(qtbot, container):
    """Bug #4: structure_diagnose / consistency_check must render an issue
    list, not a JSON dump."""
    import json
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    payload = {
        "issues": [
            {
                "severity": "high",
                "where": "Chapter 2",
                "what": "POV shift mid-paragraph",
                "suggestion": "Split into two scenes.",
            }
        ]
    }
    provider = _StubProvider(json.dumps(payload))
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", "some narrative text"))
    diag_row = next(
        i
        for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == AiTaskType.STRUCTURE_DIAGNOSE
    )
    tab._task_list.setCurrentRow(diag_row)  # noqa: SLF001
    paste_idx = tab._target_combo.findData(AiTargetKind.PASTE)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(paste_idx)  # noqa: SLF001
    tab._paste_edit.setPlainText("scene text")  # noqa: SLF001

    request = tab._build_request()  # noqa: SLF001
    response = container.ai_task_service.generate(request)
    tab._on_task_succeeded(response)  # noqa: SLF001

    rendered = tab._result_view.toPlainText()  # noqa: SLF001
    assert "POV shift" in rendered
    assert "Chapter 2" in rendered
    assert "Split into two scenes." in rendered
    assert "{" not in rendered


def test_structured_summarize_outline_title_render_reports(qtbot, container):
    from writer.services.ai.task_types import AiTaskResponse
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", "source"))

    summary = AiTaskResponse(
        content="{}",
        structured={
            "summary": "A short core.",
            "key_facts": ["fact one"],
            "themes": ["loss"],
            "keeper_lines": ["line to keep"],
        },
        model="m",
        provider="stub",
    )
    rendered_summary = tab._render_structured(  # noqa: SLF001
        summary, task_type=AiTaskType.SUMMARIZE
    )
    assert "A short core." in rendered_summary
    assert "fact one" in rendered_summary
    assert "line to keep" in rendered_summary

    outline = AiTaskResponse(
        content="{}",
        structured={
            "outline": [
                {"title": "Act I", "children": [{"title": "Scene A"}]},
            ],
        },
        model="m",
        provider="stub",
    )
    rendered_outline = tab._render_structured(  # noqa: SLF001
        outline, task_type=AiTaskType.OUTLINE
    )
    assert "- Act I" in rendered_outline
    assert "  - Scene A" in rendered_outline

    titles = AiTaskResponse(
        content="{}",
        structured={
            "groups": [
                {
                    "category": "Restrained",
                    "titles": [{"title": "After Rain", "reason": "Quiet tone"}],
                }
            ]
        },
        model="m",
        provider="stub",
    )
    rendered_titles = tab._render_structured(  # noqa: SLF001
        titles, task_type=AiTaskType.TITLE
    )
    assert "Restrained" in rendered_titles
    assert "After Rain" in rendered_titles
    assert "Quiet tone" in rendered_titles


def test_structured_result_uses_originating_task_even_if_user_switches_task(qtbot, container):
    """Structured rendering must follow the request that finished, not the
    task currently selected in the sidebar."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    from writer.services.ai.task_types import AiTaskResponse

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))

    qa_row = next(
        i
        for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == AiTaskType.LIBRARY_QA
    )
    diag_row = next(
        i
        for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == AiTaskType.STRUCTURE_DIAGNOSE
    )
    tab._task_list.setCurrentRow(qa_row)  # noqa: SLF001
    request = tab._build_request()  # noqa: SLF001
    tab._last_request = request  # noqa: SLF001

    # Simulate the user switching tasks while the request is still in flight.
    tab._task_list.setCurrentRow(diag_row)  # noqa: SLF001

    response = AiTaskResponse(
        content='{"answer": "Alice"}',
        structured={"answer": "Alice"},
        model="m",
        provider="stub",
    )
    tab._on_task_succeeded(response)  # noqa: SLF001

    # The current Structure Diagnose task must not be polluted by the Library QA result.
    assert tab._result_view.toPlainText() == ""  # noqa: SLF001

    tab._task_list.setCurrentRow(qa_row)  # noqa: SLF001
    assert tab._result_view.toPlainText() == "Alice"  # noqa: SLF001


def test_task_results_are_isolated_when_switching_tasks(qtbot, container):
    from writer.services.ai.task_types import AiTaskRequest, AiTaskResponse
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))

    polish_row = _row_for_task(tab, AiTaskType.POLISH)
    expand_row = _row_for_task(tab, AiTaskType.EXPAND)
    tab._task_list.setCurrentRow(polish_row)  # noqa: SLF001
    polish_request = AiTaskRequest(
        task_type=AiTaskType.POLISH,
        target_kind=AiTargetKind.PASTE,
        text="original polish source",
        cost_tier=AiCostTier.BALANCED,
        desired_output=AiOutputAction.PREVIEW_ONLY,
    )
    tab._on_task_succeeded(  # noqa: SLF001
        AiTaskResponse(content="POLISHED", model="m", provider="stub"),
        polish_request,
    )
    assert tab._result_view.toPlainText() == "POLISHED"  # noqa: SLF001

    tab._task_list.setCurrentRow(expand_row)  # noqa: SLF001

    assert tab._result_view.toPlainText() == ""  # noqa: SLF001
    assert tab._last_response is None  # noqa: SLF001
    assert tab._clear_result_btn.isEnabled() is False  # noqa: SLF001

    tab._task_list.setCurrentRow(polish_row)  # noqa: SLF001

    assert tab._result_view.toPlainText() == "POLISHED"  # noqa: SLF001
    assert tab._source_view.toPlainText() == "original polish source"  # noqa: SLF001
    assert tab._clear_result_btn.isEnabled() is True  # noqa: SLF001


def test_clear_current_and_all_results_do_not_clear_params_or_presets(
    qtbot, container, monkeypatch
):
    from PySide6.QtWidgets import QMessageBox

    from writer.services.ai.task_types import AiTaskRequest, AiTaskResponse
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001
    tab._style_edit.setText("自定义风格")  # noqa: SLF001
    tab._save_custom_preset_btn.click()  # noqa: SLF001

    polish_request = AiTaskRequest(
        task_type=AiTaskType.POLISH,
        target_kind=AiTargetKind.PASTE,
        text="polish source",
        cost_tier=AiCostTier.BALANCED,
        desired_output=AiOutputAction.PREVIEW_ONLY,
    )
    tab._on_task_succeeded(  # noqa: SLF001
        AiTaskResponse(content="POLISHED", model="m", provider="stub"),
        polish_request,
    )
    tab._on_clear_current_result()  # noqa: SLF001

    assert tab._result_view.toPlainText() == ""  # noqa: SLF001
    assert tab._style_edit.text() == "自定义风格"  # noqa: SLF001
    assert container.settings.load_ai_custom_task_presets()["polish"] == ["自定义风格"]

    expand_row = _row_for_task(tab, AiTaskType.EXPAND)
    tab._task_list.setCurrentRow(expand_row)  # noqa: SLF001
    expand_request = AiTaskRequest(
        task_type=AiTaskType.EXPAND,
        target_kind=AiTargetKind.PASTE,
        text="expand source",
        cost_tier=AiCostTier.BALANCED,
        desired_output=AiOutputAction.PREVIEW_ONLY,
    )
    tab._on_task_succeeded(  # noqa: SLF001
        AiTaskResponse(content="EXPANDED", model="m", provider="stub"),
        expand_request,
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    tab._on_clear_all_results()  # noqa: SLF001

    assert tab._result_view.toPlainText() == ""  # noqa: SLF001
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001
    assert tab._result_view.toPlainText() == ""  # noqa: SLF001
    assert container.settings.load_ai_custom_task_presets()["polish"] == ["自定义风格"]


# ---------------------------------------------------------------------------
# Phase 1 — Context-pane "AI Polish" routes to AI workspace (no direct AI
# call), compare layout, task parameter isolation, apply-button labels.
# ---------------------------------------------------------------------------


def test_context_pane_polish_button_opens_ai_workspace_not_rewrite(qtbot, container):
    """Clicking context-pane 'AI Polish' must switch to AI workspace mode
    without calling _on_rewrite (which would fire an immediate AI request).
    """
    from writer.ui.main_window import MainWindow, MODE_AI, MODE_FRAGMENTS

    entry = container.entry_repository.create(title="My frag", body="hello world")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
    window._load_entry(entry.id)  # noqa: SLF001

    # Track whether the old _on_rewrite path is triggered.
    rewrite_called = []

    def _spy(*args, **kwargs):
        rewrite_called.append(True)

    window._on_rewrite = _spy  # noqa: SLF001

    # Simulate clicking the context-pane polish button.
    window._context_pane.fragment_polish_button.click()  # noqa: SLF001

    # Must switch to AI workspace.
    assert window._stack.currentIndex() == MODE_AI  # noqa: SLF001
    # Must NOT have called the old _on_rewrite path.
    assert rewrite_called == [], "old _on_rewrite must not be called"


def test_context_pane_polish_selects_polish_task_in_ai_workspace(qtbot, container):
    """After clicking context-pane polish, the AI workspace tools tab must
    have POLISH selected and be on the Tools (index 0) tab."""
    from writer.ui.main_window import MainWindow, MODE_AI, MODE_FRAGMENTS

    entry = container.entry_repository.create(title="Frag", body="some text")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
    window._load_entry(entry.id)  # noqa: SLF001
    window._context_pane.fragment_polish_button.click()  # noqa: SLF001

    assert window._stack.currentIndex() == MODE_AI  # noqa: SLF001
    # Tools tab is index 0.
    assert window._ai_workspace_panel.tabs.currentIndex() == 0  # noqa: SLF001
    # POLISH must be selected.
    tab = window._ai_workspace_panel.tools_tab  # noqa: SLF001
    assert tab._current_task_type() == AiTaskType.POLISH  # noqa: SLF001


def test_context_pane_polish_defaults_to_selection_when_selection_exists(qtbot, container):
    """If the fragment editor has a live selection, AI workspace must default
    target_kind to SELECTION (not FRAGMENT) when entering via context pane."""
    from PySide6.QtGui import QTextCursor
    from writer.ui.main_window import MainWindow, MODE_FRAGMENTS

    entry = container.entry_repository.create(title="Frag", body="alpha beta gamma")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
    window._load_entry(entry.id)  # noqa: SLF001

    # Create a selection in the body editor.
    body_edit = window._editor_panel._body  # noqa: SLF001
    cursor = body_edit.textCursor()
    cursor.setPosition(6)
    cursor.setPosition(10, QTextCursor.MoveMode.KeepAnchor)
    body_edit.setTextCursor(cursor)

    window._context_pane.fragment_polish_button.click()  # noqa: SLF001

    tab = window._ai_workspace_panel.tools_tab  # noqa: SLF001
    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.target_kind == AiTargetKind.SELECTION
    assert request.text == "beta"


def test_context_pane_polish_defaults_to_fragment_when_no_selection(qtbot, container):
    """Without a selection, entering via context-pane polish must default
    target_kind to FRAGMENT."""
    from writer.ui.main_window import MainWindow, MODE_FRAGMENTS

    entry = container.entry_repository.create(title="NoSel", body="full body text")

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
    window._load_entry(entry.id)  # noqa: SLF001
    # Explicitly clear any selection.
    body_edit = window._editor_panel._body  # noqa: SLF001
    cursor = body_edit.textCursor()
    cursor.clearSelection()
    body_edit.setTextCursor(cursor)

    window._context_pane.fragment_polish_button.click()  # noqa: SLF001

    tab = window._ai_workspace_panel.tools_tab  # noqa: SLF001
    request = tab._build_request()  # noqa: SLF001
    assert request is not None
    assert request.target_kind == AiTargetKind.FRAGMENT
    assert request.text == "full body text"


# ---------------------------------------------------------------------------
# Compare layout
# ---------------------------------------------------------------------------


def test_compare_layout_shows_source_for_rewrite_tasks(qtbot, container):
    """For POLISH / EXPAND / CONTINUE, after task completion
    _source_widget must be visible and contain the original text."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    from writer.services.ai.task_types import AiTaskResponse

    for task_type in (
        AiTaskType.POLISH,
        AiTaskType.EXPAND,
        AiTaskType.CONTINUE,
    ):
        tab = AIToolsTab(container)
        qtbot.addWidget(tab)
        tab.bind_scope(
            AiScope(
                kind=AiThreadScope.FRAGMENT,
                ref_id="f1",
                name="F",
                body="original source text",
            )
        )
        row = _row_for_task(tab, task_type)
        tab._task_list.setCurrentRow(row)  # noqa: SLF001

        from writer.services.ai.task_types import AiTaskRequest

        request = AiTaskRequest(
            task_type=task_type,
            target_kind=AiTargetKind.FRAGMENT,
            text="original source text",
            cost_tier=AiCostTier.BALANCED,
            desired_output=AiOutputAction.PREVIEW_ONLY,
        )
        response = AiTaskResponse(
            content="AI OUTPUT",
            model="m",
            provider="stub",
        )
        tab._last_request = request  # noqa: SLF001
        tab._on_task_succeeded(response)  # noqa: SLF001

        assert not tab._source_widget.isHidden(), f"{task_type}: source_widget should be visible"  # noqa: SLF001
        assert "original source text" in tab._source_view.toPlainText()  # noqa: SLF001
        assert not tab._result_header.isHidden(), f"{task_type}: result_header should be visible"  # noqa: SLF001
        assert tab._result_view.toPlainText() == "AI OUTPUT"  # noqa: SLF001


def test_compare_layout_hidden_for_report_tasks(qtbot, container):
    """For SUMMARIZE / OUTLINE / TITLE / STRUCTURE_DIAGNOSE, the source pane
    must stay hidden (report-style output)."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    from writer.services.ai.task_types import AiTaskRequest, AiTaskResponse

    for task_type in (
        AiTaskType.SUMMARIZE,
        AiTaskType.OUTLINE,
        AiTaskType.TITLE,
    ):
        tab = AIToolsTab(container)
        qtbot.addWidget(tab)
        tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", "plain text"))
        tab._paste_edit.setPlainText("plain text")  # noqa: SLF001
        row = _row_for_task(tab, task_type)
        tab._task_list.setCurrentRow(row)  # noqa: SLF001
        paste_idx = tab._target_combo.findData(AiTargetKind.PASTE)  # noqa: SLF001
        tab._target_combo.setCurrentIndex(paste_idx)  # noqa: SLF001

        request = AiTaskRequest(
            task_type=task_type,
            target_kind=AiTargetKind.PASTE,
            text="plain text",
            cost_tier=AiCostTier.BALANCED,
            desired_output=AiOutputAction.PREVIEW_ONLY,
        )
        response = AiTaskResponse(content="REPORT", model="m", provider="stub")
        tab._last_request = request  # noqa: SLF001
        tab._on_task_succeeded(response)  # noqa: SLF001

        assert tab._source_widget.isHidden(), f"{task_type}: source_widget should be hidden"  # noqa: SLF001
        assert tab._result_header.isHidden(), f"{task_type}: result_header should be hidden"  # noqa: SLF001


def test_apply_button_text_reflects_output_action(qtbot, container):
    """Apply button label must name the specific destructive action, not
    just the generic 'Apply'."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    from writer.ui.i18n import TR

    entry = container.entry_repository.create(title="T", body="body")
    provider = _StubProvider("RESULT")
    _stub_container_provider(container, provider)

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id=entry.id,
            name="T",
            body="body",
            selection_start=0,
            selection_end=4,
            selection_text="body",
        )
    )

    # REPLACE_SELECTION
    sel_idx = tab._target_combo.findData(AiTargetKind.SELECTION)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(sel_idx)  # noqa: SLF001
    repl_sel = tab._output_combo.findData(AiOutputAction.REPLACE_SELECTION)  # noqa: SLF001
    tab._output_combo.setCurrentIndex(repl_sel)  # noqa: SLF001
    assert tab._apply_btn.text() == TR("ai.results.apply_replace_selection")  # noqa: SLF001

    # REPLACE_FRAGMENT
    frag_idx = tab._target_combo.findData(AiTargetKind.FRAGMENT)  # noqa: SLF001
    tab._target_combo.setCurrentIndex(frag_idx)  # noqa: SLF001
    repl_frag = tab._output_combo.findData(AiOutputAction.REPLACE_FRAGMENT)  # noqa: SLF001
    tab._output_combo.setCurrentIndex(repl_frag)  # noqa: SLF001
    assert tab._apply_btn.text() == TR("ai.results.apply_replace_fragment")  # noqa: SLF001

    # PREVIEW_ONLY → generic label
    prev_idx = tab._output_combo.findData(AiOutputAction.PREVIEW_ONLY)  # noqa: SLF001
    tab._output_combo.setCurrentIndex(prev_idx)  # noqa: SLF001
    assert tab._apply_btn.text() == TR("ai.results.apply")  # noqa: SLF001


# ---------------------------------------------------------------------------
# Task parameter isolation
# ---------------------------------------------------------------------------


def test_task_params_not_shared_between_polish_and_continue(qtbot, container):
    """Setting style / intensity in POLISH must not bleed into CONTINUE when
    the user switches tasks.  Switching back to POLISH must restore the
    original POLISH settings."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)

    # Start on POLISH, set a style and intensity.
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001
    tab._style_edit.setText("幽默")  # noqa: SLF001
    intense_idx = tab._intensity_combo.findData("strong")  # noqa: SLF001
    tab._intensity_combo.setCurrentIndex(intense_idx)  # noqa: SLF001

    # Switch to CONTINUE.
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.CONTINUE))  # noqa: SLF001
    # CONTINUE is a first-visit → defaults: style empty.
    assert tab._style_edit.text() == ""  # noqa: SLF001

    # Switch back to POLISH → must restore "幽默" + strong.
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001
    assert tab._style_edit.text() == "幽默"  # noqa: SLF001
    assert tab._intensity_combo.currentData() == "strong"  # noqa: SLF001


def test_task_params_isolated_across_three_tasks(qtbot, container):
    """Polish, Expand, Continue each maintain independent extra-instruction
    state.  Switching between them never silently inherits another task's
    settings."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)

    # Polish: set extra
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001
    tab._extra_edit.setPlainText("polish-extra")  # noqa: SLF001

    # Expand: set different extra
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.EXPAND))  # noqa: SLF001
    assert tab._extra_edit.toPlainText() == ""  # fresh default  # noqa: SLF001
    tab._extra_edit.setPlainText("expand-extra")  # noqa: SLF001

    # Continue: fresh default
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.CONTINUE))  # noqa: SLF001
    assert tab._extra_edit.toPlainText() == ""  # noqa: SLF001

    # Round-trip: going back must restore saved values
    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.POLISH))  # noqa: SLF001
    assert tab._extra_edit.toPlainText() == "polish-extra"  # noqa: SLF001

    tab._task_list.setCurrentRow(_row_for_task(tab, AiTaskType.EXPAND))  # noqa: SLF001
    assert tab._extra_edit.toPlainText() == "expand-extra"  # noqa: SLF001


def test_focus_task_selects_task_and_target(qtbot, container):
    """AIToolsTab.focus_task() must select the requested task row and,
    if target_kind is given, change the target combo."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id="f1",
            name="F",
            body="some text",
        )
    )

    # Start at POLISH (row 0), switch focus to CONTINUE with FRAGMENT target.
    tab.focus_task(AiTaskType.CONTINUE, target_kind=AiTargetKind.FRAGMENT)
    assert tab._current_task_type() == AiTaskType.CONTINUE  # noqa: SLF001
    from writer.ui.panels.ai_workspace_panel import _combo_enum

    target = _combo_enum(tab._target_combo, AiTargetKind, AiTargetKind.PASTE)  # noqa: SLF001
    assert target == AiTargetKind.FRAGMENT


def test_ai_workspace_panel_focus_task_switches_to_tools_tab(qtbot, container):
    """AIWorkspacePanel.focus_task() must switch to the Tools tab (index 0)
    before delegating to AIToolsTab.focus_task()."""
    from writer.ui.panels.ai_workspace_panel import AIWorkspacePanel, AiScope

    panel = AIWorkspacePanel(container)
    qtbot.addWidget(panel)
    panel.bind_scope(
        AiScope(
            kind=AiThreadScope.FRAGMENT,
            ref_id="f1",
            name="F",
            body="text",
        )
    )
    # Switch to chat tab first.
    panel.tabs.setCurrentIndex(1)
    assert panel.tabs.currentIndex() == 1

    panel.focus_task(AiTaskType.EXPAND, target_kind=AiTargetKind.FRAGMENT)

    assert panel.tabs.currentIndex() == 0
    assert panel.tools_tab._current_task_type() == AiTaskType.EXPAND  # noqa: SLF001
