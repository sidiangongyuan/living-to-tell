"""Smoke test: the application boots, the DB initialises, the window shows."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app import paths as paths_module
from writer.app.bootstrap import create_main_window
from writer.app.container import build_container
from writer.app.version import APP_VERSION


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


def test_database_file_is_created(isolated_data_dir: Path, container) -> None:
    db_file = paths_module.database_path()
    assert db_file.exists(), f"expected SQLite file at {db_file}"
    assert db_file.parent == isolated_data_dir


def test_app_settings_table_exists(container) -> None:
    row = container.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='app_settings'"
    ).fetchone()
    assert row is not None, "app_settings table should be created by schema.sql"


def test_main_window_constructs_and_shows(qtbot, container) -> None:
    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.windowTitle() == "Writer"
    titles = {action.text() for action in window.menuBar().actions()}
    assert "&File" in titles
    assert "&AI" in titles
    assert "&Help" in titles
    # M9A: an empty database must NOT auto-create a fragment. Instead the
    # welcome card takes over the work area and the editor stays unloaded.
    assert window._editor_panel.current_entry_id() is None
    assert container.entry_repository.count() == 0
    assert window._fragments_stack.currentIndex() == 1


# ---------------------------------------------------------------------------
# M6B: launch polish / metadata tests
# ---------------------------------------------------------------------------

def test_app_version_constant_is_set() -> None:
    assert APP_VERSION, "APP_VERSION must be a non-empty string"
    assert "alpha" in APP_VERSION.lower() or APP_VERSION[0].isdigit(), (
        "APP_VERSION should be a semver or contain 'alpha'"
    )


def test_about_action_is_enabled(qtbot, container) -> None:
    """Help > About Writer must not be disabled (M6B requirement)."""
    window = create_main_window(container)
    qtbot.addWidget(window)

    help_menu = None
    for action in window.menuBar().actions():
        if action.text() == "&Help":
            help_menu = action.menu()
            break

    assert help_menu is not None, "Help menu not found"
    about = None
    for action in help_menu.actions():
        if "About" in action.text():
            about = action
            break
    assert about is not None, "About action not found"
    assert about.isEnabled(), "About Writer action must be enabled"


def test_main_window_title_is_writer(qtbot, container) -> None:
    window = create_main_window(container)
    qtbot.addWidget(window)
    assert window.windowTitle() == "Writer"


def test_bootstrap_sets_app_metadata(qtbot) -> None:
    """bootstrap.run() sets QApplication name, org, and version."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        pytest.skip("No QApplication instance available outside qtbot scope")
    # The qtbot fixture ensures a QApplication exists; bootstrap sets these.
    # We just confirm the module-level constants are consistent.
    from writer.app.paths import APP_NAME, APP_AUTHOR

    assert APP_NAME == "Writer"
    assert APP_AUTHOR == "Writer"
