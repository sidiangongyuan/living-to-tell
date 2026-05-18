"""Tests for the reference-library panel's kind combo (M-Dates / reflib)."""
from __future__ import annotations

from pathlib import Path

import pytest

from writer.app.container import build_container
from writer.domain.models.reference_passage import (
    REFERENCE_KIND_CHARACTER,
    REFERENCE_KIND_EXCERPT,
    REFERENCE_KIND_LOCATION,
)


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


def test_panel_round_trips_kind_via_combo(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    panel = ReferenceLibraryPanel(container.reference_repository)
    qtbot.addWidget(panel)

    # New + select character kind in combo.
    panel._on_new()  # noqa: SLF001
    panel._title_edit.setText("Ahab")  # noqa: SLF001
    panel._content_edit.setPlainText("captain")  # noqa: SLF001
    # find character index in combo
    for i in range(panel._kind_combo.count()):  # noqa: SLF001
        if panel._kind_combo.itemData(i) == REFERENCE_KIND_CHARACTER:  # noqa: SLF001
            panel._kind_combo.setCurrentIndex(i)  # noqa: SLF001
            break
    panel._on_save()  # noqa: SLF001

    saved = container.reference_repository.list_recent()[0]
    assert saved.kind == REFERENCE_KIND_CHARACTER

    # Reload via list selection should restore the kind in the combo.
    panel._list.setCurrentRow(0)  # noqa: SLF001
    assert panel._kind_combo.currentData() == REFERENCE_KIND_CHARACTER  # noqa: SLF001


def test_kind_filter_combo_filters_list(qtbot, container):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    repo = container.reference_repository
    repo.create(source_title="Char1", content="c1", kind=REFERENCE_KIND_CHARACTER)
    repo.create(source_title="Loc1", content="l1", kind=REFERENCE_KIND_LOCATION)
    repo.create(source_title="Ex1", content="e1", kind=REFERENCE_KIND_EXCERPT)

    panel = ReferenceLibraryPanel(repo)
    qtbot.addWidget(panel)
    assert panel._list.count() == 3  # noqa: SLF001

    # Switch filter to "character" only.
    for i in range(panel._kind_filter_combo.count()):  # noqa: SLF001
        if panel._kind_filter_combo.itemData(i) == REFERENCE_KIND_CHARACTER:  # noqa: SLF001
            panel._kind_filter_combo.setCurrentIndex(i)  # noqa: SLF001
            break
    assert panel._list.count() == 1  # noqa: SLF001
    item = panel._list.item(0)  # noqa: SLF001
    assert item.data(0x0100) is not None
    assert item.data(0x0101).source_title == "Char1"  # noqa: SLF001
