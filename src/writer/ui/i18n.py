"""Lightweight UI string catalog for English / Simplified Chinese.

Usage::

    from writer.ui.i18n import TR

    button = QPushButton(TR("list.new_button"))

Strings are frozen at application startup — language changes take effect
after a restart.
"""
from __future__ import annotations

from writer.app.locale import current_locale

# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

_CATALOG: dict[str, dict[str, str]] = {
    "en": {
        # ── Fragment list panel ──────────────────────────────────────────────
        "list.search_placeholder": "Search fragments…",
        "list.new_button": "New",
        "list.all_tags": "All tags",
        "list.empty_fragment": "(empty fragment)",
        "list.empty_state": "No fragments yet.\nClick New to start writing.",
        "list.empty_search": "No results found.",
        # ── Editor panel ─────────────────────────────────────────────────────
        "editor.title_placeholder": "Title (optional)",
        "editor.tags_placeholder": "Tags (comma-separated)",
        "editor.body_placeholder": "Start writing…",
        "editor.meta_created": "created",
        "editor.meta_updated": "updated",
        # ── Main window – menus ───────────────────────────────────────────────
        "menu.file": "&File",
        "menu.new_fragment": "&New Fragment",
        "menu.assign_to_project": "&Assign to Project…",
        "menu.projects": "&Projects…",
        "menu.version_history": "Version &History…",
        "menu.export": "&Export",
        "menu.export_fragment_md": "Current &fragment as Markdown…",
        "menu.export_fragment_txt": "Current fragment as &text…",
        "menu.export_project_md": "Current &project as Markdown…",
        "menu.export_project_txt": "Current project as text…",
        "menu.quit": "&Quit",
        "menu.ai": "&AI",
        "menu.polish": "&Polish",
        "menu.expand": "&Expand",
        "menu.continue": "&Continue",
        "menu.references": "&References Library…",
        "menu.settings": "&Settings…",
        "menu.help": "&Help",
        "menu.about": "&About Writer",
        "menu.command_palette": "&Command Palette…",
        # ── Main window – toolbar / status bar ───────────────────────────────
        "toolbar.toggle_sidebar": "Toggle sidebar",
        "toolbar.language_switch": "中文",
        "toolbar.language_switch_tooltip": "Switch to Simplified Chinese (restart required)",
        # ── M9A: shell / navigation rail ─────────────────────────────────────
        "shell.brand": "Writer",
        "rail.fragments": "Fragments",
        "rail.works": "Works",
        "rail.collections": "Collections",
        "rail.search": "Search",
        "rail.theme": "Theme",
        "rail.settings": "Settings",
        "shell.toggle_context_pane": "Toggle context panel",
        # ── M9A: theme menu ──────────────────────────────────────────────────
        "theme.menu_title": "Theme",
        "theme.light": "Light",
        "theme.dark": "Dark",
        "theme.system": "Follow system",
        # ── M9A: column titles ───────────────────────────────────────────────
        "column.fragments": "Fragments",
        "column.works": "Works",
        "column.collections": "Collections",
        # ── M9A: context pane ────────────────────────────────────────────────
        "context.title_fragment": "Fragment",
        "context.title_work": "Work",
        "context.title_collection": "Collection",
        "context.empty_title": "The context panel lives here.",
        "context.empty_desc": (
            "Pick a fragment, work, or collection and you'll see word counts, "
            "status, exports, and other helpers here."
        ),
        "context.label_words": "Words",
        "context.label_chars": "Characters",
        "context.label_tags": "Tags",
        "context.label_created": "Created",
        "context.label_updated": "Updated",
        "context.label_status": "Status",
        "context.label_summary": "Summary",
        "context.label_target": "Target",
        "context.label_work_count": "Works in collection",
        "context.action_polish": "Polish…",
        "context.action_include": "Include in work…",
        "context.action_versions": "Versions…",
        "context.action_export_work": "Export…",
        "context.action_export_collection": "Export…",
        "context.no_value": "—",
        "context.no_target": "No target set",
        # ── M9A: empty states (welcome + per mode) ───────────────────────────
        "empty.welcome_title": "Start with a single line.",
        "empty.welcome_desc": (
            "Write a fragment, then assemble fragments into a work, then "
            "arrange works into a collection. Writer keeps all three in one "
            "workspace."
        ),
        "empty.welcome_primary": "New fragment",
        "empty.welcome_secondary": "New work",
        "empty.fragments_title": "This is where raw material lives.",
        "empty.fragments_desc": (
            "Ideas, sentences, paragraphs, scenes — capture them as fragments "
            "first. You can shape them into works later."
        ),
        "empty.fragments_primary": "New fragment",
        "empty.fragments_secondary": "Open global search",
        "empty.fragments_search_title": "No fragments matched.",
        "empty.fragments_search_desc": (
            "Try a different word, or search for a shorter snippet, title, "
            "or tag."
        ),
        "empty.fragments_search_primary": "Clear search",
        "empty.fragments_search_secondary": "Show all fragments",
        "empty.works_title": "No works yet.",
        "empty.works_desc": (
            "When you're ready to gather scattered fragments into a finished "
            "draft, this is where you start."
        ),
        "empty.works_primary": "New work",
        "empty.works_secondary": "Include current fragment in a work",
        "empty.work_unselected_title": "Pick a work, or start a new one.",
        "empty.work_unselected_desc": (
            "Works are for arranging chapters, restructuring, and saving "
            "snapshots."
        ),
        "empty.work_unselected_primary": "New work",
        "empty.work_unselected_secondary": "Show recent works",
        "empty.collections_title": "Collections haven't started yet.",
        "empty.collections_desc": (
            "A collection is for ordering works and exporting them as a "
            "set — short story collections, essay anthologies, themed bundles."
        ),
        "empty.collections_primary": "New collection",
        "empty.collections_secondary": "Go organise a work first",
        "empty.collection_unselected_title": "Pick a collection first.",
        "empty.collection_unselected_desc": (
            "Then you can reorder works inside it and prepare a single "
            "consolidated export."
        ),
        "empty.collection_unselected_primary": "New collection",
        "empty.collection_unselected_secondary": "View existing collections",
        # ── Dialogs / message boxes ───────────────────────────────────────────
        "dlg.nothing_to_rewrite": "Nothing to rewrite",
        "dlg.nothing_to_rewrite_msg": (
            "The fragment is empty. Write something first or select text."
        ),
        "dlg.working": "Working",
        "dlg.rewrite_cancel": "Cancel",
        "dlg.ai_failed": "AI request failed",
        "dlg.no_project": "No project",
        "dlg.no_project_msg": (
            "The current fragment isn't assigned to a project. "
            "Use File - Assign to Project first."
        ),
        "dlg.no_fragment_to_include_title": "No fragment to include",
        "dlg.no_fragment_to_include_msg": (
            "Open or create a fragment first, then come back and include "
            "it in a work."
        ),
        "dlg.chapter_not_assigned": "Chapter not assigned",
        "dlg.chapter_not_assigned_msg": "Could not attach the fragment to that chapter:\n",
        "dlg.export_failed": "Export failed",
        "dlg.export_save_title": "Export",
        "dlg.export_md_filter": "Markdown (*.md)",
        "dlg.export_txt_filter": "Text files (*.txt)",
        # ── About dialog ─────────────────────────────────────────────────────
        "about.title": "About Writer",
        "about.content": (
            "<b>Writer</b><br>"
            "Version {version}<br><br>"
            "A personal writing tool with lightweight AI rewrite assistance.<br><br>"
            "<i>Internal alpha — not a final release.</i>"
        ),
        # ── Settings dialog ───────────────────────────────────────────────────
        "settings.title": "Settings",
        "settings.tab_ai": "AI",
        "settings.tab_ui": "Appearance",
        "settings.base_url": "Base URL",
        "settings.model": "Model",
        "settings.wire_api": "Wire API",
        "settings.api_key_source": "API key source",
        "settings.import_codex": "Import from Codex config…",
        "settings.language_label": "Language",
        "settings.lang_en": "English",
        "settings.lang_zh_cn": "简体中文",
        "settings.restart_required_title": "Restart required",
        "settings.restart_required_msg": (
            "Language change will take effect after restarting the application."
        ),
        "settings.key_only_env": (
            "Use env:VAR or the literal string 'codex'. The API key is "
            "never stored on disk."
        ),
        "settings.key_enter_var": "Enter an environment variable name after env:.",
        "settings.key_set": "✓ {var} is set in the current environment.",
        "settings.key_not_set": "⚠ {var} is not set. Export it before invoking AI.",
        "settings.codex_auth_available": (
            "✓ Local Codex auth available at {path}."
        ),
        "settings.codex_auth_missing_file": (
            "⚠ No Codex auth file at {path}. Run Codex once or switch to env:VAR."
        ),
        "settings.codex_auth_missing_key": (
            "⚠ Codex auth file at {path} has no OPENAI_API_KEY field."
        ),
        "settings.codex_auth_unreadable": (
            "⚠ Codex auth file at {path} could not be read."
        ),
        "settings.nothing_imported": "Nothing imported",
        "settings.nothing_imported_msg": (
            "No supported fields (base_url / model / wire_api) were found."
        ),
        "settings.imported": "Imported",
        "settings.imported_msg": "Codex configuration imported. Click OK to save.",
        "settings.missing_model": "Missing model",
        "settings.missing_model_msg": "Please enter a model name.",
        "settings.invalid_setting": "Invalid setting",
        "settings.codex_select_title": "Select Codex config.toml",
        "settings.codex_import_failed": "Import failed",
        # ── Rewrite compare dialog ─────────────────────────────────────────────
        "compare.original_label": "Original",
        "compare.generated_label_base": "AI rewrite (editable before accepting)",
        "compare.notice": (
            "Accepting will replace the original text and record both the "
            "original and the AI version in the entry's history."
        ),
        "compare.accept_btn": "Accept",
        "compare.accept_selection_btn": "Accept Selection",
        "compare.accept_selection_tooltip": "Select text in the generated pane first",
        "compare.cancel_btn": "Cancel",
        # ── Command palette ────────────────────────────────────────────────────
        "cmd.placeholder": "Type to search actions…",
        "cmd.title": "Command Palette",
        "cmd.no_results": "No matching actions",
        "cmd.focus_search": "Focus fragment search",
        "cmd.switch_language": "Switch language",
        # ── Version History Dialog ─────────────────────────────────────────────
        "vhd.title": "Version History",
        "vhd.history_label": "History (newest first)",
        "vhd.current_body_label": "Current body",
        "vhd.no_version_selected": "(select a version to compare)",
        "vhd.no_version_selected_placeholder": "No version selected",
        "vhd.no_history": "No version history yet.",
        "vhd.restore_btn": "Restore Selected Version",
        "vhd.close_btn": "Close",
        "vhd.restore_confirm_title": "Restore version",
        "vhd.restore_confirm_msg": (
            "Replace the current body with this version?\n\n"
            "Your current body will be saved as a snapshot so you can "
            "restore it again later."
        ),
        "vhd.restore_failed": "Restore failed",
        "vhd.nothing_changed_title": "Nothing changed",
        "vhd.nothing_changed_msg": "The selected version is identical to the current body.",
        "vhd.restored_title": "Restored",
        "vhd.restored_msg": (
            "The version has been restored. Your previous body was saved "
            "as a snapshot."
        ),
        # ── Assign Fragment Dialog ─────────────────────────────────────────────
        "assign.title": "Assign fragment",
        "assign.no_project": "(no project)",
        "assign.no_chapter": "(no chapter)",
        "assign.project_label": "Project",
        "assign.chapter_label": "Chapter",
        "assign.untitled_chapter": "Untitled chapter",
        # ── Projects Dialog ────────────────────────────────────────────────────
        "projects.title": "Projects",
        # ── Reference Library Dialog ───────────────────────────────────────────
        "reflib.title": "Reference library",
        # ── Reference Picker Dialog ────────────────────────────────────────────
        "refpicker.title": "Attach references",
        "refpicker.hint": "Tick passages to include as tonal inspiration (optional).",
        "refpicker.search_placeholder": "Search references…",
        "refpicker.use_btn": "Use selected",
        "refpicker.skip_btn": "Skip references",
        "refpicker.cancel_btn": "Cancel",
        # ── Project Panel ──────────────────────────────────────────────────────
        "pp.projects_label": "Projects",
        "pp.sections_label": "Sections",
        "pp.entries_label": "Entries",
        "pp.new_btn": "New",
        "pp.rename_btn": "Rename",
        "pp.delete_btn": "Delete",
        "pp.unchaptered": "Unchaptered",
        "pp.untitled_chapter": "Untitled chapter",
        "pp.untitled_fragment": "Untitled fragment",
        "pp.description_label": "Description",
        "pp.description_placeholder": "Project description — shown in exported manuscripts.",
        "pp.save_desc_btn": "Save description",
        "pp.export_md_btn": "Export Markdown…",
        "pp.export_txt_btn": "Export Text…",
        "pp.move_to_unch_btn": "Unchaptered",
        "pp.move_to_chapter_btn": "Chapter…",
        "pp.remove_entry_btn": "Remove from project",
        "pp.new_project_title": "New project",
        "pp.new_project_prompt": "Project name:",
        "pp.rename_project_title": "Rename project",
        "pp.rename_project_prompt": "Project name:",
        "pp.delete_project_title": "Delete project",
        "pp.delete_project_msg": "Delete project '{name}' and all its chapters? Fragments will be detached but kept.",
        "pp.new_chapter_title": "New chapter",
        "pp.new_chapter_prompt": "Chapter title:",
        "pp.rename_chapter_title": "Rename chapter",
        "pp.rename_chapter_prompt": "Chapter title:",
        "pp.delete_chapter_title": "Delete chapter",
        "pp.delete_chapter_msg": "Delete chapter '{title}'? Its fragments will remain in the project as unchaptered.",
        "pp.no_chapters_title": "No chapters",
        "pp.no_chapters_msg": "This project has no chapters yet. Create one first.",
        "pp.move_to_chapter_title": "Move to chapter",
        "pp.move_to_chapter_prompt": "Chapter:",
        "pp.move_failed": "Move failed",
        "pp.remove_entry_title": "Remove from project",
        "pp.remove_entry_msg": (
            "Detach this fragment from the project? The fragment itself is "
            "kept and stays editable from the main window."
        ),
        "pp.no_project_export": "No project",
        "pp.no_project_export_msg": "Select a project to export.",
        "pp.export_project_title": "Export project",
        "pp.export_failed": "Export failed",
        # ── Reference Library Panel ────────────────────────────────────────────
        "rlp.search_placeholder": "Search references…",
        "rlp.new_btn": "New",
        "rlp.delete_btn": "Delete",
        "rlp.save_btn": "Save",
        "rlp.source_title_label": "Source title *",
        "rlp.author_label": "Author",
        "rlp.tags_label": "Tags (free text)",
        "rlp.content_label": "Passage content *",
        "rlp.missing_title": "Missing title",
        "rlp.missing_title_msg": "Source title is required.",
        "rlp.missing_content": "Missing content",
        "rlp.missing_content_msg": "Passage content is required.",
        "rlp.invalid_ref": "Invalid reference",
        "rlp.not_found": "Not found",
        "rlp.not_found_msg": "Reference no longer exists.",
        "rlp.confirm_delete_title": "Delete reference",
        "rlp.confirm_delete_msg": "Delete this reference passage?",
        # ── Fragment list panel (additional) ───────────────────────────────────
        "list.new_button_tooltip": "Create a new blank fragment (Ctrl+N)",
        # ── Main window (additional) ───────────────────────────────────────────
        "dlg.rewrite_progress": "Asking the model to {action} the text…",
        "dlg.review_title": "Review AI {action}",
        "action.polish": "Polish",
        "action.expand": "Expand",
        "action.continue": "Continue",
        # ── AI preflight / config guidance (M7B) ───────────────────────────────
        "dlg.ai_not_ready": "AI is not ready",
        "settings.test_btn": "Test AI configuration",
        "settings.test_ok_title": "AI configuration looks good",
        "settings.test_ok_msg": (
            "All required fields are set and the environment variable "
            "holding the API key is present.\n\n"
            "This does not send a network request — it only validates the "
            "local configuration."
        ),
        "settings.test_fail_title": "AI configuration has issues",
        "settings.codex_imported_title": "Codex config imported",
        "settings.codex_imported_body": (
            "Imported only: endpoint (base_url), model, wire protocol.\n\n"
            "The API key was NOT imported. The app never stores API keys on "
            "disk. Set an environment variable (for example OPENAI_API_KEY) "
            "and make sure 'API key source' reads env:OPENAI_API_KEY."
        ),
        "settings.codex_imported_body_with_auth": (
            "Imported endpoint (base_url), model, and wire protocol.\n\n"
            "The imported config requires OpenAI auth, and a local Codex "
            "auth file was found — 'API key source' has been set to 'codex' "
            "automatically. The key is read from ~/.codex/auth.json at "
            "request time and never stored by this app."
        ),
        # ── Fragment delete / batch (M7B) ──────────────────────────────────────
        "list.delete_btn": "Delete",
        "list.delete_tooltip": "Delete selected fragment(s)",
        "list.archive_btn": "Archive",
        "list.unarchive_btn": "Unarchive",
        "list.sort_label": "Sort:",
        "list.sort_updated": "Recently updated",
        "list.sort_created": "Recently created",
        "list.sort_title": "Title (A–Z)",
        "list.show_archived": "Show archived",
        "list.archived_badge": " [archived]",
        "dlg.confirm_delete_title": "Delete fragment",
        "dlg.confirm_delete_one": (
            "Delete this fragment permanently?\n\nTitle: {title}\n\n"
            "You can recover the most recent deletion via File → "
            "Recover last deleted fragment."
        ),
        "dlg.confirm_delete_many": (
            "Delete {count} fragments permanently?\n\nThis cannot be "
            "undone from the list, but the most recent deletion is "
            "recoverable via File → Recover last deleted fragment."
        ),
        # ── Save / recovery (M7B) ──────────────────────────────────────────────
        "menu.save": "&Save",
        "menu.recover_last_deleted": "Recover last deleted fragment",
        "status.saved": "All changes saved",
        "status.saving": "Saving…",
        "status.unsaved": "Unsaved changes",
        "status.no_entry": "",
        "dlg.nothing_to_recover_title": "Nothing to recover",
        "dlg.nothing_to_recover_msg": (
            "No recently deleted fragment is available for recovery."
        ),
        "dlg.recovered_title": "Recovered",
        "dlg.recovered_msg": "The deleted fragment has been restored.",
        # ── Word count (M7B) ───────────────────────────────────────────────────
        "editor.word_count": "{words} words · {chars} chars",
        "editor.word_count_with_sel": (
            "{words} words · {chars} chars  (selection: {sel_words} / {sel_chars})"
        ),
        # ── M8: works / sections / collections / include / global search ─────
        "menu.include_fragment": "&Include Fragment into Work…",
        "menu.global_search": "&Global Search…",
        "toolbar.mode_fragments": "Fragments",
        "toolbar.mode_works": "Works",
        "toolbar.mode_collections": "Collections",
        "toolbar.global_search": "Search",
        "cmd.global_search": "Global search…",
        "cmd.include_fragment": "Include fragment into work…",
        "works.new": "New work",
        "works.delete": "Delete",
        "works.delete_confirm": "Delete this work and all its sections? This cannot be undone.",
        "works.show_archived": "Show archived",
        "works.untitled": "(untitled work)",
        "works.archive": "Archive",
        "works.unarchive": "Unarchive",
        "works.archived_badge": "archived",
        "works.export": "Export work\u2026",
        "works.export_done": "Exported to {path}",
        "work.title": "Title",
        "work.title_placeholder": "Work title",
        "work.summary": "Summary",
        "work.summary_placeholder": "One-line summary (optional)",
        "work.tags": "Tags",
        "work.tags_placeholder": "comma-separated",
        "work.status": "Status",
        "work.status.idea": "Idea",
        "work.status.draft": "Draft",
        "work.status.revising": "Revising",
        "work.status.final": "Final",
        "work.status.archived": "Archived",
        "work.target_wc": "Target",
        "work.no_target": "—",
        "work.add_body": "Add body",
        "work.add_heading": "Add heading",
        "work.toggle_type": "Toggle type",
        "work.delete_section": "Delete section",
        "work.body_placeholder": "Section content…",
        "work.untitled_heading": "(untitled heading)",
        "work.empty_body": "(empty body)",
        "work.save_snapshot": "Save snapshot",
        "work.versions": "Versions…",
        "work.snapshot_saved": "Snapshot saved",
        "work.snapshot_saved_msg": "A manual version snapshot was saved.",
        "work.word_count": "Words: {words}",
        "work.word_count_with_target": "Words: {words} / {target}",
        "work_versions.title": "Version history",
        "work_versions.restore": "Restore selected",
        "work_versions.restore_confirm": "Replace current work with this version? A pre-restore snapshot will be saved automatically.",
        "collections.label": "Collections",
        "collections.works_label": "Works in collection",
        "collections.new": "New",
        "collections.rename": "Rename",
        "collections.delete": "Delete",
        "collections.delete_confirm": "Delete this collection? Works inside will not be deleted.",
        "collections.new_name_prompt": "Collection name:",
        "collections.untitled": "(untitled collection)",
        "collections.add_work": "Add work…",
        "collections.remove_work": "Remove",
        "collections.export": "Export…",
        "collections.export_done": "Exported to {path}",
        "include.title": "Include fragment into work",
        "include.work": "Work",
        "include.section": "Section",
        "include.text": "Text to insert (edit before confirming):",
        "include.preview_label": "Click in the section preview to choose the insertion point:",
        "include.preview_placeholder": "(no section content)",
        "include.position_at": "Insertion point: {pos} / {total}",
        "include.position_new_section": "Will be appended as a new section.",
        "include.confirm": "Insert",
        "include.new_section": "(append as new section)",
        "include.no_works": "No works yet — create one in the Works tab first.",
        "include.empty_text": "Text cannot be empty.",
        "include.success_msg": "Fragment included. Curation status set to 'included'.",
        "search.title": "Global search",
        "search.placeholder": "Search fragments and works…",
        "search.open": "Open",
        "search.kind_fragment": "Fragment",
        "search.kind_work": "Work",
        "search.untitled": "(untitled)",
        "work_picker.title": "Choose a work",
        "work_picker.search_placeholder": "Filter by title or summary…",
        "export.filter_all": "All supported (*.txt *.md *.docx);;Text (*.txt);;Markdown (*.md);;Word (*.docx)",
    },

    "zh_CN": {
        # ── Fragment list panel ──────────────────────────────────────────────
        "list.search_placeholder": "搜索片段…",
        "list.new_button": "新建",
        "list.all_tags": "所有标签",
        "list.empty_fragment": "（空片段）",
        "list.empty_state": "暂无片段。\n点击「新建」开始写作。",
        "list.empty_search": "未找到相关结果。",
        # ── Editor panel ─────────────────────────────────────────────────────
        "editor.title_placeholder": "标题（可选）",
        "editor.tags_placeholder": "标签（逗号分隔）",
        "editor.body_placeholder": "开始写作…",
        "editor.meta_created": "创建于",
        "editor.meta_updated": "更新于",
        # ── Main window – menus ───────────────────────────────────────────────
        "menu.file": "文件(&F)",
        "menu.new_fragment": "新建片段(&N)",
        "menu.assign_to_project": "分配到项目(&A)…",
        "menu.projects": "项目管理(&P)…",
        "menu.version_history": "版本历史(&H)…",
        "menu.export": "导出(&E)",
        "menu.export_fragment_md": "当前片段导出为 Markdown(&M)…",
        "menu.export_fragment_txt": "当前片段导出为纯文本(&T)…",
        "menu.export_project_md": "当前项目导出为 Markdown(&R)…",
        "menu.export_project_txt": "当前项目导出为纯文本…",
        "menu.quit": "退出(&Q)",
        "menu.ai": "AI(&A)",
        "menu.polish": "润色(&P)",
        "menu.expand": "扩写(&E)",
        "menu.continue": "续写(&C)",
        "menu.references": "参考库(&R)…",
        "menu.settings": "设置(&S)…",
        "menu.help": "帮助(&H)",
        "menu.about": "关于 Writer(&A)",
        "menu.command_palette": "命令面板(&P)…",
        # ── Toolbar ────────────────────────────────────────────────────────────
        "toolbar.toggle_sidebar": "切换侧栏",
        "toolbar.language_switch": "EN",
        "toolbar.language_switch_tooltip": "切换到英文（重启后生效）",
        # ── M9A：壳层 / 导航栏 ───────────────────────────────────────────────
        "shell.brand": "Writer",
        "rail.fragments": "片段",
        "rail.works": "作品",
        "rail.collections": "作品集",
        "rail.search": "搜索",
        "rail.theme": "主题",
        "rail.settings": "设置",
        "shell.toggle_context_pane": "显示/隐藏上下文栏",
        # ── M9A：主题菜单 ────────────────────────────────────────────────────
        "theme.menu_title": "主题",
        "theme.light": "浅色",
        "theme.dark": "深色",
        "theme.system": "跟随系统",
        # ── M9A：列标题 ──────────────────────────────────────────────────────
        "column.fragments": "片段",
        "column.works": "作品",
        "column.collections": "作品集",
        # ── M9A：上下文栏 ────────────────────────────────────────────────────
        "context.title_fragment": "片段",
        "context.title_work": "作品",
        "context.title_collection": "作品集",
        "context.empty_title": "这里会显示上下文。",
        "context.empty_desc": "选中片段、作品或作品集后，你会在这里看到字数、状态、导出和其他辅助信息。",
        "context.label_words": "字数",
        "context.label_chars": "字符数",
        "context.label_tags": "标签",
        "context.label_created": "创建",
        "context.label_updated": "更新",
        "context.label_status": "状态",
        "context.label_summary": "摘要",
        "context.label_target": "目标字数",
        "context.label_work_count": "作品数量",
        "context.action_polish": "润色…",
        "context.action_include": "收入作品…",
        "context.action_versions": "版本…",
        "context.action_export_work": "导出…",
        "context.action_export_collection": "导出…",
        "context.no_value": "—",
        "context.no_target": "未设置目标字数",
        # ── M9A：空状态 ──────────────────────────────────────────────────────
        "empty.welcome_title": "从一句话开始。",
        "empty.welcome_desc": "先写片段，再整理成作品，最后编成作品集。Writer 把这三步放在同一个工作台里。",
        "empty.welcome_primary": "新建片段",
        "empty.welcome_secondary": "新建作品",
        "empty.fragments_title": "这里先放素材。",
        "empty.fragments_desc": "灵感、句子、段落、场景，都可以先记成片段。以后再慢慢整理成作品。",
        "empty.fragments_primary": "新建片段",
        "empty.fragments_secondary": "打开全局搜索",
        "empty.fragments_search_title": "没找到相关片段。",
        "empty.fragments_search_desc": "换个词试试，或者搜索更短的片段、标题和标签。",
        "empty.fragments_search_primary": "清空搜索",
        "empty.fragments_search_secondary": "查看全部片段",
        "empty.works_title": "还没有作品。",
        "empty.works_desc": "当你准备把零散片段整理成完整稿件，就从这里开始。",
        "empty.works_primary": "新建作品",
        "empty.works_secondary": "从当前片段收入作品",
        "empty.work_unselected_title": "选一个作品，或者新建一个。",
        "empty.work_unselected_desc": "作品适合整理章节、调整结构、保存版本。",
        "empty.work_unselected_primary": "新建作品",
        "empty.work_unselected_secondary": "显示最近作品",
        "empty.collections_title": "作品集还没开始。",
        "empty.collections_desc": "作品集用来编排顺序、准备导出，适合小说集、散文集和专题合集。",
        "empty.collections_primary": "新建作品集",
        "empty.collections_secondary": "先去整理作品",
        "empty.collection_unselected_title": "先选一个作品集。",
        "empty.collection_unselected_desc": "然后你可以调整作品顺序，准备整组导出。",
        "empty.collection_unselected_primary": "新建作品集",
        "empty.collection_unselected_secondary": "查看已有作品集",
        # ── Dialogs / message boxes ───────────────────────────────────────────
        "dlg.nothing_to_rewrite": "没有可改写的内容",
        "dlg.nothing_to_rewrite_msg": "片段为空，请先写入内容或选中文本。",
        "dlg.working": "处理中",
        "dlg.rewrite_cancel": "取消",
        "dlg.ai_failed": "AI 请求失败",
        "dlg.no_project": "未关联项目",
        "dlg.no_project_msg": "当前片段未分配到任何项目。请先使用「文件 - 分配到项目」。",
        "dlg.no_fragment_to_include_title": "暂时还没有可收入的片段",
        "dlg.no_fragment_to_include_msg": (
            "先打开或新建一个片段，再回来把它收入作品。"
        ),
        "dlg.chapter_not_assigned": "章节未分配",
        "dlg.chapter_not_assigned_msg": "无法将片段附加到该章节：\n",
        "dlg.export_failed": "导出失败",
        "dlg.export_save_title": "导出",
        "dlg.export_md_filter": "Markdown (*.md)",
        "dlg.export_txt_filter": "文本文件 (*.txt)",
        # ── About dialog ─────────────────────────────────────────────────────
        "about.title": "关于 Writer",
        "about.content": (
            "<b>Writer</b><br>"
            "版本 {version}<br><br>"
            "专注写作的个人写作工具，内置轻量 AI 改写辅助。<br><br>"
            "<i>内部 Alpha 版本 — 非最终发布版。</i>"
        ),
        # ── Settings dialog ───────────────────────────────────────────────────
        "settings.title": "设置",
        "settings.tab_ai": "AI",
        "settings.tab_ui": "外观",
        "settings.base_url": "Base URL",
        "settings.model": "模型",
        "settings.wire_api": "接口协议",
        "settings.api_key_source": "API 密钥来源",
        "settings.import_codex": "从 Codex 配置导入…",
        "settings.language_label": "语言",
        "settings.lang_en": "English",
        "settings.lang_zh_cn": "简体中文",
        "settings.restart_required_title": "需要重启",
        "settings.restart_required_msg": "语言设置将在重启应用后生效。",
        "settings.key_only_env": "支持 env:VAR 或字面量 'codex'。API 密钥不会存储在磁盘上。",
        "settings.key_enter_var": "请在 env: 后输入环境变量名称。",
        "settings.key_set": "✓ {var} 已在当前环境中设置。",
        "settings.key_not_set": "⚠ {var} 未设置。请在调用 AI 前先导出该变量。",
        "settings.codex_auth_available": "✓ 已找到本地 Codex 认证：{path}。",
        "settings.codex_auth_missing_file": "⚠ 未找到 Codex 认证文件：{path}。请先运行一次 Codex，或改用 env:VAR。",
        "settings.codex_auth_missing_key": "⚠ Codex 认证文件 {path} 中未包含 OPENAI_API_KEY 字段。",
        "settings.codex_auth_unreadable": "⚠ 无法读取 Codex 认证文件：{path}。",
        "settings.nothing_imported": "未导入任何内容",
        "settings.nothing_imported_msg": "未找到支持的字段（base_url / model / wire_api）。",
        "settings.imported": "导入成功",
        "settings.imported_msg": "已导入 Codex 配置，点击确定保存。",
        "settings.missing_model": "缺少模型名称",
        "settings.missing_model_msg": "请输入模型名称。",
        "settings.invalid_setting": "设置无效",
        "settings.codex_select_title": "选择 Codex config.toml",
        "settings.codex_import_failed": "导入失败",
        # ── Rewrite compare dialog ─────────────────────────────────────────────
        "compare.original_label": "原文",
        "compare.generated_label_base": "AI 改写结果（接受前可编辑）",
        "compare.notice": "接受后，当前文本将被替换，原文和 AI 版本均会记录在片段历史中。",
        "compare.accept_btn": "接受",
        "compare.accept_selection_btn": "接受所选",
        "compare.accept_selection_tooltip": "请先在生成结果中选择文本",
        "compare.cancel_btn": "取消",
        # ── Command palette ────────────────────────────────────────────────────
        "cmd.placeholder": "输入以搜索命令…",
        "cmd.title": "命令面板",
        "cmd.no_results": "未找到匹配命令",
        "cmd.focus_search": "聚焦搜索框",
        "cmd.switch_language": "切换语言",
        # ── Version History Dialog ─────────────────────────────────────────────
        "vhd.title": "版本历史",
        "vhd.history_label": "历史记录（最新在前）",
        "vhd.current_body_label": "当前正文",
        "vhd.no_version_selected": "（选择一个版本进行对比）",
        "vhd.no_version_selected_placeholder": "未选择版本",
        "vhd.no_history": "暂无版本历史。",
        "vhd.restore_btn": "还原所选版本",
        "vhd.close_btn": "关闭",
        "vhd.restore_confirm_title": "还原版本",
        "vhd.restore_confirm_msg": (
            "用此版本替换当前正文？\n\n"
            "当前正文将被保存为快照，以便日后还原。"
        ),
        "vhd.restore_failed": "还原失败",
        "vhd.nothing_changed_title": "无变化",
        "vhd.nothing_changed_msg": "所选版本与当前正文完全相同。",
        "vhd.restored_title": "已还原",
        "vhd.restored_msg": "版本已还原，原正文已保存为快照。",
        # ── Assign Fragment Dialog ─────────────────────────────────────────────
        "assign.title": "分配片段",
        "assign.no_project": "（无项目）",
        "assign.no_chapter": "（无章节）",
        "assign.project_label": "项目",
        "assign.chapter_label": "章节",
        "assign.untitled_chapter": "未命名章节",
        # ── Projects Dialog ────────────────────────────────────────────────────
        "projects.title": "项目管理",
        # ── Reference Library Dialog ───────────────────────────────────────────
        "reflib.title": "参考库",
        # ── Reference Picker Dialog ────────────────────────────────────────────
        "refpicker.title": "附加参考文献",
        "refpicker.hint": "勾选要作为风格参考的段落（可选）。",
        "refpicker.search_placeholder": "搜索参考文献…",
        "refpicker.use_btn": "使用所选",
        "refpicker.skip_btn": "跳过参考文献",
        "refpicker.cancel_btn": "取消",
        # ── Project Panel ──────────────────────────────────────────────────────
        "pp.projects_label": "项目",
        "pp.sections_label": "章节",
        "pp.entries_label": "片段",
        "pp.new_btn": "新建",
        "pp.rename_btn": "重命名",
        "pp.delete_btn": "删除",
        "pp.unchaptered": "未分章",
        "pp.untitled_chapter": "未命名章节",
        "pp.untitled_fragment": "未命名片段",
        "pp.description_label": "简介",
        "pp.description_placeholder": "项目简介 — 将显示在导出的文稿中。",
        "pp.save_desc_btn": "保存简介",
        "pp.export_md_btn": "导出 Markdown…",
        "pp.export_txt_btn": "导出纯文本…",
        "pp.move_to_unch_btn": "移至未分章",
        "pp.move_to_chapter_btn": "移至章节…",
        "pp.remove_entry_btn": "从项目中移除",
        "pp.new_project_title": "新建项目",
        "pp.new_project_prompt": "项目名称：",
        "pp.rename_project_title": "重命名项目",
        "pp.rename_project_prompt": "项目名称：",
        "pp.delete_project_title": "删除项目",
        "pp.delete_project_msg": "删除项目\"{name}\"及其所有章节？片段将被解绑，但不会被删除。",
        "pp.new_chapter_title": "新建章节",
        "pp.new_chapter_prompt": "章节标题：",
        "pp.rename_chapter_title": "重命名章节",
        "pp.rename_chapter_prompt": "章节标题：",
        "pp.delete_chapter_title": "删除章节",
        "pp.delete_chapter_msg": "删除章节\"{title}\"？其中的片段将保留在项目的未分章区域。",
        "pp.no_chapters_title": "暂无章节",
        "pp.no_chapters_msg": "该项目还没有章节，请先创建一个。",
        "pp.move_to_chapter_title": "移至章节",
        "pp.move_to_chapter_prompt": "章节：",
        "pp.move_failed": "移动失败",
        "pp.remove_entry_title": "从项目中移除",
        "pp.remove_entry_msg": "将此片段从项目中解绑？片段本身不会被删除，仍可在主窗口中编辑。",
        "pp.no_project_export": "未选择项目",
        "pp.no_project_export_msg": "请先选择一个项目再导出。",
        "pp.export_project_title": "导出项目",
        "pp.export_failed": "导出失败",
        # ── Reference Library Panel ────────────────────────────────────────────
        "rlp.search_placeholder": "搜索参考文献…",
        "rlp.new_btn": "新建",
        "rlp.delete_btn": "删除",
        "rlp.save_btn": "保存",
        "rlp.source_title_label": "来源标题 *",
        "rlp.author_label": "作者",
        "rlp.tags_label": "标签（自由文本）",
        "rlp.content_label": "段落内容 *",
        "rlp.missing_title": "缺少标题",
        "rlp.missing_title_msg": "来源标题为必填项。",
        "rlp.missing_content": "缺少内容",
        "rlp.missing_content_msg": "段落内容为必填项。",
        "rlp.invalid_ref": "参考文献无效",
        "rlp.not_found": "未找到",
        "rlp.not_found_msg": "该参考文献已不存在。",
        "rlp.confirm_delete_title": "删除参考文献",
        "rlp.confirm_delete_msg": "确定删除此参考段落吗？",
        # ── Fragment list panel (additional) ───────────────────────────────────
        "list.new_button_tooltip": "新建空片段（Ctrl+N）",
        # ── Main window (additional) ───────────────────────────────────────────
        "dlg.rewrite_progress": "正在请求模型对文本执行\"{action}\"操作…",
        "dlg.review_title": "AI 审阅：{action}",
        "action.polish": "润色",
        "action.expand": "扩写",
        "action.continue": "续写",
        # ── AI preflight / config guidance (M7B) ───────────────────────────────
        "dlg.ai_not_ready": "AI 尚未就绪",
        "settings.test_btn": "测试 AI 配置",
        "settings.test_ok_title": "AI 配置看起来没问题",
        "settings.test_ok_msg": (
            "所需字段已填写，密钥环境变量也已设置。\n\n"
            "本测试仅校验本地配置，不会发起网络请求。"
        ),
        "settings.test_fail_title": "AI 配置存在问题",
        "settings.codex_imported_title": "已导入 Codex 配置",
        "settings.codex_imported_body": (
            "仅导入：endpoint（base_url）、model、接口协议（wire_api）。\n\n"
            "API 密钥未被导入。本应用永不在磁盘上存储 API 密钥。"
            "请设置环境变量（例如 OPENAI_API_KEY），并确保「API 密钥来源」"
            "为 env:OPENAI_API_KEY。"
        ),
        "settings.codex_imported_body_with_auth": (
            "已导入 endpoint（base_url）、model、接口协议（wire_api）。\n\n"
            "导入的配置要求 OpenAI 认证，且检测到本地 Codex 认证文件——"
            "「API 密钥来源」已自动设为 'codex'。密钥将在请求时从 "
            "~/.codex/auth.json 读取，本应用不会持久化该值。"
        ),
        # ── Fragment delete / batch (M7B) ──────────────────────────────────────
        "list.delete_btn": "删除",
        "list.delete_tooltip": "删除所选片段",
        "list.archive_btn": "归档",
        "list.unarchive_btn": "取消归档",
        "list.sort_label": "排序：",
        "list.sort_updated": "最近更新",
        "list.sort_created": "最近创建",
        "list.sort_title": "标题（A–Z）",
        "list.show_archived": "显示归档",
        "list.archived_badge": "［已归档］",
        "dlg.confirm_delete_title": "删除片段",
        "dlg.confirm_delete_one": (
            "要永久删除此片段吗？\n\n标题：{title}\n\n"
            "可通过「文件 → 恢复最近删除的片段」找回最近一次的删除。"
        ),
        "dlg.confirm_delete_many": (
            "要永久删除所选的 {count} 个片段吗？\n\n"
            "此操作无法从列表直接撤销，但最近一次删除可通过"
            "「文件 → 恢复最近删除的片段」找回。"
        ),
        # ── Save / recovery (M7B) ──────────────────────────────────────────────
        "menu.save": "保存(&S)",
        "menu.recover_last_deleted": "恢复最近删除的片段",
        "status.saved": "所有更改已保存",
        "status.saving": "保存中…",
        "status.unsaved": "有未保存的更改",
        "status.no_entry": "",
        "dlg.nothing_to_recover_title": "没有可恢复的片段",
        "dlg.nothing_to_recover_msg": "当前没有最近被删除的片段可供恢复。",
        "dlg.recovered_title": "已恢复",
        "dlg.recovered_msg": "已删除的片段已被恢复。",
        # ── Word count (M7B) ───────────────────────────────────────────────────
        "editor.word_count": "{words} 字 · {chars} 字符",
        "editor.word_count_with_sel": (
            "{words} 字 · {chars} 字符  （选中：{sel_words} / {sel_chars}）"
        ),
        # ── M8: 作品 / 节块 / 作品集 / 纳入 / 全局搜索 ───────────────────────
        "menu.include_fragment": "将片段纳入作品(&I)…",
        "menu.global_search": "全局搜索(&G)…",
        "toolbar.mode_fragments": "片段",
        "toolbar.mode_works": "作品",
        "toolbar.mode_collections": "作品集",
        "toolbar.global_search": "搜索",
        "cmd.global_search": "全局搜索…",
        "cmd.include_fragment": "将片段纳入作品…",
        "works.new": "新建作品",
        "works.delete": "删除",
        "works.delete_confirm": "确定删除此作品及其所有节块？此操作无法撤销。",
        "works.show_archived": "显示已归档",
        "works.untitled": "（未命名作品）",
        "works.archive": "归档",
        "works.unarchive": "取消归档",
        "works.archived_badge": "已归档",
        "works.export": "导出作品…",
        "works.export_done": "已导出到 {path}",
        "work.title": "标题",
        "work.title_placeholder": "作品标题",
        "work.summary": "摘要",
        "work.summary_placeholder": "一句话摘要（可选）",
        "work.tags": "标签",
        "work.tags_placeholder": "逗号分隔",
        "work.status": "状态",
        "work.status.idea": "构思中",
        "work.status.draft": "草稿",
        "work.status.revising": "修改中",
        "work.status.final": "定稿",
        "work.status.archived": "已归档",
        "work.target_wc": "目标字数",
        "work.no_target": "—",
        "work.add_body": "新增正文",
        "work.add_heading": "新增小标题",
        "work.toggle_type": "切换类型",
        "work.delete_section": "删除节块",
        "work.body_placeholder": "节块内容…",
        "work.untitled_heading": "（未命名小标题）",
        "work.empty_body": "（空正文）",
        "work.save_snapshot": "保存快照",
        "work.versions": "版本历史…",
        "work.snapshot_saved": "已保存快照",
        "work.snapshot_saved_msg": "已保存一个手动版本快照。",
        "work.word_count": "字数：{words}",
        "work.word_count_with_target": "字数：{words} / {target}",
        "work_versions.title": "版本历史",
        "work_versions.restore": "恢复所选版本",
        "work_versions.restore_confirm": "用此版本替换当前作品？将自动保存一份恢复前的快照。",
        "collections.label": "作品集",
        "collections.works_label": "集中作品",
        "collections.new": "新建",
        "collections.rename": "重命名",
        "collections.delete": "删除",
        "collections.delete_confirm": "删除此作品集？其中的作品不会被删除。",
        "collections.new_name_prompt": "作品集名称：",
        "collections.untitled": "（未命名作品集）",
        "collections.add_work": "添加作品…",
        "collections.remove_work": "移除",
        "collections.export": "导出…",
        "collections.export_done": "已导出到 {path}",
        "include.title": "将片段纳入作品",
        "include.work": "目标作品",
        "include.section": "目标节块",
        "include.text": "要插入的文本（确认前可编辑）：",
        "include.preview_label": "点击下方节块预览选择插入位置：",
        "include.preview_placeholder": "（节块内容为空）",
        "include.position_at": "插入位置：{pos} / {total}",
        "include.position_new_section": "将追加为新节块。",
        "include.confirm": "插入",
        "include.new_section": "（追加为新节块）",
        "include.no_works": "暂无作品 — 请先在「作品」标签页创建一个。",
        "include.empty_text": "文本不能为空。",
        "include.success_msg": "片段已纳入作品；整理状态自动改为「已纳入」。",
        "search.title": "全局搜索",
        "search.placeholder": "搜索片段和作品…",
        "search.open": "打开",
        "search.kind_fragment": "片段",
        "search.kind_work": "作品",
        "search.untitled": "（未命名）",
        "work_picker.title": "选择作品",
        "work_picker.search_placeholder": "按标题或摘要过滤…",
        "export.filter_all": "全部支持 (*.txt *.md *.docx);;纯文本 (*.txt);;Markdown (*.md);;Word (*.docx)",
    },
}


def TR(key: str) -> str:  # noqa: N802 — intentionally uppercase to match Qt convention
    """Return the translated string for *key* in the current locale.

    Falls back to English if the key or locale is missing.
    """
    locale = current_locale()
    locale_strings = _CATALOG.get(locale, _CATALOG["en"])
    return locale_strings.get(key, _CATALOG["en"].get(key, key))


def rewrite_action_label(action) -> str:
    """Return the localized display name for a RewriteAction enum value."""
    _KEY_MAP = {
        "polish": "action.polish",
        "expand": "action.expand",
        "continue": "action.continue",
    }
    key = _KEY_MAP.get(action.value, action.value)
    return TR(key)
