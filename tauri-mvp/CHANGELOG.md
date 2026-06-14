# Writer Tauri MVP Changelog

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
- Added article right-context membership display and “add to collection” action.
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
