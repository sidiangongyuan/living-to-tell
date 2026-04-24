"""Main application window.

Redesigned for M7A as a focus-writing shell: the editor is the primary
surface, the sidebar is collapsible and its width is persisted. A command
palette (Ctrl+P) gives quick access to all menu actions. Language and
splitter state are persisted in the settings database.

UI code never touches SQLite directly; everything goes through the
container's repositories and services.
"""
from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QToolBar,
    QWidget,
)

from writer.app.container import AppContainer
from writer.app.locale import LOCALE_EN, LOCALE_ZH_CN
from writer.domain.enums import RewriteAction
from writer.services.ai.interfaces import RewriteRequest, RewriteResponse
from writer.services.autosave_service import AutosaveService
from writer.ui.dialogs.assign_fragment_dialog import AssignFragmentDialog
from writer.ui.dialogs.command_palette_dialog import CommandPaletteDialog
from writer.ui.dialogs.projects_dialog import ProjectsDialog
from writer.ui.dialogs.reference_library_dialog import ReferenceLibraryDialog
from writer.ui.dialogs.reference_picker_dialog import ReferencePickerDialog
from writer.ui.dialogs.rewrite_compare_dialog import AcceptMode, RewriteCompareDialog
from writer.ui.dialogs.settings_dialog import SettingsDialog
from writer.ui.dialogs.version_history_dialog import VersionHistoryDialog
from writer.ui.i18n import TR, rewrite_action_label
from writer.ui.panels.editor_panel import EditorPanel
from writer.ui.panels.fragment_list_panel import FragmentListPanel
from writer.ui.rewrite_worker import RewriteWorker

_SPLITTER_SIZES_KEY = "ui.splitter_sizes"
_SIDEBAR_COLLAPSED_KEY = "ui.sidebar_collapsed"
_DEFAULT_SIDEBAR_WIDTH = 280
_DEFAULT_EDITOR_WIDTH = 820


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

        self.setWindowTitle("Writer")
        self.resize(1100, 680)

        self._list_panel = FragmentListPanel()
        self._editor_panel = EditorPanel()

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._list_panel)
        self._splitter.addWidget(self._editor_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.splitterMoved.connect(self._on_splitter_moved)

        # Restore persisted splitter sizes (or fall back to defaults)
        self._sidebar_collapsed = False
        self._restore_splitter_state()

        self.setCentralWidget(self._splitter)

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
        self._editor_panel.content_changed.connect(self._on_editor_changed)
        self._autosave.saved.connect(self._on_autosaved)

        self._build_menu_bar()
        self._build_toolbar()
        self._initial_load()

    # --------------------------------------------------------------
    def _build_menu_bar(self) -> None:
        menu_bar: QMenuBar = self.menuBar()

        file_menu = menu_bar.addMenu(TR("menu.file"))
        new_action = QAction(TR("menu.new_fragment"), self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._on_new_fragment)
        file_menu.addAction(new_action)
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
        quit_action = QAction(TR("menu.quit"), self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        ai_menu = menu_bar.addMenu(TR("menu.ai"))
        polish_action = QAction(TR("menu.polish"), self)
        polish_action.triggered.connect(lambda: self._on_rewrite(RewriteAction.POLISH))
        ai_menu.addAction(polish_action)
        expand_action = QAction(TR("menu.expand"), self)
        expand_action.triggered.connect(lambda: self._on_rewrite(RewriteAction.EXPAND))
        ai_menu.addAction(expand_action)
        continue_action = QAction(TR("menu.continue"), self)
        continue_action.triggered.connect(lambda: self._on_rewrite(RewriteAction.CONTINUE))
        ai_menu.addAction(continue_action)
        ai_menu.addSeparator()
        references_action = QAction(TR("menu.references"), self)
        references_action.triggered.connect(self._on_open_reference_library)
        ai_menu.addAction(references_action)
        settings_action = QAction(TR("menu.settings"), self)
        settings_action.triggered.connect(self._on_open_settings)
        ai_menu.addAction(settings_action)

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
        toolbar = QToolBar("Quick actions", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        # Sidebar toggle button
        self._sidebar_btn = QPushButton("◀")
        self._sidebar_btn.setToolTip(TR("toolbar.toggle_sidebar"))
        self._sidebar_btn.setFixedWidth(28)
        self._sidebar_btn.clicked.connect(self._toggle_sidebar)
        toolbar.addWidget(self._sidebar_btn)

        # Spacer to push language button to the right
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(),
            spacer.sizePolicy().verticalPolicy(),
        )
        from PySide6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Language quick-switch button
        self._lang_btn = QPushButton(TR("toolbar.language_switch"))
        self._lang_btn.setToolTip(TR("toolbar.language_switch_tooltip"))
        self._lang_btn.setFixedWidth(40)
        self._lang_btn.clicked.connect(self._on_toggle_language)
        toolbar.addWidget(self._lang_btn)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

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
                    self._splitter.setSizes(sizes)
                    return
            except (json.JSONDecodeError, TypeError):
                pass
        # Default sizes
        if self._sidebar_collapsed:
            self._splitter.setSizes([0, _DEFAULT_EDITOR_WIDTH])
        else:
            self._splitter.setSizes([_DEFAULT_SIDEBAR_WIDTH, _DEFAULT_EDITOR_WIDTH])

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        sizes = self._splitter.sizes()
        self._container.settings.set(_SPLITTER_SIZES_KEY, json.dumps(sizes))
        # Update collapsed state based on actual size
        self._sidebar_collapsed = sizes[0] == 0
        self._container.settings.set(
            _SIDEBAR_COLLAPSED_KEY, "true" if self._sidebar_collapsed else "false"
        )
        self._sidebar_btn.setText("▶" if self._sidebar_collapsed else "◀")

    def _toggle_sidebar(self) -> None:
        if self._sidebar_collapsed:
            self._splitter.setSizes([_DEFAULT_SIDEBAR_WIDTH, _DEFAULT_EDITOR_WIDTH])
            self._sidebar_collapsed = False
            self._sidebar_btn.setText("◀")
        else:
            self._splitter.setSizes([0, self._splitter.width()])
            self._sidebar_collapsed = True
            self._sidebar_btn.setText("▶")
        sizes = self._splitter.sizes()
        self._container.settings.set(_SPLITTER_SIZES_KEY, json.dumps(sizes))
        self._container.settings.set(
            _SIDEBAR_COLLAPSED_KEY, "true" if self._sidebar_collapsed else "false"
        )

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

    def _on_command_palette(self) -> None:
        dialog = CommandPaletteDialog(
            self._all_menu_actions + self._extra_palette_actions, parent=self
        )
        dialog.exec()

    # --------------------------------------------------------------
    def _initial_load(self) -> None:
        repo = self._container.entry_repository
        if repo.count() == 0:
            entry = repo.create()
            self._refresh_tag_filter()
            self._list_panel.set_entries([entry], select_id=entry.id)
            self._load_entry(entry.id)
        else:
            entries = repo.list_recent()
            first = entries[0]
            self._refresh_tag_filter()
            self._list_panel.set_entries(entries, select_id=first.id)
            self._load_entry(first.id)

    def _refresh_tag_filter(self) -> None:
        tags = self._container.entry_repository.list_all_tags()
        self._list_panel.set_tag_options(tags)

    def _refresh_list(self, *, select_id: Optional[str] = None) -> None:
        search = self._list_panel.search_text().strip()
        tag = self._list_panel.current_tag_filter()
        repo = self._container.entry_repository

        if search and tag:
            results = self._container.search_service.search(search)
            tag_lower = tag.lower()
            entries = [e for e in results if any(t.lower() == tag_lower for t in e.tags)]
        elif search:
            entries = self._container.search_service.search(search)
        elif tag:
            entries = repo.list_recent_by_tag(tag)
        else:
            entries = repo.list_recent()

        self._list_panel.set_entries(entries, select_id=select_id)

    def _load_entry(self, entry_id: str) -> None:
        entry = self._container.entry_repository.get(entry_id)
        if entry is None:
            self._editor_panel.set_entry(None)
            return
        from writer.storage.repositories.entry_repository import serialize_tags
        self._editor_panel.set_entry(entry)
        self._autosave.remember_clean(
            entry.id, entry.title, entry.body, serialize_tags(entry.tags)
        )

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
        # Auto-focus the body editor so the user can start writing immediately
        self._editor_panel.focus_body()

    def _on_search_changed(self, _query: str) -> None:
        self._refresh_list(select_id=self._editor_panel.current_entry_id())

    def _on_tag_filter_changed(self, _tag: str) -> None:
        self._refresh_list(select_id=self._editor_panel.current_entry_id())

    def _on_editor_changed(self) -> None:
        self._autosave.mark_dirty()

    def _on_autosaved(self, entry_id: str) -> None:
        self._refresh_tag_filter()
        self._refresh_list(select_id=entry_id)

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
        dialog.exec()

    def _on_open_reference_library(self) -> None:
        dialog = ReferenceLibraryDialog(
            self._container.reference_repository, parent=self
        )
        dialog.exec()

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
        if entry_id is None:
            return
        # Make sure the in-memory edits are flushed before snapshotting.
        self._autosave.flush()

        full_body = self._editor_panel.body_text()
        title = self._editor_panel.title_text()
        selection = self._editor_panel.selection_range()
        selected_text = self._editor_panel.selected_body_text()

        if action is RewriteAction.CONTINUE:
            target_text = selected_text or full_body
        else:
            target_text = selected_text or full_body

        if not target_text.strip():
            QMessageBox.information(
                self,
                TR("dlg.nothing_to_rewrite"),
                TR("dlg.nothing_to_rewrite_msg"),
            )
            return

        references = self._collect_references()
        if references is None:
            # User cancelled the reference picker.
            return

        request = RewriteRequest(
            action=action, text=target_text, references=list(references)
        )

        cancelled = {"flag": False}

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
            progress.close()
            if cancelled["flag"]:
                worker.deleteLater()
                return
            QMessageBox.critical(self, TR("dlg.ai_failed"), message)
            worker.deleteLater()

        def _on_cancel() -> None:
            cancelled["flag"] = True
            worker.requestInterruption()

        worker.succeeded.connect(_on_success)
        worker.failed.connect(_on_failure)
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
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        try:
            self._autosave.flush()
            self._autosave.stop()
        finally:
            super().closeEvent(event)
