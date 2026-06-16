# Writer Tauri Preview Changelog

## 0.1.6 - Public Preview Final Fixes (2026-06-16)

### Added

- Added public screenshot assets for article writing, focus mode, collections, reference library, AI, and settings.
- Added a public-facing README structure with screenshots, features, download, quick start, AI setup, privacy, development, and roadmap sections.
- Added repeatable screenshot capture script at `tauri-mvp/scripts/capture-screenshots.cjs`.
- Added release notes for `tauri-v0.1.6`.

### Changed

- Changed GitHub Actions workflows to manual-only `workflow_dispatch` triggers.
- Public preview now forces light mode and hides dark mode UI entry points until the full dark theme is polished.
- Updated version metadata to `0.1.6`.
- Clarified that preview releases are built locally and uploaded manually instead of using automatic GitHub Actions builds.

### Fixed

- Fixed the Tauri close confirmation event by switching from the custom-protocol-like event name to `writer-confirm-close`.
- Fixed the close preference prompt so `ask`, `tray`, and `exit` paths are reachable from the window close button.
- Improved the tray-unavailable fallback so the prompt shows a clear message and lets the user confirm direct exit.

### Verification

- Pending for final release pass:
  - `D:\anaconda\envs\writer\python.exe -m pytest`
  - `npm test`
  - `npm run build`
  - `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
  - `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

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

- `D:\anaconda\envs\writer\python.exe -m pytest`
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

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py`
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
- `D:\anaconda\envs\writer\python.exe -m pytest`

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

- `D:\anaconda\envs\writer\python.exe -m pytest tests\storage\test_article_collections.py tests\services\test_article_collection_export.py tests\test_tauri_mvp_api.py`
- `npm run build`
- `cargo check`

## 0.1.0 - Initial MVP (2026-06-13)

- Tauri shell with Vue frontend and FastAPI backend sidecar.
- Articles, Dates, Collections, AI, Library, AI Cards, Backup, and Settings surfaces.
- Shared Writer SQLite data layer.
