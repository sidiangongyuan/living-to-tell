"""Application bootstrap — wires Qt, storage, and the main window."""
from __future__ import annotations

import sys
import traceback
from typing import List, Optional

from PySide6.QtWidgets import QApplication, QMessageBox

from writer.app.application_controller import ApplicationController
from writer.app.container import AppContainer, build_container
from writer.app.version import APP_VERSION
from writer.ui.main_window import MainWindow


def _ensure_qapplication(argv: List[str]) -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing  # type: ignore[return-value]
    return QApplication(argv)


def create_main_window(container: AppContainer) -> MainWindow:
    """Build (but do not show) the main window for a given container."""
    return MainWindow(container)


def run(argv: Optional[List[str]] = None) -> int:
    """Boot the application and run the Qt event loop."""
    args = list(argv) if argv is not None else sys.argv
    app = _ensure_qapplication(args)
    app.setApplicationName("Writer")
    app.setOrganizationName("Writer")
    app.setApplicationVersion(APP_VERSION)

    try:
        container = build_container()
    except Exception:  # noqa: BLE001
        _show_startup_error("Failed to initialise the database or services.")
        return 1

    # Load the persisted locale before any UI is constructed so TR() calls
    # during widget initialisation pick up the right language.
    try:
        from writer.app import locale as locale_module
        from writer.ui.i18n import TR as _TR_unused  # noqa: F401 — side-effect import
        locale_module.set_locale(container.settings.language)
    except Exception:  # noqa: BLE001 — locale failure must not block startup
        pass

    # M9A: install the visual theme before any widgets are constructed so
    # the entire shell picks up the right palette / QSS on the first paint.
    try:
        from writer.app.settings import KEY_THEME_MODE, DEFAULT_THEME_MODE
        from writer.ui.theme import ThemeMode, apply_theme

        mode_raw = container.settings.get(KEY_THEME_MODE, DEFAULT_THEME_MODE)
        apply_theme(app, ThemeMode.parse(mode_raw))
    except Exception:  # noqa: BLE001 — theme failure must not block startup
        pass

    try:
        controller = ApplicationController(
            app,
            container,
            main_window_factory=create_main_window,
        )
        controller.start()
        return app.exec()
    except Exception:  # noqa: BLE001
        _show_startup_error("An unexpected error occurred during startup.")
        return 1
    finally:
        container.close()


def _show_startup_error(message: str) -> None:
    """Display a visible error dialog and print to stderr."""
    full = f"{message}\n\n{traceback.format_exc()}"
    print(full, file=sys.stderr)
    # QApplication may already exist (called from tests), so be safe.
    try:
        QMessageBox.critical(None, "Writer — Startup Error", full)
    except Exception:  # noqa: BLE001
        pass  # if Qt itself is broken, at least stderr was written
