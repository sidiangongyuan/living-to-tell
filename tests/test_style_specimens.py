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

    fts_cols = {
        info["name"] for info in conn.execute("PRAGMA table_info(reference_passages_fts)")
    }
    assert "usage_kind" in fts_cols
    assert "personal_note" in fts_cols

    repo_search = conn.execute(
        """
        SELECT r.id
          FROM reference_passages_fts f
          JOIN reference_passages r ON r.rowid = f.rowid
         WHERE reference_passages_fts MATCH ?
        """,
        ("\"old\"*",),
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
    for task in (AiTaskType.POLISH, AiTaskType.EXPAND, AiTaskType.CONTINUE,
                 AiTaskType.STYLE_TRANSFER):
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
    request = AiTaskRequest(
        task_type=AiTaskType.POLISH,
        target_kind=AiTargetKind.PASTE,
        text="Some text.",
        attachments=[
            AiContextAttachment(
                kind="fragment",
                ref_id="f1",
                name="Fragment A",
                body="Some fragment.",
            ),
        ],
    )
    msgs = builder.build_messages(request)
    system = msgs[0]["content"]
    assert "specimen" not in system.lower()


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
        assert dlg._list.count() == 3  # noqa: SLF001

        # Filter to imagery only.
        uidx = dlg._usage_filter.findData("imagery")  # noqa: SLF001
        assert uidx >= 0
        dlg._usage_filter.setCurrentIndex(uidx)  # noqa: SLF001
        assert dlg._list.count() == 2  # noqa: SLF001

        # Filter to style only.
        sidx = dlg._usage_filter.findData("style")  # noqa: SLF001
        dlg._usage_filter.setCurrentIndex(sidx)  # noqa: SLF001
        assert dlg._list.count() == 1  # noqa: SLF001
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

        assert dlg._list.count() == 2  # noqa: SLF001
        dlg._search.setText("ocean")  # noqa: SLF001
        assert dlg._list.count() == 1  # noqa: SLF001
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

        assert dlg._list.count() == 2  # noqa: SLF001
        assert "Strong" in dlg._list.item(0).text()  # noqa: SLF001
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


def test_main_window_context_save_specimen_uses_selection(
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
