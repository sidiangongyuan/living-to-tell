"""Application lifecycle controller for tray, hotkeys, and quick capture."""
from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from writer.app.container import AppContainer
from writer.app.global_hotkeys import GlobalHotkeyManager, wintypes
from writer.app.quick_capture import is_quick_capture_entry
from writer.app.settings import (
    DEFAULT_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
    DEFAULT_QUICK_CAPTURE_GLOBAL_HOTKEY,
    DEFAULT_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY,
    KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
    KEY_QUICK_CAPTURE_GLOBAL_HOTKEY,
    KEY_QUICK_CAPTURE_LAST_ENTRY_ID,
    KEY_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY,
    LEGACY_QUICK_CAPTURE_GLOBAL_HOTKEY,
)
from writer.ui.i18n import TR
from writer.ui.main_window import MainWindow
from writer.ui.quick_capture_window import QuickCaptureWindow


class ApplicationController(QObject):
    def __init__(
        self,
        app: QApplication,
        container: AppContainer,
        *,
        main_window_factory: Callable[[AppContainer], MainWindow],
        quick_capture_factory: Callable[..., QuickCaptureWindow] = QuickCaptureWindow,
        hotkey_manager: Optional[GlobalHotkeyManager] = None,
        tray_icon_factory=QSystemTrayIcon,
        tray_available: Optional[bool] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._container = container
        self._main_window = main_window_factory(container)
        self._main_window.set_close_request_handler(self._handle_main_window_close)
        self._main_window.set_native_event_handler(self._handle_native_event)

        self._quick_capture_window = quick_capture_factory(container.entry_repository)
        self._quick_capture_window.entry_saved.connect(self._on_quick_entry_saved)
        self._quick_capture_window.open_writer_requested.connect(
            self._on_open_writer_requested
        )
        self._quick_capture_window.session_entry_changed.connect(
            self._on_quick_session_entry_changed
        )

        self._hotkeys = hotkey_manager or GlobalHotkeyManager(parent=self)
        self._hotkeys.registration_failed.connect(self._on_hotkey_registration_failed)

        self._shutdown_started = False
        self._tray_available = (
            QSystemTrayIcon.isSystemTrayAvailable()
            if tray_available is None
            else tray_available
        )
        self._tray_icon = self._create_tray_icon(tray_icon_factory) if self._tray_available else None
        self._app.aboutToQuit.connect(self._cleanup_for_exit)

    @property
    def main_window(self) -> MainWindow:
        return self._main_window

    @property
    def quick_capture_window(self) -> QuickCaptureWindow:
        return self._quick_capture_window

    def start(self) -> None:
        if self._tray_icon is not None:
            self._tray_icon.show()
        self._main_window.show()
        QTimer.singleShot(0, self._register_hotkeys)

    def shutdown(self) -> None:
        if self._shutdown_started:
            return
        self._shutdown_started = True
        self._cleanup_for_exit()
        self._quick_capture_window.shutdown()
        self._main_window.force_close()
        self._app.quit()

    def show_quick_capture(self) -> None:
        self._restore_quick_capture_session_if_needed()
        self._quick_capture_window.show_for_typing()

    def show_main_window(self, entry_id: Optional[str] = None) -> None:
        if entry_id:
            self._main_window.show_fragment_entry(entry_id)
            return
        self._main_window.show()
        if self._main_window.isMinimized():
            self._main_window.showNormal()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def toggle_main_window(self) -> None:
        if self._main_window.isVisible() and not self._main_window.isMinimized():
            self._main_window.hide()
            return
        self.show_main_window()

    def _create_tray_icon(self, tray_icon_factory):
        icon = self._app.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        tray = tray_icon_factory(icon, self)
        menu = QMenu()

        quick_action = QAction(TR("tray.quick_capture"), menu)
        quick_action.triggered.connect(self.show_quick_capture)
        menu.addAction(quick_action)

        main_action = QAction(TR("tray.show_writer"), menu)
        main_action.triggered.connect(self.show_main_window)
        menu.addAction(main_action)

        menu.addSeparator()

        exit_action = QAction(TR("tray.exit"), menu)
        exit_action.triggered.connect(self.shutdown)
        menu.addAction(exit_action)

        tray.setContextMenu(menu)
        if hasattr(tray, "activated"):
            tray.activated.connect(self._on_tray_activated)
        return tray

    def _register_hotkeys(self) -> None:
        self._hotkeys.unregister_all()
        self._hotkeys.set_host_window(self._main_window)
        quick_sequence = self._container.settings.get(
            KEY_QUICK_CAPTURE_GLOBAL_HOTKEY,
            DEFAULT_QUICK_CAPTURE_GLOBAL_HOTKEY,
        ) or DEFAULT_QUICK_CAPTURE_GLOBAL_HOTKEY
        if quick_sequence.strip().casefold() == LEGACY_QUICK_CAPTURE_GLOBAL_HOTKEY.casefold():
            quick_sequence = DEFAULT_QUICK_CAPTURE_GLOBAL_HOTKEY
        main_sequence = self._container.settings.get(
            KEY_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY,
            DEFAULT_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY,
        ) or DEFAULT_QUICK_CAPTURE_MAIN_WINDOW_HOTKEY
        self._hotkeys.register_hotkey(
            name="quick_capture",
            sequence=quick_sequence,
            callback=self.show_quick_capture,
        )
        self._hotkeys.register_hotkey(
            name="main_window",
            sequence=main_sequence,
            callback=self.toggle_main_window,
        )

    def _on_hotkey_registration_failed(self, _name: str, error: str) -> None:
        try:
            self._main_window.statusBar().showMessage(error, 5000)
        except Exception:  # noqa: BLE001
            print(error)

    def _handle_native_event(self, _event_type, message) -> bool:
        if not self._hotkeys.supported or sys.platform != "win32" or wintypes is None:
            return False
        msg = wintypes.MSG.from_address(int(message))
        return self._hotkeys.handle_native_message(int(msg.message), int(msg.wParam))

    def _handle_main_window_close(self) -> bool:
        if self._shutdown_started or self._tray_icon is None:
            return False
        enabled = self._container.settings.get(
            KEY_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED,
            "true" if DEFAULT_QUICK_CAPTURE_CLOSE_TO_TRAY_ENABLED else "false",
        )
        if (enabled or "").strip().lower() != "true":
            return False
        self._main_window.hide()
        return True

    def _restore_quick_capture_session_if_needed(self) -> None:
        if self._quick_capture_window.current_entry_id is not None:
            return
        last_entry_id = (
            self._container.settings.get(KEY_QUICK_CAPTURE_LAST_ENTRY_ID, "") or ""
        ).strip()
        if not last_entry_id:
            return
        entry = self._container.entry_repository.get(last_entry_id)
        if entry is None or not is_quick_capture_entry(entry):
            self._remember_quick_session_entry(None)
            return
        self._quick_capture_window.load_entry(entry)

    def _remember_quick_session_entry(self, entry_id: Optional[str]) -> None:
        self._container.settings.set(KEY_QUICK_CAPTURE_LAST_ENTRY_ID, entry_id or "")

    def _on_quick_entry_saved(self, entry_id: str) -> None:
        self._main_window.sync_external_entry(entry_id)

    def _on_open_writer_requested(self, entry_id: Optional[str]) -> None:
        self._quick_capture_window.start_new()
        self._quick_capture_window.hide()
        self._remember_quick_session_entry(None)
        self.show_main_window(entry_id)

    def _on_quick_session_entry_changed(self, entry_id: Optional[str]) -> None:
        self._remember_quick_session_entry(entry_id)

    def _on_tray_activated(self, reason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.show_quick_capture()

    def _cleanup_for_exit(self) -> None:
        self._hotkeys.unregister_all()
        if self._tray_icon is not None:
            self._tray_icon.hide()