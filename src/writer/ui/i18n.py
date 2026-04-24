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
            "Only env:VAR is supported. The API key is never stored on disk."
        ),
        "settings.key_enter_var": "Enter an environment variable name after env:.",
        "settings.key_set": "✓ {var} is set in the current environment.",
        "settings.key_not_set": "⚠ {var} is not set. Export it before invoking AI.",
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
        # ── Dialogs / message boxes ───────────────────────────────────────────
        "dlg.nothing_to_rewrite": "没有可改写的内容",
        "dlg.nothing_to_rewrite_msg": "片段为空，请先写入内容或选中文本。",
        "dlg.working": "处理中",
        "dlg.rewrite_cancel": "取消",
        "dlg.ai_failed": "AI 请求失败",
        "dlg.no_project": "未关联项目",
        "dlg.no_project_msg": "当前片段未分配到任何项目。请先使用「文件 - 分配到项目」。",
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
        "settings.key_only_env": "仅支持 env:VAR 格式。API 密钥不会存储在磁盘上。",
        "settings.key_enter_var": "请在 env: 后输入环境变量名称。",
        "settings.key_set": "✓ {var} 已在当前环境中设置。",
        "settings.key_not_set": "⚠ {var} 未设置。请在调用 AI 前先导出该变量。",
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
