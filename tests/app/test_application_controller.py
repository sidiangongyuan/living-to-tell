from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from writer.app.application_controller import ApplicationController
from writer.app.bootstrap import create_main_window
from writer.app.container import build_container
from writer.app.quick_capture import quick_capture_tag
from writer.app.settings import KEY_QUICK_CAPTURE_LAST_ENTRY_ID
from writer.ui.main_window import MODE_FRAGMENTS


class DummyHotkeyManager(QObject):
    registration_failed = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.supported = True
        self.host_window = None
        self.registrations: list[tuple[str, str]] = []
        self.unregistered = False

    def set_host_window(self, window) -> None:
        self.host_window = window

    def register_hotkey(self, *, name: str, sequence: str, callback) -> bool:
        self.registrations.append((name, sequence))
        return True

    def unregister_all(self) -> None:
        self.unregistered = True

    def handle_native_message(self, message: int, wparam: int) -> bool:
        return False


class FakeTrayIcon(QObject):
    activated = Signal(object)

    def __init__(self, icon, parent=None) -> None:
        super().__init__(parent)
        self.icon = icon
        self.menu = None
        self.visible = False

    def setContextMenu(self, menu) -> None:
        self.menu = menu

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def _build_controller(
    container,
    *,
    hotkeys=None,
    tray_available=False,
    tray_icon_factory=FakeTrayIcon,
):
    app = QApplication.instance() or QApplication([])
    return ApplicationController(
        app,
        container,
        main_window_factory=create_main_window,
        hotkey_manager=hotkeys or DummyHotkeyManager(),
        tray_available=tray_available,
        tray_icon_factory=tray_icon_factory,
    )


def test_controller_registers_both_default_hotkeys(qtbot, container):
    hotkeys = DummyHotkeyManager()
    controller = _build_controller(container, hotkeys=hotkeys)

    controller.start()

    qtbot.waitUntil(lambda: len(hotkeys.registrations) == 2)
    assert hotkeys.host_window is controller.main_window
    assert hotkeys.registrations == [
        ("quick_capture", "Ctrl+Alt+`"),
        ("main_window", "Ctrl+Alt+M"),
    ]

    controller.shutdown()


def test_controller_maps_legacy_quick_capture_hotkey_to_new_default(qtbot, container):
    from writer.app.settings import KEY_QUICK_CAPTURE_GLOBAL_HOTKEY

    container.settings.set(KEY_QUICK_CAPTURE_GLOBAL_HOTKEY, "Ctrl+Alt+W")
    hotkeys = DummyHotkeyManager()
    controller = _build_controller(container, hotkeys=hotkeys)

    controller.start()

    qtbot.waitUntil(lambda: len(hotkeys.registrations) == 2)
    assert hotkeys.registrations[0] == ("quick_capture", "Ctrl+Alt+`")

    controller.shutdown()


def test_controller_closing_main_window_hides_to_tray(qtbot, container):
    controller = _build_controller(container, tray_available=True)

    controller.start()
    qtbot.waitUntil(lambda: controller.main_window.isVisible())

    controller.main_window.close()

    qtbot.waitUntil(lambda: not controller.main_window.isVisible())
    assert controller._tray_icon is not None  # noqa: SLF001
    assert controller._tray_icon.visible is True  # noqa: SLF001

    controller.shutdown()


def test_controller_restores_last_quick_capture_entry(qtbot, container):
    entry = container.entry_repository.create(
        title="resume",
        body="resume this quick note",
        tags=[quick_capture_tag()],
    )
    container.settings.set(KEY_QUICK_CAPTURE_LAST_ENTRY_ID, entry.id)
    controller = _build_controller(container)

    controller.show_quick_capture()

    qtbot.waitUntil(lambda: controller.quick_capture_window.current_entry_id == entry.id)
    assert controller.quick_capture_window._body_edit.toPlainText() == "resume this quick note"  # noqa: SLF001

    controller.shutdown()


def test_quick_capture_save_refreshes_main_list_and_dates(qtbot, container):
    controller = _build_controller(container)
    controller.start()

    controller.show_quick_capture()
    controller.quick_capture_window._body_edit.setPlainText("sync from quick capture")  # noqa: SLF001

    qtbot.waitUntil(lambda: controller.main_window._list_panel._list.count() == 1)  # noqa: SLF001
    assert controller.main_window._fragments_stack.currentIndex() == 0  # noqa: SLF001
    assert controller.main_window._dates_panel._entry_list.count() == 1  # noqa: SLF001

    controller.shutdown()


def test_quick_capture_open_writer_loads_saved_entry(qtbot, container):
    controller = _build_controller(container)
    controller.start()
    controller.show_quick_capture()

    controller.quick_capture_window._body_edit.setPlainText("open writer handoff")  # noqa: SLF001
    entry_id = controller.quick_capture_window.save_now()

    controller.quick_capture_window._open_writer_btn.click()  # noqa: SLF001

    qtbot.waitUntil(
        lambda: controller.main_window._editor_panel.current_entry_id() == entry_id  # noqa: SLF001
    )
    assert controller.main_window._stack.currentIndex() == MODE_FRAGMENTS  # noqa: SLF001
    assert not controller.quick_capture_window.isVisible()
    assert container.settings.get(KEY_QUICK_CAPTURE_LAST_ENTRY_ID, "") == ""

    controller.shutdown()