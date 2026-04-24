"""UI and integration tests for M5E: entry tags, metadata area, recall filters.

Covers:
- EditorPanel: tags QLineEdit, content_changed signal, created/updated metadata
- FragmentListPanel: tag filter combo, signal emission
- MainWindow: autosave saves tags, tag filter refreshes list, search+tag combo,
  version-history restore does NOT change tags
"""
from __future__ import annotations

import pytest

from writer.app.container import build_container
from writer.storage.repositories.entry_repository import parse_tags, serialize_tags


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


# ---------------------------------------------------------------------------
# EditorPanel
# ---------------------------------------------------------------------------

def test_editor_panel_tags_field_exists(qtbot):
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    assert hasattr(panel, "_tags")


def test_editor_panel_set_entry_populates_tags(qtbot, container):
    from writer.ui.panels.editor_panel import EditorPanel

    entry = container.entry_repository.create(
        title="t", body="b", tags=["summer", "rain"]
    )
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.set_entry(entry)

    assert panel.tags_text() == "summer, rain"


def test_editor_panel_set_entry_none_clears_tags(qtbot, container):
    from writer.ui.panels.editor_panel import EditorPanel

    entry = container.entry_repository.create(
        title="t", body="b", tags=["summer"]
    )
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.set_entry(entry)
    panel.set_entry(None)

    assert panel.tags_text() == ""
    assert not panel.isEnabled()


def test_editor_panel_tags_change_emits_content_changed(qtbot, container):
    from writer.ui.panels.editor_panel import EditorPanel

    entry = container.entry_repository.create(title="t", body="b")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.set_entry(entry)

    with qtbot.waitSignal(panel.content_changed, timeout=500):
        panel._tags.setText("new tag")  # noqa: SLF001


def test_editor_panel_metadata_shows_created_and_updated(qtbot, container):
    from writer.ui.panels.editor_panel import EditorPanel

    entry = container.entry_repository.create(title="t", body="b")
    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.set_entry(entry)

    meta_text = panel._meta.text()  # noqa: SLF001
    assert "created" in meta_text
    assert "updated" in meta_text


# ---------------------------------------------------------------------------
# FragmentListPanel
# ---------------------------------------------------------------------------

def test_fragment_list_panel_tag_combo_exists(qtbot):
    from writer.ui.panels.fragment_list_panel import FragmentListPanel

    panel = FragmentListPanel()
    qtbot.addWidget(panel)
    assert hasattr(panel, "_tag_combo")


def test_fragment_list_panel_set_tag_options_populates_combo(qtbot):
    from writer.ui.panels.fragment_list_panel import FragmentListPanel

    panel = FragmentListPanel()
    qtbot.addWidget(panel)
    panel.set_tag_options(["apple", "banana", "cherry"])

    # index 0 = "All tags", then the three tags
    assert panel._tag_combo.count() == 4  # noqa: SLF001
    assert panel.current_tag_filter() is None  # default = "All tags"


def test_fragment_list_panel_tag_filter_signal(qtbot):
    from writer.ui.panels.fragment_list_panel import FragmentListPanel

    panel = FragmentListPanel()
    qtbot.addWidget(panel)
    panel.set_tag_options(["summer"])

    with qtbot.waitSignal(panel.tag_filter_changed, timeout=500):
        panel._tag_combo.setCurrentIndex(1)  # noqa: SLF001


def test_fragment_list_panel_current_tag_filter(qtbot):
    from writer.ui.panels.fragment_list_panel import FragmentListPanel

    panel = FragmentListPanel()
    qtbot.addWidget(panel)
    panel.set_tag_options(["summer", "winter"])
    panel._tag_combo.setCurrentIndex(1)  # "summer"  # noqa: SLF001

    assert panel.current_tag_filter() == "summer"


def test_fragment_list_panel_tag_filter_fallback_when_tag_removed(qtbot):
    """If the current tag is removed from the list, panel falls back to All tags."""
    from writer.ui.panels.fragment_list_panel import FragmentListPanel

    panel = FragmentListPanel()
    qtbot.addWidget(panel)
    panel.set_tag_options(["summer", "winter"])
    panel._tag_combo.setCurrentIndex(1)  # "summer"  # noqa: SLF001
    assert panel.current_tag_filter() == "summer"

    # Refresh without "summer"
    panel.set_tag_options(["winter"])
    assert panel.current_tag_filter() is None  # fell back to "All tags"


# ---------------------------------------------------------------------------
# MainWindow: autosave saves tags
# ---------------------------------------------------------------------------

def test_main_window_autosave_saves_tags(qtbot, container):
    """Editing tags in the editor triggers autosave which persists tags."""
    from writer.ui.main_window import MainWindow

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    entry = container.entry_repository.create(title="t", body="b")
    window._load_entry(entry.id)  # noqa: SLF001

    # Set tags in editor
    window._editor_panel._tags.setText("sky, ocean")  # noqa: SLF001

    # Manually flush autosave
    window._autosave.flush()  # noqa: SLF001

    reloaded = container.entry_repository.get(entry.id)
    assert reloaded is not None
    assert set(reloaded.tags) == {"sky", "ocean"}


def test_main_window_switch_entry_flushes_tags(qtbot, container):
    """When switching entries, autosave flush must persist current tags."""
    from writer.ui.main_window import MainWindow

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    entry_a = container.entry_repository.create(title="a", body="body a")
    entry_b = container.entry_repository.create(title="b", body="body b")
    window._load_entry(entry_a.id)  # noqa: SLF001

    # Set tags
    window._editor_panel._tags.setText("summer")  # noqa: SLF001

    # Switch to entry_b — flush must happen
    window._on_entry_selected(entry_b.id)  # noqa: SLF001

    reloaded_a = container.entry_repository.get(entry_a.id)
    assert reloaded_a is not None
    assert "summer" in reloaded_a.tags


# ---------------------------------------------------------------------------
# MainWindow: tag filter controls list
# ---------------------------------------------------------------------------

def test_main_window_tag_filter_shows_only_matching(qtbot, container):
    """With a tag filter active, the list shows only entries with that tag."""
    from PySide6.QtCore import Qt

    from writer.ui.main_window import MainWindow

    e_summer = container.entry_repository.create(title="summer frag", tags=["summer"])
    _e_winter = container.entry_repository.create(title="winter frag", tags=["winter"])

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    window._list_panel.set_tag_options(["summer", "winter"])  # noqa: SLF001
    # Activate "summer" filter
    idx = window._list_panel._tag_combo.findText("summer")  # noqa: SLF001
    window._list_panel._tag_combo.setCurrentIndex(idx)  # noqa: SLF001
    window._refresh_list()  # noqa: SLF001

    lst = window._list_panel._list  # noqa: SLF001
    ids = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())]
    assert e_summer.id in ids
    # All shown entries must have the "summer" tag
    for eid in ids:
        entry = container.entry_repository.get(eid)
        assert entry is not None
        assert any(t.lower() == "summer" for t in entry.tags)


def test_main_window_search_and_tag_filter_combined(qtbot, container):
    """Both search and tag filter active: result is the intersection."""
    from PySide6.QtCore import Qt

    from writer.ui.main_window import MainWindow

    a = container.entry_repository.create(
        title="autumn rain", body="", tags=["autumn"]
    )
    _b = container.entry_repository.create(
        title="autumn sun", body="", tags=["summer"]
    )
    _c = container.entry_repository.create(
        title="winter rain", body="", tags=["autumn"]
    )

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    # Set search = "autumn", tag filter = "autumn"
    window._list_panel._search.setText("autumn")  # noqa: SLF001
    window._list_panel.set_tag_options(["autumn", "summer"])  # noqa: SLF001
    idx = window._list_panel._tag_combo.findText("autumn")  # noqa: SLF001
    window._list_panel._tag_combo.setCurrentIndex(idx)  # noqa: SLF001
    window._refresh_list()  # noqa: SLF001

    lst = window._list_panel._list  # noqa: SLF001
    ids = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())]
    # Only 'a' has title matching "autumn" AND tag "autumn"
    assert a.id in ids


# ---------------------------------------------------------------------------
# Version history restore does NOT change tags
# ---------------------------------------------------------------------------

def test_version_history_restore_preserves_tags(qtbot, container):
    """Restoring a body version must not alter the entry's tags."""
    from writer.domain.enums import VersionType

    entry = container.entry_repository.create(
        title="t", body="original body", tags=["precious", "keep"]
    )
    container.version_repository.add(
        entry_id=entry.id,
        version_type=VersionType.ORIGINAL.value,
        content="original body",
    )

    # Restore returns a new body; tags should be unchanged
    outcome = container.version_history_service.restore(
        entry.id,
        container.version_repository.list_for_entry(entry.id)[0].id,
    )
    # no-op because same content — tags still intact
    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.tags == ["precious", "keep"]


def test_version_history_restore_body_change_preserves_tags(qtbot, container):
    """Restoring to a different body version leaves tags untouched."""
    from writer.domain.enums import VersionType

    entry = container.entry_repository.create(
        title="t", body="live body", tags=["important"]
    )
    v = container.version_repository.add(
        entry_id=entry.id,
        version_type=VersionType.ORIGINAL.value,
        content="old body",
    )

    container.version_history_service.restore(entry.id, v.id)

    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.body == "old body"
    assert reloaded.tags == ["important"]


# ---------------------------------------------------------------------------
# Regression: New Fragment resets tag filter (M5E fix)
# ---------------------------------------------------------------------------

def test_new_fragment_resets_tag_filter_and_appears_in_list(qtbot, container):
    """New Fragment while a tag filter is active must reset the filter and
    make the new (untagged) fragment visible and selected in the list."""
    from PySide6.QtCore import Qt

    from writer.ui.main_window import MainWindow

    # Create an existing tagged entry so the filter has something to show
    container.entry_repository.create(title="tagged", tags=["summer"])

    window = MainWindow(container, autosave_debounce_ms=50)
    qtbot.addWidget(window)

    # Activate a tag filter
    window._list_panel.set_tag_options(["summer"])  # noqa: SLF001
    idx = window._list_panel._tag_combo.findText("summer")  # noqa: SLF001
    window._list_panel._tag_combo.setCurrentIndex(idx)  # noqa: SLF001
    assert window._list_panel.current_tag_filter() == "summer"

    # Create a new fragment while filter is active
    window._on_new_fragment()  # noqa: SLF001

    # Tag filter must have been reset to "All tags"
    assert window._list_panel.current_tag_filter() is None

    # New fragment must appear in the list
    lst = window._list_panel._list  # noqa: SLF001
    ids = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())]
    current_id = window._editor_panel.current_entry_id()
    assert current_id is not None
    assert current_id in ids

    # New fragment must be the selected item in the list
    selected = lst.currentItem()
    assert selected is not None
    assert selected.data(Qt.ItemDataRole.UserRole) == current_id
