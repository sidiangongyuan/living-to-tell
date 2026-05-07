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


def test_dates_panel_shows_empty_daily_quote_state_without_reference_passages(qtbot, container):
    from writer.ui.panels.dates_panel import DatesPanel

    panel = DatesPanel(container)
    qtbot.addWidget(panel)

    assert panel._quote_stack.currentIndex() == 1  # noqa: SLF001
    assert panel._displayed_daily_quote_id is None  # noqa: SLF001


def test_dates_panel_shows_daily_quote_from_reference_library(qtbot, container):
    from writer.ui.panels.dates_panel import DatesPanel

    passage = container.reference_repository.create(
        source_title="Le Petit Prince",
        source_author="Saint-Exupery",
        content="What is essential is invisible to the eye.",
        usage_kind="style",
        tags="wisdom",
    )

    panel = DatesPanel(container)
    qtbot.addWidget(panel)

    assert panel._quote_stack.currentIndex() == 0  # noqa: SLF001
    assert panel._displayed_daily_quote_id == passage.id  # noqa: SLF001
    assert "essential" in panel._quote_body.text()  # noqa: SLF001


def test_daily_quote_default_selection_is_stable_for_same_day(container):
    from writer.ui.panels.dates_panel import choose_default_daily_quote

    a = container.reference_repository.create(
        source_title="A",
        content="A short quote that fits the card nicely.",
        usage_kind="style",
    )
    b = container.reference_repository.create(
        source_title="B",
        content="Another short quote for a steady daily pick.",
        usage_kind="imagery",
    )
    quotes = container.reference_repository.list_recent(limit=50)

    first = choose_default_daily_quote(quotes, date(2026, 5, 7))
    second = choose_default_daily_quote(quotes, date(2026, 5, 7))

    assert first is not None
    assert first.id == second.id
    assert first.id in {a.id, b.id}


def test_dates_panel_replace_quote_changes_only_current_session(qtbot, container):
    from writer.ui.panels.dates_panel import DatesPanel

    container.reference_repository.create(
        source_title="A",
        content="A short quote that fits the daily card well.",
        usage_kind="style",
    )
    container.reference_repository.create(
        source_title="B",
        content="B short quote that also fits the daily quote card.",
        usage_kind="technique",
    )

    panel = DatesPanel(container)
    qtbot.addWidget(panel)
    default_id = panel._displayed_daily_quote_id  # noqa: SLF001

    panel._on_replace_daily_quote()  # noqa: SLF001

    assert panel._displayed_daily_quote_id != default_id  # noqa: SLF001

    panel2 = DatesPanel(container)
    qtbot.addWidget(panel2)
    assert panel2._displayed_daily_quote_id == default_id  # noqa: SLF001


def test_dates_panel_manage_quotes_button_emits_signal(qtbot, container):
    from writer.ui.panels.dates_panel import DatesPanel

    panel = DatesPanel(container)
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.manage_quotes_requested, timeout=1000):
        panel._manage_quotes_btn.click()  # noqa: SLF001


def test_daily_quote_buttons_keep_readable_size(qtbot, container):
    from writer.ui.panels.dates_panel import DatesPanel

    panel = DatesPanel(container)
    qtbot.addWidget(panel)

    buttons = (
        panel._replace_quote_btn,  # noqa: SLF001
        panel._manage_quotes_btn,  # noqa: SLF001
        panel._copy_quote_btn,  # noqa: SLF001
    )
    for button in buttons:
        assert button.minimumHeight() >= max(button.fontMetrics().height() + 16, 36)
        assert button.minimumWidth() >= button.fontMetrics().horizontalAdvance(button.text()) + 40
