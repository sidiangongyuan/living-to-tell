from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtCore import Qt

from writer.app.container import build_container
from writer.app.quick_capture import quick_capture_tag
from writer.ui.i18n import TR
from writer.ui.quick_capture_window import QuickCaptureWindow


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_quick_capture_focuses_body_on_show(qtbot, container):
    window = QuickCaptureWindow(container.entry_repository, debounce_ms=20)
    qtbot.addWidget(window)

    window.show_for_typing()

    qtbot.waitUntil(lambda: window._body_edit.hasFocus())  # noqa: SLF001


def test_quick_capture_empty_close_does_not_create_entry(qtbot, container):
    window = QuickCaptureWindow(container.entry_repository, debounce_ms=20)
    qtbot.addWidget(window)
    window.show()

    window.close()

    qtbot.waitUntil(lambda: not window.isVisible())
    assert container.entry_repository.count() == 0
    assert window.current_entry_id is None


def test_quick_capture_creates_entry_on_first_body_input(qtbot, container):
    window = QuickCaptureWindow(container.entry_repository, debounce_ms=20)
    qtbot.addWidget(window)
    window.show_for_typing()

    qtbot.keyClicks(window._body_edit, "first quick note")  # noqa: SLF001

    qtbot.waitUntil(
        lambda: container.entry_repository.count() == 1
        and container.entry_repository.list_recent(limit=1)[0].body == "first quick note"
    )
    entry = container.entry_repository.list_recent(limit=1)[0]
    assert entry.body == "first quick note"
    assert quick_capture_tag() in entry.tags
    assert window.current_entry_id == entry.id
    assert window._status_label.text() == TR("quick.status_saved")  # noqa: SLF001


def test_quick_capture_autosaves_existing_entry_after_edit(qtbot, container):
    window = QuickCaptureWindow(container.entry_repository, debounce_ms=20)
    qtbot.addWidget(window)
    window.show_for_typing()

    qtbot.keyClicks(window._body_edit, "draft")  # noqa: SLF001
    qtbot.waitUntil(
        lambda: container.entry_repository.count() == 1
        and container.entry_repository.list_recent(limit=1)[0].body == "draft"
    )
    entry_id = window.current_entry_id

    qtbot.keyClicks(window._body_edit, " updated")  # noqa: SLF001

    assert window._status_label.text() == TR("quick.status_unsaved")  # noqa: SLF001
    qtbot.waitUntil(
        lambda: container.entry_repository.get(entry_id).body == "draft updated"
    )
    assert window._status_label.text() == TR("quick.status_saved")  # noqa: SLF001


def test_quick_capture_generates_title_from_body_when_blank(qtbot, container):
    window = QuickCaptureWindow(container.entry_repository, debounce_ms=20)
    qtbot.addWidget(window)
    window.show_for_typing()

    window._body_edit.setPlainText("\n\nA generated title line\nrest")  # noqa: SLF001
    entry_id = window.save_now()

    entry = container.entry_repository.get(entry_id)
    assert entry is not None
    assert entry.title == "A generated title line"
    assert window._title_edit.text() == "A generated title line"  # noqa: SLF001


def test_quick_capture_ctrl_s_saves_current_body(qtbot, container):
    window = QuickCaptureWindow(container.entry_repository, debounce_ms=200)
    qtbot.addWidget(window)
    window.show_for_typing()

    qtbot.keyClicks(window._body_edit, "save shortcut")  # noqa: SLF001
    qtbot.keyClick(window._body_edit, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)

    qtbot.waitUntil(
        lambda: container.entry_repository.count() == 1
        and container.entry_repository.list_recent(limit=1)[0].body == "save shortcut"
    )
    entry = container.entry_repository.list_recent(limit=1)[0]
    assert entry.body == "save shortcut"


def test_quick_capture_ctrl_enter_saves_and_starts_next_entry(qtbot, container):
    window = QuickCaptureWindow(container.entry_repository, debounce_ms=200)
    qtbot.addWidget(window)
    window.show_for_typing()

    qtbot.keyClicks(window._body_edit, "first note")  # noqa: SLF001
    qtbot.keyClick(
        window._body_edit,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.ControlModifier,
    )

    qtbot.waitUntil(
        lambda: container.entry_repository.count() == 1
        and container.entry_repository.list_recent(limit=1)[0].body == "first note"
    )
    entry = container.entry_repository.list_recent(limit=1)[0]
    assert entry.body == "first note"
    assert window.current_entry_id is None
    assert window._body_edit.toPlainText() == ""  # noqa: SLF001
    assert window._title_edit.text() == ""  # noqa: SLF001