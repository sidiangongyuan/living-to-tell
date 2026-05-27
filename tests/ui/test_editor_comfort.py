from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from writer.app.container import build_container
from writer.app.settings import DEFAULT_EDITOR_FONT_FAMILY, EditorDisplaySettings


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_editor_display_settings_load_defaults(container):
    settings = container.settings.load_editor_display_settings()

    assert settings == EditorDisplaySettings()
    assert settings.font_family == DEFAULT_EDITOR_FONT_FAMILY


def test_editor_display_settings_persists_font_and_reduced_motion(container):
    custom = EditorDisplaySettings(
        font_family="Noto Serif SC, 宋体",
        page_vertical_padding=40,
        page_gap=20,
        auto_paragraph_indent_enabled=False,
        soft_page_guides_enabled=False,
    )

    container.settings.save_editor_display_settings(custom)
    container.settings.save_reduced_motion_enabled(True)

    loaded = container.settings.load_editor_display_settings()
    assert loaded.font_family == "Noto Serif SC, 宋体"
    assert loaded.page_vertical_padding == 40
    assert loaded.page_gap == 20
    assert loaded.auto_paragraph_indent_enabled is False
    assert loaded.soft_page_guides_enabled is False
    assert container.settings.reduced_motion_enabled() is True


def test_editor_display_settings_falls_back_for_blank_font(container):
    container.settings.set("editor.font_family", "  ,  ")

    assert (
        container.settings.load_editor_display_settings().font_family == DEFAULT_EDITOR_FONT_FAMILY
    )


def test_editor_panel_applies_display_settings_to_body(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel, _font_families

    panel = EditorPanel()
    qtbot.addWidget(panel)

    custom = EditorDisplaySettings(
        font_size=22,
        line_height=2.1,
        paragraph_spacing=1.0,
        content_width=680,
        font_family="Georgia, Cambria",
        visual_first_line_indent_enabled=True,
        typewriter_mode_enabled=False,
    )
    panel.apply_display_settings(custom)
    panel.replace_body("第一段\n第二段")
    qtbot.waitUntil(
        lambda: panel._body.document().firstBlock().blockFormat().lineHeight() > 0  # noqa: SLF001
    )

    block = panel._body.document().firstBlock()  # noqa: SLF001
    block_format = block.blockFormat()
    expected_families = _font_families(custom.font_family)

    assert panel._body.font().pointSize() == 22  # noqa: SLF001
    assert panel._body.font().families()[: len(expected_families)] == expected_families  # noqa: SLF001
    assert panel._content_wrap.maximumWidth() == 680  # noqa: SLF001
    assert block_format.lineHeight() == 210.0
    assert block_format.textIndent() > 0


def test_visual_first_line_indent_does_not_mutate_plain_text(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.apply_display_settings(EditorDisplaySettings(visual_first_line_indent_enabled=True))

    original = "第一段\n第二段"
    panel.replace_body(original)

    assert panel.body_text() == original
    assert panel._body.toPlainText() == original  # noqa: SLF001


def test_editor_panel_typewriter_override_does_not_break_plain_editing(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel
    from writer.domain.models.entry import Entry

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.set_entry(Entry(id="entry-1", title="t", body="one\ntwo\nthree"))
    panel.focus_body()

    panel.set_focus_mode_enabled(True)
    qtbot.keyClicks(panel._body, " more")  # noqa: SLF001
    qtbot.waitUntil(lambda: panel.body_text().endswith(" more"))

    panel.set_focus_mode_enabled(False)
    assert panel.body_text().endswith(" more")


def test_editor_panel_epigraph_card_tracks_body_without_mutating_text(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel
    from writer.domain.models.entry import Entry

    body = "人可生如蚁，而美如神。\n——《一句顶一万句》 刘震云\n\n正文。"
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_entry(Entry(id="entry-1", title="t", body=body))

    assert panel._epigraph_card.isHidden() is False  # noqa: SLF001
    assert panel._epigraph_quote.text() == "人可生如蚁，而美如神。"  # noqa: SLF001
    assert panel._epigraph_attr.text() == "《一句顶一万句》 刘震云"  # noqa: SLF001
    assert panel.body_text() == body


def test_editor_panel_epigraph_card_hides_when_attribution_removed(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel
    from writer.domain.models.entry import Entry

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_entry(
        Entry(
            id="entry-1",
            title="t",
            body="人可生如蚁，而美如神。\n——《一句顶一万句》 刘震云\n\n正文。",
        )
    )

    panel.replace_body("人可生如蚁，而美如神。\n\n正文。")

    assert panel._epigraph_card.isHidden() is True  # noqa: SLF001
    assert panel.body_text() == "人可生如蚁，而美如神。\n\n正文。"


def test_editor_panel_writing_notes_card_emits_actions(qtbot):
    from PySide6.QtWidgets import QPushButton

    from writer.domain.models.entry import Entry
    from writer.domain.models.entry_writing_note import EntryWritingNote
    from writer.ui.i18n import TR
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_entry(Entry(id="entry-1", title="t", body="body"))
    panel.set_writing_notes(
        [
            EntryWritingNote(
                id="note-1",
                entry_id="entry-1",
                body="下一段让母亲先沉默。",
                pinned=True,
            )
        ]
    )

    assert panel._writing_notes_card.isHidden() is False  # noqa: SLF001
    assert panel._writing_notes_rows_layout.count() == 1  # noqa: SLF001
    assert panel._writing_notes_rows.isHidden() is False  # noqa: SLF001
    assert "1" in panel._writing_notes_count.text()  # noqa: SLF001

    panel._writing_note_input.setText("补一个下雨的细节")  # noqa: SLF001
    with qtbot.waitSignal(panel.writing_note_add_requested) as add_signal:
        panel._writing_note_add_btn.click()  # noqa: SLF001
    assert add_signal.args == ["补一个下雨的细节"]

    buttons = panel._writing_notes_rows.findChildren(QPushButton)  # noqa: SLF001
    edit_button = next(button for button in buttons if button.text() == TR("editor.writing_notes.edit"))
    done_button = next(button for button in buttons if button.text() == TR("editor.writing_notes.done"))

    edit_button.click()
    edit_input = next(
        child
        for child in panel._writing_notes_rows.findChildren(type(panel._writing_note_input))  # noqa: SLF001
        if child.isVisible() and child.text() == "下一段让母亲先沉默。"
    )
    edit_input.setText("下一段让母亲先沉默，然后看雨。")
    save_button = next(
        button
        for button in panel._writing_notes_rows.findChildren(QPushButton)  # noqa: SLF001
        if button.text() == TR("editor.writing_notes.save") and button.isVisible()
    )
    with qtbot.waitSignal(panel.writing_note_update_requested) as update_signal:
        save_button.click()
    assert update_signal.args == ["note-1", "下一段让母亲先沉默，然后看雨。"]

    with qtbot.waitSignal(panel.writing_note_done_requested) as done_signal:
        done_button.click()
    assert done_signal.args == ["note-1", True]

    with qtbot.waitSignal(panel.writing_notes_continue_requested):
        panel._writing_notes_continue_btn.click()  # noqa: SLF001


def test_main_window_writing_notes_do_not_leak_between_fragments(qtbot, container):
    from writer.ui.main_window import MainWindow

    first = container.entry_repository.create(title="A", body="body a")
    second = container.entry_repository.create(title="B", body="body b")
    container.entry_writing_note_repository.create(
        entry_id=first.id,
        body="A only",
    )

    window = MainWindow(container, autosave_debounce_ms=20)
    qtbot.addWidget(window)

    window._load_entry(first.id)  # noqa: SLF001
    assert "1" in window._editor_panel._writing_notes_count.text()  # noqa: SLF001
    window._load_entry(second.id)  # noqa: SLF001
    assert "0" in window._editor_panel._writing_notes_count.text()  # noqa: SLF001
    assert window._editor_panel._writing_notes_rows_layout.count() == 0  # noqa: SLF001


def test_main_window_continue_with_writing_notes_opens_ai_continue(qtbot, container):
    from writer.domain.enums import AiTargetKind, AiTaskType
    from writer.ui.main_window import MainWindow

    entry = container.entry_repository.create(title="A", body="body a")
    container.entry_writing_note_repository.create(
        entry_id=entry.id,
        body="next beat",
    )

    window = MainWindow(container, autosave_debounce_ms=20)
    qtbot.addWidget(window)
    window._load_entry(entry.id)  # noqa: SLF001

    window._editor_panel._writing_notes_continue_btn.click()  # noqa: SLF001

    tools = window._ai_workspace_panel.tools_tab  # noqa: SLF001
    assert tools._current_task_type() is AiTaskType.CONTINUE  # noqa: SLF001
    assert tools._target_combo.currentData() == AiTargetKind.FRAGMENT  # noqa: SLF001
    assert tools._include_writing_notes_check.isChecked() is True  # noqa: SLF001


def test_editor_panel_focus_mode_adds_current_paragraph_selection(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel
    from writer.domain.models.entry import Entry

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.set_entry(Entry(id="entry-1", title="t", body="one\n\ntwo"))
    panel.focus_body()

    assert panel._body.extraSelections() == []  # noqa: SLF001
    panel.set_focus_mode_enabled(True)
    qtbot.waitUntil(lambda: len(panel._body.extraSelections()) >= 1)  # noqa: SLF001

    panel.set_focus_mode_enabled(False)
    assert panel._body.extraSelections() == []  # noqa: SLF001


def test_editor_panel_reduced_motion_scrolls_immediately(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel
    from writer.domain.models.entry import Entry

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(600, 260)
    panel.show()
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(80))))
    panel.set_focus_mode_enabled(True)
    panel.set_reduced_motion(True)
    panel.focus_body()

    scrollbar = panel._body.verticalScrollBar()  # noqa: SLF001
    before = scrollbar.value()
    panel._body._adjust_typewriter_scroll()  # noqa: SLF001

    assert scrollbar.value() >= before
    assert getattr(scrollbar, "_writer_scroll_animation", None) is None


def test_editor_panel_enter_inserts_full_width_indent(qtbot):
    from PySide6.QtCore import Qt

    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.apply_display_settings(EditorDisplaySettings(auto_paragraph_indent_enabled=True))
    panel.set_entry(Entry(id="entry-1", title="t", body="第一段"))
    panel.focus_body()

    qtbot.keyClick(panel._body, Qt.Key.Key_Return)  # noqa: SLF001

    assert panel.body_text() == "第一段\n　　"


def test_editor_panel_enter_indent_can_be_disabled(qtbot):
    from PySide6.QtCore import Qt

    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.apply_display_settings(EditorDisplaySettings(auto_paragraph_indent_enabled=False))
    panel.set_entry(Entry(id="entry-1", title="t", body="第一段"))
    panel.focus_body()

    qtbot.keyClick(panel._body, Qt.Key.Key_Return)  # noqa: SLF001

    assert panel.body_text() == "第一段\n"


def test_editor_panel_mouse_click_does_not_schedule_typewriter_scroll(qtbot):
    from PySide6.QtCore import QPoint, Qt

    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(600, 260)
    panel.show()
    panel.apply_display_settings(EditorDisplaySettings(typewriter_mode_enabled=True))
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(80))))
    qtbot.wait(20)

    body = panel._body  # noqa: SLF001
    body.verticalScrollBar().setValue(30)
    body._typewriter_adjust_allowed = False  # noqa: SLF001
    qtbot.mouseClick(body.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(20, 20))

    assert body._typewriter_timer.isActive() is False  # noqa: SLF001


def test_editor_panel_backspace_does_not_recentre_small_window_typewriter(qtbot):
    from PySide6.QtCore import Qt

    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(440, 220)
    panel.show()
    panel.apply_display_settings(EditorDisplaySettings(typewriter_mode_enabled=True))
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(120))))
    panel.focus_body()
    body = panel._body  # noqa: SLF001
    scrollbar = body.verticalScrollBar()
    qtbot.waitUntil(lambda: scrollbar.value() > 0)

    qtbot.keyClick(body, Qt.Key.Key_Backspace)
    qtbot.wait(30)

    assert scrollbar.value() >= max(0, scrollbar.maximum() - 5)
    assert body._typewriter_timer.isActive() is False  # noqa: SLF001
    assert getattr(scrollbar, "_writer_scroll_animation", None) is None


def test_editor_panel_focus_mode_continuous_delete_does_not_recentre(qtbot):
    from PySide6.QtCore import Qt

    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(440, 220)
    panel.show()
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(120))))
    panel.set_focus_mode_enabled(True)
    panel.focus_body()
    body = panel._body  # noqa: SLF001
    scrollbar = body.verticalScrollBar()
    qtbot.waitUntil(lambda: scrollbar.value() > 0)
    body._schedule_typewriter_adjust(force=True)  # noqa: SLF001
    body._typewriter_timer.start(1000)  # noqa: SLF001

    for _ in range(5):
        qtbot.keyClick(body, Qt.Key.Key_Backspace)
        qtbot.wait(10)

    qtbot.wait(30)

    assert body._typewriter_timer.isActive() is False  # noqa: SLF001
    assert getattr(scrollbar, "_writer_scroll_animation", None) is None


def test_editor_panel_delete_cancels_pending_follow_and_scroll_animation(qtbot):
    from PySide6.QtCore import Qt

    from writer.domain.models.entry import Entry
    from writer.ui.motion import smooth_scrollbar_to
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(440, 220)
    panel.show()
    panel.apply_display_settings(EditorDisplaySettings(typewriter_mode_enabled=True))
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(120))))
    panel.focus_body()
    body = panel._body  # noqa: SLF001
    scrollbar = body.verticalScrollBar()
    qtbot.waitUntil(lambda: scrollbar.maximum() > 0)

    body._schedule_typewriter_adjust(force=True)  # noqa: SLF001
    body._typewriter_timer.start(1000)  # noqa: SLF001
    scrollbar.setValue(0)
    smooth_scrollbar_to(scrollbar, min(60, scrollbar.maximum()), duration_ms=500)
    animation = getattr(scrollbar, "_writer_scroll_animation", None)

    assert animation is not None
    assert body._typewriter_timer.isActive() is True  # noqa: SLF001

    qtbot.keyClick(body, Qt.Key.Key_Delete)
    qtbot.waitUntil(lambda: getattr(scrollbar, "_writer_scroll_animation", None) is None)

    assert body._typewriter_timer.isActive() is False  # noqa: SLF001
    assert getattr(scrollbar, "_writer_scroll_animation", None) is None
    assert animation.state() == animation.State.Stopped


def test_editor_panel_text_input_and_return_still_schedule_typewriter_follow(qtbot):
    from PySide6.QtCore import Qt

    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(440, 220)
    panel.show()
    panel.apply_display_settings(
        EditorDisplaySettings(
            auto_paragraph_indent_enabled=False,
            typewriter_mode_enabled=True,
        )
    )
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(120))))
    panel.focus_body()
    body = panel._body  # noqa: SLF001

    qtbot.keyClicks(body, "x")
    assert body._typewriter_timer.isActive() is True  # noqa: SLF001
    body._typewriter_timer.stop()  # noqa: SLF001

    qtbot.keyClick(body, Qt.Key.Key_Return)
    assert body._typewriter_timer.isActive() is True  # noqa: SLF001


def test_editor_panel_focus_mode_expands_writing_surface(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel, FOCUS_MODE_CONTENT_WIDTH

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.apply_display_settings(EditorDisplaySettings(content_width=680))

    assert panel._content_wrap.maximumWidth() == 680  # noqa: SLF001

    panel.set_focus_mode_enabled(True)
    assert panel._content_wrap.maximumWidth() == FOCUS_MODE_CONTENT_WIDTH  # noqa: SLF001

    panel.set_focus_mode_enabled(False)
    assert panel._content_wrap.maximumWidth() == 680  # noqa: SLF001


def test_editor_panel_expands_when_window_is_wide(qtbot):
    from PySide6.QtWidgets import QSizePolicy

    from writer.ui.panels.editor_panel import (
        EDITOR_RESPONSIVE_SIDE_MARGIN,
        FOCUS_MODE_RESPONSIVE_SIDE_MARGIN,
        EditorPanel,
    )

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.apply_display_settings(EditorDisplaySettings(content_width=680))
    panel.resize(1500, 800)
    panel._apply_content_width()  # noqa: SLF001

    assert panel._content_wrap.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding  # noqa: SLF001
    assert panel._content_wrap.maximumWidth() == 1500 - EDITOR_RESPONSIVE_SIDE_MARGIN  # noqa: SLF001

    panel.set_focus_mode_enabled(True)
    assert panel._content_wrap.maximumWidth() == 1500 - FOCUS_MODE_RESPONSIVE_SIDE_MARGIN  # noqa: SLF001


def test_main_window_applies_persisted_editor_preferences(qtbot, container):
    from writer.ui.main_window import MainWindow

    container.settings.save_editor_display_settings(
        EditorDisplaySettings(
            font_size=20,
            line_height=2.0,
            paragraph_spacing=1.0,
            content_width=700,
            font_family="Georgia",
            visual_first_line_indent_enabled=False,
            typewriter_mode_enabled=False,
            soft_page_guides_enabled=False,
        )
    )

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    applied = window._editor_panel.display_settings()  # noqa: SLF001
    assert applied.font_size == 20
    assert applied.line_height == 2.0
    assert applied.content_width == 700
    assert applied.font_family == "Georgia"
    assert applied.visual_first_line_indent_enabled is False
    assert applied.soft_page_guides_enabled is False


def test_editor_panel_find_shortcuts_highlight_and_cycle(qtbot):
    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_entry(
        Entry(
            id="entry-1",
            title="t",
            body="Alpha beta\n中文标点，alpha。\nALPHA again",
        )
    )
    panel.focus_body()

    qtbot.keyClick(panel._body, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)  # noqa: SLF001
    qtbot.waitUntil(lambda: panel._find_bar.isVisible())  # noqa: SLF001
    qtbot.keyClicks(panel._find_bar._input, "alpha")  # noqa: SLF001
    qtbot.waitUntil(lambda: panel._find_bar._count_label.text() == "1/3")  # noqa: SLF001

    assert len(panel._body.extraSelections()) >= 3  # noqa: SLF001
    assert panel.selected_body_text().lower() == "alpha"

    qtbot.keyClick(panel._find_bar._input, Qt.Key.Key_Return)  # noqa: SLF001
    assert panel._find_bar._count_label.text() == "2/3"  # noqa: SLF001
    assert panel.selected_body_text().lower() == "alpha"

    qtbot.keyClick(
        panel._find_bar._input,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.ShiftModifier,
    )  # noqa: SLF001
    assert panel._find_bar._count_label.text() == "1/3"  # noqa: SLF001

    qtbot.keyClick(panel._find_bar._input, Qt.Key.Key_Escape)  # noqa: SLF001
    assert panel._find_bar.isHidden() is True  # noqa: SLF001


def test_editor_panel_find_no_results_keeps_cursor_and_reports_empty(qtbot):
    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_entry(Entry(id="entry-1", title="t", body="中文错别字，English Mixed Case"))
    panel.focus_body()
    original_pos = panel._body.textCursor().position()  # noqa: SLF001

    panel._find_bar.open_and_focus()  # noqa: SLF001
    panel._find_bar.set_query("不存在")  # noqa: SLF001

    assert panel._find_bar._count_label.text() == "无结果" or panel._find_bar._count_label.text() == "No results"  # noqa: SLF001
    panel._find_bar.go_next()  # noqa: SLF001
    assert panel._body.textCursor().position() == original_pos  # noqa: SLF001


def test_editor_panel_find_refreshes_after_body_change_and_entry_switch(qtbot, container):
    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    first = Entry(id="entry-1", title="t1", body="apple apple")
    second = Entry(id="entry-2", title="t2", body="banana only")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_entry(first)

    panel._find_bar.activate_excerpt("apple")  # noqa: SLF001
    assert panel._find_bar._count_label.text() == "1/2"  # noqa: SLF001

    panel.replace_body("apple")
    qtbot.waitUntil(lambda: panel._find_bar._count_label.text() == "1/1")  # noqa: SLF001

    panel.set_entry(second)
    qtbot.waitUntil(lambda: panel._find_bar._count_label.text() == "无结果" or panel._find_bar._count_label.text() == "No results")  # noqa: SLF001
    assert panel._body.extraSelections() == [] or len(panel._body.extraSelections()) == 0  # noqa: SLF001


def test_work_editor_find_shortcuts_refresh_on_section_switch(qtbot, container):
    from writer.domain.enums import SectionType
    from writer.ui.panels.work_editor_panel import WorkEditorPanel

    work = container.work_repository.create(title="W")
    first = container.work_section_repository.create(work.id, section_type=SectionType.BODY.value, content="moon river moon")
    second = container.work_section_repository.create(work.id, section_type=SectionType.BODY.value, content="sun only")

    panel = WorkEditorPanel(container)
    qtbot.addWidget(panel)
    panel.show()
    panel.load_work(work.id)
    panel.focus_section(first.id)

    qtbot.keyClick(panel._editor, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)  # noqa: SLF001
    qtbot.waitUntil(lambda: panel._find_bar.isVisible())  # noqa: SLF001
    qtbot.keyClicks(panel._find_bar._input, "moon")  # noqa: SLF001
    qtbot.waitUntil(lambda: panel._find_bar._count_label.text() == "1/2")  # noqa: SLF001

    qtbot.keyClick(panel._find_bar._input, Qt.Key.Key_Return)  # noqa: SLF001
    assert panel._find_bar._count_label.text() == "2/2"  # noqa: SLF001

    panel.focus_section(second.id)
    qtbot.waitUntil(lambda: panel._find_bar._count_label.text() == "无结果" or panel._find_bar._count_label.text() == "No results")  # noqa: SLF001


def test_soft_page_guides_toggle_does_not_mutate_plain_text(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    text = "第一段\n第二段"
    panel.replace_body(text)

    panel.apply_display_settings(EditorDisplaySettings(soft_page_guides_enabled=True))
    assert panel.body_text() == text
    assert panel._body.soft_page_guides_enabled() is True  # noqa: SLF001

    panel.apply_display_settings(EditorDisplaySettings(soft_page_guides_enabled=False))
    assert panel.body_text() == text
    assert panel._body.soft_page_guides_enabled() is False  # noqa: SLF001
    assert panel._page_controls.isVisible() is False  # noqa: SLF001


def test_editor_page_controls_turn_pages_without_mutating_text(qtbot):
    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    text = "\n".join(str(i) for i in range(160))
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(520, 260)
    panel.show()
    panel.set_reduced_motion(True)
    panel.apply_display_settings(EditorDisplaySettings(soft_page_guides_enabled=True))
    panel.set_entry(Entry(id="entry-1", title="t", body=text))
    body = panel._body  # noqa: SLF001
    scrollbar = body.verticalScrollBar()
    qtbot.waitUntil(lambda: scrollbar.maximum() > 0)

    panel._page_controls.next_page()  # noqa: SLF001
    qtbot.waitUntil(lambda: scrollbar.value() > 0)

    assert panel.body_text() == text
    assert body.current_soft_page() >= 2


def test_editor_page_controls_work_with_epigraph_and_do_not_draw_body_guides(qtbot):
    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    body_text = (
        "“从来没爱你，绵绵。可惜我爱怀念。”      —— 《绵绵》 陈奕迅\n"
        "　　\n"
        + "\n".join(
            "　　这是一段用于验证长文翻页的正文，包含足够多的文字，避免纸页控件因为短文而禁用。"
            for _ in range(90)
        )
    )
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(900, 700)
    panel.show()
    panel.set_reduced_motion(True)
    panel.apply_display_settings(EditorDisplaySettings(soft_page_guides_enabled=True))
    panel.set_entry(Entry(id="entry-1", title="绵绵", body=body_text))
    body = panel._body  # noqa: SLF001
    scrollbar = body.verticalScrollBar()

    qtbot.waitUntil(lambda: scrollbar.maximum() > 0)
    qtbot.waitUntil(lambda: panel._page_controls._next_btn.isEnabled())  # noqa: SLF001
    assert not hasattr(body, "_paint_soft_page_guides")

    panel._page_controls._next_btn.click()  # noqa: SLF001
    qtbot.waitUntil(lambda: scrollbar.value() > 0)

    assert panel.body_text() == body_text
    assert panel._epigraph_card.isVisible() is True  # noqa: SLF001


def test_work_editor_page_controls_disable_at_reachable_end(qtbot, container):
    from writer.domain.enums import SectionType
    from writer.ui.panels.work_editor_panel import WorkEditorPanel

    body_text = "\n".join(f"line {i}" for i in range(4))
    work = container.work_repository.create(title="W")
    container.work_section_repository.create(
        work.id,
        section_type=SectionType.BODY.value,
        content=body_text,
    )

    panel = WorkEditorPanel(container)
    qtbot.addWidget(panel)
    panel.resize(720, 320)
    panel.show()
    panel.load_work(work.id)
    editor = panel._editor  # noqa: SLF001
    editor.set_reduced_motion(True)
    scrollbar = editor.verticalScrollBar()

    qtbot.waitUntil(lambda: editor.toPlainText() == body_text)
    qtbot.waitUntil(lambda: panel._page_controls._next_btn.isEnabled())  # noqa: SLF001

    for _ in range(10):
        if scrollbar.value() == scrollbar.maximum():
            break
        previous = scrollbar.value()
        panel._page_controls.next_page()  # noqa: SLF001
        qtbot.waitUntil(lambda: scrollbar.value() > previous)

    assert scrollbar.value() == scrollbar.maximum()
    assert editor.current_soft_page() == editor.soft_page_count()
    assert panel._page_controls._next_btn.isEnabled() is False  # noqa: SLF001


def test_editor_panel_page_keys_use_paper_scroll_not_typewriter_follow(qtbot):
    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(440, 260)
    panel.show()
    panel.apply_display_settings(EditorDisplaySettings(typewriter_mode_enabled=True))
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(120))))
    panel.focus_body()
    body = panel._body  # noqa: SLF001

    qtbot.keyClick(body, Qt.Key.Key_PageDown)

    assert body._typewriter_timer.isActive() is False  # noqa: SLF001


def test_editor_panel_wheel_scrolls_precisely_not_to_end(qtbot):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QWheelEvent

    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.resize(520, 260)
    panel.show()
    panel.apply_display_settings(
        EditorDisplaySettings(
            typewriter_mode_enabled=False,
            soft_page_guides_enabled=True,
        )
    )
    panel.set_reduced_motion(True)
    panel.set_entry(Entry(id="entry-1", title="t", body="\n".join(str(i) for i in range(200))))
    body = panel._body  # noqa: SLF001
    scrollbar = body.verticalScrollBar()
    scrollbar.setValue(0)
    qtbot.waitUntil(lambda: scrollbar.maximum() > 0)

    event = QWheelEvent(
        QPoint(20, 20),
        body.viewport().mapToGlobal(QPoint(20, 20)),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    body.wheelEvent(event)  # noqa: SLF001
    qtbot.waitUntil(lambda: scrollbar.value() > 0)

    assert scrollbar.value() < scrollbar.maximum() // 4


def test_work_editor_wheel_scrolls_precisely_not_to_end(qtbot, container):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QWheelEvent

    from writer.domain.enums import SectionType
    from writer.ui.panels.work_editor_panel import WorkEditorPanel

    work = container.work_repository.create(title="W")
    container.work_section_repository.create(
        work.id,
        section_type=SectionType.BODY.value,
        content="\n".join(str(i) for i in range(200)),
    )
    panel = WorkEditorPanel(container)
    qtbot.addWidget(panel)
    panel.resize(720, 320)
    panel.show()
    panel.load_work(work.id)
    editor = panel._editor  # noqa: SLF001
    editor.set_reduced_motion(True)
    scrollbar = editor.verticalScrollBar()
    scrollbar.setValue(0)
    qtbot.waitUntil(lambda: scrollbar.maximum() > 0)

    event = QWheelEvent(
        QPoint(20, 20),
        editor.viewport().mapToGlobal(QPoint(20, 20)),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    editor.wheelEvent(event)  # noqa: SLF001
    qtbot.waitUntil(lambda: scrollbar.value() > 0)

    assert scrollbar.value() < scrollbar.maximum() // 4
