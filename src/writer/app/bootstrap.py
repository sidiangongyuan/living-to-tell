"""Application bootstrap — wires Qt, storage, and the main window."""
from __future__ import annotations

import sys
import traceback
from typing import List, Optional

from PySide6.QtWidgets import QApplication, QMessageBox

from writer.app.container import AppContainer, build_container
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
    app.setApplicationVersion("0.1.0-alpha")

    try:
        container = build_container()
    except Exception:  # noqa: BLE001
        _show_startup_error("Failed to initialise the database or services.")
        return 1

    try:
        window = create_main_window(container)
        window.show()
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
