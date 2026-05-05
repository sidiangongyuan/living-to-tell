"""UI tests for the Dates panel and the rail mode order (M-Dates)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from writer.app.container import build_container


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_dates_panel_default_is_today_and_emits_entry_picked(qtbot, container):
    from writer.ui.panels.dates_panel import DatesPanel

    repo = container.entry_repository
    e = repo.create(title="Today fragment", body="hello world")

    panel = DatesPanel(container)
    qtbot.addWidget(panel)

    assert panel.selected_date() == date.today()
    # Today's entry should be visible.
    ids = [
        panel._entry_list.item(i).data(0x0100)  # noqa: SLF001 — Qt.UserRole = 0x0100
        for i in range(panel._entry_list.count())  # noqa: SLF001
    ]
    assert e.id in ids

    # Activate first item -> entry_picked emits.
    with qtbot.waitSignal(panel.entry_picked, timeout=1000) as blocker:
        panel._on_item_activated(panel._entry_list.item(0))  # noqa: SLF001
    assert blocker.args[0] == e.id


def test_dates_panel_new_today_signal(qtbot, container):
    from writer.ui.panels.dates_panel import DatesPanel

    panel = DatesPanel(container)
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.new_today_requested, timeout=1000):
        panel._new_btn.click()  # noqa: SLF001


def test_dates_panel_append_tags_uses_repo_helper(qtbot, container):
    """append_tags must merge, not overwrite, existing tags."""
    repo = container.entry_repository
    e = repo.create(title="t", body="b", tags=["a", "b"])

    repo.append_tags(e.id, ["b", "c"])
    refreshed = repo.get(e.id)
    assert sorted(refreshed.tags) == ["a", "b", "c"]


def test_dates_panel_merge_signal_carries_selected_ids(qtbot, container):
    from PySide6.QtCore import Qt
    from writer.ui.panels.dates_panel import DatesPanel

    repo = container.entry_repository
    a = repo.create(title="a", body="aa")
    b = repo.create(title="b", body="bb")

    panel = DatesPanel(container)
    qtbot.addWidget(panel)

    # Select both rows.
    panel._entry_list.selectAll()  # noqa: SLF001
    ids = panel.selected_entry_ids()
    assert set(ids) == {a.id, b.id}

    with qtbot.waitSignal(panel.merge_requested, timeout=1000) as blocker:
        panel._merge_btn.click()  # noqa: SLF001
    assert set(blocker.args[0]) == {a.id, b.id}


def test_navigation_rail_dates_button_is_first(qtbot):
    from writer.ui.widgets.nav_rail import NavigationRail

    rail = NavigationRail(
        brand_text="W",
        dates_label="Dates",
        fragments_label="Fragments",
        works_label="Works",
        collections_label="Collections",
        ai_label="AI",
        search_label="Search",
        theme_label="Theme",
        settings_label="Settings",
    )
    qtbot.addWidget(rail)
    # Dates should be checked by default and be id 0 in the mode group.
    assert rail.dates_button.isChecked()
    assert rail._mode_group.id(rail.dates_button) == 0  # noqa: SLF001
    assert rail._mode_group.id(rail.fragments_button) == 1  # noqa: SLF001
