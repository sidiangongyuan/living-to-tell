"""Tests for the style specimens (文脉标本库) feature (M-StyleSpecimen).

Covers:
- Storage: usage_kind + personal_note round-trip, filter by usage_kind, migration.
- Domain model: normalise_usage_kind.
- Prompt builder: specimen constraint injected when style_specimen attachments present.
- UI: ReferenceLibraryPanel round-trip with new fields; SpecimenPickerDialog filtering.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _specimen_item_rows(dlg) -> list[int]:
    return [
        row
        for row in range(dlg._list.count())  # noqa: SLF001
        if dlg._list.item(row).data(0x0100) != "__none__"  # noqa: SLF001
    ]


def _specimen_item_count(dlg) -> int:
    return len(_specimen_item_rows(dlg))


def _specimen_card(dlg, row: int):
    return dlg._list.itemWidget(dlg._list.item(row))  # noqa: SLF001


# ---------------------------------------------------------------------------
# Storage / domain tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path: Path):
    from writer.storage.database import open_and_initialize

    c = open_and_initialize(tmp_path / "specimens.sqlite3")
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def repo(conn):
    from writer.storage.repositories.reference_repository import ReferenceRepository

    return ReferenceRepository(conn)


def test_create_with_usage_kind_and_personal_note(repo):
    p = repo.create(
        source_title="Proust",
        content="Long sentence about madeleines.",
        usage_kind="imagery",
        personal_note="Great for sensory recall.",
    )
    assert p.usage_kind == "imagery"
    assert p.personal_note == "Great for sensory recall."

    loaded = repo.get(p.id)
    assert loaded
    assert loaded.usage_kind == "imagery"
    assert loaded.personal_note == "Great for sensory recall."


def test_default_usage_kind_is_style(repo):
    p = repo.create(source_title="t", content="c")
    assert p.usage_kind == "style"


def test_default_personal_note_is_empty(repo):
    p = repo.create(source_title="t", content="c")
    assert p.personal_note == ""


def test_update_usage_kind_and_personal_note(repo):
    p = repo.create(source_title="t", content="c", usage_kind="style")
    updated = repo.update(
        p.id,
        source_title="t",
        content="c",
        usage_kind="technique",
        personal_note="Fragmented phrasing.",
    )
    assert updated
    assert updated.usage_kind == "technique"
    assert updated.personal_note == "Fragmented phrasing."


def test_unknown_usage_kind_normalised_to_style(repo):
    from writer.domain.models.reference_passage import normalise_usage_kind

    assert normalise_usage_kind("bogus") == "style"
    assert normalise_usage_kind(None) == "style"


def test_tauri_frontend_usage_kinds_round_trip(repo):
    frontend_usage_kinds = [
        "style",
        "imagery",
        "structure",
        "rhetoric",
        "diction",
        "reflection",
        "setting",
        "technique",
        "other",
    ]

    for usage_kind in frontend_usage_kinds:
        passage = repo.create(
            source_title=f"title-{usage_kind}",
            content=f"body-{usage_kind}",
            usage_kind=usage_kind,
        )
        assert passage.usage_kind == usage_kind

        updated = repo.update(
            passage.id,
            source_title=passage.source_title,
            content=passage.content,
            usage_kind=usage_kind,
        )
        assert updated is not None
        assert updated.usage_kind == usage_kind


def test_reference_grouping_helper_groups_unlabeled_source_and_tag(repo):
    from writer.domain.models.reference_passage import ReferencePassage
    from writer.ui.reference_grouping import (
        GROUP_MODE_SOURCE,
        GROUP_MODE_TAG,
        group_reference_passages,
    )

    a = ReferencePassage(id="a", source_title="", content="alpha", tags="")
    b = ReferencePassage(id="b", source_title="Book", content="beta", tags="sea")

    by_source = group_reference_passages([a, b], GROUP_MODE_SOURCE)
    assert by_source[0].title in {"未标注来源", "Unlabeled Source"}

    by_tag = group_reference_passages([a, b], GROUP_MODE_TAG)
    assert any(group.title in {"未标注标签", "Unlabeled Tag"} for group in by_tag)


def test_list_recent_filter_by_usage_kind(repo):
    repo.create(source_title="a", content="ca", usage_kind="style")
    repo.create(source_title="b", content="cb", usage_kind="imagery")
    repo.create(source_title="c", content="cc", usage_kind="imagery")

    style_items = repo.list_recent(usage_kind="style")
    assert len(style_items) == 1
    assert style_items[0].source_title == "a"

    imagery_items = repo.list_recent(usage_kind="imagery")
    assert len(imagery_items) == 2


def test_list_recent_filter_by_kind_and_usage_kind(repo):
    repo.create(source_title="a", content="ca", kind="excerpt", usage_kind="style")
    repo.create(source_title="b", content="cb", kind="character", usage_kind="style")
    repo.create(source_title="c", content="cc", kind="excerpt", usage_kind="imagery")

    result = repo.list_recent(kind="excerpt", usage_kind="style")
    assert len(result) == 1
    assert result[0].source_title == "a"


def test_search_filter_by_usage_kind(repo):
    repo.create(source_title="river falls", content="water flows", usage_kind="imagery")
    repo.create(source_title="river delta", content="water streams", usage_kind="technique")

    results = repo.search("river", usage_kind="imagery")
    assert len(results) == 1
    assert results[0].usage_kind == "imagery"


def test_search_matches_personal_note_via_fts(repo):
    p = repo.create(
        source_title="sea",
        content="plain body",
        personal_note="evokes briny melancholy",
    )

    results = repo.search("briny")
    assert [r.id for r in results] == [p.id]


def test_all_usage_kinds_round_trip(repo):
    from writer.domain.models.reference_passage import USAGE_KINDS

    for uk in USAGE_KINDS:
        p = repo.create(source_title=f"test_{uk}", content="body", usage_kind=uk)
        assert p.usage_kind == uk


def test_reference_library_panel_can_start_filtered_to_usage_kind(qtbot, repo):
    from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

    imagery = repo.create(source_title="Q", content="A neat passage.", usage_kind="imagery")
    repo.create(source_title="S", content="A style passage.", usage_kind="style")

    panel = ReferenceLibraryPanel(repo, initial_usage_kind_filter="imagery")
    qtbot.addWidget(panel)

    assert panel._usage_kind_filter_combo.currentData() == "imagery"  # noqa: SLF001
    assert panel._list.count() == 1  # noqa: SLF001
    assert panel._list.item(0).data(0x0100) == imagery.id  # noqa: SLF001


# ---------------------------------------------------------------------------
# Migration test: upgrading an old DB without new columns
# ---------------------------------------------------------------------------


def test_migration_adds_usage_kind_and_personal_note_columns(tmp_path: Path):
    """Simulate a DB that was created before M-StyleSpecimen was added."""
    import sqlite3
    from writer.storage.database import initialize_schema

    db_path = tmp_path / "old.sqlite3"
    # Manually create the old schema without the new columns.
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE reference_passages (
            id            TEXT PRIMARY KEY,
            source_title  TEXT NOT NULL,
            source_author TEXT NOT NULL DEFAULT '',
            content       TEXT NOT NULL,
            tags          TEXT NOT NULL DEFAULT '',
            kind          TEXT NOT NULL DEFAULT 'excerpt',
            created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
    """)
    conn.execute("""
        INSERT INTO reference_passages (id, source_title, content)
        VALUES ('testid', 'Old Title', 'Old Content')
    """)
    conn.commit()

    # Now run the full initialization (which includes migration).
    initialize_schema(conn)

    # Both new columns should now exist with default values.
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(reference_passages)")}
    assert "usage_kind" in cols
    assert "personal_note" in cols

    row = conn.execute("SELECT * FROM reference_passages WHERE id = 'testid'").fetchone()
    assert row["usage_kind"] == "style"
    assert row["personal_note"] == ""

    fts_cols = {info["name"] for info in conn.execute("PRAGMA table_info(reference_passages_fts)")}
    assert "usage_kind" in fts_cols
    assert "personal_note" in fts_cols

    repo_search = conn.execute(
        """
        SELECT r.id
          FROM reference_passages_fts f
          JOIN reference_passages r ON r.rowid = f.rowid
         WHERE reference_passages_fts MATCH ?
        """,
        ('"old"*',),
    ).fetchall()
    assert [row["id"] for row in repo_search] == ["testid"]
    conn.close()


# ---------------------------------------------------------------------------
# Prompt builder tests
# ---------------------------------------------------------------------------


def test_specimen_constraint_injected_for_rewrite_tasks():
    from writer.domain.enums import AiTaskType, AiTargetKind
    from writer.services.ai.task_prompt_builder import TaskPromptBuilder
    from writer.services.ai.task_types import AiContextAttachment, AiTaskRequest

    builder = TaskPromptBuilder()
    for task in (
        AiTaskType.POLISH,
        AiTaskType.STYLE_TRANSFER,
        AiTaskType.EXPAND,
        AiTaskType.CONTINUE,
    ):
        request = AiTaskRequest(
            task_type=task,
            target_kind=AiTargetKind.PASTE,
            text="Some text.",
            attachments=[
                AiContextAttachment(
                    kind="style_specimen",
                    ref_id="s1",
                    name="Proust",
                    body="Du côté de chez Swann...",
                ),
            ],
        )
        msgs = builder.build_messages(request)
        system = msgs[0]["content"]
        # Constraint language must be present, but NOT copying sentences.
        assert "style_specimen" in system.lower() or "specimen" in system.lower(), (
            f"No specimen constraint in system prompt for {task}"
        )
        assert "not" in system.lower() or "不" in system, (
            f"No prohibitive language in system prompt for {task}"
        )
        lowered = system.lower()
        assert "purpose" in lowered or "用途" in system
        assert "author note" in lowered or "作者备注" in system
        assert "mechanically" in lowered or "机械" in system
        assert "named entities" in lowered or "专有名词" in system


def test_specimen_constraint_not_injected_for_non_rewrite_tasks():
    from writer.domain.enums import AiTaskType, AiTargetKind
    from writer.services.ai.task_prompt_builder import TaskPromptBuilder
    from writer.services.ai.task_types import AiContextAttachment, AiTaskRequest

    builder = TaskPromptBuilder()
    request = AiTaskRequest(
        task_type=AiTaskType.SUMMARIZE,
        target_kind=AiTargetKind.PASTE,
        text="A long passage.",
        attachments=[
            AiContextAttachment(
                kind="style_specimen",
                ref_id="s1",
                name="Proust",
                body="Du côté de chez Swann...",
            ),
        ],
    )
    msgs = builder.build_messages(request)
    # Summarize should not get the specimen constraint (it's not a rewrite task).
    system = msgs[0]["content"]
    assert "specimen" not in system.lower()


def test_no_specimen_constraint_without_specimen_attachments():
    from writer.domain.enums import AiTaskType, AiTargetKind
    from writer.services.ai.task_prompt_builder import TaskPromptBuilder
    from writer.services.ai.task_types import AiContextAttachment, AiTaskRequest

    builder = TaskPromptBuilder()
    for kind in ("fragment", "reference", "ai_card", "writing_note"):
        request = AiTaskRequest(
            task_type=AiTaskType.POLISH,
            target_kind=AiTargetKind.PASTE,
            text="Some text.",
            attachments=[
                AiContextAttachment(
                    kind=kind,
                    ref_id=f"{kind}-1",
                    name=f"{kind} context",
                    body="Some context.",
                ),
            ],
        )
        msgs = builder.build_messages(request)
        system = msgs[0]["content"]
        assert "Style Specimen Usage Rules" not in system
        assert "Do NOT copy sentences or passages" not in system


# ---------------------------------------------------------------------------
# UI tests
# ---------------------------------------------------------------------------


def test_reference_library_panel_saves_usage_kind_and_personal_note(qtbot, isolated_data_dir):
    from writer.app.container import build_container

    container = build_container()
    try:
        from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

        panel = ReferenceLibraryPanel(container.reference_repository)
        qtbot.addWidget(panel)

        panel._on_new()  # noqa: SLF001
        panel._title_edit.setText("Virginia Woolf")  # noqa: SLF001
        panel._content_edit.setPlainText("The waves broke on the shore.")  # noqa: SLF001

        # Set usage_kind to "imagery"
        uidx = panel._usage_kind_combo.findData("imagery")  # noqa: SLF001
        assert uidx >= 0, "imagery usage kind not found in combo"
        panel._usage_kind_combo.setCurrentIndex(uidx)  # noqa: SLF001
        panel._personal_note_edit.setPlainText("Sea metaphor used for time.")  # noqa: SLF001

        panel._on_save()  # noqa: SLF001

        saved = container.reference_repository.list_recent()[0]
        assert saved.usage_kind == "imagery"
        assert saved.personal_note == "Sea metaphor used for time."
    finally:
        container.close()


def test_reference_library_panel_has_no_category_chip_ui(qtbot, isolated_data_dir):
    from writer.app.container import build_container

    container = build_container()
    try:
        from writer.ui.panels.reference_library_panel import ReferenceLibraryPanel

        panel = ReferenceLibraryPanel(container.reference_repository)
        qtbot.addWidget(panel)

        panel._on_new()  # noqa: SLF001
        panel._tags_edit.setText("环境描写, 哲思句子")  # noqa: SLF001
        assert not hasattr(panel, "_category_chip_buttons")  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_dialog_filters_by_usage_kind(qtbot, isolated_data_dir):
    from writer.app.container import build_container

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="style_one", content="s1 body", usage_kind="style")
        repo.create(source_title="imagery_one", content="i1 body", usage_kind="imagery")
        repo.create(source_title="imagery_two", content="i2 body", usage_kind="imagery")

        from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)

        # Initially all 3 are shown.
        assert _specimen_item_count(dlg) == 3

        # Filter to imagery only.
        uidx = dlg._usage_filter.findData("imagery")  # noqa: SLF001
        assert uidx >= 0
        dlg._usage_filter.setCurrentIndex(uidx)  # noqa: SLF001
        assert _specimen_item_count(dlg) == 2

        # Filter to style only.
        sidx = dlg._usage_filter.findData("style")  # noqa: SLF001
        dlg._usage_filter.setCurrentIndex(sidx)  # noqa: SLF001
        assert _specimen_item_count(dlg) == 1
    finally:
        container.close()


def test_specimen_picker_dialog_search(qtbot, isolated_data_dir):
    from writer.app.container import build_container

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="ocean waves", content="waves crash", usage_kind="imagery")
        repo.create(source_title="mountain peak", content="summit view", usage_kind="technique")

        from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)

        assert _specimen_item_count(dlg) == 2
        dlg._search.setText("ocean")  # noqa: SLF001
        assert _specimen_item_count(dlg) == 1
    finally:
        container.close()


def test_specimen_picker_preview_follows_current_item(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(
            source_title="Book A",
            source_author="Author A",
            content="first excerpt body",
            tags="rain, night",
            usage_kind="imagery",
            personal_note="good for wet streets",
        )
        repo.create(source_title="Book B", content="second excerpt body")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)
        dlg.show()

        book_a_row = next(
            row
            for row in _specimen_item_rows(dlg)
            if dlg._list.item(row).data(0x0101).source_title == "Book A"  # noqa: SLF001
        )
        book_b_row = next(
            row
            for row in _specimen_item_rows(dlg)
            if dlg._list.item(row).data(0x0101).source_title == "Book B"  # noqa: SLF001
        )

        dlg._list.setCurrentRow(book_a_row)  # noqa: SLF001
        first = dlg._list.currentItem()  # noqa: SLF001
        dlg._show_preview_for_item(first)  # noqa: SLF001

        assert dlg._preview_card.isVisible() is True  # noqa: SLF001
        assert dlg._preview_title.text() == "Book A"  # noqa: SLF001
        assert "Author A" in dlg._preview_source.text()  # noqa: SLF001
        assert "rain, night" in dlg._preview_tags.text()  # noqa: SLF001
        assert "good for wet streets" in dlg._preview_note.text()  # noqa: SLF001
        assert dlg._preview_body.toPlainText() == "first excerpt body"  # noqa: SLF001

        dlg._list.setCurrentRow(book_b_row)  # noqa: SLF001
        assert dlg._preview_title.text() == "Book B"  # noqa: SLF001
        assert dlg._preview_body.toPlainText() == "second excerpt body"  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_preview_hides_for_empty_results(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Book A", content="first excerpt body")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)
        dlg.show()
        dlg._show_preview_for_item(dlg._list.item(0))  # noqa: SLF001
        assert dlg._preview_card.isVisible() is True  # noqa: SLF001

        dlg._search.setText("missing query")  # noqa: SLF001

        assert _specimen_item_count(dlg) == 0
        assert dlg._preview_card.isHidden() is True  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_filter_keeps_checks_and_updates_preview(qtbot, isolated_data_dir):
    from PySide6.QtCore import Qt

    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Style One", content="style body", usage_kind="style")
        repo.create(source_title="Imagery One", content="imagery body", usage_kind="imagery")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)
        dlg.show()

        dlg._list.item(_specimen_item_rows(dlg)[0]).setCheckState(Qt.CheckState.Checked)  # noqa: SLF001
        checked_before = dlg._checked_ids()  # noqa: SLF001
        assert checked_before

        uidx = dlg._usage_filter.findData("imagery")  # noqa: SLF001
        dlg._usage_filter.setCurrentIndex(uidx)  # noqa: SLF001

        assert _specimen_item_count(dlg) == 1
        assert dlg._preview_title.text() == "Imagery One"  # noqa: SLF001
        assert dlg._checked_ids().issubset(checked_before)  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_multi_select_still_returns_checked_passages(qtbot, isolated_data_dir):
    from PySide6.QtCore import Qt

    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="One", content="one body")
        repo.create(source_title="Two", content="two body")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)

        rows = _specimen_item_rows(dlg)
        dlg._list.item(rows[0]).setCheckState(Qt.CheckState.Checked)  # noqa: SLF001
        dlg._list.item(rows[1]).setCheckState(Qt.CheckState.Checked)  # noqa: SLF001
        dlg._on_accept()  # noqa: SLF001

        assert {p.source_title for p in dlg.selected_passages} == {"One", "Two"}
    finally:
        container.close()


def test_save_specimen_dialog_shows_similar_recommendations(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.save_specimen_dialog import SaveSpecimenDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(
            source_title="Sea Notebook",
            content="melancholy briny tide",
            personal_note="salt-air cadence",
        )
        repo.create(source_title="Other", content="mountain snow pine")

        dlg = SaveSpecimenDialog(
            repo,
            default_body="melancholy briny",
            default_source_title="Draft",
        )
        qtbot.addWidget(dlg)

        items = [dlg._similar_list.item(i).text() for i in range(dlg._similar_list.count())]  # noqa: SLF001
        assert any("Sea Notebook" in text for text in items)
    finally:
        container.close()


def test_save_specimen_dialog_blocks_exact_duplicate(qtbot, isolated_data_dir, monkeypatch):
    from writer.app.container import build_container
    from writer.ui.dialogs.save_specimen_dialog import SaveSpecimenDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Existing", content="same text")
        warnings: list[tuple[str, str]] = []

        def _warning(_parent, title, message):
            warnings.append((title, message))

        monkeypatch.setattr("writer.ui.dialogs.save_specimen_dialog.QMessageBox.warning", _warning)

        dlg = SaveSpecimenDialog(
            repo,
            default_body="same   text",
            default_source_title="Draft",
        )
        qtbot.addWidget(dlg)
        dlg._on_accept()  # noqa: SLF001

        assert repo.count() == 1
        assert warnings
        assert "Existing" in warnings[-1][1]
    finally:
        container.close()


def test_similarity_ranking_prefers_multi_term_overlap():
    from writer.domain.models.reference_passage import ReferencePassage
    from writer.ui.dialogs.specimen_similarity import rank_similar_passages

    weak = ReferencePassage(id="weak", source_title="Weak", content="melancholy")
    strong = ReferencePassage(
        id="strong",
        source_title="Strong",
        content="melancholy briny tide with salt-air cadence",
    )

    ranked = rank_similar_passages([weak, strong], "melancholy briny tide")
    assert [p.id for p in ranked[:2]] == ["strong", "weak"]


def test_specimen_picker_uses_recommended_text_for_initial_order(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Strong", content="melancholy briny tide cadence")
        repo.create(source_title="Weak", content="melancholy")

        dlg = SpecimenPickerDialog(repo, recommended_text="melancholy briny tide")
        qtbot.addWidget(dlg)

        rows = _specimen_item_rows(dlg)
        assert len(rows) == 2
        assert dlg._list.item(rows[0]).data(0x0101).source_title == "Strong"  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_preselected_ids_restore_checked_state(qtbot, isolated_data_dir):
    from PySide6.QtCore import Qt

    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        first = repo.create(source_title="Book A", content="body a")
        repo.create(source_title="Book B", content="body b")

        dlg = SpecimenPickerDialog(repo, preselected_ids=[first.id])
        qtbot.addWidget(dlg)

        checked_rows = [
            row
            for row in _specimen_item_rows(dlg)
            if dlg._list.item(row).checkState() == Qt.CheckState.Checked  # noqa: SLF001
        ]
        assert len(checked_rows) == 1
        assert dlg._list.item(checked_rows[0]).data(0x0100) == first.id  # noqa: SLF001
        assert _specimen_card(dlg, checked_rows[0])._select_button.text() in {  # noqa: SLF001
            "✓ 已选",
            "✓ Selected",
        }
    finally:
        container.close()


def test_specimen_picker_uses_widget_cards_without_native_item_text(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Book A", content="body a")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)

        row = _specimen_item_rows(dlg)[0]
        item = dlg._list.item(row)  # noqa: SLF001
        group_item = dlg._group_list.item(0)  # noqa: SLF001

        assert item.text() == ""
        assert group_item.text() == ""
        assert item.data(0x0101).source_title == "Book A"  # noqa: SLF001
        assert dlg._list.itemWidget(item).objectName() == "SpecimenListCard"  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_long_card_sizehint_is_not_clipped(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import (
        _SPECIMEN_CARD_MIN_HEIGHT,
        SpecimenPickerDialog,
    )

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(
            source_title="Long Form Notebook",
            source_author="Verbose Author",
            content=" ".join(f"line{i}" for i in range(220)),
            personal_note=" ".join(f"note{i}" for i in range(80)),
            tags="alpha, beta, gamma",
            usage_kind="imagery",
        )

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)
        dlg.resize(1180, 700)
        dlg.show()
        qtbot.waitExposed(dlg)

        row = _specimen_item_rows(dlg)[0]
        item = dlg._list.item(row)  # noqa: SLF001
        card = _specimen_card(dlg, row)
        qtbot.waitUntil(lambda: item.sizeHint().height() > 0)  # noqa: SLF001

        assert item.sizeHint().height() >= _SPECIMEN_CARD_MIN_HEIGHT
        assert item.sizeHint().height() >= card.sizeHint().height()
        assert item.sizeHint().height() >= card.minimumSizeHint().height()
    finally:
        container.close()


def test_specimen_picker_group_mode_switch_keeps_checked(qtbot, isolated_data_dir):
    from PySide6.QtCore import Qt

    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Book A", content="body a", usage_kind="style", tags="x")
        repo.create(source_title="Book B", content="body b", usage_kind="imagery", tags="y")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)

        first_row = _specimen_item_rows(dlg)[0]
        checked_id = dlg._list.item(first_row).data(0x0100)  # noqa: SLF001
        dlg._list.item(first_row).setCheckState(Qt.CheckState.Checked)  # noqa: SLF001

        idx = dlg._group_mode_combo.findData("usage_tag")  # noqa: SLF001
        dlg._group_mode_combo.setCurrentIndex(idx)  # noqa: SLF001

        assert checked_id in dlg._checked_ids()  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_select_badge_syncs_check_state_and_preview(qtbot, isolated_data_dir):
    from PySide6.QtCore import Qt

    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Book A", content="body a")
        repo.create(source_title="Book B", content="body b")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)
        dlg.show()

        row = _specimen_item_rows(dlg)[0]
        item = dlg._list.item(row)  # noqa: SLF001
        card = _specimen_card(dlg, row)

        assert item.checkState() == Qt.CheckState.Unchecked
        assert card._select_button.text() in {"选择", "Select"}  # noqa: SLF001

        card.clicked.emit()
        assert dlg._list.currentItem() is item  # noqa: SLF001
        assert dlg._preview_title.text() == item.data(0x0101).source_title  # noqa: SLF001
        assert item.checkState() == Qt.CheckState.Unchecked

        card._select_button.click()  # noqa: SLF001
        assert item.checkState() == Qt.CheckState.Checked
        assert item.data(0x0100) in dlg._checked_ids()  # noqa: SLF001
        assert card._select_button.text() in {"✓ 已选", "✓ Selected"}  # noqa: SLF001

        card._select_button.click()  # noqa: SLF001
        assert item.checkState() == Qt.CheckState.Unchecked
        assert item.data(0x0100) not in dlg._checked_ids()  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_does_not_flash_label_windows(qtbot, isolated_data_dir):
    from PySide6.QtCore import QObject, QEvent
    from PySide6.QtWidgets import QApplication, QLabel

    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(
            source_title="Quiet Book",
            source_author="Quiet Author",
            content="Quiet body",
            personal_note="Quiet note",
        )

        class WindowShowSpy(QObject):
            def __init__(self) -> None:
                super().__init__()
                self.label_windows = []

            def eventFilter(self, obj, event) -> bool:  # noqa: N802
                if (
                    event.type() == QEvent.Type.Show
                    and isinstance(obj, QLabel)
                    and obj.isWindow()
                ):
                    self.label_windows.append(obj.objectName())
                return False

        app = QApplication.instance()
        assert app is not None
        spy = WindowShowSpy()
        app.installEventFilter(spy)
        try:
            dlg = SpecimenPickerDialog(repo)
            qtbot.addWidget(dlg)
            dlg.show()
            qtbot.waitUntil(dlg.isVisible)
        finally:
            app.removeEventFilter(spy)

        assert spy.label_windows == []
    finally:
        container.close()


def test_specimen_picker_save_default_group_mode(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        dlg = SpecimenPickerDialog(
            container.reference_repository,
            settings=container.settings,
        )
        qtbot.addWidget(dlg)

        idx = dlg._group_mode_combo.findData("recent")  # noqa: SLF001
        dlg._group_mode_combo.setCurrentIndex(idx)  # noqa: SLF001
        dlg._save_group_mode_as_default()  # noqa: SLF001

        assert container.settings.specimen_picker_default_group_mode() == "recent"
    finally:
        container.close()


def test_specimen_picker_blank_hover_does_not_hide_preview(qtbot, isolated_data_dir):
    from PySide6.QtCore import QPoint

    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Book A", content="body a")
        repo.create(source_title="Book B", content="body b")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)
        dlg.show()

        dlg._list.setCurrentRow(_specimen_item_rows(dlg)[0])  # noqa: SLF001
        assert dlg._preview_card.isVisible() is True  # noqa: SLF001

        blank_point = dlg._list.viewport().rect().bottomRight() - QPoint(4, 4)  # noqa: SLF001
        qtbot.mouseMove(dlg._list.viewport(), blank_point)

        assert dlg._preview_card.isVisible() is True  # noqa: SLF001
    finally:
        container.close()


def test_specimen_picker_preview_body_can_focus_and_select(qtbot, isolated_data_dir):
    from writer.app.container import build_container
    from writer.ui.dialogs.specimen_picker_dialog import SpecimenPickerDialog

    container = build_container()
    try:
        repo = container.reference_repository
        repo.create(source_title="Book A", content="selectable specimen body")

        dlg = SpecimenPickerDialog(repo)
        qtbot.addWidget(dlg)
        dlg.show()
        dlg._list.setCurrentRow(_specimen_item_rows(dlg)[0])  # noqa: SLF001

        dlg._preview_body.setFocus()
        qtbot.waitUntil(lambda: dlg._preview_body.hasFocus())  # noqa: SLF001
        cursor = dlg._preview_body.textCursor()  # noqa: SLF001
        cursor.select(cursor.SelectionType.Document)
        dlg._preview_body.setTextCursor(cursor)  # noqa: SLF001

        assert dlg._preview_body.textCursor().hasSelection() is True  # noqa: SLF001
        assert dlg._preview_body.textCursor().selectedText() == "selectable specimen body"  # noqa: SLF001
    finally:
        container.close()


def test_editor_panel_save_specimen_button_emits(qtbot):
    from writer.domain.models.entry import Entry
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    assert panel.save_specimen_button.isEnabled() is False

    panel.set_entry(Entry(id="e1", title="Draft", body="alpha beta"))
    assert panel.save_specimen_button.isEnabled() is True

    with qtbot.waitSignal(panel.save_specimen_requested, timeout=500):
        panel.save_specimen_button.click()


def test_editor_panel_context_menu_has_save_specimen_action(qtbot):
    from PySide6.QtCore import QPoint

    from writer.domain.models.entry import Entry
    from writer.ui.i18n import TR
    from writer.ui.panels.editor_panel import EditorPanel

    panel = EditorPanel()
    qtbot.addWidget(panel)
    panel.set_entry(Entry(id="e1", title="Draft", body="alpha beta"))

    menu = panel._create_body_context_menu(QPoint(0, 0))  # noqa: SLF001
    try:
        actions = [
            action
            for action in menu.actions()
            if action.text() == TR("context.action_save_specimen")
        ]
        assert len(actions) == 1
        assert actions[0].isEnabled() is True
        with qtbot.waitSignal(panel.save_specimen_requested, timeout=500):
            actions[0].trigger()
    finally:
        menu.deleteLater()


def test_main_window_context_save_specimen_uses_selection(qtbot, isolated_data_dir, monkeypatch):
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QDialog

    import writer.ui.dialogs.save_specimen_dialog as dlg_mod
    import writer.ui.main_window as main_window_mod
    from writer.app.container import build_container
    from writer.ui.main_window import MainWindow, MODE_FRAGMENTS

    container = build_container()
    try:
        entry = container.entry_repository.create(
            title="Rain Draft",
            body="alpha beta gamma",
        )

        captured: dict[str, str] = {}

        class FakeSaveSpecimenDialog:
            def __init__(
                self,
                repo,
                *,
                default_body,
                default_source_title="",
                default_source_author="",
                default_tags="",
                parent=None,
            ) -> None:
                captured["default_body"] = default_body
                captured["default_source_title"] = default_source_title
                self.saved_passage = repo.create(
                    source_title=default_source_title or "Captured",
                    content=default_body,
                )

            def exec(self):
                return QDialog.DialogCode.Accepted

        monkeypatch.setattr(dlg_mod, "SaveSpecimenDialog", FakeSaveSpecimenDialog)
        monkeypatch.setattr(main_window_mod.QMessageBox, "information", lambda *a, **k: None)

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
        window._load_entry(entry.id)  # noqa: SLF001

        body_edit = window._editor_panel._body  # noqa: SLF001
        cursor = body_edit.textCursor()
        cursor.setPosition(6)
        cursor.setPosition(10, QTextCursor.MoveMode.KeepAnchor)
        body_edit.setTextCursor(cursor)

        window._context_pane.fragment_save_specimen_button.click()  # noqa: SLF001

        assert captured["default_body"] == "beta"
        assert captured["default_source_title"] == "Rain Draft"
        saved = container.reference_repository.list_recent()[0]
        assert saved.content == "beta"
    finally:
        container.close()


def test_main_window_editor_save_specimen_button_uses_selection(
    qtbot, isolated_data_dir, monkeypatch
):
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QDialog

    import writer.ui.dialogs.save_specimen_dialog as dlg_mod
    import writer.ui.main_window as main_window_mod
    from writer.app.container import build_container
    from writer.ui.main_window import MainWindow, MODE_FRAGMENTS

    container = build_container()
    try:
        entry = container.entry_repository.create(
            title="Button Draft",
            body="one two three",
        )

        captured: dict[str, str] = {}

        class FakeSaveSpecimenDialog:
            def __init__(
                self,
                repo,
                *,
                default_body,
                default_source_title="",
                default_source_author="",
                default_tags="",
                parent=None,
            ) -> None:
                captured["default_body"] = default_body
                captured["default_source_title"] = default_source_title
                self.saved_passage = repo.create(
                    source_title=default_source_title or "Captured",
                    content=default_body,
                )

            def exec(self):
                return QDialog.DialogCode.Accepted

        monkeypatch.setattr(dlg_mod, "SaveSpecimenDialog", FakeSaveSpecimenDialog)
        monkeypatch.setattr(main_window_mod.QMessageBox, "information", lambda *a, **k: None)

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
        window._load_entry(entry.id)  # noqa: SLF001

        body_edit = window._editor_panel._body  # noqa: SLF001
        cursor = body_edit.textCursor()
        cursor.setPosition(4)
        cursor.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
        body_edit.setTextCursor(cursor)

        window._editor_panel.save_specimen_button.click()  # noqa: SLF001

        assert captured["default_body"] == "two"
        assert captured["default_source_title"] == "Button Draft"
        saved = container.reference_repository.list_recent()[0]
        assert saved.content == "two"
    finally:
        container.close()
