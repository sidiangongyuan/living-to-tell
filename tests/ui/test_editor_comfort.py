from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container
from writer.app.settings import EditorDisplaySettings


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


def test_editor_panel_applies_display_settings_to_body(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)

    custom = EditorDisplaySettings(
        font_size=22,
        line_height=2.1,
        paragraph_spacing=1.0,
        content_width=680,
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

    assert panel._body.font().pointSize() == 22  # noqa: SLF001
    assert panel._content_wrap.maximumWidth() == 680  # noqa: SLF001
    assert block_format.lineHeight() == 210.0
    assert block_format.textIndent() > 0


def test_visual_first_line_indent_does_not_mutate_plain_text(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.apply_display_settings(
        EditorDisplaySettings(visual_first_line_indent_enabled=True)
    )

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
            visual_first_line_indent_enabled=False,
            typewriter_mode_enabled=False,
        )
    )

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    applied = window._editor_panel.display_settings()  # noqa: SLF001
    assert applied.font_size == 20
    assert applied.line_height == 2.0
    assert applied.content_width == 700
    assert applied.visual_first_line_indent_enabled is False