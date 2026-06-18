"""M7A tests: i18n, tag colours, command palette, splitter, About, version."""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_locale() -> None:
    """Force locale back to 'en' so tests don't bleed into each other."""
    from writer.app import locale as locale_mod

    locale_mod.set_locale("en")


# ---------------------------------------------------------------------------
# app.locale
# ---------------------------------------------------------------------------


class TestLocale:
    def setup_method(self):
        _reset_locale()

    def teardown_method(self):
        _reset_locale()

    def test_default_locale_is_english(self):
        from writer.app.locale import current_locale

        assert current_locale() == "en"

    def test_set_valid_locale(self):
        from writer.app.locale import LOCALE_ZH_CN, current_locale, set_locale

        set_locale(LOCALE_ZH_CN)
        assert current_locale() == LOCALE_ZH_CN

    def test_unsupported_locale_falls_back_to_english(self):
        from writer.app.locale import current_locale, set_locale

        set_locale("fr_FR")
        assert current_locale() == "en"

    def test_set_locale_idempotent(self):
        from writer.app.locale import current_locale, set_locale

        set_locale("en")
        set_locale("en")
        assert current_locale() == "en"


# ---------------------------------------------------------------------------
# ui.i18n.TR()
# ---------------------------------------------------------------------------


class TestTR:
    def setup_method(self):
        _reset_locale()

    def teardown_method(self):
        _reset_locale()

    def test_tr_returns_english_by_default(self):
        from writer.ui.i18n import TR

        assert TR("menu.new_fragment") == "&New Fragment"

    def test_tr_returns_chinese_when_locale_is_zh_cn(self):
        from writer.app.locale import set_locale
        from writer.ui.i18n import TR

        set_locale("zh_CN")
        assert TR("menu.new_fragment") == "新建片段(&N)"

    def test_tr_falls_back_to_english_for_unknown_key(self):
        from writer.ui.i18n import TR

        # Should return the key itself as last resort
        result = TR("nonexistent.key.xyz")
        assert result == "nonexistent.key.xyz"

    def test_tr_falls_back_to_english_key_in_unknown_locale(self):
        """If locale is somehow set to an unsupported value, TR still returns EN."""
        import writer.app.locale as loc_mod
        from writer.ui.i18n import TR

        # Bypass set_locale validation to test fallback directly
        loc_mod._CURRENT_LOCALE = "ja_JP"
        try:
            result = TR("menu.new_fragment")
            assert result == "&New Fragment"
        finally:
            loc_mod._CURRENT_LOCALE = "en"

    def test_about_content_has_version_placeholder(self):
        from writer.ui.i18n import TR

        content = TR("about.content")
        assert "{version}" in content

    def test_about_content_zh_has_version_placeholder(self):
        from writer.app.locale import set_locale
        from writer.ui.i18n import TR

        set_locale("zh_CN")
        content = TR("about.content")
        assert "{version}" in content

    def test_ai_article_labels_use_article_wording(self):
        from writer.ui.i18n import TR

        assert TR("ai.scope_fragment") == "Article: {name}"
        assert TR("ai.target.fragment") == "Article"
        assert TR("ai.attachments.kind_fragment") == "Article"

    def test_ai_article_labels_use_article_wording_in_zh(self):
        from writer.app.locale import set_locale
        from writer.ui.i18n import TR

        set_locale("zh_CN")
        assert TR("ai.scope_fragment") == "文章：{name}"
        assert TR("ai.target.fragment") == "文章"
        assert TR("ai.attachments.kind_fragment") == "文章"


# ---------------------------------------------------------------------------
# Settings language persistence
# ---------------------------------------------------------------------------


class TestSettingsLanguage:
    def test_default_language_is_english(self, isolated_data_dir: Path):
        from writer.app.container import build_container

        c = build_container()
        try:
            assert c.settings.language == "en"
        finally:
            c.close()

    def test_save_and_reload_language(self, isolated_data_dir: Path):
        from writer.app.container import build_container

        c = build_container()
        try:
            c.settings.save_language("zh_CN")
            assert c.settings.language == "zh_CN"
        finally:
            c.close()

    def test_save_invalid_language_raises(self, isolated_data_dir: Path):
        from writer.app.container import build_container

        c = build_container()
        try:
            with pytest.raises(ValueError):
                c.settings.save_language("xx_XX")
        finally:
            c.close()


# ---------------------------------------------------------------------------
# app.version
# ---------------------------------------------------------------------------


class TestAppVersion:
    def test_version_is_0_2_0_alpha_1(self):
        from writer.app.version import APP_VERSION

        # Accept any 0.2.0-alpha.* build so later milestones don't churn this test.
        assert APP_VERSION.startswith("0.2.0-alpha.")

    def test_version_non_empty(self):
        from writer.app.version import APP_VERSION

        assert APP_VERSION and APP_VERSION.strip()


# ---------------------------------------------------------------------------
# tag_colors
# ---------------------------------------------------------------------------


class TestTagColors:
    def test_same_tag_returns_same_color(self):
        from writer.ui.tag_colors import get_tag_color

        assert get_tag_color("fiction") == get_tag_color("fiction")

    def test_case_insensitive_normalization(self):
        from writer.ui.tag_colors import get_tag_color

        assert get_tag_color("Python") == get_tag_color("python")
        assert get_tag_color("PYTHON") == get_tag_color("python")

    def test_returns_tuple_of_two_hex_strings(self):
        from writer.ui.tag_colors import get_tag_color

        bg, fg = get_tag_color("test-tag")
        assert bg.startswith("#") and len(bg) == 7
        assert fg.startswith("#") and len(fg) == 7

    def test_empty_tag_returns_neutral_gray(self):
        from writer.ui.tag_colors import get_tag_color

        bg, fg = get_tag_color("")
        assert bg == "#F0F0F0"
        assert fg == "#555555"

    def test_whitespace_only_tag_returns_neutral(self):
        from writer.ui.tag_colors import get_tag_color

        bg, _fg = get_tag_color("   ")
        assert bg == "#F0F0F0"

    def test_different_tags_may_differ(self):
        from writer.ui.tag_colors import get_tag_color

        # With 12 slots in the palette, statistically at least some distinct tags differ
        colors = {get_tag_color(t) for t in ["alpha", "beta", "gamma", "delta", "epsilon"]}
        assert len(colors) > 1

    def test_stable_across_calls(self):
        from writer.ui.tag_colors import get_tag_color

        first = get_tag_color("writing")
        second = get_tag_color("writing")
        assert first == second

    def test_tag_style_sheet_contains_bg_color(self):
        from writer.ui.tag_colors import get_tag_color, tag_style_sheet

        bg, _fg = get_tag_color("test")
        style = tag_style_sheet("test")
        assert bg in style

    def test_palette_covers_twelve_slots(self):
        """Ensure the palette has exactly 12 entries."""
        from writer.ui.tag_colors import _PALETTE

        assert len(_PALETTE) == 12


# ---------------------------------------------------------------------------
# PromptBuilder locale-awareness
# ---------------------------------------------------------------------------


class TestPromptBuilderLocale:
    def setup_method(self):
        _reset_locale()

    def teardown_method(self):
        _reset_locale()

    def test_system_prompt_english_by_default(self):
        from writer.services.ai.prompt_builder import PromptBuilder

        pb = PromptBuilder()
        prompt = pb.system_prompt("polish")
        # English prompt should be in English
        assert prompt
        assert isinstance(prompt, str)

    def test_system_prompt_chinese_when_locale_zh_cn(self):
        from writer.app.locale import set_locale
        from writer.services.ai.prompt_builder import PromptBuilder

        set_locale("zh_CN")
        pb = PromptBuilder()
        prompt = pb.system_prompt("polish")
        assert prompt
        # Chinese prompt should contain Chinese characters
        assert any("\u4e00" <= ch <= "\u9fff" for ch in prompt)

    def test_system_prompt_falls_back_to_english_for_unknown_action(self):
        """Unknown action raises ValueError — expected behavior."""
        from writer.services.ai.prompt_builder import PromptBuilder

        pb = PromptBuilder()
        with pytest.raises(ValueError, match="Unknown rewrite action"):
            pb.system_prompt("nonexistent_action_xyz")


# ---------------------------------------------------------------------------
# CommandPaletteDialog
# ---------------------------------------------------------------------------


class TestCommandPaletteDialog:
    def test_constructs_with_empty_actions(self, qtbot):
        from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog

        dlg = CommandPaletteDialog(actions=[], parent=None)
        qtbot.addWidget(dlg)
        assert dlg is not None

    def test_shows_all_enabled_actions(self, qtbot):
        from PySide6.QtGui import QAction

        from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog

        a1 = QAction("New Fragment")
        a1.setEnabled(True)
        a2 = QAction("Export")
        a2.setEnabled(True)

        dlg = CommandPaletteDialog(actions=[a1, a2], parent=None)
        qtbot.addWidget(dlg)
        assert dlg._list.count() == 2

    def test_disabled_actions_are_hidden(self, qtbot):
        from PySide6.QtGui import QAction

        from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog

        a1 = QAction("Enabled Action")
        a1.setEnabled(True)
        a2 = QAction("Disabled Action")
        a2.setEnabled(False)

        dlg = CommandPaletteDialog(actions=[a1, a2], parent=None)
        qtbot.addWidget(dlg)
        assert dlg._list.count() == 1

    def test_filter_narrows_results(self, qtbot):
        from PySide6.QtGui import QAction

        from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog

        a1 = QAction("New Fragment")
        a1.setEnabled(True)
        a2 = QAction("Export Markdown")
        a2.setEnabled(True)

        dlg = CommandPaletteDialog(actions=[a1, a2], parent=None)
        qtbot.addWidget(dlg)

        dlg._search.setText("export")
        assert dlg._list.count() == 1

    def test_no_results_label_shown_when_filter_matches_nothing(self, qtbot):
        from PySide6.QtGui import QAction

        from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog

        a1 = QAction("New Fragment")
        a1.setEnabled(True)

        dlg = CommandPaletteDialog(actions=[a1], parent=None)
        qtbot.addWidget(dlg)

        dlg._search.setText("zzznomatch")
        # Widget is not shown, so use isHidden() to check explicit hide state
        assert not dlg._no_results.isHidden()
        assert dlg._list.isHidden()

    def test_triggered_action_is_none_before_activation(self, qtbot):
        from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog

        dlg = CommandPaletteDialog(actions=[], parent=None)
        qtbot.addWidget(dlg)
        assert dlg.triggered_action() is None


# ---------------------------------------------------------------------------
# About action enabled
# ---------------------------------------------------------------------------


class TestAboutAction:
    def test_about_action_enabled(self, qtbot, isolated_data_dir: Path):
        from writer.app.bootstrap import create_main_window
        from writer.app.container import build_container

        c = build_container()
        window = create_main_window(c)
        qtbot.addWidget(window)

        help_menu = None
        for action in window.menuBar().actions():
            if action.text() == "&Help":
                help_menu = action.menu()
                break

        assert help_menu is not None
        about = None
        for action in help_menu.actions():
            if "About" in action.text():
                about = action
                break

        assert about is not None
        assert about.isEnabled()
        c.close()

    def test_about_action_text_contains_about(self, qtbot, isolated_data_dir: Path):
        from writer.app.bootstrap import create_main_window
        from writer.app.container import build_container

        c = build_container()
        window = create_main_window(c)
        qtbot.addWidget(window)

        help_menu = None
        for action in window.menuBar().actions():
            if action.text() == "&Help":
                help_menu = action.menu()
                break

        about_texts = [a.text() for a in help_menu.actions() if "About" in a.text()]
        assert about_texts, "Expected at least one About action"
        c.close()


# ---------------------------------------------------------------------------
# Splitter state persistence via settings
# ---------------------------------------------------------------------------


class TestSplitterStatePersistence:
    def test_splitter_sizes_key_exists_in_settings(self):
        from writer.app.settings import KEY_SPLITTER_SIZES

        assert KEY_SPLITTER_SIZES == "ui.splitter_sizes"

    def test_splitter_state_can_be_saved_and_read(self, isolated_data_dir: Path):
        import json

        from writer.app.container import build_container
        from writer.app.settings import KEY_SPLITTER_SIZES

        c = build_container()
        try:
            sizes = [280, 820]
            c.settings.set(KEY_SPLITTER_SIZES, json.dumps(sizes))
            restored = json.loads(c.settings.get(KEY_SPLITTER_SIZES))
            assert restored == sizes
        finally:
            c.close()


# ---------------------------------------------------------------------------
# Main window integration: toolbar and sidebar toggle
# ---------------------------------------------------------------------------


class TestMainWindowM7A:
    def test_window_has_toolbar(self, qtbot, isolated_data_dir: Path):
        from writer.app.bootstrap import create_main_window
        from writer.app.container import build_container

        c = build_container()
        window = create_main_window(c)
        qtbot.addWidget(window)
        window.show()

        toolbars = window.findChildren(__import__("PySide6.QtWidgets", fromlist=["QToolBar"]).QToolBar)
        assert len(toolbars) >= 1, "Expected at least one toolbar"
        c.close()

    def test_command_palette_shortcut_action_exists(self, qtbot, isolated_data_dir: Path):
        """Ctrl+P command palette action is registered on the main window."""
        from writer.app.bootstrap import create_main_window
        from writer.app.container import build_container

        c = build_container()
        window = create_main_window(c)
        qtbot.addWidget(window)

        # Command palette is added to window directly (Ctrl+P), not to a menu
        palette_action = None
        for action in window.actions():
            if "Command" in action.text() or "Palette" in action.text():
                palette_action = action
                break
        assert palette_action is not None, "Command Palette action not found in window actions"
        c.close()

    def test_version_displayed_in_window_title(self, qtbot, isolated_data_dir: Path):
        from writer.app.bootstrap import create_main_window
        from writer.app.container import build_container

        c = build_container()
        window = create_main_window(c)
        qtbot.addWidget(window)

        assert window.windowTitle() == "活着为了讲述"
        c.close()

    def test_extra_palette_actions_exist(self, qtbot, isolated_data_dir: Path):
        """Command palette must include 'Focus search' and 'Switch language'."""
        from writer.app.bootstrap import create_main_window
        from writer.app.container import build_container

        c = build_container()
        window = create_main_window(c)
        qtbot.addWidget(window)

        texts = [a.text() for a in window._extra_palette_actions]
        assert any("search" in t.lower() or "focus" in t.lower() for t in texts), (
            f"No focus-search action found in extra palette actions: {texts}"
        )
        assert any("language" in t.lower() or "switch" in t.lower() for t in texts), (
            f"No switch-language action found in extra palette actions: {texts}"
        )
        c.close()

    def test_palette_total_includes_extras(self, qtbot, isolated_data_dir: Path):
        """Total actions passed to palette must include menu actions + extras."""
        from writer.app.bootstrap import create_main_window
        from writer.app.container import build_container

        c = build_container()
        window = create_main_window(c)
        qtbot.addWidget(window)

        total = len(window._all_menu_actions) + len(window._extra_palette_actions)
        assert total > len(window._all_menu_actions), (
            "Extra palette actions not appended"
        )
        assert len(window._extra_palette_actions) >= 2
        c.close()


# ---------------------------------------------------------------------------
# Acceptance Fix 1: i18n coverage on dialogs
# ---------------------------------------------------------------------------
class TestI18nDialogCoverage:
    def test_assign_fragment_dialog_zh_title(self, qtbot, isolated_data_dir: Path):
        """assign_fragment_dialog shows Chinese title when locale is zh_CN."""
        from writer.app.locale import set_locale, LOCALE_ZH_CN
        from writer.ui.dialogs.assign_fragment_dialog import AssignFragmentDialog
        from writer.storage.repositories.chapter_repository import ChapterRepository
        from writer.storage.repositories.project_repository import ProjectRepository
        from writer.storage.database import open_and_initialize

        conn = open_and_initialize(isolated_data_dir / "assign_test.db")
        proj_repo = ProjectRepository(conn)
        chap_repo = ChapterRepository(conn)

        set_locale(LOCALE_ZH_CN)
        try:
            dlg = AssignFragmentDialog(
                proj_repo, chap_repo,
                current_project_id=None, current_chapter_id=None
            )
            qtbot.addWidget(dlg)
            from writer.ui.i18n import TR
            assert dlg.windowTitle() == TR("assign.title")
        finally:
            set_locale("en")
        conn.close()

    def test_version_history_dialog_zh_title(self, qtbot, isolated_data_dir: Path):
        """Version history dialog shows Chinese title in zh_CN."""
        from writer.app.locale import set_locale, LOCALE_ZH_CN
        from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog
        from writer.ui.i18n import TR
        from writer.storage.database import open_and_initialize
        from writer.storage.repositories.entry_repository import EntryRepository
        from writer.storage.repositories.version_repository import VersionRepository
        from writer.services.version_history_service import VersionHistoryService

        conn = open_and_initialize(isolated_data_dir / "vhd_test.db")
        entry_repo = EntryRepository(conn)
        version_repo = VersionRepository(conn)
        entry = entry_repo.create()
        svc = VersionHistoryService(entry_repo, version_repo)

        set_locale(LOCALE_ZH_CN)
        try:
            dlg = VersionHistoryDialog(entry.id, entry.body, svc)
            qtbot.addWidget(dlg)
            assert dlg.windowTitle() == TR("vhd.title")
        finally:
            set_locale("en")
        conn.close()


# ---------------------------------------------------------------------------
# Acceptance Fix 3: editor panel tag chips
# ---------------------------------------------------------------------------
class TestEditorTagChips:
    def test_tag_chips_hidden_when_no_tags(self, qtbot):
        from writer.ui.panels.editor_panel import EditorPanel

        panel = EditorPanel()
        qtbot.addWidget(panel)
        assert panel._tag_chips_widget.isHidden()

    def test_tag_chips_visible_with_tags(self, qtbot):
        from writer.ui.panels.editor_panel import EditorPanel
        from writer.domain.models.entry import Entry
        from datetime import datetime

        entry = Entry(
            id="e1",
            title="Test",
            body="body",
            tags=["poetry", "draft"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        panel = EditorPanel()
        qtbot.addWidget(panel)
        panel.set_entry(entry)
        assert not panel._tag_chips_widget.isHidden(), "Tag chips should be visible when tags exist"
        # Should have 2 chip labels (plus the stretch item)
        visible_chips = [
            panel._tag_chips_layout.itemAt(i).widget()
            for i in range(panel._tag_chips_layout.count() - 1)  # exclude stretch
        ]
        assert len(visible_chips) == 2

    def test_tag_chips_clear_on_empty(self, qtbot):
        from writer.ui.panels.editor_panel import EditorPanel
        from writer.domain.models.entry import Entry
        from datetime import datetime

        entry = Entry(
            id="e1",
            title="T",
            body="b",
            tags=["one"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        panel = EditorPanel()
        qtbot.addWidget(panel)
        panel.set_entry(entry)
        assert not panel._tag_chips_widget.isHidden(), "Chips visible after set_entry"
        panel.set_entry(None)
        assert panel._tag_chips_widget.isHidden(), "Chips hidden after set_entry(None)"


# ---------------------------------------------------------------------------
# M7A acceptance fix: rewrite compare dialog title + progress text i18n
# ---------------------------------------------------------------------------
class TestRewriteI18n:
    def test_rewrite_compare_dialog_title_zh(self, qtbot):
        """RewriteCompareDialog title shows fully-localized Chinese action name in zh_CN."""
        from writer.app.locale import set_locale, LOCALE_ZH_CN
        from writer.domain.enums import RewriteAction
        from writer.ui.dialogs.rewrite_compare_dialog import RewriteCompareDialog
        from writer.ui.i18n import TR, rewrite_action_label

        set_locale(LOCALE_ZH_CN)
        try:
            localized_name = rewrite_action_label(RewriteAction.POLISH)
            dlg = RewriteCompareDialog(
                original_text="orig",
                generated_text="gen",
                action_label=localized_name,
            )
            qtbot.addWidget(dlg)
            title = dlg.windowTitle()
            # Title must contain the Chinese action name, not the raw enum value
            assert localized_name in title, f"Localized name '{localized_name}' not in title '{title}'"
            assert "polish" not in title, f"Raw enum value 'polish' must not appear in zh_CN title: '{title}'"
            assert "Review AI" not in title, f"English boilerplate must not appear in zh_CN title: '{title}'"
        finally:
            set_locale("en")

    def test_rewrite_progress_text_localized(self):
        """Progress text uses localized action name, not raw enum value."""
        from writer.app.locale import set_locale, LOCALE_ZH_CN
        from writer.domain.enums import RewriteAction
        from writer.ui.i18n import TR, rewrite_action_label

        # EN: localized name is "Polish", raw value is "polish"
        set_locale("en")
        en_label = rewrite_action_label(RewriteAction.POLISH)
        en_text = TR("dlg.rewrite_progress").format(action=en_label)
        assert "Polish" in en_text, f"EN progress should contain 'Polish', got: '{en_text}'"
        assert "polish" not in en_text, f"EN progress should not contain raw 'polish', got: '{en_text}'"

        # ZH_CN: localized name is "润色", raw value is "polish"
        set_locale(LOCALE_ZH_CN)
        zh_label = rewrite_action_label(RewriteAction.POLISH)
        zh_text = TR("dlg.rewrite_progress").format(action=zh_label)
        assert "polish" not in zh_text, f"ZH_CN progress must not contain raw 'polish': '{zh_text}'"
        assert zh_label in zh_text, f"ZH_CN localized label '{zh_label}' not in progress text: '{zh_text}'"
        assert zh_text != en_text, "ZH_CN and EN progress text should differ"

        set_locale("en")
