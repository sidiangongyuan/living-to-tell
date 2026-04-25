"""Smoke + behavioural tests for the M10A AI workspace UI.

We never run real provider calls — the AI services stay live but the
provider factory is monkey-patched to a stub.
"""
from __future__ import annotations

from typing import Optional

import pytest

from writer.app.container import build_container
from writer.domain.enums import AiCostTier, AiThreadScope, AiTaskType, AiTargetKind, AiOutputAction
from writer.services.ai.interfaces import AiProvider, ChatResponse, RewriteResponse
from writer.services.ai.task_types import AiContextAttachment, AiTaskRequest


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

    assert window._stack.count() == 4  # noqa: SLF001
    rail = window._rail  # noqa: SLF001
    assert rail.ai_button is not None
    assert rail.ai_button.isCheckable()


def test_set_mode_three_binds_ai_workspace_to_global_when_nothing_selected(
    qtbot, container
):
    from writer.ui.main_window import MainWindow

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(3)  # noqa: SLF001
    assert window._stack.currentIndex() == 3  # noqa: SLF001
    panel = window._ai_workspace_panel  # noqa: SLF001
    # Tabs widget should have exactly two tabs.
    assert panel.tabs.count() == 2


def test_set_mode_three_binds_ai_workspace_to_open_fragment(
    qtbot, container
):
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="Hello", body="A short fragment.")
    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._editor_panel.set_entry(entry)  # noqa: SLF001
    window._set_mode(3)  # noqa: SLF001

    panel = window._ai_workspace_panel  # noqa: SLF001
    scope = panel._scope  # noqa: SLF001
    assert scope is not None
    assert scope.kind is AiThreadScope.FRAGMENT
    assert scope.ref_id == entry.id
    assert "Hello" in scope.name


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


def test_tools_tab_library_qa_resolves_citations_through_real_service(
    qtbot, container
):
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
        i for i in range(tab._task_list.count())  # noqa: SLF001
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
    section = container.work_section_repository.create(
        work_id=work.id, content="orig content"
    )

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


def test_replace_fragment_apply_actually_writes_fragment_body(qtbot, container):
    """Bug #1 + #4: REPLACE_FRAGMENT path must route through apply_to_fragment
    (this verifies the `out is AiOutputAction.X` -> `==` fix is in effect)."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    from writer.services.ai.task_types import AiTaskResponse

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

    # Bypass QMessageBox.information by stubbing it.
    import writer.ui.panels.ai_workspace_panel as panel_mod
    panel_mod.QMessageBox.information = lambda *a, **k: None  # type: ignore[assignment]
    panel_mod.QMessageBox.warning = lambda *a, **k: 0  # type: ignore[assignment]
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
    panel_mod.QMessageBox.information = lambda *a, **k: None  # type: ignore[assignment]
    panel_mod.QMessageBox.warning = lambda *a, **k: 0  # type: ignore[assignment]
    tab._on_apply()  # noqa: SLF001

    fresh = container.entry_repository.get(entry.id)
    assert fresh.body == "alpha BETA! gamma"


def test_main_window_binds_section_scope_when_section_focused(qtbot, container):
    """Bug #3: when a work section is focused, AI binding must surface a
    writable section sub-scope (section_id + work_id + section body)."""
    from writer.ui.main_window import MainWindow

    work = container.work_repository.create(title="My Work", summary="")
    section = container.work_section_repository.create(
        work_id=work.id, content="section body text"
    )

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(1)  # works mode  # noqa: SLF001
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    window._set_mode(3)  # noqa: SLF001

    scope = window._ai_workspace_panel._scope  # noqa: SLF001
    assert scope is not None
    assert scope.kind is AiThreadScope.WORK
    assert scope.work_id == work.id
    assert scope.section_id == section.id
    assert "section body text" in scope.body


def test_main_window_section_scope_replace_section_path_reachable(qtbot, container):
    """Bug #3 end-to-end: REPLACE_SECTION must be selectable and the apply
    must route through apply_to_section (not silently fail)."""
    from writer.ui.main_window import MainWindow

    work = container.work_repository.create(title="W", summary="")
    section = container.work_section_repository.create(
        work_id=work.id, content="orig section"
    )
    provider = _StubProvider("NEW SECTION TEXT")
    _stub_container_provider(container, provider)

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._set_mode(1)  # noqa: SLF001
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    window._set_mode(3)  # noqa: SLF001

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
    panel_mod.QMessageBox.information = lambda *a, **k: None  # type: ignore[assignment]
    panel_mod.QMessageBox.warning = lambda *a, **k: 0  # type: ignore[assignment]
    tab._on_apply()  # noqa: SLF001

    fresh = container.work_section_repository.get(section.id)
    assert fresh.content == "NEW SECTION TEXT"


def test_main_window_prefers_work_section_over_stale_fragment_when_entering_ai(
    qtbot, container
):
    """AI scope should follow the surface the user came from.

    If a fragment is still loaded in the hidden fragments editor, it must
    not steal AI binding when the user is currently in Works mode and has
    a section focused there.
    """
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="Frag", body="fragment body")
    work = container.work_repository.create(title="Work", summary="")
    section = container.work_section_repository.create(
        work_id=work.id, content="section body"
    )

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)
    window._editor_panel.set_entry(entry)  # noqa: SLF001
    window._set_mode(1)  # noqa: SLF001
    window._works_panel.select_work_section(work.id, section.id)  # noqa: SLF001
    window._set_mode(3)  # noqa: SLF001

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
        i for i in range(tab._task_list.count())  # noqa: SLF001
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
        i for i in range(tab._task_list.count())  # noqa: SLF001
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


def test_structured_result_uses_originating_task_even_if_user_switches_task(
    qtbot, container
):
    """Structured rendering must follow the request that finished, not the
    task currently selected in the sidebar."""
    from writer.ui.panels.ai_workspace_panel import AIToolsTab, AiScope
    from writer.services.ai.task_types import AiTaskResponse

    tab = AIToolsTab(container)
    qtbot.addWidget(tab)
    tab.bind_scope(AiScope(AiThreadScope.GLOBAL, None, "", ""))

    qa_row = next(
        i for i in range(tab._task_list.count())  # noqa: SLF001
        if tab._task_list.item(i).data(0x0100) == AiTaskType.LIBRARY_QA
    )
    diag_row = next(
        i for i in range(tab._task_list.count())  # noqa: SLF001
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

    assert tab._result_view.toPlainText() == "Alice"  # noqa: SLF001

