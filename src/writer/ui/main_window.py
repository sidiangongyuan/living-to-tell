"""Main application window.

Redesigned for M9A as a four-column shell:

    [navigation rail] [list column] [main work area] [context pane]

The rail stays narrow and always visible, so the user can switch between
Articles / Collections without hunting for tabs. The right-side
context pane is collapsible and its visibility is persisted, alongside
the splitter sizes that already existed before M9A.

UI code never touches SQLite directly; everything goes through the
container's repositories and services.
"""
from __future__ import annotations

import json
from typing import Callable, Optional

from PySide6.QtCore import QEvent, QSignalBlocker, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from writer.app.container import AppContainer
from writer.app.locale import LOCALE_EN, LOCALE_ZH_CN
from writer.app.settings import (
    DEFAULT_THEME_MODE,
    KEY_ACTIVE_MODE,
    KEY_CONTEXT_PANE_VISIBLE,
    KEY_THEME_MODE,
)
from writer.domain.enums import RewriteAction, AiThreadScope, AiTaskType, AiTargetKind
from writer.services.ai.interfaces import RewriteRequest, RewriteResponse
from writer.services.autosave_service import AutosaveService
from writer.storage.repositories.entry_repository import (
    SORT_UPDATED,
    serialize_tags,
)
from writer.ui.dialogs.assign_fragment_dialog import AssignFragmentDialog
from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog
from writer.ui.dialogs.global_search_dialog import GlobalSearchDialog
from writer.ui.dialogs.entry_collection_picker_dialog import EntryCollectionPickerDialog
from writer.ui.dialogs.projects_dialog import ProjectsDialog
from writer.ui.dialogs.reference_library_dialog import ReferenceLibraryDialog
from writer.ui.dialogs.reference_picker_dialog import ReferencePickerDialog
from writer.ui.dialogs.rewrite_compare_dialog import AcceptMode, RewriteCompareDialog
from writer.ui.dialogs.settings_dialog import SettingsDialog
from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog
from writer.ui.i18n import TR, rewrite_action_label
from writer.ui.motion import set_stack_index
from writer.ui.panels.collections_panel import CollectionsPanel
from writer.ui.panels.editor_panel import EditorPanel, _count_words
from writer.ui.panels.fragment_list_panel import FragmentListPanel
from writer.ui.panels.ai_workspace_panel import AIWorkspacePanel, AiScope
from writer.ui.rewrite_worker import RewriteWorker
from writer.ui.theme import ThemeMode, apply_theme
from writer.ui.widgets import ContextPane, NavigationRail

_SPLITTER_SIZES_KEY = "ui.splitter_sizes"
_MAIN_SPLITTER_SIZES_KEY = "ui.main_splitter_sizes"
_SIDEBAR_COLLAPSED_KEY = "ui.sidebar_collapsed"
_DEFAULT_SIDEBAR_WIDTH = 280
_MAX_SIDEBAR_WIDTH = 340
_DEFAULT_EDITOR_WIDTH = 1120
_MIN_MAIN_AREA_WIDTH = 700
_MIN_CONTEXT_WIDTH = 220


# Mode-stack indices. Dates was added at index 0 in M-Dates, shifting
# every other mode up by one. Tests and code that referenced the old
# integer indices have been migrated to these names.
MODE_DATES = 0
MODE_FRAGMENTS = 1
MODE_COLLECTIONS = 2
MODE_AI = 3
_MODE_COUNT = 4
_LEGACY_MODE_WORKS = 2
_LEGACY_MODE_COLLECTIONS = 3
_LEGACY_MODE_AI = 4


class MainWindow(QMainWindow):
    def __init__(
        self,
        container: AppContainer,
        parent: QWidget | None = None,
        *,
        autosave_debounce_ms: int = 800,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._close_request_handler: Optional[Callable[[], bool]] = None
        self._native_event_handler: Optional[Callable[[object, object], bool]] = None
        self._force_close = False
        self._focus_mode_enabled = False
        self._focus_restore_state: Optional[dict[str, object]] = None
        self._reduced_motion = container.settings.reduced_motion_enabled()
        self._context_pane_visible = True
        self._last_context_pane_width = ContextPane.DEFAULT_WIDTH

        self.setWindowTitle("Writer")
        self.resize(1280, 780)

        # ---- Fragments mode panels (preserve attribute names for tests) ----
        self._list_panel = FragmentListPanel()
        self._list_panel.setMaximumWidth(_MAX_SIDEBAR_WIDTH)
        self._editor_panel = EditorPanel()
        self._editor_panel.save_specimen_requested.connect(
            self._on_save_style_specimen
        )

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._list_panel)
        self._splitter.addWidget(self._editor_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.splitterMoved.connect(self._on_splitter_moved)
        self._sidebar_collapsed = False
        self._restore_splitter_state()

        # M9A: when the fragment library is genuinely empty we want the
        # welcome card to take over the whole work area instead of an
        # auto-created blank fragment masking it. Wrap the fragments
        # splitter in a QStackedWidget [splitter, welcome_card] and flip
        # based on entry count.
        from writer.ui.widgets.empty_state import EmptyStateCard

        self._welcome_card = EmptyStateCard(
            TR("empty.welcome_title"),
            TR("empty.welcome_desc"),
            primary_label=TR("empty.welcome_primary"),
            primary_callback=self._on_new_fragment,
        )
        welcome_wrap = QWidget()
        welcome_wrap.setObjectName("WriterWorkspaceOverlay")
        wl = QVBoxLayout(welcome_wrap)
        wl.setContentsMargins(48, 64, 48, 48)
        wl.addWidget(self._welcome_card)
        wl.addStretch(1)

        self._fragments_stack = QStackedWidget()
        self._fragments_stack.addWidget(self._splitter)   # 0 — workspace
        self._fragments_stack.addWidget(welcome_wrap)      # 1 — welcome card
        # Preserve the historical attribute name for the outer mode stack.
        self._fragments_widget = self._fragments_stack

        # ---- Other modes ----
        self._collections_panel = CollectionsPanel(container)
        self._ai_workspace_panel = AIWorkspacePanel(container)

        # M-Dates: top-level dates / daily-writing view.
        from writer.ui.panels.dates_panel import DatesPanel
        self._dates_panel = DatesPanel(container)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._dates_panel)            # 0 — Dates
        self._stack.addWidget(self._fragments_widget)       # 1 — Articles
        self._stack.addWidget(self._collections_panel)      # 2 — Collections
        self._stack.addWidget(self._ai_workspace_panel)     # 3 — AI workspace
        self._last_mode_before_ai = MODE_FRAGMENTS
        self._return_to_ai_after_writing_note_add_entry_id: Optional[str] = None

        # ---- Context pane ----
        self._context_pane = ContextPane(
            empty_title=TR("context.empty_title"),
            empty_description=TR("context.empty_desc"),
            meta_labels={
                "words": TR("context.label_words"),
                "chars": TR("context.label_chars"),
                "tags": TR("context.label_tags"),
                "collections": TR("context.label_collections"),
                "writing_notes": TR("context.label_writing_notes"),
                "created": TR("context.label_created"),
                "updated": TR("context.label_updated"),
                "status": TR("context.label_status"),
                "summary": TR("context.label_summary"),
                "target": TR("context.label_target"),
                "work_count": TR("context.label_work_count"),
            },
            action_labels={
                "polish": TR("context.action_polish"),
                "add_to_collection": TR("context.action_add_to_collection"),
                "writing_notes": TR("context.action_writing_notes"),
                "checkpoint": TR("context.action_checkpoint"),
                "save_specimen": TR("context.action_save_specimen"),
                "versions": TR("context.action_versions"),
                "export_fragment": TR("context.action_export_fragment"),
                "export_collection": TR("context.action_export_collection"),
            },
        )
        self._context_pane.set_reduced_motion(self._reduced_motion)
        # Wire context-pane action buttons to existing handlers.
        self._context_pane.fragment_polish_button.clicked.connect(
            self._on_open_ai_polish_from_context
        )
        self._context_pane.fragment_add_to_collection_button.clicked.connect(
            self._on_add_current_article_to_collections
        )
        self._context_pane.fragment_writing_notes_button.clicked.connect(
            self._on_toggle_writing_notes_from_context
        )
        self._context_pane.fragment_checkpoint_button.clicked.connect(
            self._on_save_checkpoint
        )
        self._context_pane.fragment_versions_button.clicked.connect(
            self._on_open_version_history
        )
        self._context_pane.fragment_export_button.clicked.connect(
            self._on_export_current_fragment_from_context
        )
        self._context_pane.fragment_save_specimen_button.clicked.connect(
            self._on_save_style_specimen
        )
        self._context_pane.collection_export_button.clicked.connect(
            self._on_export_current_collection_from_context
        )

        # ---- Navigation rail ----
        self._rail = NavigationRail(
            brand_text=TR("shell.brand"),
            dates_label=TR("rail.dates"),
            fragments_label=TR("rail.fragments"),
            collections_label=TR("rail.collections"),
            search_label=TR("rail.search"),
            theme_label=TR("rail.theme"),
            settings_label=TR("rail.settings"),
            ai_label=TR("rail.ai"),
        )
        self._rail.mode_changed.connect(self._set_mode)
        self._rail.search_clicked.connect(self._on_global_search)
        self._rail.theme_clicked.connect(self._on_open_theme_menu)
        self._rail.settings_clicked.connect(self._on_open_settings)

        # ---- Outer shell splitter (rail | content_stack | context_pane) ----
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setObjectName("WriterShellSplitter")
        self._main_splitter.setHandleWidth(7)
        self._main_splitter.setChildrenCollapsible(False)

        # Wrap the stack so it can take an object name for QSS.
        self._main_area = QWidget()
        self._main_area.setObjectName("WriterMain")
        main_layout = QHBoxLayout(self._main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._stack)
        self._editor_panel.set_writing_notes_layer(self._main_area)
        self._editor_panel.set_writing_notes_anchor(self._context_pane)

        self._main_splitter.addWidget(self._rail)
        self._main_splitter.addWidget(self._main_area)
        self._main_splitter.addWidget(self._context_pane)
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)
        self._main_splitter.setStretchFactor(2, 0)
        # Rail width is fixed by NavigationRail itself; just give sensible
        # initial widths to the other two columns.
        self._main_splitter.setSizes([
            NavigationRail.RAIL_WIDTH,
            900,
            ContextPane.DEFAULT_WIDTH,
        ])
        # Restore context-pane visibility.
        self._context_pane_visible = (
            self._container.settings.get(KEY_CONTEXT_PANE_VISIBLE, "true") != "false"
        )
        self._restore_main_splitter_state()
        self._apply_context_pane_visibility(save=False)
        self._main_splitter.splitterMoved.connect(self._on_main_splitter_moved)

        shell = QWidget()
        shell.setObjectName("WriterShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self._main_splitter)
        self.setCentralWidget(shell)

        self._autosave = AutosaveService(
            container.entry_repository,
            self._snapshot_for_autosave,
            debounce_ms=autosave_debounce_ms,
            parent=self,
        )

        # Wire signals -------------------------------------------------
        self._list_panel.entry_selected.connect(self._on_entry_selected)
        self._list_panel.new_requested.connect(self._on_new_fragment)
        self._list_panel.search_changed.connect(self._on_search_changed)
        self._list_panel.tag_filter_changed.connect(self._on_tag_filter_changed)
        self._list_panel.delete_requested.connect(self._on_delete_requested)
        self._list_panel.archive_requested.connect(self._on_archive_requested)
        self._list_panel.sort_changed.connect(self._on_sort_changed)
        self._list_panel.show_archived_changed.connect(self._on_show_archived_changed)
        self._editor_panel.content_changed.connect(self._on_editor_changed)
        self._editor_panel.content_changed.connect(self._refresh_fragment_context)
        self._editor_panel.writing_note_add_requested.connect(self._on_add_writing_note)
        self._editor_panel.writing_note_update_requested.connect(
            self._on_update_writing_note
        )
        self._editor_panel.writing_note_done_requested.connect(self._on_set_writing_note_done)
        self._editor_panel.writing_note_delete_requested.connect(self._on_delete_writing_note)
        self._editor_panel.writing_note_pin_requested.connect(self._on_pin_writing_note)
        self._editor_panel.writing_note_layout_requested.connect(
            self._on_update_writing_note_layout
        )
        self._editor_panel.writing_notes_continue_requested.connect(
            self._on_continue_with_writing_notes
        )
        self._collections_panel.collection_selected.connect(
            self._on_collection_selected_for_context
        )
        # M9A: empty-state CTAs that need cross-panel routing.
        self._list_panel.global_search_requested.connect(self._on_global_search)
        self._autosave.saved.connect(self._on_autosaved)
        self._autosave.dirty.connect(self._on_autosave_dirty)
        self._autosave.saving.connect(self._on_autosave_saving)

        # M-Dates: route Dates-panel actions through the shell so the
        # editor opens, autosave flushes, and the fragments list refreshes
        # consistently.
        self._dates_panel.entry_picked.connect(self._on_dates_entry_picked)
        self._dates_panel.new_today_requested.connect(self._on_dates_new_today)
        self._dates_panel.append_tags_requested.connect(self._on_dates_append_tags)
        self._dates_panel.merge_requested.connect(self._on_dates_merge)
        self._dates_panel.manage_quotes_requested.connect(self._on_manage_quotes)
        self._ai_workspace_panel.request_locate_excerpt.connect(self._on_locate_ai_excerpt)
        self._ai_workspace_panel.request_locate_selection.connect(
            self._on_locate_ai_selection
        )
        self._ai_workspace_panel.request_focus_writing_notes.connect(
            self._on_focus_writing_notes
        )
        self._ai_workspace_panel.request_fragment_changed.connect(
            self._on_ai_fragment_changed
        )

        # M7B: in-memory trash for the most recent deletions. Each entry is
        # a dict with title/body/tags; survives until the app closes.
        self._deleted_trash: list[dict] = []
        # M7B: active sort / archive filter state (UI -> repo kwargs).
        self._sort_mode: str = SORT_UPDATED
        self._show_archived: bool = False

        self._build_menu_bar()
        self._build_toolbar()
        self._build_status_bar()
        self._apply_editor_object_names()
        self._apply_editor_preferences()
        self._install_focus_mode_key_filters()
        self._update_focus_mode_ui()
        self._maybe_offer_legacy_work_import()
        self._initial_load()

        # Restore the persisted active mode (default Dates so users land on
        # today's writing view; falling back gracefully if the stored
        # index pre-dates the M-Dates shift and is out of range).
        persisted_mode = self._mode_from_setting(
            self._container.settings.get(KEY_ACTIVE_MODE, "dates")
        )
        self._set_mode(max(0, min(_MODE_COUNT - 1, persisted_mode)))

    @staticmethod
    def _mode_from_setting(raw: object) -> int:
        """Map persisted mode names and legacy ids onto the current stack.

        Older settings used 0=Dates, 1=Fragments, 2=Works, 3=Collections,
        4=AI. Works has no product-level entry now, so it falls back to
        Articles. New settings use names to avoid the old/new ``2``
        ambiguity.
        """
        mode_names = {
            "dates": MODE_DATES,
            "fragments": MODE_FRAGMENTS,
            "articles": MODE_FRAGMENTS,
            "collections": MODE_COLLECTIONS,
            "ai": MODE_AI,
        }
        text = str(raw or "").strip().lower()
        if text in mode_names:
            return mode_names[text]
        try:
            mode = int(text)
        except (TypeError, ValueError):
            return MODE_DATES
        if mode == _LEGACY_MODE_WORKS:
            return MODE_FRAGMENTS
        if mode == _LEGACY_MODE_COLLECTIONS:
            return MODE_COLLECTIONS
        if mode == _LEGACY_MODE_AI:
            return MODE_AI
        return mode

    @staticmethod
    def _mode_setting_name(mode: int) -> str:
        return {
            MODE_DATES: "dates",
            MODE_FRAGMENTS: "articles",
            MODE_COLLECTIONS: "collections",
            MODE_AI: "ai",
        }.get(mode, "dates")

    def _maybe_offer_legacy_work_import(self) -> None:
        service = getattr(self._container, "legacy_work_import_service", None)
        if service is None:
            return
        try:
            needs_import = service.needs_import()
        except Exception:  # noqa: BLE001
            return
        if not needs_import:
            return
        answer = QMessageBox.question(
            self,
            TR("legacy_import.title"),
            TR("legacy_import.message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            service.mark_skipped()
            return
        try:
            summary = service.import_once()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self,
                TR("legacy_import.failed_title"),
                str(exc),
            )
            return
        QMessageBox.information(
            self,
            TR("legacy_import.done_title"),
            TR("legacy_import.done_message").format(
                entries=summary.entries_created,
                collections=summary.collections_created,
            ),
        )

    # --------------------------------------------------------------
    def _build_menu_bar(self) -> None:
        menu_bar: QMenuBar = self.menuBar()

        file_menu = menu_bar.addMenu(TR("menu.file"))
        new_action = QAction(TR("menu.new_fragment"), self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._on_new_fragment)
        file_menu.addAction(new_action)
        save_action = QAction(TR("menu.save"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_manual_save)
        file_menu.addAction(save_action)
        checkpoint_action = QAction(TR("menu.save_checkpoint"), self)
        checkpoint_action.triggered.connect(self._on_save_checkpoint)
        file_menu.addAction(checkpoint_action)
        recover_action = QAction(TR("menu.recover_last_deleted"), self)
        recover_action.triggered.connect(self._on_recover_last_deleted)
        file_menu.addAction(recover_action)
        file_menu.addSeparator()
        assign_action = QAction(TR("menu.assign_to_project"), self)
        assign_action.triggered.connect(self._on_assign_fragment)
        file_menu.addAction(assign_action)
        projects_action = QAction(TR("menu.projects"), self)
        projects_action.triggered.connect(self._on_open_projects)
        file_menu.addAction(projects_action)
        file_menu.addSeparator()
        history_action = QAction(TR("menu.version_history"), self)
        history_action.triggered.connect(self._on_open_version_history)
        file_menu.addAction(history_action)
        export_menu = file_menu.addMenu(TR("menu.export"))
        export_fragment_md = QAction(TR("menu.export_fragment_md"), self)
        export_fragment_md.triggered.connect(
            lambda: self._on_export("fragment", "markdown")
        )
        export_menu.addAction(export_fragment_md)
        export_fragment_txt = QAction(TR("menu.export_fragment_txt"), self)
        export_fragment_txt.triggered.connect(
            lambda: self._on_export("fragment", "text")
        )
        export_menu.addAction(export_fragment_txt)
        export_menu.addSeparator()
        export_project_md = QAction(TR("menu.export_project_md"), self)
        export_project_md.triggered.connect(
            lambda: self._on_export("project", "markdown")
        )
        export_menu.addAction(export_project_md)
        export_project_txt = QAction(TR("menu.export_project_txt"), self)
        export_project_txt.triggered.connect(
            lambda: self._on_export("project", "text")
        )
        export_menu.addAction(export_project_txt)
        file_menu.addSeparator()
        global_search_action = QAction(TR("menu.global_search"), self)
        global_search_action.triggered.connect(self._on_global_search)
        file_menu.addAction(global_search_action)
        references_action = QAction(TR("menu.references"), self)
        references_action.triggered.connect(self._on_open_reference_library)
        file_menu.addAction(references_action)
        file_menu.addSeparator()
        quit_action = QAction(TR("menu.quit"), self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menu_bar.addMenu(TR("menu.view"))
        self._focus_mode_action = QAction(TR("menu.focus_mode"), self)
        self._focus_mode_action.setShortcut(QKeySequence("F11"))
        self._focus_mode_action.triggered.connect(self._toggle_focus_mode)
        view_menu.addAction(self._focus_mode_action)
        self.addAction(self._focus_mode_action)
        self._focus_mode_shortcut = QShortcut(QKeySequence("F11"), self)
        self._focus_mode_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._focus_mode_shortcut.activated.connect(self._toggle_focus_mode)

        help_menu = menu_bar.addMenu(TR("menu.help"))
        about_action = QAction(TR("menu.about"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

        # Collect all leaf actions for the command palette (populated after
        # building, so the list is available at Ctrl+P time)
        self._all_menu_actions: list[QAction] = []
        for top in menu_bar.actions():
            menu = top.menu()
            if menu:
                self._collect_actions(menu, self._all_menu_actions)

    def _collect_actions(self, menu, out: list) -> None:
        for action in menu.actions():
            if action.isSeparator():
                continue
            if action.menu():
                self._collect_actions(action.menu(), out)
            else:
                out.append(action)

    # --------------------------------------------------------------
    def _build_toolbar(self) -> None:
        """Slim secondary toolbar.

        With the navigation rail covering mode switching, the toolbar only
        carries small utility actions: context-pane toggle and the language
        quick-switch button. We keep it as a real ``QToolBar`` so existing
        infrastructure (and the M7A test that asserts at least one toolbar
        exists) keeps working.
        """
        toolbar = QToolBar("Quick actions", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setObjectName("WriterTopToolbar")
        self._top_toolbar = toolbar

        self._sidebar_btn = QPushButton(TR("toolbar.sidebar"))
        self._sidebar_btn.setObjectName("GhostButton")
        self._sidebar_btn.setCheckable(True)
        self._sidebar_btn.setToolTip(TR("toolbar.toggle_sidebar"))
        self._sidebar_btn.clicked.connect(self._toggle_sidebar)
        toolbar.addWidget(self._sidebar_btn)

        self._context_toggle_btn = QPushButton(TR("toolbar.context"))
        self._context_toggle_btn.setObjectName("GhostButton")
        self._context_toggle_btn.setCheckable(True)
        self._context_toggle_btn.setToolTip(TR("shell.toggle_context_pane"))
        self._context_toggle_btn.clicked.connect(self._toggle_context_pane)
        toolbar.addWidget(self._context_toggle_btn)

        self._focus_toggle_btn = QPushButton(TR("toolbar.focus_mode"))
        self._focus_toggle_btn.setObjectName("GhostButton")
        self._focus_toggle_btn.clicked.connect(self._toggle_focus_mode)
        toolbar.addWidget(self._focus_toggle_btn)

        # Spacer to push the language button to the right.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Language quick-switch button.
        self._lang_btn = QPushButton(TR("toolbar.language_switch"))
        self._lang_btn.setObjectName("GhostButton")
        self._lang_btn.setToolTip(TR("toolbar.language_switch_tooltip"))
        self._lang_btn.setMinimumWidth(
            max(
                self._lang_btn.sizeHint().width(),
                self._lang_btn.fontMetrics().height() + 28,
            )
        )
        self._lang_btn.clicked.connect(self._on_toggle_language)
        toolbar.addWidget(self._lang_btn)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self._update_shell_toggle_buttons()

        # Extra (non-menu) actions exposed in the command palette
        focus_search_action = QAction(TR("cmd.focus_search"), self)
        focus_search_action.triggered.connect(
            lambda: self._list_panel._search.setFocus()
        )
        switch_lang_action = QAction(TR("cmd.switch_language"), self)
        switch_lang_action.triggered.connect(self._on_toggle_language)
        self._extra_palette_actions: list[QAction] = [
            focus_search_action,
            switch_lang_action,
        ]

        # Command palette shortcut
        cmd_action = QAction(TR("menu.command_palette"), self)
        cmd_action.setShortcut(QKeySequence("Ctrl+P"))
        cmd_action.triggered.connect(self._on_command_palette)
        self.addAction(cmd_action)

        # M8 global search shortcut (Ctrl+Shift+F).
        gsearch_action = QAction(TR("cmd.global_search"), self)
        gsearch_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        gsearch_action.triggered.connect(self._on_global_search)
        self.addAction(gsearch_action)
        self._extra_palette_actions.append(gsearch_action)

    # --------------------------------------------------------------
    def _restore_splitter_state(self) -> None:
        """Restore sidebar width and collapsed state from persisted settings."""
        collapsed_raw = self._container.settings.get(_SIDEBAR_COLLAPSED_KEY, "false")
        self._sidebar_collapsed = collapsed_raw == "true"

        sizes_raw = self._container.settings.get(_SPLITTER_SIZES_KEY)
        if sizes_raw:
            try:
                sizes = json.loads(sizes_raw)
                if (
                    isinstance(sizes, list)
                    and len(sizes) == 2
                    and all(isinstance(s, int) for s in sizes)
                ):
                    self._splitter.setSizes(self._normalized_fragment_splitter_sizes(sizes))
                    return
            except (json.JSONDecodeError, TypeError):
                pass
        # Default sizes
        if self._sidebar_collapsed:
            self._splitter.setSizes([0, _DEFAULT_EDITOR_WIDTH])
        else:
            self._splitter.setSizes([_DEFAULT_SIDEBAR_WIDTH, _DEFAULT_EDITOR_WIDTH])
        self._update_shell_toggle_buttons()

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        sizes = self._splitter.sizes()
        self._container.settings.set(_SPLITTER_SIZES_KEY, json.dumps(sizes))
        # Update collapsed state based on actual size
        self._sidebar_collapsed = sizes[0] == 0
        self._container.settings.set(
            _SIDEBAR_COLLAPSED_KEY, "true" if self._sidebar_collapsed else "false"
        )
        self._update_shell_toggle_buttons()

    def _toggle_sidebar(self) -> None:
        if self._sidebar_collapsed:
            self._splitter.setSizes([_DEFAULT_SIDEBAR_WIDTH, _DEFAULT_EDITOR_WIDTH])
            self._sidebar_collapsed = False
        else:
            self._splitter.setSizes([0, self._splitter.width()])
            self._sidebar_collapsed = True
        sizes = self._splitter.sizes()
        self._container.settings.set(_SPLITTER_SIZES_KEY, json.dumps(sizes))
        self._container.settings.set(
            _SIDEBAR_COLLAPSED_KEY, "true" if self._sidebar_collapsed else "false"
        )
        self._update_shell_toggle_buttons()
        # Opening/closing the sidebar changes the main area's minimum width
        # (sidebar + editor content vs editor alone). Qt propagates the new
        # minimum asynchronously; schedule the outer-splitter re-normalize to
        # the next event loop so it sees the updated constraint and pulls the
        # context pane back to its preferred width.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._normalize_main_splitter_sizes)

    def _restore_main_splitter_state(self) -> None:
        sizes_raw = self._container.settings.get(_MAIN_SPLITTER_SIZES_KEY)
        if not sizes_raw:
            return
        try:
            sizes = json.loads(sizes_raw)
        except (json.JSONDecodeError, TypeError):
            return
        if (
            isinstance(sizes, list)
            and len(sizes) == 3
            and all(isinstance(size, int) for size in sizes)
        ):
            if sizes[2] > 0:
                self._last_context_pane_width = max(_MIN_CONTEXT_WIDTH, sizes[2])
            self._main_splitter.setSizes(self._normalized_main_splitter_sizes(sizes))

    def _on_main_splitter_moved(self, _pos: int, _index: int) -> None:
        # Record the dragged width FIRST so the normalize pass below honours
        # the user's drag instead of pulling the pane back to the previous
        # width (the old order acted as a grow-only ratchet that eventually
        # froze the handle at the pane's maximum width).
        if self._context_pane_visible:
            sizes = self._main_splitter.sizes()
            if len(sizes) >= 3 and sizes[2] > 0:
                self._last_context_pane_width = max(_MIN_CONTEXT_WIDTH, sizes[2])
        self._normalize_main_splitter_sizes()
        self._container.settings.set(
            _MAIN_SPLITTER_SIZES_KEY,
            json.dumps(self._main_splitter.sizes()),
        )
        self._editor_panel.refresh_writing_notes_layer()

    def _update_shell_toggle_buttons(self) -> None:
        if hasattr(self, "_sidebar_btn"):
            self._sidebar_btn.setChecked(not self._sidebar_collapsed)
            self._sidebar_btn.setToolTip(TR("toolbar.toggle_sidebar"))
        if hasattr(self, "_context_toggle_btn"):
            self._context_toggle_btn.setChecked(self._context_pane_visible)
            self._context_toggle_btn.setToolTip(TR("shell.toggle_context_pane"))

    def _normalized_fragment_splitter_sizes(
        self,
        sizes: list[int],
        *,
        available_width: Optional[int] = None,
    ) -> list[int]:
        total = max(
            1,
            int(available_width or 0),
            sum(max(0, int(size)) for size in sizes),
        )
        max_sidebar = max(0, min(_MAX_SIDEBAR_WIDTH, total - _MIN_MAIN_AREA_WIDTH))
        sidebar = max(0, min(max_sidebar, int(sizes[0])))
        if self._sidebar_collapsed:
            sidebar = 0
        editor = max(1, total - sidebar)
        return [sidebar, editor]

    def _normalize_fragment_splitter_sizes(self) -> None:
        if not hasattr(self, "_splitter"):
            return
        width = self._splitter.width()
        if width <= 0:
            return
        self._splitter.setSizes(
            self._normalized_fragment_splitter_sizes(
                self._splitter.sizes(),
                available_width=width,
            )
        )

    def _normalize_main_splitter_sizes(self) -> None:
        if not hasattr(self, "_main_splitter"):
            return
        self._main_splitter.setSizes(
            self._normalized_main_splitter_sizes(self._main_splitter.sizes())
        )

    def _normalized_main_splitter_sizes(self, sizes: list[int]) -> list[int]:
        if len(sizes) != 3:
            sizes = [NavigationRail.RAIL_WIDTH, _MIN_MAIN_AREA_WIDTH, ContextPane.DEFAULT_WIDTH]
        cleaned = [max(0, int(size)) for size in sizes]
        # The splitter's actual width is the ONLY source of truth. Never trust
        # the sum of the input sizes: callers often pass [rail, current_main,
        # context] where current_main already fills the viewport — sum would
        # exceed the real width, forcing Qt to squeeze the context pane to fit.
        splitter_width = self._main_splitter.width() if hasattr(self, "_main_splitter") else 0
        total = max(splitter_width, 1)  # sum(cleaned) is meaningless; only trust real width
        rail = NavigationRail.RAIL_WIDTH
        available = max(1, total - rail)
        if not getattr(self, "_context_pane_visible", True):
            return [rail, available, 0]

        # Query the actual minimum width Qt will enforce for the main area,
        # accounting for all children's constraints (sidebar, editor, handles).
        main_area_actual_min = _MIN_MAIN_AREA_WIDTH
        if hasattr(self, "_main_area"):
            hint = self._main_area.minimumSizeHint()
            if hint.isValid() and hint.width() > 0:
                main_area_actual_min = max(hint.width(), _MIN_MAIN_AREA_WIDTH)

        # Adaptive strategy: allocate context its preferred width (capped at 40%),
        # then give main the rest. If the result violates Qt's hard minimums, Qt
        # will either expand the window or compress proportionally — don't second-
        # guess it with early-return checks that use stale minimumSizeHint values.
        preferred_context = self._last_context_pane_width or ContextPane.DEFAULT_WIDTH
        # Cap preferred at 40% of available space to ensure main always gets
        # a reasonable share, preventing context from squeezing main below its
        # actual minimum (which would force Qt to push context offscreen).
        max_context_share = max(_MIN_CONTEXT_WIDTH, int(available * 0.4))
        preferred_context = min(preferred_context, max_context_share)

        if available >= main_area_actual_min + preferred_context:
            # Plenty of space: context gets preferred width, main gets the rest.
            context = preferred_context
            main = available - context
        elif available >= main_area_actual_min + _MIN_CONTEXT_WIDTH:
            # Tight: main gets its actual minimum, context gets the rest.
            main = main_area_actual_min
            context = available - main
        else:
            # Insufficient space: hide context to prevent Qt from expanding window.
            # Giving context even _MIN_CONTEXT_WIDTH would leave main < main_min,
            # forcing Qt to expand the window uncontrollably.
            return [rail, available, 0]

        return [rail, main, context]

    def _on_toggle_language(self) -> None:
        from writer.app.locale import current_locale

        current = current_locale()
        new_locale = LOCALE_ZH_CN if current == LOCALE_EN else LOCALE_EN
        self._container.settings.save_language(new_locale)
        QMessageBox.information(
            self,
            TR("settings.restart_required_title"),
            TR("settings.restart_required_msg"),
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        # Defer normalization to the next event loop: during resize, the
        # splitter's width() may not yet reflect the new window size, causing
        # the normalizer to compute layout from stale constraints and squeeze
        # the context pane. Deferring ensures Qt's layout pass finishes first.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._normalize_main_splitter_sizes)
        QTimer.singleShot(0, self._normalize_fragment_splitter_sizes)
        # Writing notes layer position depends on context pane geometry, so
        # refresh after the deferred normalize has a chance to run.
        QTimer.singleShot(0, self._editor_panel.refresh_writing_notes_layer)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Defer normalization for the same reason as resizeEvent.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._normalize_main_splitter_sizes)
        QTimer.singleShot(0, self._normalize_fragment_splitter_sizes)
        self._editor_panel.set_writing_notes_active(
            self._stack.currentIndex() == MODE_FRAGMENTS and not self.isMinimized()
        )
        self._editor_panel.refresh_writing_notes_layer()

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._editor_panel.refresh_writing_notes_layer()

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._editor_panel.set_writing_notes_active(
                self._stack.currentIndex() == MODE_FRAGMENTS and not self.isMinimized()
            )

    def _on_command_palette(self) -> None:
        dialog = CommandPaletteDialog(
            self._all_menu_actions + self._extra_palette_actions, parent=self
        )
        dialog.exec()

    # --------------------------------------------------------------
    def _build_status_bar(self) -> None:
        status: QStatusBar = self.statusBar()
        self._save_status_label = QLabel("")
        self._save_status_label.setObjectName("StatusLabel")
        status.addPermanentWidget(self._save_status_label)
        self._set_save_status("saved")

    def _set_save_status(self, state: str) -> None:
        key = {
            "saved": "status.saved",
            "saving": "status.saving",
            "unsaved": "status.unsaved",
            "none": "status.no_entry",
        }.get(state, "status.saved")
        self._save_status_label.setText(TR(key))

    # --------------------------------------------------------------
    def _initial_load(self) -> None:
        repo = self._container.entry_repository
        if repo.count() == 0:
            # M9A: do NOT auto-create a placeholder fragment. Leave the DB
            # empty so the welcome card on the workspace surface is the
            # first thing the user sees. The user clicking the welcome
            # card's primary CTA goes through ``_on_new_fragment`` like
            # any other "new fragment" entry point.
            self._refresh_tag_filter()
            self._list_panel.set_entries([])
            self._editor_panel.set_entry(None)
            self._show_fragments_welcome()
            return
        entries = repo.list_recent()
        if not entries:
            # Repo has only archived (or otherwise filtered-out) entries.
            # Keep the workspace visible \u2014 the user can flip "show
            # archived" to recover them \u2014 but leave the editor empty.
            self._refresh_tag_filter()
            self._list_panel.set_entries([])
            self._editor_panel.set_entry(None)
            self._show_fragments_workspace()
            return
        first = entries[0]
        self._refresh_tag_filter()
        self._list_panel.set_entries(entries, select_id=first.id)
        self._load_entry(first.id)
        self._show_fragments_workspace()

    def _show_fragments_welcome(self) -> None:
        """Switch the fragments-mode area to the welcome card."""
        set_stack_index(self._fragments_stack, 1, reduced=self._reduced_motion)

    def _show_fragments_workspace(self) -> None:
        """Switch the fragments-mode area to the normal list+editor splitter."""
        set_stack_index(self._fragments_stack, 0, reduced=self._reduced_motion)

    def _apply_fragments_workspace_visibility(self) -> None:
        """Pick welcome vs. normal workspace based on whether the entry
        repository is **truly empty** — not whether the current visible
        list happens to be empty.

        The welcome card replaces the entire fragments work area, including
        the search box, tag filter, and the "show archived" toggle. So we
        must only show it when there is genuinely nothing to manage. If the
        repo still contains archived (or otherwise filtered-out) entries,
        we keep the normal workspace visible so the user can flip the
        "show archived" switch and recover them.
        """
        if self._container.entry_repository.count() == 0:
            self._show_fragments_welcome()
        else:
            self._show_fragments_workspace()

    def _refresh_tag_filter(self) -> None:
        tags = self._container.entry_repository.list_all_tags()
        self._list_panel.set_tag_options(tags)

    def sync_external_entry(self, entry_id: Optional[str] = None) -> None:
        self._refresh_tag_filter()
        self._refresh_list(select_id=entry_id or self._editor_panel.current_entry_id())
        self._apply_fragments_workspace_visibility()
        if entry_id:
            self._dates_panel.refresh(select_entry_id=entry_id)
        else:
            self._dates_panel.refresh()

    def show_fragment_entry(self, entry_id: Optional[str] = None) -> None:
        self._set_mode(MODE_FRAGMENTS)
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        if entry_id:
            self._list_panel.clear_search()
            self._list_panel.reset_tag_filter()
        self.sync_external_entry(entry_id)
        if entry_id:
            self._load_entry(entry_id)
            self._editor_panel.focus_body()

    def set_close_request_handler(
        self, handler: Optional[Callable[[], bool]]
    ) -> None:
        self._close_request_handler = handler

    def set_native_event_handler(
        self, handler: Optional[Callable[[object, object], bool]]
    ) -> None:
        self._native_event_handler = handler

    def force_close(self) -> None:
        self._force_close = True
        self.close()

    def _refresh_list(self, *, select_id: Optional[str] = None) -> None:
        search = self._list_panel.search_text().strip()
        tag = self._list_panel.current_tag_filter()
        repo = self._container.entry_repository

        include_archived = self._show_archived
        sort = self._sort_mode

        if search and tag:
            results = self._container.search_service.search(search)
            tag_lower = tag.lower()
            entries = [
                e for e in results if any(t.lower() == tag_lower for t in e.tags)
            ]
            if not include_archived:
                entries = [e for e in entries if not e.archived_at]
        elif search:
            entries = self._container.search_service.search(search)
            if not include_archived:
                entries = [e for e in entries if not e.archived_at]
        elif tag:
            entries = repo.list_recent_by_tag(
                tag, sort=sort, include_archived=include_archived
            )
        else:
            entries = repo.list_recent(
                sort=sort, include_archived=include_archived
            )

        self._list_panel.set_entries(entries, select_id=select_id)

    def _load_entry(self, entry_id: str) -> None:
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            self._editor_panel.set_entry(None)
            self._editor_panel.set_writing_notes([])
            self._refresh_fragment_context()
            return
        if self._return_to_ai_after_writing_note_add_entry_id not in {None, entry_id}:
            self._return_to_ai_after_writing_note_add_entry_id = None
        from writer.storage.repositories.entry_repository import serialize_tags
        self._editor_panel.set_entry(entry)
        self._refresh_writing_notes_card(entry.id)
        self._autosave.remember_clean(
            entry.id, entry.title, entry.body, serialize_tags(entry.tags)
        )
        self._refresh_fragment_context()

    def _refresh_writing_notes_card(self, entry_id: Optional[str] = None) -> None:
        target_id = entry_id or self._editor_panel.current_entry_id()
        if not target_id:
            self._editor_panel.set_writing_notes([])
            return
        notes = self._container.entry_writing_note_repository.list_for_entry(
            target_id,
            include_done=True,
        )
        self._editor_panel.set_writing_notes(notes)

    def _writing_note_count_text(self, entry_id: str) -> str:
        count = self._container.entry_writing_note_repository.count_open_for_entry(entry_id)
        return TR("context.writing_notes_count").format(count=count)

    def _writing_note_action_text(self, entry_id: str) -> str:
        count = self._container.entry_writing_note_repository.count_open_for_entry(entry_id)
        return TR("context.action_writing_notes_open").format(count=count)

    def _entry_collections_text(self, entry_id: str) -> str:
        try:
            collections = self._container.collection_repository.list_collections_containing_entry(
                entry_id
            )
        except AttributeError:
            collections = []
        if not collections:
            return TR("context.no_value")
        names = [
            collection.name or TR("collections.untitled")
            for collection in collections[:3]
        ]
        suffix = ""
        if len(collections) > len(names):
            suffix = TR("context.collections_more").format(
                count=len(collections) - len(names)
            )
        return TR("context.collections_summary").format(
            count=len(collections),
            names=", ".join(names),
            more=suffix,
        )

    def _on_toggle_writing_notes_from_context(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        self._return_to_ai_after_writing_note_add_entry_id = None
        if self._stack.currentIndex() != MODE_FRAGMENTS:
            self._set_mode(MODE_FRAGMENTS)
            self._editor_panel.focus_writing_note_input()
            return
        self._editor_panel.toggle_writing_notes_panel()

    def _on_focus_writing_notes(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        if self._stack.currentIndex() == MODE_AI:
            open_count = self._container.entry_writing_note_repository.count_open_for_entry(
                entry_id
            )
            self._return_to_ai_after_writing_note_add_entry_id = (
                entry_id if open_count == 0 else None
            )
        else:
            self._return_to_ai_after_writing_note_add_entry_id = None
        self._set_mode(MODE_FRAGMENTS)
        self._editor_panel.focus_writing_note_input()

    def _on_add_writing_note(self, body: str) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        try:
            self._container.entry_writing_note_repository.create(
                entry_id=entry_id,
                body=body,
            )
        except ValueError:
            return
        self._refresh_writing_notes_after_change(entry_id)
        if self._return_to_ai_after_writing_note_add_entry_id == entry_id:
            self._return_to_ai_after_writing_note_add_entry_id = None
            self._set_mode(MODE_AI)
            self._ai_workspace_panel.set_include_writing_notes(True)

    def _on_update_writing_note(self, note_id: str, body: str) -> None:
        try:
            note = self._container.entry_writing_note_repository.update_body(
                note_id,
                body,
            )
        except ValueError:
            return
        entry_id = note.entry_id if note is not None else self._editor_panel.current_entry_id()
        if entry_id:
            self._refresh_writing_notes_after_change(entry_id)

    def _on_set_writing_note_done(self, note_id: str, done: bool) -> None:
        note = self._container.entry_writing_note_repository.set_done(note_id, done)
        entry_id = note.entry_id if note is not None else self._editor_panel.current_entry_id()
        if entry_id:
            self._refresh_writing_notes_after_change(entry_id)

    def _on_delete_writing_note(self, note_id: str) -> None:
        note = self._container.entry_writing_note_repository.get(note_id)
        self._container.entry_writing_note_repository.delete(note_id)
        entry_id = note.entry_id if note is not None else self._editor_panel.current_entry_id()
        if entry_id:
            self._refresh_writing_notes_after_change(entry_id)

    def _on_pin_writing_note(self, note_id: str, pinned: bool) -> None:
        note = self._container.entry_writing_note_repository.set_pinned(note_id, pinned)
        entry_id = note.entry_id if note is not None else self._editor_panel.current_entry_id()
        if entry_id:
            self._refresh_writing_notes_after_change(entry_id)

    def _on_update_writing_note_layout(
        self,
        note_id: str,
        x: int,
        y: int,
        width: int,
        color_key: str,
        z_index: int,
    ) -> None:
        note = self._container.entry_writing_note_repository.update_layout(
            note_id,
            x=x,
            y=y,
            width=width,
            color_key=color_key,
            z_index=z_index,
        )
        entry_id = note.entry_id if note is not None else self._editor_panel.current_entry_id()
        if entry_id:
            self._refresh_writing_notes_after_change(entry_id)

    def _refresh_writing_notes_after_change(self, entry_id: str) -> None:
        self._refresh_writing_notes_card(entry_id)
        self._refresh_fragment_context()
        if self._stack.currentIndex() == MODE_AI:
            self._bind_ai_workspace_scope()
            self._refresh_ai_context_from_panel()

    def _on_continue_with_writing_notes(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        self._autosave.flush()
        self._set_mode(MODE_AI)
        self._ai_workspace_panel.focus_task(
            AiTaskType.CONTINUE,
            target_kind=AiTargetKind.FRAGMENT,
        )
        self._ai_workspace_panel.set_include_writing_notes(True)

    # --------------------------------------------------------------
    def _snapshot_for_autosave(self) -> Optional[tuple[str, str, str, str]]:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return None
        return (
            entry_id,
            self._editor_panel.title_text(),
            self._editor_panel.body_text(),
            self._editor_panel.tags_text(),
        )

    # --------------------------------------------------------------
    def _on_entry_selected(self, entry_id: str) -> None:
        if entry_id == self._editor_panel.current_entry_id():
            return
        self._autosave.flush()
        self._load_entry(entry_id)

    def _on_new_fragment(self) -> None:
        self._autosave.flush()
        entry = self._container.entry_repository.create()
        self._list_panel.clear_search()
        self._list_panel.reset_tag_filter()
        self._refresh_list(select_id=entry.id)
        self._load_entry(entry.id)
        # M9A: leaving the welcome state once the user has at least one entry.
        self._show_fragments_workspace()
        # Auto-focus the body editor so the user can start writing immediately
        self._editor_panel.focus_body()

    def _on_search_changed(self, _query: str) -> None:
        self._refresh_list(select_id=self._editor_panel.current_entry_id())

    def _on_tag_filter_changed(self, _tag: str) -> None:
        self._refresh_list(select_id=self._editor_panel.current_entry_id())

    def _on_editor_changed(self) -> None:
        self._return_to_ai_after_writing_note_add_entry_id = None
        self._autosave.mark_dirty()

    def _on_autosaved(self, entry_id: str) -> None:
        self._refresh_tag_filter()
        self._refresh_list(select_id=entry_id)
        self._set_save_status("saved")

    def _on_autosave_dirty(self) -> None:
        self._set_save_status("unsaved")

    def _on_autosave_saving(self, _entry_id: str) -> None:
        self._set_save_status("saving")

    # --------------------------------------------------------------
    # M7B: save / delete / archive / sort / recovery
    # --------------------------------------------------------------
    def _on_manual_save(self) -> None:
        self._autosave.flush()
        self._set_save_status("saved")

    def _on_save_checkpoint(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        self._autosave.flush()
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            return
        self._container.version_history_service.save_manual_checkpoint(entry_id)
        self._set_save_status("saved")
        QMessageBox.information(
            self,
            TR("checkpoint.saved_title"),
            TR("checkpoint.saved_msg"),
        )

    def _on_sort_changed(self, sort: str) -> None:
        self._sort_mode = sort
        self._refresh_list(select_id=self._editor_panel.current_entry_id())

    def _on_show_archived_changed(self, enabled: bool) -> None:
        self._show_archived = bool(enabled)
        self._refresh_list(select_id=self._editor_panel.current_entry_id())

    def _on_archive_requested(self, entry_id: str, archived: bool) -> None:
        self._autosave.flush()
        repo = self._container.entry_repository
        repo.set_archived(entry_id, archived)

        # If the entry we just archived is the one loaded in the editor, and
        # archived entries are currently filtered out of the list, the UI
        # would otherwise be left on a hidden row with no selection. Load a
        # visible neighbour (or a fresh blank fragment) the same way a
        # deletion does.
        current_id = self._editor_panel.current_entry_id()
        entry_disappeared = (
            archived
            and current_id == entry_id
            and not self._show_archived
        )
        if entry_disappeared:
            remaining = repo.list_recent(
                limit=1, sort=self._sort_mode, include_archived=False
            )
            if remaining:
                self._refresh_tag_filter()
                self._refresh_list(select_id=remaining[0].id)
                self._load_entry(remaining[0].id)
            else:
                # No visible (unarchived) entries left, but the repo may
                # still contain archived ones. Only flip to the welcome
                # card when the repo is truly empty; otherwise keep the
                # workspace shown so the user can toggle "show archived"
                # and find their content again.
                self._refresh_tag_filter()
                self._list_panel.set_entries([])
                self._editor_panel.set_entry(None)
                self._apply_fragments_workspace_visibility()
        else:
            self._refresh_list(select_id=entry_id)

    def _on_delete_requested(self, entry_ids: list[str]) -> None:
        if not entry_ids:
            return
        repo = self._container.entry_repository
        if len(entry_ids) == 1:
            entry = repo.get(entry_ids[0])
            if entry is None:
                return
            title = entry.title.strip() or TR("list.empty_fragment")
            msg = TR("dlg.confirm_delete_one").format(title=title)
        else:
            msg = TR("dlg.confirm_delete_many").format(count=len(entry_ids))
        reply = QMessageBox.question(
            self,
            TR("dlg.confirm_delete_title"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Stash snapshots for "Recover last deleted" before deletion.
        snapshots: list[dict] = []
        for eid in entry_ids:
            e = repo.get(eid)
            if e is not None:
                snapshots.append(
                    {
                        "title": e.title,
                        "body": e.body,
                        "tags": list(e.tags),
                        "project_id": e.project_id,
                        "chapter_id": e.chapter_id,
                        "sequence_order": e.sequence_order,
                        "archived_at": e.archived_at,
                    }
                )
        repo.delete_many(entry_ids)
        # Only keep the most recent batch — keep the behaviour simple and
        # predictable (File → Recover last deleted restores this batch).
        self._deleted_trash = snapshots

        # If the editor was showing one of the deleted entries, load a
        # fresh one (next recent), or fall back to the welcome state when
        # the library is now empty.
        current_id = self._editor_panel.current_entry_id()
        if current_id in entry_ids or current_id is None:
            remaining = repo.list_recent(
                limit=1, sort=self._sort_mode, include_archived=self._show_archived
            )
            if remaining:
                self._refresh_tag_filter()
                self._refresh_list(select_id=remaining[0].id)
                self._load_entry(remaining[0].id)
            else:
                # Library may be truly empty (welcome card) or only have
                # archived entries that are filtered out (keep workspace
                # shown so the user can toggle "show archived").
                self._refresh_tag_filter()
                self._list_panel.set_entries([])
                self._editor_panel.set_entry(None)
                self._apply_fragments_workspace_visibility()
        else:
            self._refresh_tag_filter()
            self._refresh_list(select_id=current_id)

    def _on_recover_last_deleted(self) -> None:
        if not self._deleted_trash:
            QMessageBox.information(
                self,
                TR("dlg.nothing_to_recover_title"),
                TR("dlg.nothing_to_recover_msg"),
            )
            return
        repo = self._container.entry_repository
        restored_last: Optional[str] = None
        # Restore in reverse order so the most recent deletion ends up at
        # the top of the recent list.
        for snap in reversed(self._deleted_trash):
            entry = repo.insert_restored(
                title=snap["title"],
                body=snap["body"],
                tags=snap["tags"],
                project_id=snap.get("project_id"),
                chapter_id=snap.get("chapter_id"),
                sequence_order=snap.get("sequence_order"),
                archived_at=snap.get("archived_at"),
            )
            restored_last = entry.id
        self._deleted_trash.clear()
        self._refresh_tag_filter()
        self._refresh_list(select_id=restored_last)
        if restored_last is not None:
            self._load_entry(restored_last)
        QMessageBox.information(
            self,
            TR("dlg.recovered_title"),
            TR("dlg.recovered_msg"),
        )

    # --------------------------------------------------------------
    # AI rewrite flow
    # --------------------------------------------------------------
    def _on_about(self) -> None:
        from writer.app.version import APP_VERSION

        QMessageBox.about(
            self,
            TR("about.title"),
            TR("about.content").format(version=APP_VERSION),
        )

    def _on_open_settings(self) -> None:
        dialog = SettingsDialog(self._container.settings, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._apply_motion_preferences()
            self._apply_editor_preferences()

    def _on_open_reference_library(
        self,
        *,
        initial_usage_kind: Optional[str] = None,
        select_passage_id: Optional[str] = None,
    ) -> None:
        try:
            dialog = ReferenceLibraryDialog(
                self._container.reference_repository,
                parent=self,
                initial_usage_kind=initial_usage_kind,
                settings=self._container.settings,
            )
        except TypeError:
            dialog = ReferenceLibraryDialog(
                self._container.reference_repository,
                parent=self,
                initial_usage_kind=initial_usage_kind,
            )
        if select_passage_id:
            dialog.locate_passage(select_passage_id)
        dialog.exec()
        self._dates_panel.refresh_daily_quote()

    def _on_manage_quotes(self, quote_id: str = "") -> None:
        self._on_open_reference_library(select_passage_id=quote_id or None)

    # --------------------------------------------------------------
    # M-Dates: signals from DatesPanel
    # --------------------------------------------------------------
    def _on_dates_entry_picked(self, entry_id: str) -> None:
        """Open a fragment from the Dates view in the editor."""
        self._autosave.flush()
        self._set_mode(MODE_FRAGMENTS)
        self._list_panel.clear_search()
        self._list_panel.reset_tag_filter()
        self._refresh_list(select_id=entry_id)
        self._load_entry(entry_id)
        self._show_fragments_workspace()
        self._editor_panel.focus_body()

    def _on_dates_new_today(self) -> None:
        """Quick-create today's entry from the Dates view, then open it.

        We deliberately rely on ``EntryRepository.create``'s default
        ``created_at`` (which is ``strftime('now')`` server-side). The
        spec is explicit: do NOT introduce a manual writing-date field.
        """
        self._autosave.flush()
        entry = self._container.entry_repository.create()
        # Refresh dates panel badges + list so the new entry appears today.
        self._dates_panel.refresh(select_entry_id=entry.id)
        # Then jump to the editor.
        self._on_dates_entry_picked(entry.id)

    def _on_dates_append_tags(self, entry_ids: list) -> None:
        from writer.ui.dialogs.append_tags_dialog import AppendTagsDialog

        if not entry_ids:
            return
        dlg = AppendTagsDialog(count=len(entry_ids), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        tags = dlg.tags()
        if not tags:
            return
        self._autosave.flush()
        repo = self._container.entry_repository
        touched = 0
        for eid in entry_ids:
            if repo.append_tags(eid, tags) is not None:
                touched += 1
        # Reload UIs that may show tags.
        self._dates_panel.refresh()
        self._refresh_tag_filter()
        self._refresh_list(select_id=self._editor_panel.current_entry_id())
        self._set_save_status("saved")
        QMessageBox.information(
            self,
            TR("dates.append_tags_title"),
            TR("dates.append_tags_done").format(count=touched),
        )

    def _on_dates_merge(self, entry_ids: list) -> None:
        from writer.ui.dialogs.merge_to_draft_dialog import MergeToDraftDialog

        if not entry_ids:
            return
        repo = self._container.entry_repository
        entries = [e for e in (repo.get(i) for i in entry_ids) if e is not None]
        if not entries:
            return
        dlg = MergeToDraftDialog(self._container, entries, parent=self)
        dlg.saved.connect(self._on_dates_merge_saved)
        dlg.exec()

    def _on_dates_merge_saved(self, new_entry_id: str) -> None:
        self._dates_panel.refresh(select_entry_id=new_entry_id)
        self._refresh_tag_filter()

    # --------------------------------------------------------------
    # Article collections / Search
    # --------------------------------------------------------------
    def _set_mode(self, mode: int) -> None:
        if self._focus_mode_enabled and mode != MODE_FRAGMENTS:
            self._exit_focus_mode()
        previous_mode = self._stack.currentIndex()
        if mode == MODE_AI and previous_mode != MODE_AI:
            self._last_mode_before_ai = previous_mode
        if mode != MODE_FRAGMENTS:
            self._return_to_ai_after_writing_note_add_entry_id = None
        set_stack_index(self._stack, mode, reduced=self._reduced_motion)
        self._editor_panel.set_writing_notes_active(mode == MODE_FRAGMENTS and not self.isMinimized())
        self._rail.set_active_mode(mode)
        # Persist the active mode so the next launch lands on the same view.
        try:
            self._container.settings.set(KEY_ACTIVE_MODE, self._mode_setting_name(mode))
        except Exception:  # noqa: BLE001 — settings issues must not crash UI
            pass
        if mode == MODE_DATES:
            self._dates_panel.refresh()
        elif mode == MODE_FRAGMENTS:
            self._refresh_fragment_context()
        elif mode == MODE_COLLECTIONS:
            self._collections_panel.refresh_collections()
            self._refresh_collection_context_from_panel()
        elif mode == MODE_AI:
            self._bind_ai_workspace_scope()
            self._refresh_ai_context_from_panel()

    def _bind_ai_workspace_scope(self) -> None:
        """Hand the AI workspace whichever object is most relevant.

        Preference: currently-edited article > currently-selected collection
        > GLOBAL.
        """
        def _bind_fragment_scope() -> bool:
            entry_id = self._editor_panel.current_entry_id()
            if entry_id is None:
                return False
            entry = self._container.entry_repository.get(entry_id)
            if entry is None:
                return False
            self._autosave.flush()
            entry = self._container.entry_repository.get(entry_id) or entry
            sel_range = self._editor_panel.selection_range()
            sel_text = self._editor_panel.selected_body_text()
            sel_start, sel_end = (sel_range if sel_range else (None, None))
            self._ai_workspace_panel.bind_scope(
                AiScope(
                    kind=AiThreadScope.FRAGMENT,
                    ref_id=entry.id,
                    name=(entry.title or TR("list.empty_fragment")).strip(),
                    body=entry.body or "",
                    selection_start=sel_start,
                    selection_end=sel_end,
                    selection_text=sel_text,
                )
            )
            return True

        def _bind_collection_scope() -> bool:
            try:
                coll_id = self._collections_panel._current_collection_id()  # noqa: SLF001
            except Exception:  # noqa: BLE001
                coll_id = None
            if not coll_id:
                return False
            coll = self._container.collection_repository.get(coll_id)
            if coll is None:
                return False
            self._ai_workspace_panel.bind_scope(
                AiScope(
                    kind=AiThreadScope.COLLECTION,
                    ref_id=coll.id,
                    name=coll.name or "(untitled collection)",
                    body=self._collection_scope_body(coll.id),
                )
            )
            return True

        source_mode = self._last_mode_before_ai
        binders = {
            MODE_DATES: (_bind_fragment_scope, _bind_collection_scope),
            MODE_FRAGMENTS: (_bind_fragment_scope, _bind_collection_scope),
            MODE_COLLECTIONS: (_bind_collection_scope, _bind_fragment_scope),
        }.get(source_mode, (_bind_fragment_scope, _bind_collection_scope))
        for binder in binders:
            if binder():
                return
        # 4. Global fallback.
        self._ai_workspace_panel.bind_scope(
            AiScope(kind=AiThreadScope.GLOBAL, ref_id=None, name="", body="")
        )

    def _collection_scope_body(self, collection_id: str) -> str:
        """Build read-only collection context from ordered articles."""
        entries = self._collection_entries(collection_id)
        parts: list[str] = []
        for index, entry in enumerate(entries, start=1):
            title = (entry.title or TR("list.empty_fragment")).strip()
            body = (entry.body or "").strip()
            if body:
                parts.append(f"{index}. {title}\n\n{body}")
            else:
                parts.append(f"{index}. {title}")
        return "\n\n---\n\n".join(parts)

    def _collection_entries(self, collection_id: str) -> list:
        try:
            return list(self._container.collection_repository.list_entries(collection_id))
        except AttributeError:
            return []

    def _on_open_ai_polish_from_context(self) -> None:
        """Route the context-pane 'AI Polish' button to AI workspace.

        Flushes autosave, switches to the AI workspace (which binds the
        current fragment scope including any live selection), then
        pre-selects the POLISH task with the appropriate target kind.
        No AI request is made until the user explicitly clicks Run.
        """
        if self._editor_panel.current_entry_id() is None:
            return
        self._autosave.flush()
        # _set_mode handles scope binding via _bind_ai_workspace_scope().
        self._set_mode(MODE_AI)
        # Choose target based on what bind_scope decided for this scope.
        scope = self._ai_workspace_panel.scope
        target_kind = (
            AiTargetKind.SELECTION
            if scope is not None and scope.has_selection
            else AiTargetKind.FRAGMENT
        )
        self._ai_workspace_panel.focus_task(AiTaskType.POLISH, target_kind=target_kind)

    def _on_locate_ai_excerpt(self, excerpt: str) -> None:
        scope = self._ai_workspace_panel.scope
        if scope is None:
            self.statusBar().showMessage(TR("ai.results.locate_excerpt_not_found"), 2500)
            return
        found = False
        if scope.kind is AiThreadScope.FRAGMENT and scope.ref_id:
            self._autosave.flush()
            self._set_mode(MODE_FRAGMENTS)
            self._refresh_list(select_id=scope.ref_id)
            self._load_entry(scope.ref_id)
            found = self._editor_panel.activate_excerpt_find(excerpt)
        if not found:
            self.statusBar().showMessage(TR("ai.results.locate_excerpt_not_found"), 2500)

    def _on_locate_ai_selection(self, scope: AiScope) -> None:
        if scope is None or not scope.has_selection:
            return
        if scope.kind is AiThreadScope.FRAGMENT and scope.ref_id:
            self._autosave.flush()
            self._set_mode(MODE_FRAGMENTS)
            self._refresh_list(select_id=scope.ref_id)
            self._load_entry(scope.ref_id)
            self._editor_panel.select_body_range(
                scope.selection_start or 0,
                scope.selection_end or 0,
            )

    def _on_ai_fragment_changed(self, entry_id: str) -> None:
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            return
        if self._editor_panel.current_entry_id() == entry_id:
            self._editor_panel.set_entry(entry)
            self._refresh_writing_notes_card(entry_id)
            self._autosave.remember_clean(
                entry_id,
                entry.title,
                entry.body,
                serialize_tags(entry.tags),
            )
        self._refresh_list(select_id=entry_id)
        if self._stack.currentIndex() == MODE_AI:
            self._bind_ai_workspace_scope()
            self._refresh_ai_context_from_panel()

    def _refresh_ai_context_from_panel(self) -> None:
        if self._stack.currentIndex() != MODE_AI:
            return
        scope = self._ai_workspace_panel.scope
        if scope is None or scope.kind is AiThreadScope.GLOBAL or not scope.ref_id:
            self._show_mode_empty_context(MODE_AI)
            return
        if scope.kind is AiThreadScope.FRAGMENT:
            entry = self._container.entry_repository.get(scope.ref_id)
            if entry is None:
                self._show_mode_empty_context(MODE_AI)
                return
            body = entry.body or ""
            self._context_pane.show_fragment(
                title=(entry.title or TR("list.empty_fragment")).strip(),
                words=str(_count_words(body)),
                chars=str(len(body)),
                tags=", ".join(entry.tags) or TR("context.no_value"),
                writing_notes=self._writing_note_count_text(entry.id),
                created=entry.created_at or TR("context.no_value"),
                updated=entry.updated_at or TR("context.no_value"),
                status=(
                    TR("list.archived_badge").strip(" []")
                    if entry.archived_at
                    else TR("context.no_value")
                ),
                collections=self._entry_collections_text(entry.id),
                writing_notes_action=self._writing_note_action_text(entry.id),
            )
            return
        if scope.kind is AiThreadScope.COLLECTION:
            coll = self._container.collection_repository.get(scope.ref_id)
            if coll is None:
                self._show_mode_empty_context(MODE_AI)
                return
            entries = self._collection_entries(scope.ref_id)
            total_words = sum(_count_words(entry.body or "") for entry in entries)
            self._context_pane.show_collection(
                title=coll.name or TR("collections.untitled"),
                work_count=str(len(entries)),
                words=str(total_words),
            )
            return
        self._show_mode_empty_context(MODE_AI)

    def _show_mode_empty_context(self, mode: Optional[int] = None) -> None:
        actual_mode = self._stack.currentIndex() if mode is None else mode
        title_key, desc_key = {
            MODE_COLLECTIONS: (
                "context.empty_title_collection",
                "context.empty_desc_collection",
            ),
            MODE_AI: ("context.empty_title_ai", "context.empty_desc_ai"),
        }.get(actual_mode, ("context.empty_title", "context.empty_desc"))
        self._context_pane.show_empty(TR(title_key), TR(desc_key))

    def _on_global_search(self) -> None:
        dlg = GlobalSearchDialog(self._container, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.selected_hit is None:
            return
        hit = dlg.selected_hit
        if hit.kind == "fragment":
            self._set_mode(MODE_FRAGMENTS)
            self._refresh_list(select_id=hit.id)

    def _on_save_style_specimen(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        self._autosave.flush()
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            return
        from writer.ui.dialogs.save_specimen_dialog import SaveSpecimenDialog

        selected = self._editor_panel.selected_body_text()
        dlg = SaveSpecimenDialog(
            self._container.reference_repository,
            default_body=selected or entry.body or "",
            default_source_title=entry.title or "",
            default_tags=serialize_tags(entry.tags),
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.saved_passage is None:
            return
        QMessageBox.information(
            self,
            TR("specimen.save_dialog_title"),
            TR("specimen.saved_msg"),
        )

    # --------------------------------------------------------------
    # Projects / assignment / export / version history
    # --------------------------------------------------------------
    def _on_open_version_history(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        # Flush autosave so the live body in the dialog matches what's stored.
        self._autosave.flush()
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            return
        dialog = VersionHistoryDialog(
            entry_id=entry_id,
            live_body=entry.body,
            service=self._container.version_history_service,
            parent=self,
        )
        dialog.exec()
        if dialog.restored_body() is not None:
            # A restore happened — reload the editor and refresh the list.
            self._load_entry(entry_id)
            self._refresh_list(select_id=entry_id)

    def _on_open_projects(self) -> None:
        dialog = ProjectsDialog(
            self._container.project_repository,
            self._container.chapter_repository,
            self._container.entry_repository,
            self._container.markdown_exporter,
            self._container.text_exporter,
            parent=self,
        )
        dialog.exec()
        # Project/chapter/entry assignments may have changed; refresh the
        # main window's fragment list so titles & ordering stay accurate.
        self._refresh_list(select_id=self._editor_panel.current_entry_id())

    def _on_assign_fragment(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return
        self._autosave.flush()
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            return
        dialog = AssignFragmentDialog(
            self._container.project_repository,
            self._container.chapter_repository,
            current_project_id=entry.project_id,
            current_chapter_id=entry.chapter_id,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        project_id = dialog.selected_project_id()
        chapter_id = dialog.selected_chapter_id()
        self._container.entry_repository.assign_to_project(entry.id, project_id)
        if project_id is not None:
            try:
                self._container.entry_repository.assign_to_chapter(
                    entry.id, chapter_id
                )
            except ValueError as err:
                QMessageBox.warning(
                    self,
                    TR("dlg.chapter_not_assigned"),
                    TR("dlg.chapter_not_assigned_msg") + str(err),
                )
        self._refresh_list(select_id=entry.id)

    def _on_export(self, scope: str, fmt: str) -> None:
        """Delegate to the exporter service and save via QFileDialog.

        The main window owns no string-concatenation logic — it only
        decides *what* to export and *where to save the output*.
        """
        if scope == "fragment":
            text = self._build_fragment_export(fmt)
            if text is None:
                return
            default_name = (
                self._editor_panel.title_text().strip() or "fragment"
            )
        elif scope == "project":
            text = self._build_project_export(fmt)
            if text is None:
                return
            project = self._current_entry_project()
            default_name = project.name if project is not None else "project"
        else:  # pragma: no cover — defensive
            return

        extension = "md" if fmt == "markdown" else "txt"
        filter_label = (
            TR("dlg.export_md_filter") if fmt == "markdown" else TR("dlg.export_txt_filter")
        )
        path, _ = QFileDialog.getSaveFileName(
            self, TR("dlg.export_save_title"), f"{default_name}.{extension}", filter_label
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        except OSError as err:
            QMessageBox.critical(self, TR("dlg.export_failed"), str(err))

    def _build_fragment_export(self, fmt: str) -> Optional[str]:
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return None
        self._autosave.flush()
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            return None
        exporter = (
            self._container.markdown_exporter
            if fmt == "markdown"
            else self._container.text_exporter
        )
        return exporter.export_entry(entry)

    def _build_project_export(self, fmt: str) -> Optional[str]:
        project = self._current_entry_project()
        if project is None:
            QMessageBox.information(
                self,
                TR("dlg.no_project"),
                TR("dlg.no_project_msg"),
            )
            return None
        exporter = (
            self._container.markdown_exporter
            if fmt == "markdown"
            else self._container.text_exporter
        )
        self._autosave.flush()
        return exporter.export_project(project)

    def _current_entry_project(self):
        entry_id = self._editor_panel.current_entry_id()
        if entry_id is None:
            return None
        entry = self._container.entry_repository.get(entry_id)
        if entry is None or entry.project_id is None:
            return None
        return self._container.project_repository.get(entry.project_id)

    def _collect_references(self):
        """Return a list of reference content strings, or None if cancelled.

        The picker is skipped silently if the user has no reference passages
        yet — there is nothing to choose from.
        """
        if self._container.reference_repository.count() == 0:
            return []
        dialog = ReferencePickerDialog(
            self._container.reference_repository, parent=self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_contents()


    def _on_rewrite(self, action: RewriteAction) -> None:
        entry_id = self._editor_panel.current_entry_id()
        # Make sure the in-memory edits are flushed before snapshotting.
        if entry_id is not None:
            self._autosave.flush()

        full_body = self._editor_panel.body_text()
        title = self._editor_panel.title_text()
        selection = self._editor_panel.selection_range()
        selected_text = self._editor_panel.selected_body_text()

        if action is RewriteAction.CONTINUE:
            target_text = selected_text or full_body
        else:
            target_text = selected_text or full_body

        # M7B: preflight BEFORE showing a progress window. If anything is
        # missing (no key, bad config, empty text) the user gets a clear,
        # actionable error instead of a progress box that flashes and dies.
        from writer.services.ai.preflight import (
            format_issues,
            preflight_rewrite,
        )

        issues = preflight_rewrite(
            self._container.settings.load_ai_config(),
            target_text,
            has_entry=entry_id is not None,
        )
        if issues:
            QMessageBox.warning(
                self,
                TR("dlg.ai_not_ready"),
                format_issues(issues),
            )
            return

        # From here on the target entry is guaranteed to exist.
        assert entry_id is not None

        references = self._collect_references()
        if references is None:
            # User cancelled the reference picker.
            return

        request = RewriteRequest(
            action=action, text=target_text, references=list(references)
        )

        cancelled = {"flag": False}
        finishing = {"flag": False}

        progress = QProgressDialog(
            TR("dlg.rewrite_progress").format(action=rewrite_action_label(action)),
            TR("dlg.rewrite_cancel"),
            0,
            0,
            self,
        )
        progress.setWindowTitle(TR("dlg.working"))
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        worker = RewriteWorker(self._container.rewrite_service, request, parent=self)

        def _on_success(response: RewriteResponse) -> None:
            finishing["flag"] = True
            progress.close()
            if cancelled["flag"]:
                # Fix 2: cancellation was requested before the success signal
                # was delivered; drop the result entirely.
                worker.deleteLater()
                return
            self._handle_rewrite_response(
                action=action,
                response=response,
                entry_id=entry_id,
                full_body=full_body,
                title=title,
                selection=selection,
            )
            worker.deleteLater()

        def _on_failure(message: str) -> None:
            finishing["flag"] = True
            progress.close()
            if cancelled["flag"]:
                worker.deleteLater()
                return
            QMessageBox.critical(self, TR("dlg.ai_failed"), message)
            worker.deleteLater()

        def _on_cancel() -> None:
            if finishing["flag"]:
                return
            cancelled["flag"] = True
            worker.requestInterruption()

        # RewriteWorker is a QThread subclass created on the GUI thread.
        # Force queued delivery so success/failure handlers always run back
        # on the main thread before they touch dialogs or widgets.
        worker.succeeded.connect(
            _on_success, Qt.ConnectionType.QueuedConnection
        )
        worker.failed.connect(
            _on_failure, Qt.ConnectionType.QueuedConnection
        )
        progress.canceled.connect(_on_cancel)
        worker.start()
        progress.exec()

    def _handle_rewrite_response(
        self,
        *,
        action: RewriteAction,
        response: RewriteResponse,
        entry_id: str,
        full_body: str,
        title: str,
        selection,
    ) -> None:
        original_view = (
            full_body[selection[0] : selection[1]] if selection is not None else full_body
        )
        provider_label = f"{response.provider} · {response.model}"
        dialog = RewriteCompareDialog(
            original_text=original_view,
            generated_text=response.content,
            action_label=rewrite_action_label(action),
            provider_label=provider_label,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        if dialog.accept_mode() is AcceptMode.PARTIAL:
            accepted_text = dialog.accepted_selection_text()
        else:
            accepted_text = dialog.accepted_text()

        if not accepted_text.strip():
            return

        sel_start, sel_end = (selection if selection is not None else (None, None))
        outcome = self._container.rewrite_service.apply_acceptance(
            entry_id=entry_id,
            action=action,
            original_full_body=full_body,
            selection_start=sel_start,
            selection_end=sel_end,
            generated_text=accepted_text,
            title=title,
            provider=response.provider,
            model=response.model,
        )

        # Reflect the new body in the editor without firing a dirty mark.
        self._editor_panel.replace_body(outcome.new_body)
        self._autosave.remember_clean(
            entry_id, title, outcome.new_body, self._editor_panel.tags_text()
        )
        self._refresh_list(select_id=entry_id)

    # --------------------------------------------------------------
    # M9A: shell helpers — theme menu, context pane, context refresh
    # --------------------------------------------------------------
    def _apply_editor_preferences(self) -> None:
        settings = self._container.settings.load_editor_display_settings()
        self._editor_panel.apply_display_settings(settings)
        self._editor_panel.set_writing_notes_collapsed_by_default(
            self._container.settings.writing_notes_card_collapsed_by_default()
        )
        self._editor_panel.set_reduced_motion(self._reduced_motion)
        self._editor_panel.set_focus_mode_enabled(self._focus_mode_enabled)

    def _apply_motion_preferences(self) -> None:
        self._reduced_motion = self._container.settings.reduced_motion_enabled()
        self._context_pane.set_reduced_motion(self._reduced_motion)
        self._editor_panel.set_reduced_motion(self._reduced_motion)

    def _install_focus_mode_key_filters(self) -> None:
        for widget in (
            self,
            self._editor_panel,
            self._editor_panel._title,
            self._editor_panel._tags,
            self._editor_panel._body,
        ):
            widget.installEventFilter(self)

    def _apply_editor_object_names(self) -> None:
        """Tag editor sub-widgets so the global QSS can style them."""
        try:
            self._editor_panel._body.setObjectName("FragmentBody")
            self._editor_panel._title.setObjectName("EditorTitle")
        except Exception:  # noqa: BLE001
            pass

    def _toggle_context_pane(self) -> None:
        self._context_pane_visible = not self._context_pane_visible
        self._apply_context_pane_visibility(save=True)

    def _apply_context_pane_visibility(self, *, save: bool) -> None:
        if not hasattr(self, "_main_splitter"):
            return
        self._context_pane.setVisible(self._context_pane_visible)

        # Defer setSizes to the next event loop so Qt's layout propagation
        # finishes after the visibility change. Immediate setSizes may read
        # stale splitter.width() or trigger before Qt updates constraints.
        def _apply_sizes():
            if self._context_pane_visible:
                # Showing the context pane: let the normalizer compute the layout
                # from the splitter's real width and the remembered context width,
                # instead of passing [rail, current_main_width, context] which sums
                # to more than the splitter's width and forces Qt to squeeze.
                context_width = max(
                    _MIN_CONTEXT_WIDTH,
                    self._last_context_pane_width or ContextPane.DEFAULT_WIDTH,
                )
                target = self._normalized_main_splitter_sizes(
                    [NavigationRail.RAIL_WIDTH, 1, context_width]
                )
            else:
                # Hiding the context pane: also go through the normalizer so it
                # reads the splitter's current width consistently. Passing a dummy
                # context=0 signals "hide" mode.
                target = self._normalized_main_splitter_sizes(
                    [NavigationRail.RAIL_WIDTH, 1, 0]
                )
            self._main_splitter.setSizes(target)

            # If normalizer auto-hid context due to insufficient space, inform user
            if self._context_pane_visible and target[2] == 0:
                from writer.ui.i18n import TR
                self.statusBar().showMessage(
                    TR("context.auto_hidden_insufficient_space"), 3000
                )

            self._update_shell_toggle_buttons()
            if save:
                try:
                    self._container.settings.set(
                        KEY_CONTEXT_PANE_VISIBLE,
                        "true" if self._context_pane_visible else "false",
                    )
                    self._container.settings.set(
                        _MAIN_SPLITTER_SIZES_KEY,
                        json.dumps(target),
                    )
                except Exception:  # noqa: BLE001
                    pass

        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, _apply_sizes)

    def _toggle_focus_mode(self) -> None:
        if self._focus_mode_enabled:
            self._exit_focus_mode()
            return
        self._enter_focus_mode()

    def _enter_focus_mode(self) -> None:
        if self._stack.currentIndex() != MODE_FRAGMENTS:
            self.statusBar().showMessage(TR("focus.mode_unavailable"), 3000)
            return
        if self._editor_panel.current_entry_id() is None:
            self.statusBar().showMessage(TR("focus.mode_unavailable"), 3000)
            return

        self._focus_restore_state = {
            "rail_visible": self._rail.isVisible(),
            "context_visible": self._context_pane_visible,
            "toolbar_visible": self._top_toolbar.isVisible(),
            "list_visible": self._list_panel.isVisible(),
            "main_splitter_sizes": list(self._main_splitter.sizes()),
            "fragment_splitter_sizes": list(self._splitter.sizes()),
        }
        blocker = QSignalBlocker(self._splitter)
        try:
            self._rail.setVisible(False)
            self._context_pane.setVisible(False)
            self._top_toolbar.setVisible(False)
            self._list_panel.setVisible(False)
            self._splitter.setSizes([0, max(1, self._splitter.width())])
            self._main_splitter.setSizes([0, max(1, self._main_splitter.width()), 0])
        finally:
            del blocker
        self._focus_mode_enabled = True
        self._editor_panel.set_focus_mode_enabled(True)
        self._editor_panel.focus_body()
        self._update_focus_mode_ui()
        self.statusBar().showMessage(TR("focus.mode_on"), 2000)

    def _exit_focus_mode(self) -> None:
        restore = self._focus_restore_state or {}
        blocker = QSignalBlocker(self._splitter)
        try:
            self._rail.setVisible(bool(restore.get("rail_visible", True)))
            self._context_pane_visible = bool(restore.get("context_visible", True))
            self._top_toolbar.setVisible(bool(restore.get("toolbar_visible", True)))
            self._list_panel.setVisible(bool(restore.get("list_visible", True)))
            fragment_sizes = restore.get("fragment_splitter_sizes")
            if isinstance(fragment_sizes, list) and len(fragment_sizes) == 2:
                self._splitter.setSizes(self._normalized_fragment_splitter_sizes(fragment_sizes))
            main_sizes = restore.get("main_splitter_sizes")
            if isinstance(main_sizes, list) and len(main_sizes) == 3:
                self._main_splitter.setSizes(main_sizes)
            self._apply_context_pane_visibility(save=False)
        finally:
            del blocker
        self._focus_mode_enabled = False
        self._focus_restore_state = None
        self._editor_panel.set_focus_mode_enabled(False)
        self._update_focus_mode_ui()
        self.statusBar().showMessage(TR("focus.mode_off"), 2000)

    def _update_focus_mode_ui(self) -> None:
        action_key = (
            "menu.exit_focus_mode" if self._focus_mode_enabled else "menu.focus_mode"
        )
        button_key = (
            "toolbar.exit_focus_mode"
            if self._focus_mode_enabled
            else "toolbar.focus_mode"
        )
        self._focus_mode_action.setText(TR(action_key))
        self._focus_toggle_btn.setText(TR(button_key))

    def _on_open_theme_menu(self) -> None:
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        current_raw = self._container.settings.get(
            KEY_THEME_MODE, DEFAULT_THEME_MODE
        )
        current_mode = ThemeMode.parse(current_raw)
        for label_key, mode in (
            ("theme.light", ThemeMode.LIGHT),
            ("theme.dark", ThemeMode.DARK),
            ("theme.system", ThemeMode.SYSTEM),
        ):
            act = QAction(TR(label_key), menu)
            act.setCheckable(True)
            act.setChecked(mode is current_mode)
            act.triggered.connect(
                lambda _checked=False, m=mode: self._apply_theme_mode(m)
            )
            group.addAction(act)
            menu.addAction(act)
        # Anchor the menu just below the rail's theme button.
        btn = self._rail.theme_button
        pos = btn.mapToGlobal(btn.rect().bottomRight())
        menu.exec(pos)

    def _apply_theme_mode(self, mode: ThemeMode) -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            apply_theme(app, mode)
        try:
            # Chat history bakes token colours into its HTML; re-render it so
            # a light/dark switch doesn't leave old messages in stale colours.
            self._ai_workspace_panel.refresh_theme()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._container.settings.set(KEY_THEME_MODE, mode.value)
        except Exception:  # noqa: BLE001
            pass

    # ------- Context-pane refresh helpers -------
    def _refresh_fragment_context(self) -> None:
        if self._stack.currentIndex() != MODE_FRAGMENTS:
            return
        entry_id = self._editor_panel.current_entry_id()
        if not entry_id:
            self._show_mode_empty_context(MODE_FRAGMENTS)
            return
        title = self._editor_panel.title_text().strip() or TR(
            "list.empty_fragment"
        )
        body = self._editor_panel.body_text()
        words = _count_words(body)
        chars = len(body)
        tags = self._editor_panel.tags_text().strip() or TR("context.no_value")
        try:
            entry = self._container.entry_repository.get(entry_id)
        except Exception:  # noqa: BLE001
            return
        if entry is None:
            self._show_mode_empty_context(MODE_FRAGMENTS)
            return
        status = (
            TR("list.archived_badge").strip(" []")
            if entry.archived_at
            else TR("context.no_value")
        )
        self._context_pane.show_fragment(
            title=title,
            words=str(words),
            chars=str(chars),
            tags=tags,
            writing_notes=self._writing_note_count_text(entry_id),
            created=entry.created_at or TR("context.no_value"),
            updated=entry.updated_at or TR("context.no_value"),
            status=status,
            collections=self._entry_collections_text(entry_id),
            writing_notes_action=self._writing_note_action_text(entry_id),
        )

    def _on_collection_selected_for_context(self, collection_id: str) -> None:
        self._refresh_collection_context(collection_id)

    def _refresh_collection_context_from_panel(self) -> None:
        cid = self._collections_panel._current_collection_id()
        if cid:
            self._refresh_collection_context(cid)
        else:
            self._show_mode_empty_context(MODE_COLLECTIONS)

    def _refresh_collection_context(self, collection_id: str) -> None:
        if self._stack.currentIndex() != MODE_COLLECTIONS:
            return
        coll = self._container.collection_repository.get(collection_id)
        if coll is None:
            self._show_mode_empty_context(MODE_COLLECTIONS)
            return
        entries = self._collection_entries(collection_id)
        total_words = sum(_count_words(entry.body or "") for entry in entries)
        self._context_pane.show_collection(
            title=coll.name or TR("collections.untitled"),
            work_count=str(len(entries)),
            words=str(total_words),
        )

    # ------- Context-pane action shortcuts -------
    def _on_export_current_fragment_from_context(self) -> None:
        if self._editor_panel.current_entry_id():
            self._on_export("fragment", "markdown")

    def _on_add_current_article_to_collections(self) -> None:
        entry_id = self._editor_panel.current_entry_id()
        if self._stack.currentIndex() == MODE_AI:
            scope = self._ai_workspace_panel.scope
            if scope is not None and scope.kind is AiThreadScope.FRAGMENT and scope.ref_id:
                entry_id = scope.ref_id
        if not entry_id:
            return
        try:
            existing = {
                collection.id
                for collection in self._container.collection_repository.list_collections_containing_entry(
                    entry_id
                )
            }
        except AttributeError:
            existing = set()
        dialog = EntryCollectionPickerDialog(
            self._container,
            entry_id=entry_id,
            excluded_collection_ids=existing,
            parent=self,
        )
        if (
            dialog.exec() != QDialog.DialogCode.Accepted
            or not dialog.selected_collection_ids
        ):
            return
        try:
            for collection_id in dialog.selected_collection_ids:
                self._container.collection_repository.add_entry(collection_id, entry_id)
        except AttributeError as exc:
            QMessageBox.information(
                self,
                TR("context.action_add_to_collection"),
                str(exc),
            )
            return
        self._refresh_fragment_context()
        if self._stack.currentIndex() == MODE_AI:
            self._refresh_ai_context_from_panel()
        self._collections_panel.refresh_collections()
        self.statusBar().showMessage(
            TR("context.added_to_collections").format(
                count=len(dialog.selected_collection_ids)
            ),
            2500,
        )

    def _on_export_current_collection_from_context(self) -> None:
        if self._collections_panel._current_collection_id():
            self._collections_panel._on_export_collection()

    # --------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        try:
            self._autosave.flush()
            if (
                not self._force_close
                and self._close_request_handler is not None
                and self._close_request_handler()
            ):
                event.ignore()
                return
        except Exception:  # noqa: BLE001
            pass
        try:
            self._autosave.stop()
        finally:
            super().closeEvent(event)

    def nativeEvent(self, event_type, message):  # noqa: N802 (Qt signature)
        if self._native_event_handler is not None and self._native_event_handler(
            event_type, message
        ):
            return True, 0
        return super().nativeEvent(event_type, message)

    def eventFilter(self, watched, event):  # noqa: N802 (Qt signature)
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_F11:
            self._toggle_focus_mode()
            return True
        return super().eventFilter(watched, event)
