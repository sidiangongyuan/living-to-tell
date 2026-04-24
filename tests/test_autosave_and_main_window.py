"""Tests for AutosaveService and the editor-list interaction in MainWindow."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.bootstrap import create_main_window
from writer.app.container import build_container
from writer.services.autosave_service import AutosaveService


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


# AutosaveService --------------------------------------------------------
def test_autosave_debounces_and_writes(qtbot, container) -> None:
    repo = container.entry_repository
    entry = repo.create(title="orig", body="orig body")

    state = {"title": "orig", "body": "orig body", "tags_text": ""}

    def snapshot():
        return entry.id, state["title"], state["body"], state["tags_text"]

    service = AutosaveService(repo, snapshot, debounce_ms=30)
    service.remember_clean(entry.id, "orig", "orig body", "")

    # No-op flush when nothing changed.
    service.flush()
    assert repo.get(entry.id).body == "orig body"

    # Mutate snapshot and trigger debounce.
    state["title"] = "edited"
    state["body"] = "edited body"

    with qtbot.waitSignal(service.saved, timeout=1000) as blocker:
        service.mark_dirty()

    assert blocker.args == [entry.id]
    reloaded = repo.get(entry.id)
    assert reloaded.title == "edited"
    assert reloaded.body == "edited body"


def test_autosave_skips_when_no_active_entry(container) -> None:
    repo = container.entry_repository
    service = AutosaveService(repo, lambda: None, debounce_ms=10)
    service.flush()  # must not raise


# MainWindow integration -------------------------------------------------
def test_main_window_auto_creates_blank_when_db_is_empty(qtbot, container) -> None:
    assert container.entry_repository.count() == 0
    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()
    assert container.entry_repository.count() == 1
    entries = container.entry_repository.list_recent()
    assert window._editor_panel.current_entry_id() == entries[0].id


def test_main_window_new_fragment_action_appends_entry(qtbot, container) -> None:
    window = create_main_window(container)
    qtbot.addWidget(window)
    window.show()
    initial = container.entry_repository.count()
    window._on_new_fragment()
    assert container.entry_repository.count() == initial + 1
