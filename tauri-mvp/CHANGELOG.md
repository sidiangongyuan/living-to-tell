# Living to Tell Tauri Preview Changelog

## 0.1.8 - Layout And AI Card Quality Update (2026-06-25)

### Added

- Added reusable resizable pane controls for dense windowed layouts.
- Added persistent pane widths for Articles, AI Workspace, AI Cards, Reference Library, Collections, and Motif Star Map surfaces.
- Added a shared right-click context menu for destructive actions that already had a visible delete button.
- Added right-click delete entry points for articles, article notes, AI cards, AI task presets, reference passages, collections, collection articles, motifs, motif excerpts, backups, and checkpoints.
- Added persisted AI Card tags with a database migration for existing local databases.

### Changed

- Improved windowed-mode behavior so side panes can be adjusted instead of forcing fixed widths that can obstruct content.
- Tightened context menu styling for a calmer desktop-tool feel.
- Removed public AI Card sample restore controls.
- Stopped AI Card list/search requests from automatically re-seeding built-in sample cards.
- Deprecated the old AI Card preset generation endpoint; it now returns a clear `410` response instead of recreating samples.

### Fixed

- Fixed AI Card tags disappearing after save by storing them in `ai_cards.tags_text`.
- Fixed AI Card tag search so saved tags participate in card search.
- Fixed the product behavior where built-in AI Card samples could reappear after users deleted them.
- Fixed rigid windowed layouts across the main writing and knowledge-management surfaces.

### Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

### Release artifacts

- `LivingToTell_0.1.8_x64-setup.exe`
  - SHA256: `2DB5EC63E7FE936F58E1ECC4586D03D173F5A74E83E470B34B8FF027103EE102`
- `LivingToTell_0.1.8_x64_zh-CN.msi`
  - SHA256: `E9387AE7A42CD0A1AB1F9427BD794D1CAAE7250E1892EB4388DA791A60671578`

## 0.1.7 - Living to Tell Major Preview (2026-06-20)

### Added

- Added the public brand **Living to Tell / 活着为了讲述**.
- Added copy-only migration from the old Writer data directory to `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`.
- Added safe demo-data screenshot capture so public screenshots do not include private writing, account paths, or local credential files.
- Added migration tests for the new app data path.
- Added Data and Storage settings that show the current data directory, SQLite database, backup folder, checkpoint folder, and custom-directory status.
- Added copy-based data-directory migration so users can switch storage locations without deleting the old folder.
- Added a light Tauri startup splash window so cold starts show progress instead of a blank window.
- Added article-scoped AI chat with standing instructions, copy actions, and save-reply-as-article-note actions.
- Added fixed-template AI Cards for style, character, and scene cards.
- Added AI-assisted card draft generation with preview-before-save behavior.
- Added manual scene-module search and attachment in the AI workspace.
- Added a real AI provider test request in Settings, separate from the local credential/configuration check.
- Added OpenCode local-auth support through the local `opencode auth login` session.
- Added live OpenCode model fetching in Settings. Current OpenCode models include `opencode/big-pickle`, `opencode/deepseek-v4-flash-free`, `opencode/mimo-v2.5-free`, `opencode/nemotron-3-ultra-free`, and `opencode/north-mini-code-free`.
- Added first-run welcome checklist entries for creating articles, saving references, configuring AI, opening article chat, and reading data/backup notes.
- Added the Motif Star Map for saving selected article/reference text into motifs, exploring co-occurrence, and jumping back to source anchors.
- Added motif excerpt deduplication and repair for position drift after article edits.

### Changed

- Updated the Windows app display name, window title, installer name, Tauri identifier, package metadata, README, user guides, TODO, and public release copy.
- Updated release assets to use English filenames: `LivingToTell_0.1.7_x64-setup.exe` and `LivingToTell_0.1.7_x64_zh-CN.msi`.
- Renamed the packaged backend sidecar to `living-to-tell-backend`.
- Kept old Writer data and preferences as compatibility sources; no old user data is deleted.
- Public AI chat UI now focuses on article context instead of exposing unfinished global or collection chat entry points.
- AI card types now focus on `style`, `character`, and `scene`; the old public `setting` card type is removed.
- Gemini configurations that use `sk-...` proxy keys with a custom base URL now automatically use the gateway-compatible `/v1/chat/completions` transport while staying configured as Gemini.
- OpenCode requests run through the same AI provider path as polish, chat, and AI Card generation, and report provider/model/transport/cost diagnostics.
- Reference-library line statistics now use non-empty paragraph counts where appropriate.
- Article list filtering now supports single-tag filtering combined with keyword search.
- The motif attach flow now uses right-click selection instead of opening automatically after a left-click selection.

### Fixed

- Removed the bad tracked `app-icon.png` file that contained HTML instead of image bytes.
- Updated installer process cleanup so upgrades can close both old Writer processes and new Living to Tell processes before copying files.
- Hid the installer/uninstaller app-data deletion option so uninstalling does not offer a dangerous one-click path to writing data.
- Fixed old backend sidecar leftovers by tightening process cleanup and adding backend capability/version checks.
- Replaced raw `Not Found` and `Failed to fetch` surfaces with user-facing backend connection/version messages.
- Sanitized AI provider HTML errors so 403 pages and raw proxy responses are not shown in the UI.
- Fixed Gemini proxy 403 failures caused by routing custom-base `sk-...` keys through Gemini-native endpoints.
- Fixed article position restore by using a reliable outer-scroll writing surface and separate read/edit position records.
- Fixed article epigraph saving so leading full-width indentation in the first body paragraph is preserved.
- Fixed context tag switching in the reference library.
- Fixed backend processes lingering after app exit.
- Fixed motif star map density controls, local graph label overlap, duplicate bottom index, and English `Motif not found` errors.
- Fixed motif excerpt deletion semantics so removing from one motif does not delete the same excerpt from other motifs.
- Fixed motif lookup after source-position drift so the same sentence reopens existing motif chips and historical duplicate anchors merge automatically.
- Fixed AI settings and AI card generation to report provider/model/transport diagnostics without exposing API keys.

### Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- Real OpenCode probe through the app settings API with `opencode/deepseek-v4-flash-free`.
- Real gated Gemini probe with local configuration: `WRITER_RUN_LIVE_AI_TEST=1 python -m pytest tests\services\ai\test_gemini_provider.py::test_live_gemini_config_can_answer_minimal_probe -q`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

### Release artifacts

- `LivingToTell_0.1.7_x64-setup.exe`
  - SHA256: `FF6A5E37F45E0CACD07E6E41EB3AF54A1B1CC4BB803029944269DC8C1F20E78F`
- `LivingToTell_0.1.7_x64_zh-CN.msi`
  - SHA256: `BD1DB35B44477C8BF81DA4ED021D8F2EAAA78EC4F471FC5038A61C7D0EF1A4F5`

## 0.1.6 - Public Preview Final Fixes (2026-06-16)

### Added

- Added public screenshot assets for article writing, focus mode, collections, reference library, AI, and settings.
- Added a public-facing README structure with screenshots, features, download, quick start, AI setup, privacy, development, and roadmap sections.
- Added repeatable screenshot capture script at `tauri-mvp/scripts/capture-screenshots.cjs`.
- Added release notes for `tauri-v0.1.6`.
- Added article notes in the article context pane for reminders, fragments, and next-step ideas.
- Added focused controls for polish, rewrite, expand, and continue AI tools.
- Added per-tool AI writing presets.
- Added manual article-note and reference attachments for AI tool context.
- Added explicit AI writeback actions: replace, insert, copy, and return to the source article.

### Changed

- Changed GitHub Actions workflows to manual-only `workflow_dispatch` triggers.
- Public preview now forces light mode and hides dark mode UI entry points until the full dark theme is polished.
- Updated version metadata to `0.1.6`.
- Clarified that preview releases are built locally and uploaded manually instead of using automatic GitHub Actions builds.
- AI tool results now default to review-first behavior instead of automatic manuscript changes.
- Public TODO and README roadmap now reflect completed article notes, focused AI tools, and safe writeback.

### Fixed

- Fixed the Tauri close confirmation event by switching from the custom-protocol-like event name to `writer-confirm-close`.
- Fixed the close preference prompt so `ask`, `tray`, and `exit` paths are reachable from the window close button.
- Improved the tray-unavailable fallback so the prompt shows a clear message and lets the user confirm direct exit.
- Fixed the Windows title-bar close button so it no longer depends on the web UI receiving a close event.
- Fixed article AI writeback so selected body ranges can be replaced or appended without rewriting the whole article.

### Verification

- `python -m pytest`
- `python -m pytest tests\test_tauri_mvp_api.py -q`
- `npm test`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

## 0.1.5 - Public Polish and AI Settings (2026-06-16)

### Added

- Added a cleaner focus mode for articles that hides surrounding panels and keeps only the writing area.
- Added a real "Start Writing" action on empty date pages, creating a new article for the selected date.
- Added Reference Library copy actions for passage text and full source citation.
- Added backend-backed AI settings for OpenAI-compatible providers, Codex local auth, Gemini API, local Gemini config, and Gemini CLI / OAuth.
- Added AI credential status and config validation without saving raw API keys.

### Changed

- Removed implementation-oriented epigraph helper copy from the public article UI.
- Removed unavailable Claude provider choices from the public settings UI.
- Updated public documentation for focus mode, reference copying, AI settings, and date writing actions.

### Verification

- `python -m pytest`
- `npm test`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`

## 0.1.4 - Writing and AI MVP Completion (2026-06-16)

### Added

- Added full daily quote display with a link from Dates to the matching Reference Library passage.
- Added Reference Library organization by source book or usage type, with persisted group mode and deep-link selection.
- Added article epigraph editing: detected opening epigraphs appear in a separate editing area while staying stored as plain text.
- Added single-article export for TXT, Markdown, and DOCX.
- Added AI Tool / Chat tabs. Chat supports one ongoing conversation for global, each article, and each collection.
- Added article and collection shortcuts into scoped AI Chat.
- Added AI Card filtering by type, source, keyword, and sort order.
- Added first-run close behavior choices: ask, minimize to tray, or exit directly.

### Fixed

- Moved focus-mode exit control to the top-right safe area so it no longer overlaps article titles.
- Preserved existing Writer SQLite data access in the Tauri backend while expanding article, collection, reference, and AI endpoints.
- Prevented article/collection AI chat from creating empty-scope conversations.

### Verification

- `python -m pytest tests\test_tauri_mvp_api.py`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`

## 0.1.3 - Packaged API Fix (2026-06-15)

### Fixed

- Fixed the packaged Python sidecar returning `404 Not Found` for article, collection, library, AI, backup, and settings-related API routes.
- Fixed the release package so Tauri reads the existing Qt Writer database instead of showing an empty app surface.

### Verification

- Direct sidecar smoke: `/api/articles` returned existing articles from `%APPDATA%\Writer\Writer\writer.sqlite3`.
- Direct sidecar smoke: `/api/library/references` returned existing reference passages from the same database.

## 0.1.2 - UI and Localization Polish (2026-06-15)

### Fixed

- Fixed article find/replace so previous/next navigation selects the matching text in the editor instead of acting like a placeholder control.
- Removed remaining visible English from key Chinese-mode screens: AI, dates, library, backup, settings, command palette, quick capture, and find/replace.
- Reworked several buttons and empty states so actions are either wired, clearly disabled with an explanation, or removed.

### Changed

- Simplified the AI workspace copy and result actions for the current Tauri MVP surface.
- Updated public-facing documentation to describe articles, article collections, AI Cards, reference library, backup, and settings without legacy Work terminology.

### Verification

- `npm run build`
- `python -m pytest`

## 0.1.1 - Stabilization Pass (2026-06-14)

### Fixed

- Fixed AI Card API crashes caused by mismatched repository methods and fields.
- Fixed built-in AI Card samples so they are seeded as normal editable cards without duplicating on every launch.
- Replaced legacy Work-based collection endpoints in the Tauri UI flow with article-based collection endpoints.
- Fixed collection creation, article add/remove/reorder, entry membership lookup, and collection export endpoints.
- Fixed release sidecar port discovery: Tauri now reads `WRITER_PORT=...` from the backend and exposes the correct API base URL to the frontend.
- Removed static `localhost:8000` usage from active frontend API clients.

### Changed

- Rebuilt the Collections page as an article reading/order workspace with shelf, article cards, preview, export, and batch add.
- Added article right-context membership display and "add to collection" action.
- Changed the article right context pane from a draggable-width panel into a persisted show/hide panel.
- Improved Chinese localization for navigation, article context, collections, AI Cards, empty states, and action labels.
- Added visible error/notice states to AI Cards instead of silent console failures.

### Verification

- `python -m pytest tests\storage\test_article_collections.py tests\services\test_article_collection_export.py tests\test_tauri_mvp_api.py`
- `npm run build`
- `cargo check`

## 0.1.0 - Initial MVP (2026-06-13)

- Tauri shell with Vue frontend and FastAPI backend sidecar.
- Articles, Dates, Collections, AI, Library, AI Cards, Backup, and Settings surfaces.
- Shared Writer SQLite data layer.
