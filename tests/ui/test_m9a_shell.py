"""M9A tests: theme system, shell layout, context pane, empty states."""
from __future__ import annotations

import json

import pytest

from writer.app.container import build_container


@pytest.fixture()
def container(isolated_data_dir):
    c = build_container()
    try:
        yield c
    finally:
        c.close()


# ---------------------------------------------------------------------------
# Theme module
# ---------------------------------------------------------------------------


class TestThemeTokens:
    def test_parse_theme_mode_handles_known_values(self):
        from writer.ui.theme import ThemeMode

        assert ThemeMode.parse("light") is ThemeMode.LIGHT
        assert ThemeMode.parse("dark") is ThemeMode.DARK
        assert ThemeMode.parse("system") is ThemeMode.SYSTEM

    def test_parse_theme_mode_falls_back_to_system(self):
        from writer.ui.theme import ThemeMode

        assert ThemeMode.parse(None) is ThemeMode.SYSTEM
        assert ThemeMode.parse("nonsense") is ThemeMode.SYSTEM

    def test_light_and_dark_tokens_differ(self):
        from writer.ui.theme import DARK_TOKENS, LIGHT_TOKENS

        assert LIGHT_TOKENS.bg_window != DARK_TOKENS.bg_window
        assert LIGHT_TOKENS.text_primary != DARK_TOKENS.text_primary

    def test_build_qss_returns_non_empty_string(self):
        from writer.ui.theme import LIGHT_TOKENS, build_qss

        qss = build_qss(LIGHT_TOKENS)
        assert isinstance(qss, str)
        assert "#PrimaryButton" in qss or "PrimaryButton" in qss
        assert len(qss) > 100

    def test_build_qss_styles_ai_workspace_surfaces(self):
        from writer.ui.theme import LIGHT_TOKENS, build_qss

        qss = build_qss(LIGHT_TOKENS)

        assert "AIWorkspacePanel" in qss
        assert "AIToolsRight" in qss
        assert LIGHT_TOKENS.bg_main in qss

    def test_build_qss_styles_ai_combo_popups_for_readability(self):
        from writer.ui.theme import LIGHT_TOKENS, build_qss

        qss = build_qss(LIGHT_TOKENS)

        assert "QWidget#AIWorkspacePanel QComboBox QAbstractItemView" in qss
        assert LIGHT_TOKENS.bg_card in qss

    def test_build_qss_uses_semantic_preview_tokens(self):
        from writer.ui.theme import DARK_TOKENS, LIGHT_TOKENS, build_qss

        light_qss = build_qss(LIGHT_TOKENS)
        dark_qss = build_qss(DARK_TOKENS)

        assert LIGHT_TOKENS.bg_preview in light_qss
        assert DARK_TOKENS.bg_preview in dark_qss
        assert "#FFF9EF" not in dark_qss
        assert "#F5F1E8" not in dark_qss


# ---------------------------------------------------------------------------
# Theme persistence via settings
# ---------------------------------------------------------------------------


class TestThemePersistence:
    def test_apply_theme_mode_persists_setting(self, qtbot, container):
        from writer.app.settings import KEY_THEME_MODE
        from writer.ui.main_window import MainWindow
        from writer.ui.theme import ThemeMode

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._apply_theme_mode(ThemeMode.DARK)  # noqa: SLF001
        assert container.settings.get(KEY_THEME_MODE) == "dark"

        window._apply_theme_mode(ThemeMode.LIGHT)  # noqa: SLF001
        assert container.settings.get(KEY_THEME_MODE) == "light"


# ---------------------------------------------------------------------------
# Shell: rail + stack + context pane
# ---------------------------------------------------------------------------


class TestShellLayout:
    def test_window_has_rail_and_context_pane(self, qtbot, container):
        from writer.ui.main_window import MainWindow
        from writer.ui.widgets import ContextPane, NavigationRail

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        assert window.findChild(NavigationRail) is not None
        assert window.findChild(ContextPane) is not None

    def test_rail_changes_stack_index(self, qtbot, container):
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._set_mode(2)  # noqa: SLF001 — works mode
        assert window._stack.currentIndex() == 2  # noqa: SLF001

        window._set_mode(3)  # noqa: SLF001 — collections mode
        assert window._stack.currentIndex() == 3  # noqa: SLF001

    def test_active_mode_persists(self, qtbot, container):
        from writer.app.settings import KEY_ACTIVE_MODE
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._set_mode(2)  # noqa: SLF001
        assert container.settings.get(KEY_ACTIVE_MODE) == "2"

        # New window should restore mode 2 (works).
        window2 = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window2)
        assert window2._stack.currentIndex() == 2  # noqa: SLF001

    def test_context_pane_visibility_persists(self, qtbot, container):
        from writer.app.settings import KEY_CONTEXT_PANE_VISIBLE
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        # Default state is visible; toggling once should hide.
        window._toggle_context_pane()  # noqa: SLF001
        assert container.settings.get(KEY_CONTEXT_PANE_VISIBLE) == "false"

        window2 = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window2)
        # Persisted hidden flag should be honoured at construction.
        assert window2._context_pane_visible is False  # noqa: SLF001

    def test_window_still_has_toolbar_for_backcompat(self, qtbot, container):
        from PySide6.QtWidgets import QToolBar

        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        assert len(window.findChildren(QToolBar)) >= 1

    def test_toolbar_shell_toggles_have_distinct_semantics(self, qtbot, container):
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        assert window._sidebar_btn is not window._context_toggle_btn  # noqa: SLF001
        assert window._sidebar_btn.text() in {"Sidebar", "侧栏"}  # noqa: SLF001
        assert window._context_toggle_btn.text() in {"Context", "上下文"}  # noqa: SLF001

        before_context = window._context_pane_visible  # noqa: SLF001
        window._context_toggle_btn.click()  # noqa: SLF001
        assert window._context_pane_visible is (not before_context)  # noqa: SLF001
        assert window._context_toggle_btn.isChecked() is window._context_pane_visible  # noqa: SLF001

        before_sidebar = window._sidebar_collapsed  # noqa: SLF001
        window._sidebar_btn.click()  # noqa: SLF001
        assert window._sidebar_collapsed is (not before_sidebar)  # noqa: SLF001
        assert window._sidebar_btn.isChecked() is (not window._sidebar_collapsed)  # noqa: SLF001

    def test_context_pane_remains_visible_with_fragment_notes_on_wide_window(self, qtbot, container):
        from writer.ui.main_window import MODE_FRAGMENTS, MainWindow

        entry = container.entry_repository.create(title="wide", body="body")
        container.entry_writing_note_repository.create(
            entry_id=entry.id,
            body="贴在页面上的灵感便签。",
        )
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window.resize(1500, 900)
        window.show()
        window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
        window._load_entry(entry.id)  # noqa: SLF001
        window._editor_panel.focus_writing_note_input()  # noqa: SLF001

        assert window._context_pane.isVisible()  # noqa: SLF001
        assert window._context_pane.width() >= 220  # noqa: SLF001
        assert window._editor_panel._writing_notes_board.width() <= 320  # noqa: SLF001

    def test_focus_mode_hides_and_restores_shell_surfaces(self, qtbot, container):
        from writer.ui.main_window import MainWindow, MODE_FRAGMENTS

        entry = container.entry_repository.create(title="focus", body="hello world")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window.show()
        window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
        window._load_entry(entry.id)  # noqa: SLF001

        assert window._rail.isVisible()  # noqa: SLF001
        assert window._context_pane.isVisible()  # noqa: SLF001
        assert window._top_toolbar.isVisible()  # noqa: SLF001
        assert window._list_panel.isVisible()  # noqa: SLF001

        window._toggle_focus_mode()  # noqa: SLF001

        assert window._focus_mode_enabled is True  # noqa: SLF001
        assert not window._rail.isVisible()  # noqa: SLF001
        assert not window._context_pane.isVisible()  # noqa: SLF001
        assert not window._top_toolbar.isVisible()  # noqa: SLF001
        assert not window._list_panel.isVisible()  # noqa: SLF001

        window._toggle_focus_mode()  # noqa: SLF001

        assert window._focus_mode_enabled is False  # noqa: SLF001
        assert window._rail.isVisible()  # noqa: SLF001
        assert window._context_pane.isVisible()  # noqa: SLF001
        assert window._top_toolbar.isVisible()  # noqa: SLF001
        assert window._list_panel.isVisible()  # noqa: SLF001

    def test_f11_toggles_focus_mode(self, qtbot, container):
        from PySide6.QtCore import Qt

        from writer.ui.main_window import MainWindow, MODE_FRAGMENTS

        entry = container.entry_repository.create(title="focus", body="hello world")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window.show()
        window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
        window._load_entry(entry.id)  # noqa: SLF001
        window._editor_panel.focus_body()  # noqa: SLF001

        qtbot.keyClick(window._editor_panel._body, Qt.Key.Key_F11)  # noqa: SLF001
        qtbot.waitUntil(lambda: window._focus_mode_enabled is True)  # noqa: SLF001

        qtbot.keyClick(window._editor_panel._body, Qt.Key.Key_F11)  # noqa: SLF001
        qtbot.waitUntil(lambda: window._focus_mode_enabled is False)  # noqa: SLF001

    def test_main_window_caps_fragment_list_width_for_wide_editor(
        self, qtbot, container
    ):
        from writer.ui.main_window import MainWindow, _MAX_SIDEBAR_WIDTH

        container.settings.set("ui.splitter_sizes", json.dumps([520, 760]))

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        assert window._list_panel.maximumWidth() == _MAX_SIDEBAR_WIDTH  # noqa: SLF001

    def test_main_window_normalizes_bad_fragment_splitter_sizes(
        self, qtbot, container
    ):
        from writer.ui.main_window import MainWindow, _MAX_SIDEBAR_WIDTH

        container.settings.set("ui.splitter_sizes", json.dumps([900, 0]))
        container.entry_repository.create(title="layout", body="body")

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window.resize(1400, 860)
        window.show()

        sidebar, editor = window._splitter.sizes()  # noqa: SLF001
        assert sidebar <= _MAX_SIDEBAR_WIDTH
        assert editor >= 600
        assert window._editor_panel.width() >= 600  # noqa: SLF001

    def test_main_window_normalizes_context_pane_after_bad_focus_restore(
        self, qtbot, container
    ):
        from writer.ui.main_window import MainWindow
        from writer.ui.widgets import ContextPane

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window.resize(1500, 900)
        window.show()

        window._main_splitter.setSizes([72, 1400, 0])  # noqa: SLF001
        window._normalize_main_splitter_sizes()  # noqa: SLF001

        sizes = window._main_splitter.sizes()  # noqa: SLF001
        assert sizes[1] >= 640
        assert sizes[2] >= ContextPane.DEFAULT_WIDTH or sizes[2] >= 220
        assert window._context_pane.width() >= 220  # noqa: SLF001

    def test_manage_quotes_opens_reference_library_without_extra_filter(
        self, qtbot, container, monkeypatch
    ):
        from writer.ui.main_window import MainWindow

        seen: dict[str, object] = {}

        class _FakeDialog:
            def __init__(self, repo, parent=None, *, initial_usage_kind=None):
                seen["repo"] = repo
                seen["parent"] = parent
                seen["initial_usage_kind"] = initial_usage_kind

            def exec(self):
                return 0

        import writer.ui.main_window as main_window_mod

        monkeypatch.setattr(main_window_mod, "ReferenceLibraryDialog", _FakeDialog)

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._on_manage_quotes()  # noqa: SLF001

        assert seen["repo"] is container.reference_repository
        assert seen["parent"] is window
        assert seen["initial_usage_kind"] is None


# ---------------------------------------------------------------------------
# Empty states
# ---------------------------------------------------------------------------


class TestEmptyStates:
    def test_fragment_panel_shows_empty_card_when_no_entries(self, qtbot, container):
        from writer.ui.panels.fragment_list_panel import FragmentListPanel

        panel = FragmentListPanel()
        qtbot.addWidget(panel)
        panel.set_entries([])
        # The panel uses an internal stack; index 1 is the empty page.
        assert panel._stack.currentIndex() == 1  # noqa: SLF001

    def test_fragment_search_empty_state_switches_copy(self, qtbot):
        from writer.ui.i18n import TR
        from writer.ui.panels.fragment_list_panel import FragmentListPanel

        panel = FragmentListPanel()
        qtbot.addWidget(panel)
        # Simulate active search by typing into the search field, then call
        # set_entries with an empty list (which is what main window does
        # when search returns nothing).
        panel._search.setText("zzzz_no_match_zzzz")  # noqa: SLF001
        panel.set_entries([])

        assert panel._stack.currentIndex() == 1  # noqa: SLF001
        assert panel._empty_in_search_mode is True  # noqa: SLF001
        assert (
            panel._empty_card.primary_button.text()  # noqa: SLF001
            == TR("empty.fragments_search_primary")
        )

    def test_works_panel_shows_empty_card_when_no_works(self, qtbot, container):
        from writer.ui.panels.works_panel import WorksPanel

        panel = WorksPanel(container)
        qtbot.addWidget(panel)
        assert panel._list_stack.currentIndex() == 1  # noqa: SLF001

    def test_collections_panel_shows_empty_card_when_no_collections(
        self, qtbot, container
    ):
        from writer.ui.panels.collections_panel import CollectionsPanel

        panel = CollectionsPanel(container)
        qtbot.addWidget(panel)
        assert panel._collections_stack.currentIndex() == 1  # noqa: SLF001


# ---------------------------------------------------------------------------
# Context pane
# ---------------------------------------------------------------------------


class TestContextPane:
    def test_context_pane_show_empty_switches_to_empty_page(self, qtbot, container):
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._context_pane.show_empty()  # noqa: SLF001
        assert window._context_pane._stack.currentIndex() == 0  # noqa: SLF001

    def test_context_pane_shows_fragment_after_load(self, qtbot, container):
        from writer.ui.main_window import MainWindow, MODE_FRAGMENTS

        entry = container.entry_repository.create(title="t", body="hello world")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._set_mode(MODE_FRAGMENTS)  # noqa: SLF001
        window._load_entry(entry.id)  # noqa: SLF001
        assert window._context_pane._stack.currentIndex() == 1  # noqa: SLF001

    def test_context_pane_action_buttons_are_vertical_and_readable(
        self, qtbot, container
    ):
        from PySide6.QtWidgets import QVBoxLayout

        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        pane = window._context_pane  # noqa: SLF001
        assert isinstance(pane._frag_actions_row, QVBoxLayout)  # noqa: SLF001
        for button in (
            pane.fragment_polish_button,
            pane.fragment_include_button,
            pane.fragment_save_specimen_button,
        ):
            assert button.minimumHeight() >= max(button.fontMetrics().height() + 16, 36)

    def test_context_pane_shows_work_in_works_mode(self, qtbot, container):
        from writer.ui.main_window import MainWindow, MODE_WORKS

        work = container.work_repository.create(title="W", summary="sum")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._set_mode(MODE_WORKS)  # noqa: SLF001
        window._refresh_work_context(work.id)  # noqa: SLF001

        assert window._context_pane._stack.currentIndex() == 2  # noqa: SLF001

    def test_context_pane_shows_collection_in_collections_mode(self, qtbot, container):
        from writer.ui.main_window import MainWindow, MODE_COLLECTIONS

        collection = container.collection_repository.create(name="C")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._set_mode(MODE_COLLECTIONS)  # noqa: SLF001
        window._refresh_collection_context(collection.id)  # noqa: SLF001

        assert window._context_pane._stack.currentIndex() == 3  # noqa: SLF001

    def test_context_pane_shows_work_specific_empty_copy_without_selection(
        self, qtbot, container
    ):
        from writer.ui.i18n import TR
        from writer.ui.main_window import MainWindow, MODE_WORKS

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._set_mode(MODE_WORKS)  # noqa: SLF001

        assert window._context_pane._stack.currentIndex() == 0  # noqa: SLF001
        assert window._context_pane._empty._title.text() == TR("context.empty_title_work")  # noqa: SLF001

    def test_context_pane_shows_collection_specific_empty_copy_without_selection(
        self, qtbot, container
    ):
        from writer.ui.i18n import TR
        from writer.ui.main_window import MainWindow, MODE_COLLECTIONS

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._set_mode(MODE_COLLECTIONS)  # noqa: SLF001

        assert window._context_pane._stack.currentIndex() == 0  # noqa: SLF001
        assert window._context_pane._empty._title.text() == TR("context.empty_title_collection")  # noqa: SLF001

    def test_context_pane_shows_ai_bound_fragment_in_ai_mode(self, qtbot, container):
        from writer.ui.main_window import MainWindow, MODE_AI

        entry = container.entry_repository.create(title="AI Entry", body="hello ai")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._editor_panel.set_entry(entry)  # noqa: SLF001
        window._set_mode(MODE_AI)  # noqa: SLF001

        assert window._context_pane._stack.currentIndex() == 1  # noqa: SLF001
        assert window._context_pane._title.text() == "AI Entry"  # noqa: SLF001

    def test_context_pane_shows_ai_global_empty_copy_when_unbound(self, qtbot, container):
        from writer.ui.i18n import TR
        from writer.ui.main_window import MainWindow, MODE_AI

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        window._set_mode(MODE_AI)  # noqa: SLF001

        assert window._context_pane._stack.currentIndex() == 0  # noqa: SLF001
        assert window._context_pane._empty._title.text() == TR("context.empty_title_ai")  # noqa: SLF001


# ---------------------------------------------------------------------------
# M9A audit follow-up: empty-state CTAs, welcome/unselected reachability,
# and theme-aware tag chips.
# ---------------------------------------------------------------------------


class TestEmptyStateCTAs:
    """All empty-state secondary CTAs must be wired to a real handler."""

    def test_fragment_empty_secondary_emits_global_search(self, qtbot):
        from writer.ui.panels.fragment_list_panel import FragmentListPanel

        panel = FragmentListPanel()
        qtbot.addWidget(panel)
        panel.set_entries([])  # not in search mode
        with qtbot.waitSignal(panel.global_search_requested, timeout=500):
            panel._empty_card.secondary_button.click()  # noqa: SLF001

    def test_works_empty_secondary_emits_include_fragment(self, qtbot, container):
        from writer.ui.panels.works_panel import WorksPanel

        panel = WorksPanel(container)
        qtbot.addWidget(panel)
        with qtbot.waitSignal(panel.include_fragment_requested, timeout=500):
            panel._empty_card.secondary_button.click()  # noqa: SLF001

    def test_collections_empty_secondary_emits_switch_to_works(
        self, qtbot, container
    ):
        from writer.ui.panels.collections_panel import CollectionsPanel

        panel = CollectionsPanel(container)
        qtbot.addWidget(panel)
        with qtbot.waitSignal(panel.switch_to_works_requested, timeout=500):
            panel._collections_empty.secondary_button.click()  # noqa: SLF001


class TestWelcomeAndUnselectedReachability:
    """The welcome and per-mode unselected cards must actually be reachable
    instead of being hidden behind auto-create / auto-select-row-0 logic."""

    def test_main_window_empty_db_shows_welcome(self, qtbot, container):
        from writer.ui.main_window import MainWindow

        assert container.entry_repository.count() == 0
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        assert container.entry_repository.count() == 0
        assert window._editor_panel.current_entry_id() is None  # noqa: SLF001
        assert window._fragments_stack.currentIndex() == 1  # noqa: SLF001

    def test_new_fragment_from_welcome_dismisses_welcome(self, qtbot, container):
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        assert window._fragments_stack.currentIndex() == 1  # noqa: SLF001

        window._on_new_fragment()  # noqa: SLF001
        assert window._fragments_stack.currentIndex() == 0  # noqa: SLF001
        assert container.entry_repository.count() == 1
        assert window._editor_panel.current_entry_id() is not None  # noqa: SLF001

    def test_works_panel_unselected_card_visible_when_no_selection(
        self, qtbot, container
    ):
        from writer.ui.panels.works_panel import WorksPanel

        container.work_repository.create(title="Pre-existing")
        panel = WorksPanel(container)
        qtbot.addWidget(panel)

        # No work auto-selected; right side shows the unselected card.
        assert panel._list.currentRow() == -1  # noqa: SLF001
        assert panel._right_stack.currentIndex() == 1  # noqa: SLF001

        panel._list.setCurrentRow(0)  # noqa: SLF001
        assert panel._right_stack.currentIndex() == 0  # noqa: SLF001

    def test_collections_panel_unselected_card_visible_when_no_selection(
        self, qtbot, container
    ):
        from writer.ui.panels.collections_panel import CollectionsPanel

        container.collection_repository.create(name="Pre-existing")
        panel = CollectionsPanel(container)
        qtbot.addWidget(panel)

        # No collection auto-selected; right side shows the unselected card.
        assert panel._collections.currentRow() == -1  # noqa: SLF001
        assert panel._right_stack.currentIndex() == 1  # noqa: SLF001

        panel._collections.setCurrentRow(0)  # noqa: SLF001
        assert panel._right_stack.currentIndex() == 0  # noqa: SLF001

    def test_include_fragment_from_works_empty_warns_when_no_current(
        self, qtbot, container, monkeypatch
    ):
        """If the user clicks 'Include current fragment' while there is no
        current fragment loaded, MainWindow shows an informational dialog
        rather than silently doing nothing."""
        from PySide6.QtWidgets import QMessageBox

        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)

        called = {"count": 0}

        def fake_info(*args, **kwargs):
            called["count"] += 1
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr(QMessageBox, "information", fake_info)

        window._on_include_fragment_from_empty_state()  # noqa: SLF001
        assert called["count"] == 1


class TestThemeConsolidation:
    """No hardcoded grey colors; all status / meta / dialog-note / no-results
    labels rely on object-name driven QSS, and tag chips adapt to dark mode."""

    def test_status_label_uses_object_name(self, qtbot, container):
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        assert (
            window._save_status_label.objectName() == "StatusLabel"  # noqa: SLF001
        )

    def test_editor_meta_labels_use_object_name(self, qtbot, container):
        from writer.ui.panels.editor_panel import EditorPanel

        panel = EditorPanel()
        qtbot.addWidget(panel)
        assert panel._meta.objectName() == "MetaLabel"  # noqa: SLF001
        assert panel._word_count.objectName() == "MetaLabel"  # noqa: SLF001

    def test_tag_style_sheet_is_theme_aware(self, qtbot):
        # qtbot ensures a QApplication exists for apply_theme.
        from PySide6.QtWidgets import QApplication

        from writer.ui.tag_colors import tag_style_sheet
        from writer.ui.theme import ThemeMode, apply_theme

        app = QApplication.instance()
        try:
            apply_theme(app, ThemeMode.LIGHT)
            light = tag_style_sheet("python")
            apply_theme(app, ThemeMode.DARK)
            dark = tag_style_sheet("python")
        finally:
            apply_theme(app, ThemeMode.LIGHT)

        assert light != dark
        assert "border" in dark.lower()


# ---------------------------------------------------------------------------
# M9A blocker-fix follow-up:
#   1) welcome state must trigger ONLY when the entry repo is truly empty
#   2) Works empty-state secondary CTA must form a real closure
# ---------------------------------------------------------------------------


class TestWelcomeTriggerCondition:
    """Welcome card appears only when ``entry_repository.count() == 0``."""

    def test_empty_db_shows_welcome(self, qtbot, container):
        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        assert window._fragments_stack.currentIndex() == 1  # noqa: SLF001

    def test_only_archived_entries_does_not_show_welcome(
        self, qtbot, container
    ):
        """If the repo only contains archived entries, the workspace must
        stay visible so the user can flip "show archived" and find them."""
        from writer.ui.main_window import MainWindow

        repo = container.entry_repository
        e = repo.create(title="archived-one")
        repo.set_archived(e.id, True)
        assert repo.count() == 1
        # Sanity: default list (without archived) is empty.
        assert repo.list_recent() == []

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        # Workspace (splitter), NOT welcome.
        assert window._fragments_stack.currentIndex() == 0  # noqa: SLF001

    def test_archive_last_visible_keeps_workspace_when_repo_not_empty(
        self, qtbot, container
    ):
        from writer.ui.main_window import MainWindow

        repo = container.entry_repository
        only = repo.create(title="only-one")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._load_entry(only.id)  # noqa: SLF001

        window._on_archive_requested(only.id, True)  # noqa: SLF001

        # Repo still has the archived entry, so workspace must stay.
        assert repo.count() == 1
        assert window._fragments_stack.currentIndex() == 0  # noqa: SLF001

    def test_delete_last_entry_finally_shows_welcome(
        self, qtbot, container, monkeypatch
    ):
        from PySide6.QtWidgets import QMessageBox

        from writer.ui.main_window import MainWindow

        repo = container.entry_repository
        e = repo.create(title="last")
        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._load_entry(e.id)  # noqa: SLF001

        # Auto-confirm the delete dialog.
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *a, **k: QMessageBox.StandardButton.Yes,
        )

        window._on_delete_requested([e.id])  # noqa: SLF001

        assert repo.count() == 0
        assert window._fragments_stack.currentIndex() == 1  # noqa: SLF001


class TestWorksEmptyCTAClosure:
    """The Works-empty secondary CTA must drive the include flow to a real
    completion path, not stop at "no works yet"."""

    def test_no_current_fragment_shows_info_dialog(
        self, qtbot, container, monkeypatch
    ):
        from PySide6.QtWidgets import QMessageBox

        from writer.ui.main_window import MainWindow

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        assert window._editor_panel.current_entry_id() is None  # noqa: SLF001

        called = {"info": 0}

        def fake_info(*a, **k):
            called["info"] += 1
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr(QMessageBox, "information", fake_info)

        # No work should be created in the no-current-fragment branch.
        window._on_include_fragment_from_empty_state()  # noqa: SLF001
        assert called["info"] == 1
        assert container.work_repository.count() == 0

    def test_with_current_fragment_but_no_work_auto_creates_and_opens_dialog(
        self, qtbot, container, monkeypatch
    ):
        """User has a fragment, no works exist. CTA must:
          * auto-create a work,
          * then open the IncludeFragmentDialog with that work as a target.
        """
        from PySide6.QtWidgets import QDialog

        from writer.ui import main_window as mw_module
        from writer.ui.main_window import MainWindow

        repo = container.entry_repository
        entry = repo.create(title="frag", body="payload")

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._load_entry(entry.id)  # noqa: SLF001
        assert container.work_repository.count() == 0

        # Capture dialog construction; auto-reject so the dialog does not
        # actually run a modal loop.
        constructed = {"count": 0, "work_count_at_open": None}

        class _StubDialog:
            def __init__(self, container_arg, entry_arg, default_text=None, parent=None):
                constructed["count"] += 1
                constructed["work_count_at_open"] = (
                    container_arg.work_repository.count()
                )
                self.included_outcome = None

            def exec(self):
                return QDialog.DialogCode.Rejected

        monkeypatch.setattr(mw_module, "IncludeFragmentDialog", _StubDialog)

        window._on_include_fragment_from_empty_state()  # noqa: SLF001

        # A work was bootstrapped before the include dialog opened.
        assert container.work_repository.count() == 1
        assert constructed["count"] == 1
        assert constructed["work_count_at_open"] == 1

    def test_with_existing_work_does_not_create_extra_one(
        self, qtbot, container, monkeypatch
    ):
        from PySide6.QtWidgets import QDialog

        from writer.ui import main_window as mw_module
        from writer.ui.main_window import MainWindow

        container.work_repository.create(title="Pre-existing")
        entry = container.entry_repository.create(title="frag", body="body")

        window = MainWindow(container, autosave_debounce_ms=50)
        qtbot.addWidget(window)
        window._load_entry(entry.id)  # noqa: SLF001

        class _StubDialog:
            def __init__(self, *a, **k):
                self.included_outcome = None

            def exec(self):
                return QDialog.DialogCode.Rejected

        monkeypatch.setattr(mw_module, "IncludeFragmentDialog", _StubDialog)

        before = container.work_repository.count()
        window._on_include_fragment_from_empty_state()  # noqa: SLF001
        after = container.work_repository.count()
        assert after == before  # no extra auto-creation
